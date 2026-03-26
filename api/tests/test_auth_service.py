"""
Local auth service unit tests.

These tests target the planned LocalAuthService, not the old AuthService
that was never fully implemented.
"""

import pytest


def test_placeholder_baseline_note():
    """
    Baseline note: The previous auth_service tests imported a module
    (hyper_trader_api.services.auth_service) that does not exist.

    This test file will be replaced with tests for LocalAuthService
    during Task 4 of the v1 implementation plan.

    Target service: LocalAuthService
    - system_initialized() -> bool
    - bootstrap_admin(username, password) -> User
    - authenticate(username, password) -> User | None
    """
    assert True


class TestLocalAuthService:
    """Tests for LocalAuthService - to be implemented in Task 4"""

    @pytest.mark.skip(reason="Pending implementation in Task 4")
    def test_system_initialized_returns_false_initially(self):
        pass

    @pytest.mark.skip(reason="Pending implementation in Task 4")
    def test_bootstrap_admin_creates_admin_user(self):
        pass

    @pytest.mark.skip(reason="Pending implementation in Task 4")
    def test_bootstrap_admin_only_once(self):
        pass

    @pytest.mark.skip(reason="Pending implementation in Task 4")
    def test_authenticate_with_valid_credentials(self):
        pass

    @pytest.mark.skip(reason="Pending implementation in Task 4")
    def test_authenticate_with_invalid_credentials(self):
        pass
