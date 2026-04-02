# HyperTrader API Tests

**Mock-based test suite** for the HyperTrader API - NO real database or Docker required.

## Overview

All tests use `unittest.mock` to mock database sessions, services, and external dependencies. This approach:
- ✅ Runs fast (all tests in under 1 second)
- ✅ No database setup required
- ✅ No Docker or Docker Swarm setup needed
- ✅ Tests business logic in isolation
- ✅ 80%+ code coverage

## Test Structure

```
api/tests/
├── __init__.py
├── conftest.py              # Pytest fixtures and mocked app setup
├── test_auth.py             # Authentication endpoint tests
├── test_auth_service.py     # AuthService unit tests
├── test_traders.py          # Trader endpoint tests
└── test_docker_runtime.py   # Docker Swarm runtime unit tests
```

## Test Coverage

### Authentication Tests (test_auth.py)
- ✅ User registration (password modes)
- ✅ Login with valid/invalid credentials
- ✅ Get current user
- ✅ Logout and session token revocation

### Auth Service Tests (test_auth_service.py)
- ✅ User registration logic
- ✅ Password authentication
- ✅ Session token generation and validation

### Trader Tests (test_traders.py)
- ✅ Create trader (valid/invalid data)
- ✅ List traders
- ✅ Get trader details
- ✅ Update trader configuration
- ✅ Delete trader
- ✅ Restart trader
- ✅ Get trader status
- ✅ Get trader logs

### Docker Runtime Tests (test_docker_runtime.py)
- ✅ Swarm initialization (auto-init if not active)
- ✅ create_trader creates Docker secret for private key
- ✅ create_trader creates Swarm service with secret attached
- ✅ remove_trader removes both service and secret
- ✅ remove_trader handles missing secret gracefully

## Running Tests

### Run all tests
```bash
cd api
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
uv run pytest tests/test_docker_runtime.py -v
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
- Example: `@patch("hyper_trader_api.routers.traders.TraderService")`
- Allows testing HTTP layer independently from business logic

### Authentication Mocking
- Session token middleware is mocked for protected endpoints
- Tests can simulate authenticated/unauthenticated requests

### Docker Mocking
- Docker client is mocked in runtime tests
- `client.secrets` and `client.services` are fully mocked
- No Docker Swarm required to run tests

## Example Test

```python
@patch("hyper_trader_api.routers.traders.TraderService")
def test_create_trader_success(self, mock_service_class, client, mock_user, mock_trader):
    # Setup mocks
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
- Includes id, username, etc.

### `mock_trader`
- Pre-configured mock trader object
- Includes wallet address, runtime_name, status, etc.

### `auth_headers`
- Authorization headers with mock token
- Use for authenticated requests

## Key Benefits

1. **Fast execution**: All tests run in under 1 second
2. **No external dependencies**: No Docker Swarm or SQLite needed
3. **Isolated testing**: Each test is completely independent
4. **Clear failures**: Mock assertions provide clear error messages
5. **Easy debugging**: No database state to track
6. **CI/CD friendly**: No Docker or database setup in CI pipeline

## Secret Management Architecture

Private keys are stored as Docker Swarm secrets — not in the database. The test suite mocks `client.secrets` and `client.services` so no real Swarm is needed:

```python
mock_client.secrets.create.return_value = mock_secret  # No real secret created
mock_client.services.create.return_value = mock_service  # No real service started
```

The runtime creates secrets named `ht_{trader_id}_private_key`, which are mounted at `/run/secrets/private_key` inside each trader service.
