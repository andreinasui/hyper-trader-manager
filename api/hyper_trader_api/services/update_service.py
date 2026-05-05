from __future__ import annotations

import logging
import os
import re
import socket
import tempfile
from collections.abc import Iterable
from pathlib import Path

import docker.errors
import httpx
from packaging.version import InvalidVersion, Version

from hyper_trader_api.schemas.update import ServiceStatus, ServiceStatusEntry, UpdateStateFile

log = logging.getLogger(__name__)

STATE_FILENAME = "update-state.json"
TAG_RE = re.compile(r"^v(\d+\.\d+\.\d+)$")


def _find_volume_name_for_path(client, container_path: str) -> str | None:
    """Return the Docker volume name mounted at *container_path* in this container.

    Docker Compose prefixes volume names with the project name (e.g.
    ``hyper-trader_update-state``).  If we hard-code the short name
    (``update-state``) when spawning the helper, Docker creates a *new*,
    unrelated volume instead of reusing the one the API is already using.
    Self-inspection via the Docker socket is the only reliable way to get the
    correct prefixed name regardless of project name or install path.
    """
    try:
        # In Docker the container hostname is set to the (short) container ID.
        container = client.containers.get(socket.gethostname())
        for mount in container.attrs.get("Mounts", []):
            if mount.get("Type") == "volume" and mount.get("Destination") == container_path:
                name: str | None = mount.get("Name")
                return name
    except Exception:
        log.warning(
            "Could not resolve volume name for path %s via self-inspection", container_path
        )
    return None


def _entry_for(client, name: str) -> ServiceStatusEntry:
    try:
        c = client.containers.get(name)
    except docker.errors.NotFound:
        return ServiceStatusEntry()
    state = c.attrs.get("State", {})
    health = state.get("Health", {}).get("Status")
    return ServiceStatusEntry(
        image=c.attrs.get("Config", {}).get("Image"),
        running=state.get("Status") == "running",
        healthy=health == "healthy",
    )


def parse_tags(tags: Iterable[dict]) -> list[str]:
    """Filter to stable vX.Y.Z tags and return sorted descending by semver."""
    out: list[tuple[Version, str]] = []
    for t in tags:
        name = t.get("name", "")
        m = TAG_RE.match(name)
        if not m:
            continue
        try:
            v = Version(m.group(1))
        except InvalidVersion:
            continue
        out.append((v, name))
    out.sort(key=lambda x: x[0], reverse=True)
    return [name for _, name in out]


def is_newer(latest: str, current: str) -> bool:
    """True iff latest > current under semver."""
    try:
        return Version(latest) > Version(current)
    except InvalidVersion:
        return False


class UpdateService:
    def __init__(
        self,
        state_dir: Path | str,
        compose_project_dir: Path | str | None,
    ) -> None:
        self.state_dir = Path(state_dir)
        self.compose_project_dir = Path(compose_project_dir) if compose_project_dir else None

    @property
    def configured(self) -> bool:
        return self.compose_project_dir is not None

    @property
    def state_file(self) -> Path:
        return self.state_dir / STATE_FILENAME

    def read_state(self) -> UpdateStateFile:
        if not self.state_file.exists():
            return UpdateStateFile()
        try:
            return UpdateStateFile.model_validate_json(self.state_file.read_text())
        except Exception:
            log.exception("Corrupt update-state.json, returning defaults")
            return UpdateStateFile()

    def write_state(self, state: UpdateStateFile) -> None:
        self.state_dir.mkdir(parents=True, exist_ok=True)
        # atomic write
        with tempfile.NamedTemporaryFile(
            "w", dir=self.state_dir, delete=False, encoding="utf-8"
        ) as tmp:
            tmp.write(state.model_dump_json(indent=2))
            tmp_name = tmp.name
        os.replace(tmp_name, self.state_file)

    def fetch_latest_tag(self, *, repo: str, timeout: float = 10.0) -> str | None:
        url = f"https://api.github.com/repos/{repo}/tags?per_page=100"
        try:
            with httpx.Client(timeout=timeout) as client:
                resp = client.get(url, headers={"Accept": "application/vnd.github+json"})
                resp.raise_for_status()
                tags = parse_tags(resp.json())
        except (httpx.HTTPError, ValueError):
            log.warning("Failed to fetch GitHub tags for %s", repo, exc_info=True)
            return None
        return tags[0] if tags else None

    def spawn_helper(
        self,
        *,
        client,  # docker.DockerClient
        helper_image: str,
        old_api_image: str,
        old_web_image: str,
        new_api_image: str,
        new_web_image: str,
    ) -> None:
        if not self.compose_project_dir:
            raise RuntimeError("update system not configured")
        project_dir = str(self.compose_project_dir)

        # Discover the actual Docker volume name mounted at state_dir.  Compose
        # prefixes volumes with the project name (e.g. "hyper-trader_update-state"),
        # so we must not hard-code the short name or Docker will create a second,
        # unrelated volume and the helper will write completion state there while
        # the API keeps reading the original (still-"updating") volume.
        state_dir_str = str(self.state_dir)
        state_volume = _find_volume_name_for_path(client, state_dir_str)
        if state_volume is None:
            # Fallback: use the short name (works in dev / non-Compose setups).
            log.warning(
                "Could not discover volume name for %s; falling back to bare 'update-state'",
                state_dir_str,
            )
            state_volume = "update-state"

        client.containers.run(
            image=helper_image,
            name="hyper-trader-update-helper",
            detach=True,
            remove=True,
            environment={
                "COMPOSE_PROJECT_DIR": project_dir,
                "OLD_API_IMAGE": old_api_image,
                "OLD_WEB_IMAGE": old_web_image,
                "NEW_API_IMAGE": new_api_image,
                "NEW_WEB_IMAGE": new_web_image,
            },
            volumes={
                "/var/run/docker.sock": {"bind": "/var/run/docker.sock", "mode": "rw"},
                project_dir: {"bind": project_dir, "mode": "rw"},
                state_volume: {"bind": state_dir_str, "mode": "rw"},
            },
        )

    def collect_service_status(self, *, client) -> ServiceStatus:
        return ServiceStatus(
            api=_entry_for(client, "hypertrader-api"),
            web=_entry_for(client, "hypertrader-web"),
        )
