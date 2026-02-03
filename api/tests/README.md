# HyperTrader API Tests

**Mock-based test suite** for the HyperTrader API - NO real database or SQLite required.

## Overview

All tests use `unittest.mock` to mock database sessions, services, and external dependencies. This approach:
- ✅ Runs fast (all 64 tests in ~0.2 seconds)
- ✅ No database setup required
- ✅ No external dependencies needed
- ✅ Tests business logic in isolation
- ✅ 78% code coverage

## Test Structure

```
api/tests/
├── __init__.py
├── conftest.py              # Pytest fixtures and mocked app setup
├── test_auth.py             # Authentication endpoint tests
├── test_auth_service.py     # AuthService unit tests
├── test_jwt_service.py      # JWTService unit tests
└── test_traders.py          # Trader endpoint tests
```

## Test Coverage

### Authentication Tests (test_auth.py)
- ✅ User registration (password & API key modes)
- ✅ Login with valid/invalid credentials
- ✅ JWT token refresh
- ✅ Get current user
- ✅ Logout and token revocation
- **15 tests, 100% coverage**

### Auth Service Tests (test_auth_service.py)
- ✅ User registration logic
- ✅ Password authentication
- ✅ API key generation and validation
- **12 tests, 100% coverage**

### JWT Service Tests (test_jwt_service.py)
- ✅ Access token creation and verification
- ✅ Refresh token creation and verification
- ✅ Token revocation
- ✅ Expired token cleanup
- **17 tests, 95% coverage**

### Trader Tests (test_traders.py)
- ✅ Create trader (valid/invalid data)
- ✅ List traders
- ✅ Get trader details
- ✅ Update trader configuration
- ✅ Delete trader
- ✅ Restart trader
- ✅ Get trader status
- ✅ Get trader logs
- **20 tests, 77% coverage**

## Running Tests

### Run all tests
```bash
cd /home/andrei/Projects/hyper-trader-infra/api
just test
```

### Run with verbose output
```bash
just test -v
```

### Run with coverage
```bash
just test-cov
```

### Run specific test file
```bash
uv run pytest tests/test_auth.py -v
```

### Run specific test
```bash
uv run pytest tests/test_auth.py::TestLogin::test_login_success -v
```

## Mock Strategy

### Database Mocking
- Database sessions are mocked using `MagicMock()`
- No actual database connection is established
- Query results are mocked to return test data

### Service Mocking
- Service methods are patched at the router level
- Example: `@patch("api.routers.auth.AuthService.register_user")`
- Allows testing HTTP layer independently from business logic

### Authentication Mocking
- JWT middleware is mocked for protected endpoints
- Example: `@patch("api.middleware.jwt_auth.get_current_user_from_jwt")`
- Tests can simulate authenticated/unauthenticated requests

## Example Test

```python
@patch("api.middleware.jwt_auth.get_current_user_from_jwt")
@patch("api.routers.traders.TraderService")
def test_create_trader_success(self, mock_service_class, mock_get_user, client, mock_user, mock_trader):
    # Setup mocks
    mock_get_user.return_value = mock_user
    mock_service = MagicMock()
    mock_service.create_trader.return_value = mock_trader
    mock_service_class.return_value = mock_service

    # Make request
    response = client.post(
        "/api/v1/traders/",
        headers={"Authorization": "Bearer valid_token"},
        json={
            "wallet_address": "0x1234567890123456789012345678901234567890",
            "private_key": "0x1234567890123456789012345678901234567890123456789012345678901234",
            "config": {"name": "Test Trader", "exchange": "hyperliquid"}
        }
    )

    # Assertions
    assert response.status_code == 201
    mock_service.create_trader.assert_called_once()
```

## Fixtures (conftest.py)

### `client`
- TestClient with mocked database
- Use in tests that need to make HTTP requests

### `mock_db`
- Mocked SQLAlchemy session
- Use for direct service testing

### `mock_user`
- Pre-configured mock user object
- Includes id, email, plan_tier, etc.

### `mock_trader`
- Pre-configured mock trader object
- Includes wallet address, K8s name, status, etc.

### `auth_headers`
- Authorization headers with mock token
- Use for authenticated requests

## Coverage Report

```
Name                         Coverage
----------------------------------------------------------
services/auth_service.py     100%
services/jwt_service.py       95%
routers/auth.py               89%
routers/traders.py            77%
----------------------------------------------------------
TOTAL                         78%
```

## Key Benefits

1. **Fast execution**: All 64 tests run in under 0.2 seconds
2. **No external dependencies**: No PostgreSQL or SQLite needed
3. **Isolated testing**: Each test is completely independent
4. **Clear failures**: Mock assertions provide clear error messages
5. **Easy debugging**: No database state to track
6. **CI/CD friendly**: No database setup in CI pipeline

## Future Improvements

- [ ] Add integration tests with real database for E2E testing
- [ ] Add tests for admin endpoints
- [ ] Add tests for K8s controller (with mocked Kubernetes client)
- [ ] Add tests for reconciliation worker
- [ ] Increase coverage of error handling paths
- [ ] Add performance/load tests

## Timezone Bug Fix

✅ **The timezone bug has already been fixed** in the codebase. All datetime objects now use `datetime.now(timezone.utc)` for UTC timestamps.
