"""
Image service for HyperTrader API.

Provides read-only image version information by combining
local Docker image data with remote GHCR registry data.
"""

import logging
import re

import httpx

from hyper_trader_api.runtime.factory import get_runtime
from hyper_trader_api.schemas.image import ImageVersionInfo

logger = logging.getLogger(__name__)

SEMVER_RE = re.compile(r"^\d+\.\d+\.\d+$")

GHCR_IMAGE_OWNER = "andreinasui"
GHCR_IMAGE_NAME = "hyper-trader"
GHCR_TOKEN_URL = (
    f"https://ghcr.io/token?service=ghcr.io"
    f"&scope=repository:{GHCR_IMAGE_OWNER}/{GHCR_IMAGE_NAME}:pull"
)
GHCR_TAGS_URL = f"https://ghcr.io/v2/{GHCR_IMAGE_OWNER}/{GHCR_IMAGE_NAME}/tags/list"


def _semver_key(tag: str) -> tuple[int, int, int]:
    """Parse semver tag into sortable tuple."""
    a, b, c = tag.split(".")
    return (int(a), int(b), int(c))


class ImageService:
    """
    Service for querying image version information.

    Combines local Docker image data with remote GHCR data.
    All operations are read-only — no image pulls or updates.
    """

    def __init__(self) -> None:
        self.runtime = get_runtime()

    def get_image_versions(self) -> ImageVersionInfo:
        """
        Get local and remote image version information.

        Returns:
            ImageVersionInfo with local and remote version data.
        """
        # Local tags (always available from Docker daemon)
        local_tags = self.runtime.list_local_image_tags()
        latest_local = local_tags[0] if local_tags else None

        # Remote tags from public GHCR via Docker Registry v2 API
        remote_tags = self._fetch_remote_tags()
        latest_remote = remote_tags[0] if remote_tags else None

        return ImageVersionInfo(
            latest_local=latest_local,
            all_local=local_tags,
            latest_remote=latest_remote,
            all_remote=remote_tags,
        )

    def _fetch_remote_tags(self) -> list[str]:
        """
        Fetch available image tags from GHCR using the Docker Registry v2 API.

        Uses anonymous token auth which works for public repositories without
        any credentials.

        Returns:
            List of semver tags sorted descending (newest first).
            Returns [] on any error (network, parse failures).
        """
        try:
            # Step 1: obtain an anonymous pull token
            token_response = httpx.get(GHCR_TOKEN_URL, timeout=10.0)
            token_response.raise_for_status()
            token = token_response.json()["token"]

            # Step 2: list tags using the Registry v2 API
            tags_response = httpx.get(
                GHCR_TAGS_URL,
                headers={"Authorization": f"Bearer {token}"},
                timeout=10.0,
            )
            tags_response.raise_for_status()
            all_tags: list[str] = tags_response.json().get("tags", []) or []
        except Exception as e:
            logger.warning(f"Failed to fetch remote image tags: {e}")
            return []

        semver_tags = {tag for tag in all_tags if SEMVER_RE.match(tag)}
        return sorted(semver_tags, key=_semver_key, reverse=True)
