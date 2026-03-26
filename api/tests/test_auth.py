"""
Authentication endpoint tests for self-hosted local auth.

These tests target the planned self-hosted auth system with username/password
authentication, not the old email/refresh-token design.
"""

import pytest


def test_placeholder_baseline_note():
    """
    Baseline note: The previous auth tests targeted a completely different
    authentication system (email/password with refresh tokens) that was never
    implemented. The actual auth router uses Privy-based authentication.

    This test file will be replaced with tests for the new self-hosted
    local auth system during Task 5 of the self-hosted v1 implementation plan.

    Target endpoints for self-hosted auth:
    - GET /api/v1/auth/setup-status
    - POST /api/v1/auth/bootstrap
    - POST /api/v1/auth/login
    - GET /api/v1/auth/me
    - POST /api/v1/auth/logout
    """
    assert True


class TestSetupStatus:
    """Tests for GET /api/v1/auth/setup-status - to be implemented in Task 5"""

    @pytest.mark.skip(reason="Pending implementation in Task 5")
    def test_setup_status_returns_uninitialized(self):
        pass


class TestBootstrap:
    """Tests for POST /api/v1/auth/bootstrap - to be implemented in Task 5"""

    @pytest.mark.skip(reason="Pending implementation in Task 5")
    def test_bootstrap_creates_admin_user(self):
        pass


class TestLogin:
    """Tests for POST /api/v1/auth/login - to be implemented in Task 5"""

    @pytest.mark.skip(reason="Pending implementation in Task 5")
    def test_login_with_valid_credentials(self):
        pass


class TestGetMe:
    """Tests for GET /api/v1/auth/me - to be implemented in Task 5"""

    @pytest.mark.skip(reason="Pending implementation in Task 5")
    def test_get_me_authenticated(self):
        pass
