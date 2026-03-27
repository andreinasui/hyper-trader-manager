"""
Tests for SSL setup Pydantic schemas.

Covers:
- SSLStatusResponse: returned by GET /api/v1/setup/ssl-status
- SSLSetupRequest: sent to POST /api/v1/setup/ssl
- SSLSetupResponse: returned by POST /api/v1/setup/ssl
"""

from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from hyper_trader_api.schemas import SSLSetupRequest, SSLSetupResponse, SSLStatusResponse


class TestSSLStatusResponse:
    """Tests for SSLStatusResponse schema."""

    def test_ssl_not_configured(self):
        """SSLStatusResponse can represent an unconfigured state."""
        response = SSLStatusResponse(ssl_configured=False)

        assert response.ssl_configured is False
        assert response.mode is None
        assert response.domain is None
        assert response.configured_at is None

    def test_ssl_configured_with_domain_mode(self):
        """SSLStatusResponse can represent domain (Let's Encrypt) mode."""
        configured_at = datetime.now(UTC)
        response = SSLStatusResponse(
            ssl_configured=True,
            mode="domain",
            domain="trader.example.com",
            configured_at=configured_at,
        )

        assert response.ssl_configured is True
        assert response.mode == "domain"
        assert response.domain == "trader.example.com"
        assert response.configured_at == configured_at

    def test_ssl_configured_with_ip_only_mode(self):
        """SSLStatusResponse can represent ip_only (self-signed) mode."""
        response = SSLStatusResponse(
            ssl_configured=True,
            mode="ip_only",
            configured_at=datetime.now(UTC),
        )

        assert response.ssl_configured is True
        assert response.mode == "ip_only"
        assert response.domain is None

    def test_mode_only_accepts_domain_or_ip_only(self):
        """Mode must be 'domain' or 'ip_only' - rejects invalid values."""
        with pytest.raises(ValidationError):
            SSLStatusResponse(ssl_configured=True, mode="invalid_mode")

    def test_from_attributes_enabled(self):
        """SSLStatusResponse supports ORM from_attributes mode."""

        class FakeORM:
            ssl_configured = True
            mode = "ip_only"
            domain = None
            configured_at = None

        response = SSLStatusResponse.model_validate(FakeORM(), from_attributes=True)
        assert response.ssl_configured is True
        assert response.mode == "ip_only"


class TestSSLSetupRequest:
    """Tests for SSLSetupRequest schema."""

    def test_domain_mode_with_required_fields(self):
        """Domain mode requires domain and email fields."""
        request = SSLSetupRequest(
            mode="domain",
            domain="trader.example.com",
            email="admin@example.com",
        )

        assert request.mode == "domain"
        assert request.domain == "trader.example.com"
        assert request.email == "admin@example.com"

    def test_ip_only_mode_minimal(self):
        """IP-only mode can be set with just the mode field."""
        request = SSLSetupRequest(mode="ip_only")

        assert request.mode == "ip_only"
        assert request.domain is None
        assert request.email is None

    def test_mode_rejects_invalid_values(self):
        """Mode only accepts 'domain' or 'ip_only'."""
        with pytest.raises(ValidationError):
            SSLSetupRequest(mode="self_signed")

    def test_domain_pattern_valid_simple(self):
        """Valid simple domain is accepted."""
        request = SSLSetupRequest(
            mode="domain",
            domain="example.com",
            email="user@example.com",
        )
        assert request.domain == "example.com"

    def test_domain_pattern_valid_subdomain(self):
        """Valid subdomain is accepted."""
        request = SSLSetupRequest(
            mode="domain",
            domain="trader.my-app.io",
            email="user@example.com",
        )
        assert request.domain == "trader.my-app.io"

    def test_domain_pattern_rejects_bare_hostname(self):
        """Bare hostname without TLD is rejected."""
        with pytest.raises(ValidationError):
            SSLSetupRequest(mode="domain", domain="localhost", email="user@example.com")

    def test_domain_pattern_rejects_ip_address(self):
        """IP address is rejected as domain value."""
        with pytest.raises(ValidationError):
            SSLSetupRequest(mode="domain", domain="192.168.1.1", email="user@example.com")

    def test_email_validation_rejects_invalid(self):
        """Invalid email is rejected."""
        with pytest.raises(ValidationError):
            SSLSetupRequest(mode="domain", domain="example.com", email="not-an-email")

    def test_email_validation_accepts_valid(self):
        """Valid email is accepted."""
        request = SSLSetupRequest(
            mode="domain",
            domain="example.com",
            email="ops+alerts@sub.example.org",
        )
        assert request.email is not None

    def test_json_schema_has_examples(self):
        """Schema includes examples for documentation purposes."""
        schema = SSLSetupRequest.model_json_schema()
        examples = schema.get("examples") or []
        assert len(examples) >= 2

    def test_domain_and_email_are_optional_fields(self):
        """Domain and email are optional fields (not required at the Pydantic level)."""
        # This should not raise - business logic validation is in the router/service layer
        request = SSLSetupRequest(mode="domain")
        assert request.domain is None
        assert request.email is None


class TestSSLSetupResponse:
    """Tests for SSLSetupResponse schema."""

    def test_success_response(self):
        """SSLSetupResponse can represent a successful setup."""
        response = SSLSetupResponse(
            success=True,
            message="SSL configured successfully",
            redirect_url="https://trader.example.com",
        )

        assert response.success is True
        assert response.message == "SSL configured successfully"
        assert response.redirect_url == "https://trader.example.com"

    def test_failure_response(self):
        """SSLSetupResponse can represent a failed setup."""
        response = SSLSetupResponse(
            success=False,
            message="Failed to obtain Let's Encrypt certificate",
        )

        assert response.success is False
        assert response.message == "Failed to obtain Let's Encrypt certificate"
        assert response.redirect_url is None

    def test_redirect_url_is_optional(self):
        """redirect_url is optional and defaults to None."""
        response = SSLSetupResponse(success=True, message="Done")
        assert response.redirect_url is None


class TestSSLSchemasExports:
    """Tests that SSL schemas are properly exported from the schemas package."""

    def test_ssl_status_response_importable(self):
        """SSLStatusResponse is importable from the schemas package."""
        from hyper_trader_api.schemas import SSLStatusResponse as Imported

        assert Imported is SSLStatusResponse

    def test_ssl_setup_request_importable(self):
        """SSLSetupRequest is importable from the schemas package."""
        from hyper_trader_api.schemas import SSLSetupRequest as Imported

        assert Imported is SSLSetupRequest

    def test_ssl_setup_response_importable(self):
        """SSLSetupResponse is importable from the schemas package."""
        from hyper_trader_api.schemas import SSLSetupResponse as Imported

        assert Imported is SSLSetupResponse

    def test_all_ssl_schemas_in_dunder_all(self):
        """SSL schemas are listed in __all__ of the schemas package."""
        import hyper_trader_api.schemas as schemas_module

        assert "SSLStatusResponse" in schemas_module.__all__
        assert "SSLSetupRequest" in schemas_module.__all__
        assert "SSLSetupResponse" in schemas_module.__all__
