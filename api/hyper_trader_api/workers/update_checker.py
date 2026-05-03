# api/hyper_trader_api/workers/update_checker.py
"""Background worker that polls GitHub for new releases."""

from __future__ import annotations

import asyncio
import logging
from datetime import UTC, datetime

from hyper_trader_api.services.update_service import UpdateService, is_newer

log = logging.getLogger(__name__)


class UpdateChecker:
    """Async background worker that polls GitHub tags and updates state."""

    def __init__(
        self,
        *,
        service: UpdateService,
        repo: str,
        interval: float = 3600.0,
    ) -> None:
        self._service = service
        self._repo = repo
        self._interval = interval
        self._running = False

    @property
    def service(self) -> UpdateService:
        return self._service

    async def run_once(self) -> None:
        """Perform one check cycle."""
        state = self._service.read_state()

        # Don't interrupt an in-flight update
        if state.status == "updating":
            log.debug("update in progress, skipping check")
            return

        latest = self._service.fetch_latest_tag(repo=self._repo)
        state.last_checked = datetime.now(UTC)

        if latest is None:
            log.warning("Could not fetch latest tag for %s", self._repo)
            self._service.write_state(state)
            return

        state.latest_version = latest
        if state.current_version and is_newer(
            latest=latest.lstrip("v"), current=state.current_version.lstrip("v")
        ):
            log.info("New version available: %s (current: %s)", latest, state.current_version)
        else:
            log.debug("No new version. latest=%s current=%s", latest, state.current_version)

        self._service.write_state(state)

    async def start(self) -> None:
        """Run the check loop until stop() is called."""
        self._running = True
        log.info("UpdateChecker started (interval=%ss, repo=%s)", self._interval, self._repo)
        while self._running:
            try:
                await self.run_once()
            except Exception:
                log.exception("UpdateChecker run_once failed")
            await asyncio.sleep(self._interval)

    def stop(self) -> None:
        """Signal the loop to exit."""
        self._running = False
        log.info("UpdateChecker stopped")
