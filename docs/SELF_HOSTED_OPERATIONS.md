# Self-Hosted Operations Guide

Day-to-day operations reference for HyperTrader self-hosted v1.

## Table of Contents

- [Service Management](#service-management)
- [Backup and Restore](#backup-and-restore)
- [Upgrades](#upgrades)
- [Logs](#logs)
- [Health Checks](#health-checks)
- [Configuration Changes](#configuration-changes)
- [Trader Management](#trader-management)
- [Troubleshooting](#troubleshooting)
- [Security Hardening](#security-hardening)

---

## Service Management

### Start the stack

```bash
docker compose --env-file .env.selfhosted -f docker-compose.selfhosted.yml up -d
```

### Stop the stack

```bash
docker compose --env-file .env.selfhosted -f docker-compose.selfhosted.yml down
```

Data in `./data/` is preserved. Trader containers managed by the API are not affected.

### Restart the stack

```bash
docker compose --env-file .env.selfhosted -f docker-compose.selfhosted.yml restart
```

### Restart a single service

```bash
# Restart only the API
docker compose --env-file .env.selfhosted -f docker-compose.selfhosted.yml restart api

# Restart only the web server
docker compose --env-file .env.selfhosted -f docker-compose.selfhosted.yml restart web
```

### Check service status

```bash
docker compose --env-file .env.selfhosted -f docker-compose.selfhosted.yml ps
```

Expected output — all services should be `Up (healthy)` or `Up`:

```
NAME                    IMAGE                    STATUS
hypertrader-traefik     traefik:v3.3             Up (healthy)
hypertrader-api         hyper-trader-manager-api Up (healthy)
hypertrader-web         hyper-trader-manager-web Up (healthy)
```

### Use the install / upgrade scripts

```bash
# First-time install
./scripts/install-selfhosted.sh

# Upgrade to latest version
./scripts/upgrade-selfhosted.sh

# Backup data
./scripts/backup-selfhosted.sh
```

---

## Backup and Restore

### Run a backup

```bash
./scripts/backup-selfhosted.sh
```

Archives are stored in `./backups/` and rotated (last 10 kept).

### Run a backup to a custom directory

```bash
./scripts/backup-selfhosted.sh --output-dir /mnt/remote-storage/hypertrader-backups
```

### Backup archive contents

| Path in archive       | Contents                           |
|-----------------------|------------------------------------|
| `data/db.sqlite`      | SQLite database                    |
| `data/traders/`       | Trader config files                |
| `env.backup`          | Env config (secrets redacted)      |

> **Important:** The env.backup file has `SECRET_KEY` and `ADMIN_PASSWORD` redacted.
> Keep a separate secure copy of your actual `.env.selfhosted` file.

### Schedule automated backups (cron)

```bash
crontab -e
```

Add a daily backup at 2:00 AM:

```cron
0 2 * * * /path/to/hyper-trader-manager/scripts/backup-selfhosted.sh --quiet
```

### Restore from backup

```bash
# 1. Stop the running stack
docker compose --env-file .env.selfhosted -f docker-compose.selfhosted.yml down

# 2. Extract the backup archive
tar -xzf backups/hypertrader-backup-YYYYMMDD-HHMMSS.tar.gz -C /tmp/ht-restore

# 3. Restore the data directory
rm -rf data
cp -r /tmp/ht-restore/data ./data

# 4. Restore your env file (if needed)
#    NOTE: env.backup has secrets redacted — use your original .env.selfhosted
#    or recreate it from deploy/.env.selfhosted.example

# 5. Start the stack
docker compose --env-file .env.selfhosted -f docker-compose.selfhosted.yml up -d
```

### Verify restore

```bash
curl http://localhost:${PUBLIC_PORT}/health
curl http://localhost:${PUBLIC_PORT}/api/v1/auth/setup-status
```

---

## Upgrades

### Standard upgrade

```bash
./scripts/upgrade-selfhosted.sh
```

This will:
1. Run a pre-upgrade backup automatically
2. Pull latest git changes (if running from a git clone)
3. Rebuild images with `--pull` to fetch base image updates
4. Restart the stack with new images
5. Run a health check

### Skip the pre-upgrade backup

```bash
./scripts/upgrade-selfhosted.sh --skip-backup
```

Not recommended unless you have a recent backup already.

### Manual upgrade

```bash
# Backup first
./scripts/backup-selfhosted.sh

# Pull latest changes
git pull --ff-only

# Rebuild and restart
docker compose --env-file .env.selfhosted -f docker-compose.selfhosted.yml build --pull
docker compose --env-file .env.selfhosted -f docker-compose.selfhosted.yml up -d

# Verify
curl http://localhost:${PUBLIC_PORT}/health
```

---

## Logs

### Follow all service logs

```bash
docker compose --env-file .env.selfhosted -f docker-compose.selfhosted.yml logs -f
```

### Follow logs for a specific service

```bash
# API logs
docker compose --env-file .env.selfhosted -f docker-compose.selfhosted.yml logs -f api

# Web logs
docker compose --env-file .env.selfhosted -f docker-compose.selfhosted.yml logs -f web

# Traefik logs
docker compose --env-file .env.selfhosted -f docker-compose.selfhosted.yml logs -f traefik
```

### Show recent logs (no follow)

```bash
docker compose --env-file .env.selfhosted -f docker-compose.selfhosted.yml logs --tail=100 api
```

### Trader container logs

Trader containers are managed separately from the main stack. Find them:

```bash
docker ps --filter "label=managed-by=hypertrader"
```

View logs for a specific trader container:

```bash
docker logs <container-name> --tail=200 -f
```

---

## Health Checks

### API health endpoint

```bash
curl http://localhost:${PUBLIC_PORT}/health
```

Expected response:

```json
{"status": "ok"}
```

### Setup status endpoint

```bash
curl http://localhost:${PUBLIC_PORT}/api/v1/auth/setup-status
```

Returns whether first-run setup has been completed:

```json
{"setup_complete": true}
```

or

```json
{"setup_complete": false}
```

### Docker health checks

The compose file defines health checks for all services. Inspect them:

```bash
docker inspect hypertrader-api | grep -A5 '"Health"'
```

### Full smoke test

Run this after install or upgrade to confirm everything works:

```bash
PORT="${PUBLIC_PORT:-80}"

echo "=== Container status ==="
docker compose --env-file .env.selfhosted -f docker-compose.selfhosted.yml ps

echo "=== API health ==="
curl -sf "http://localhost:${PORT}/health" && echo " ✓ health OK" || echo " ✗ health FAILED"

echo "=== Setup status ==="
curl -sf "http://localhost:${PORT}/api/v1/auth/setup-status" && echo " ✓ setup-status OK" || echo " ✗ setup-status FAILED"

echo "=== Dashboard reachable ==="
curl -sf -o /dev/null -w "%{http_code}" "http://localhost:${PORT}/" | grep -q "200\|301\|302" && echo " ✓ dashboard OK" || echo " ✗ dashboard FAILED"
```

---

## Configuration Changes

### Change a setting

1. Edit `.env.selfhosted`
2. Restart the stack:

```bash
docker compose --env-file .env.selfhosted -f docker-compose.selfhosted.yml up -d
```

### Rotate the SECRET_KEY

> **Warning:** Rotating `SECRET_KEY` invalidates all active login sessions. Users will need to log in again.

1. Generate a new key:

```bash
openssl rand -hex 32
```

2. Update `SECRET_KEY` in `.env.selfhosted`
3. Restart the API:

```bash
docker compose --env-file .env.selfhosted -f docker-compose.selfhosted.yml restart api
```

### Change the public port

1. Update `PUBLIC_PORT` in `.env.selfhosted`
2. Open the new port in the firewall:

```bash
sudo ufw allow NEW_PORT/tcp
sudo ufw reload
```

3. Restart the stack:

```bash
docker compose --env-file .env.selfhosted -f docker-compose.selfhosted.yml up -d
```

---

## Trader Management

Traders are managed through the web dashboard or the API. The backend creates, starts, stops, and removes Docker containers for each trader.

### List trader containers

```bash
docker ps --filter "label=managed-by=hypertrader" --format "table {{.Names}}\t{{.Status}}\t{{.Image}}"
```

### Manually restart a trader container

```bash
docker restart <trader-container-name>
```

Prefer using the dashboard restart button — it ensures the API state stays in sync.

### Emergency: stop all trader containers

```bash
docker ps --filter "label=managed-by=hypertrader" -q | xargs -r docker stop
```

### Data stored per trader

Trader configs and state are stored in `./data/traders/`. Each trader has a subdirectory. Do not manually edit these files while traders are running.

---

## Troubleshooting

### Stack fails to start

```bash
docker compose --env-file .env.selfhosted -f docker-compose.selfhosted.yml up
```

Running without `-d` shows startup errors in the terminal.

### API container unhealthy

```bash
# View health check history
docker inspect hypertrader-api | grep -A20 '"Health"'

# View API logs
docker compose --env-file .env.selfhosted -f docker-compose.selfhosted.yml logs api
```

Common causes:
- `SECRET_KEY` not set or too short
- SQLite database file permissions issue
- Docker socket not accessible (check `DOCKER_GID`)

### Traefik not routing requests

```bash
# Check Traefik config is valid
docker compose --env-file .env.selfhosted -f docker-compose.selfhosted.yml logs traefik

# Verify dynamic config file is mounted
docker exec hypertrader-traefik cat /etc/traefik/dynamic.yml
```

### Permission denied on Docker socket

The API container needs access to the Docker socket to manage trader containers.

Verify the `DOCKER_GID` in your env file matches the actual GID on your host:

```bash
getent group docker | cut -d: -f3
```

Update `DOCKER_GID` in `.env.selfhosted` and restart:

```bash
docker compose --env-file .env.selfhosted -f docker-compose.selfhosted.yml up -d
```

### Database locked or corrupted

```bash
# Check if another process has the database open
lsof data/db.sqlite

# Run SQLite integrity check
sqlite3 data/db.sqlite "PRAGMA integrity_check;"
```

If corrupted, restore from the most recent backup.

### Disk space full

SQLite and log files grow over time.

```bash
# Check disk usage
df -h .
du -sh data/ backups/ /var/lib/docker/

# Prune unused Docker images
docker image prune -f
```

---

## Security Hardening

### Recommended production settings

1. **Firewall**: Allow only necessary ports

```bash
# Allow only your own IP to access the app port
sudo ufw allow from YOUR_TRUSTED_IP to any port 8080
sudo ufw deny 8080/tcp
sudo ufw reload
```

2. **Strong secrets**: Rotate default values

```bash
# Generate strong SECRET_KEY
openssl rand -hex 32
```

3. **Non-default ADMIN_PASSWORD**: Use a password manager to generate a unique, strong password.

4. **Regular backups**: Automate daily backups (see [Schedule automated backups](#schedule-automated-backups-cron)).

5. **Keep Docker updated**: Apply OS and Docker security patches regularly.

```bash
sudo apt update && sudo apt upgrade -y
```

### What is NOT supported in v1

- HTTPS / TLS termination (HTTP only)
- Multi-user accounts
- Role-based access control
- Audit logging
- 2FA / MFA

These are planned for future versions.

---

## File Reference

| Path                              | Purpose                                      |
|-----------------------------------|----------------------------------------------|
| `.env.selfhosted`                 | Runtime configuration (secrets, ports, etc.) |
| `deploy/.env.selfhosted.example`  | Template for `.env.selfhosted`               |
| `docker-compose.selfhosted.yml`   | Main Docker Compose file                     |
| `deploy/traefik/dynamic.yml`      | Traefik routing configuration                |
| `data/db.sqlite`                  | SQLite database (persistent)                 |
| `data/traders/`                   | Trader config files (persistent)             |
| `backups/`                        | Backup archives (created by backup script)   |
| `scripts/install-selfhosted.sh`   | First-time install script                    |
| `scripts/upgrade-selfhosted.sh`   | Upgrade script                               |
| `scripts/backup-selfhosted.sh`    | Backup script                                |
