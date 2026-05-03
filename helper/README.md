# hyper-trader-helper

## What It Does

The helper is a short-lived container spawned by the API to orchestrate a docker-compose rolling update. When triggered, it performs the following sequence: brings down the current services (`docker compose down`), starts the services with the new images (`docker compose up -d`), waits for health checks to pass, and rolls back to the previous images if the health check times out or fails. Throughout the process it writes structured status information to a shared JSON state file so the API can report progress and outcome to the caller.

## Required Environment Variables

| Variable | Description |
|---|---|
| `COMPOSE_PROJECT_DIR` | Absolute path to the directory containing `docker-compose.yml` and `.env` |
| `OLD_API_IMAGE` | Current GHCR image tag for the `api` service (used for rollback) |
| `OLD_WEB_IMAGE` | Current GHCR image tag for the `web` service (used for rollback) |
| `NEW_API_IMAGE` | Target GHCR image tag for the `api` service |
| `NEW_WEB_IMAGE` | Target GHCR image tag for the `web` service |

## Optional Environment Variables

| Variable | Default | Description |
|---|---|---|
| `HEALTH_TIMEOUT_SECONDS` | `60` | Seconds to wait for containers to become healthy before rolling back |
| `API_CONTAINER` | `hypertrader-api` | Name of the API container to health-check |
| `WEB_CONTAINER` | `hypertrader-web` | Name of the web container to health-check |
| `STATE_FILE` | `/var/lib/update-state/update-state.json` | Path to the JSON file where update status is written |

## Running Unit Tests

```bash
bash helper/test-update-helper.sh
```

## Building the Image

```bash
docker build -t hyper-trader-helper helper/
```

The image is also published to GHCR as:
```
ghcr.io/andreinasui/hyper-trader-manager-update-helper:<version>
```

## Note for Maintainers

The helper is spawned via `docker run` (NOT `docker compose run`). This is intentional: when the helper calls `docker compose down` on the project, it stops all services defined in the compose file — but since the helper itself was started with plain `docker run`, it is not part of that compose project and will not be killed by its own `down` command.
