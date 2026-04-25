"""
Tests for ImageService.

Tests cover local/remote tag fetching, error handling, and semver filtering.
"""

from unittest.mock import MagicMock, call, patch

import httpx

from hyper_trader_api.services.image_service import (
    GHCR_TAGS_URL,
    GHCR_TOKEN_URL,
    ImageService,
)


def _make_token_response(token: str = "anon-token") -> MagicMock:
    """Helper: mock httpx response returning a GHCR anonymous token."""
    resp = MagicMock()
    resp.json.return_value = {"token": token}
    return resp


def _make_tags_response(tags: list[str]) -> MagicMock:
    """Helper: mock httpx response returning a tag list."""
    resp = MagicMock()
    resp.json.return_value = {"name": "andreinasui/hyper-trader", "tags": tags}
    return resp


class TestImageServiceGetImageVersions:
    """Tests for ImageService.get_image_versions()."""

    def test_returns_local_and_remote_tags(self):
        """Should return both local and remote tags."""
        with patch("hyper_trader_api.services.image_service.get_runtime") as mock_get_runtime:
            mock_runtime = MagicMock()
            mock_runtime.list_local_image_tags.return_value = ["0.4.3", "0.4.2"]
            mock_get_runtime.return_value = mock_runtime

            with patch("hyper_trader_api.services.image_service.httpx.get") as mock_get:
                mock_get.side_effect = [
                    _make_token_response(),
                    _make_tags_response(["0.4.4", "0.4.3"]),
                ]

                service = ImageService()
                result = service.get_image_versions()

                assert result.latest_local == "0.4.3"
                assert result.all_local == ["0.4.3", "0.4.2"]
                assert result.latest_remote == "0.4.4"
                assert result.all_remote == ["0.4.4", "0.4.3"]

    def test_returns_none_when_no_local_tags(self):
        """With no local tags, latest_local should be None."""
        with patch("hyper_trader_api.services.image_service.get_runtime") as mock_get_runtime:
            mock_runtime = MagicMock()
            mock_runtime.list_local_image_tags.return_value = []
            mock_get_runtime.return_value = mock_runtime

            with patch("hyper_trader_api.services.image_service.httpx.get") as mock_get:
                mock_get.side_effect = [
                    _make_token_response(),
                    _make_tags_response([]),
                ]

                service = ImageService()
                result = service.get_image_versions()

                assert result.latest_local is None
                assert result.all_local == []
                assert result.latest_remote is None
                assert result.all_remote == []

    def test_returns_none_when_no_remote_tags(self):
        """When remote fetch returns empty, latest_remote should be None."""
        with patch("hyper_trader_api.services.image_service.get_runtime") as mock_get_runtime:
            mock_runtime = MagicMock()
            mock_runtime.list_local_image_tags.return_value = ["0.4.3"]
            mock_get_runtime.return_value = mock_runtime

            with patch("hyper_trader_api.services.image_service.httpx.get") as mock_get:
                mock_get.side_effect = [
                    _make_token_response(),
                    _make_tags_response([]),
                ]

                service = ImageService()
                result = service.get_image_versions()

                assert result.latest_local == "0.4.3"
                assert result.latest_remote is None
                assert result.all_remote == []


