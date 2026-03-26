"""
Token service unit tests.

These tests target the planned TokenService, not the old JWTService
with refresh token storage that was never fully implemented.
"""

import pytest


def test_placeholder_baseline_note():
    """
    Baseline note: The previous jwt_service tests imported a module
    (hyper_trader_api.services.jwt_service) that does not exist.

    This test file will be replaced with tests for TokenService
    during Task 4 of the v1 implementation plan.

    Target service: TokenService
    - create_access_token(user) -> str
    - verify_access_token(token) -> dict | None
    """
    assert True


class TestTokenService:
    """Tests for TokenService - to be implemented in Task 4"""

    @pytest.mark.skip(reason="Pending implementation in Task 4")
    def test_create_access_token_returns_string(self):
        pass

    @pytest.mark.skip(reason="Pending implementation in Task 4")
    def test_verify_access_token_with_valid_token(self):
        pass

    @pytest.mark.skip(reason="Pending implementation in Task 4")
    def test_verify_access_token_with_invalid_token(self):
        pass

    @pytest.mark.skip(reason="Pending implementation in Task 4")
    def test_verify_access_token_with_expired_token(self):
        pass
