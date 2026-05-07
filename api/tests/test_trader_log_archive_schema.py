"""
Tests for TraderLogArchiveResponse schema.

Covers:
- Field population from dict
- Security regression: file_path must NOT be in model_fields
"""

from datetime import UTC, datetime

from hyper_trader_api.schemas.trader_log_archive import TraderLogArchiveResponse

SAMPLE_DATA = {
    "id": "aaaa-bbbb-cccc-dddd",
    "trader_id": "1111-2222-3333-4444",
    "run_started_at": datetime(2026, 1, 1, 0, 0, 0, tzinfo=UTC),
    "run_ended_at": datetime(2026, 1, 1, 1, 0, 0, tzinfo=UTC),
    "file_size_bytes": 204800,
    "created_at": datetime(2026, 1, 1, 1, 0, 1, tzinfo=UTC),
}


class TestTraderLogArchiveResponse:
    """Tests for TraderLogArchiveResponse Pydantic schema."""

    def test_fields_populate_from_dict(self) -> None:
        """All expected fields are populated when constructed from a dict."""
        schema = TraderLogArchiveResponse(**SAMPLE_DATA)

        assert schema.id == "aaaa-bbbb-cccc-dddd"
        assert schema.trader_id == "1111-2222-3333-4444"
        assert schema.run_started_at == datetime(2026, 1, 1, 0, 0, 0, tzinfo=UTC)
        assert schema.run_ended_at == datetime(2026, 1, 1, 1, 0, 0, tzinfo=UTC)
        assert schema.file_size_bytes == 204800
        assert schema.created_at == datetime(2026, 1, 1, 1, 0, 1, tzinfo=UTC)

    def test_file_path_not_in_model_fields(self) -> None:
        """SECURITY: file_path must not be present in the response schema."""
        assert "file_path" not in TraderLogArchiveResponse.model_fields, (
            "SECURITY REGRESSION: file_path must never be exposed in TraderLogArchiveResponse"
        )

    def test_expected_fields_present(self) -> None:
        """All required public fields are declared in the schema."""
        expected = {
            "id",
            "trader_id",
            "run_started_at",
            "run_ended_at",
            "file_size_bytes",
            "created_at",
        }
        assert expected == set(TraderLogArchiveResponse.model_fields.keys())

    def test_from_attributes_config(self) -> None:
        """Schema supports construction from ORM model attributes."""
        assert TraderLogArchiveResponse.model_config.get("from_attributes") is True