class TestImageServiceFetchRemoteTags:
    """Tests for ImageService._fetch_remote_tags()."""

    def test_fetches_token_then_tags(self):
        """Should first fetch anonymous token, then use it to list tags."""
        with patch("hyper_trader_api.services.image_service.get_runtime") as mock_get_runtime:
            mock_runtime = MagicMock()
            mock_get_runtime.return_value = mock_runtime

            with patch("hyper_trader_api.services.image_service.httpx.get") as mock_get:
                mock_get.side_effect = [
                    _make_token_response("my-anon-token"),
                    _make_tags_response(["0.4.4", "0.4.3", "0.4.2"]),
                ]

                service = ImageService()
                result = service._fetch_remote_tags()

                assert result == ["0.4.4", "0.4.3", "0.4.2"]
                assert mock_get.call_count == 2
                assert mock_get.call_args_list[0] == call(GHCR_TOKEN_URL, timeout=10.0)
                assert mock_get.call_args_list[1][0][0] == GHCR_TAGS_URL
                assert mock_get.call_args_list[1][1]["headers"] == {
                    "Authorization": "Bearer my-anon-token"
                }

    def test_filters_non_semver_tags(self):
        """Should filter out non-semver tags like branch names."""
        with patch("hyper_trader_api.services.image_service.get_runtime") as mock_get_runtime:
            mock_runtime = MagicMock()
            mock_get_runtime.return_value = mock_runtime

            with patch("hyper_trader_api.services.image_service.httpx.get") as mock_get:
                mock_get.side_effect = [
                    _make_token_response(),
                    _make_tags_response(
                        ["0.4.4", "main", "0.4.3", "some-branch", "0.4.2", "v0.4.2", "latest"]
                    ),
                ]

                service = ImageService()
                result = service._fetch_remote_tags()

                assert result == ["0.4.4", "0.4.3", "0.4.2"]

    def test_sorts_tags_by_semver_descending(self):
        """Should sort tags by semver tuple, not string comparison."""
        with patch("hyper_trader_api.services.image_service.get_runtime") as mock_get_runtime:
            mock_runtime = MagicMock()
            mock_get_runtime.return_value = mock_runtime

            with patch("hyper_trader_api.services.image_service.httpx.get") as mock_get:
                mock_get.side_effect = [
                    _make_token_response(),
                    _make_tags_response(["0.4.3", "0.10.0", "0.4.12", "0.4.2"]),
                ]

                service = ImageService()
                result = service._fetch_remote_tags()

                # 0.10.0 > 0.4.12 > 0.4.3 > 0.4.2
                assert result == ["0.10.0", "0.4.12", "0.4.3", "0.4.2"]

    def test_handles_token_fetch_http_error(self):
        """Should return empty list when token fetch fails."""
        with patch("hyper_trader_api.services.image_service.get_runtime") as mock_get_runtime:
            mock_runtime = MagicMock()
            mock_get_runtime.return_value = mock_runtime

            with patch("hyper_trader_api.services.image_service.httpx.get") as mock_get:
                token_resp = MagicMock()
                token_resp.raise_for_status.side_effect = httpx.HTTPStatusError(
                    "401 Unauthorized",
                    request=MagicMock(),
                    response=MagicMock(status_code=401),
                )
                mock_get.return_value = token_resp

                service = ImageService()
                result = service._fetch_remote_tags()

                assert result == []

    def test_handles_tags_fetch_http_error(self):
        """Should return empty list when tags fetch fails."""
        with patch("hyper_trader_api.services.image_service.get_runtime") as mock_get_runtime:
            mock_runtime = MagicMock()
            mock_get_runtime.return_value = mock_runtime

            with patch("hyper_trader_api.services.image_service.httpx.get") as mock_get:
                tags_resp = MagicMock()
                tags_resp.raise_for_status.side_effect = httpx.HTTPStatusError(
                    "404 Not Found",
                    request=MagicMock(),
                    response=MagicMock(status_code=404),
                )
                mock_get.side_effect = [_make_token_response(), tags_resp]

                service = ImageService()
                result = service._fetch_remote_tags()

                assert result == []

    def test_handles_network_exception_gracefully(self):
        """Should return empty list on network exception."""
        with patch("hyper_trader_api.services.image_service.get_runtime") as mock_get_runtime:
            mock_runtime = MagicMock()
            mock_get_runtime.return_value = mock_runtime

            with patch("hyper_trader_api.services.image_service.httpx.get") as mock_get:
                mock_get.side_effect = httpx.ConnectError("Connection failed")

                service = ImageService()
                result = service._fetch_remote_tags()

                assert result == []

    def test_handles_json_parse_error_gracefully(self):
        """Should return empty list on JSON parse error."""
        with patch("hyper_trader_api.services.image_service.get_runtime") as mock_get_runtime:
            mock_runtime = MagicMock()
            mock_get_runtime.return_value = mock_runtime

            with patch("hyper_trader_api.services.image_service.httpx.get") as mock_get:
                bad_resp = MagicMock()
                bad_resp.json.side_effect = ValueError("Invalid JSON")
                mock_get.return_value = bad_resp

                service = ImageService()
                result = service._fetch_remote_tags()

                assert result == []

    def test_handles_null_tags_field(self):
        """Should handle response where tags field is null."""
        with patch("hyper_trader_api.services.image_service.get_runtime") as mock_get_runtime:
            mock_runtime = MagicMock()
            mock_get_runtime.return_value = mock_runtime

            with patch("hyper_trader_api.services.image_service.httpx.get") as mock_get:
                tags_resp = MagicMock()
                tags_resp.json.return_value = {"name": "andreinasui/hyper-trader", "tags": None}
                mock_get.side_effect = [_make_token_response(), tags_resp]

                service = ImageService()
                result = service._fetch_remote_tags()

                assert result == []

    def test_deduplicates_tags(self):
        """Should deduplicate tags if registry returns duplicates."""
        with patch("hyper_trader_api.services.image_service.get_runtime") as mock_get_runtime:
            mock_runtime = MagicMock()
            mock_get_runtime.return_value = mock_runtime

            with patch("hyper_trader_api.services.image_service.httpx.get") as mock_get:
                mock_get.side_effect = [
                    _make_token_response(),
                    _make_tags_response(["0.4.4", "0.4.3", "0.4.3", "0.4.2"]),
                ]

                service = ImageService()
                result = service._fetch_remote_tags()

                assert result == ["0.4.4", "0.4.3", "0.4.2"]
