"""
Image version schemas for HyperTrader API.
"""

from pydantic import BaseModel, ConfigDict


class ImageVersionInfo(BaseModel):
    """
    Image version information for the trader image.

    Provides local and remote version data to support
    version display and update decisions in the UI.
    """

    latest_local: str | None
    """Most recent locally available tag (semver, e.g. '0.4.4'), or None if no local image."""

    all_local: list[str]
    """All locally available semver tags, sorted descending (newest first)."""

    latest_remote: str | None
    """Most recent remote tag available on GHCR, or None if unavailable (no token, network error)."""

    all_remote: list[str]
    """All remote semver tags, sorted descending. Empty if unavailable."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "latest_local": "0.4.3",
                "all_local": ["0.4.3", "0.4.2"],
                "latest_remote": "0.4.4",
                "all_remote": ["0.4.4", "0.4.3", "0.4.2"],
            }
        }
    )
