# Self-Hosted Quickstart

> This is a draft user guide for the planned self-hosted v1 release.
> It reflects the approved implementation plan in `docs/plans/2026-03-08-self-hosted-v1-implementation.md`.
> Some files and commands below are planned deliverables and may not exist yet in the current branch.

## What You Get

HyperTrader self-hosted v1 is a single-VPS deployment that gives you:

- a web dashboard served directly at `http://your-ip[:port]` or `http://your-hostname[:port]`
- one local admin account with `username + password`
- trader creation and management from the UI
- logs, restart, and delete actions from the dashboard
- a simple stack built with `Traefik`, `web`, `api`, and `SQLite`

## V1 Limitations

- `HTTP only`
- single VPS
- single local admin is the primary supported mode
- `SQLite` instead of PostgreSQL
- no Kubernetes
- no Privy

## Security Warning

V1 is planned as `HTTP only`.

That means login credentials and app traffic are not encrypted in transit.

Recommended usage for v1:

- run it on a private network
- restrict access with a firewall
- or place it behind your own secure tunnel / reverse proxy

Do not expose it directly to the public Internet unless you understand and accept the risk.

## Prerequisites

Before you start, you need:

- a Linux VPS (Ubuntu is the easiest target)
- Docker installed
- Docker Compose available (`docker compose`)
- SSH access to the VPS
- one open HTTP port for the app (for example `80` or `8080`)

Optional:

- a hostname pointed at your VPS

## What You Will Download

The self-hosted release bundle is expected to contain:

- `docker-compose.selfhosted.yml`
- `deploy/.env.selfhosted.example`
- `deploy/traefik/traefik.yml`
- `deploy/traefik/dynamic.yml`
- `scripts/install-selfhosted.sh`
- `scripts/upgrade-selfhosted.sh`
- `scripts/backup-selfhosted.sh`

## Step 1: Connect to Your VPS

SSH into your server:

```bash
ssh your-user@your-vps-ip
```

Verify Docker is available:

```bash
docker --version
docker compose version
```

If needed, install Docker before continuing.

## Step 2: Download the Release Bundle

Example using git:

```bash
git clone <your-release-repo-url> hyper-trader-manager
cd hyper-trader-manager
```

Or download and extract the release archive, then `cd` into the extracted directory.

## Step 3: Create Your Self-Hosted Config File

Copy the example environment file:

```bash
cp deploy/.env.selfhosted.example .env.selfhosted
```

Edit it:

```bash
nano .env.selfhosted
```

At minimum, set:

- `PUBLIC_PORT` - the HTTP port you want to expose
- `PUBLIC_BASE_URL` - for example `http://YOUR_VPS_IP:8080` or `http://your-hostname.com`
- `JWT_SECRET_KEY` - a long random secret for login tokens
- `ENCRYPTION_KEY` - a long random secret used to protect stored trader secrets
- image tags if you want to pin a specific release

Example values:

```env
PUBLIC_PORT=8080
PUBLIC_BASE_URL=http://203.0.113.10:8080
JWT_SECRET_KEY=replace-with-a-long-random-secret
ENCRYPTION_KEY=replace-with-a-different-long-random-secret
```

## Step 4: Open the Firewall Port

Make sure your VPS firewall allows the chosen HTTP port.

Example with UFW:

```bash
sudo ufw allow 8080/tcp
sudo ufw reload
```

If you use cloud firewall rules, open the same port there too.

## Step 5: Start the Stack

Use the install script:

```bash
./scripts/install-selfhosted.sh
```

Expected stack:

- `traefik`
- `web`
- `api`
- persistent app data for `SQLite`

If you want to run the stack manually, the equivalent command is expected to be:

```bash
docker compose --env-file .env.selfhosted -f docker-compose.selfhosted.yml up -d --build
```

## Step 6: Open the Dashboard

In your browser, visit:

- `http://YOUR_VPS_IP:PORT`
- or `http://YOUR_HOSTNAME:PORT`

Examples:

- `http://203.0.113.10:8080`
- `http://trader.example.com:8080`

The dashboard should open directly at `/`.

## Step 7: Complete First-Run Setup

On the first visit, the app should show a bootstrap screen.

Create your local admin account by entering:

- `username`
- `password`

After setup is complete, the app switches to the normal login flow.

## Step 8: Log In

Sign in with the username and password you just created.

After login, you should land on the dashboard.

## Step 9: Create Your First Trader

From the dashboard, create a trader and enter the trading configuration required by the app.

The exact form fields may evolve, but you should expect to provide:

- your trader wallet address
- your trader private key
- the source account to copy
- network and strategy settings

The backend will then:

- store the config
- encrypt the sensitive secret material at rest
- create the trader runtime container
- show status and logs in the UI

## Common Operations

Once the app is running, you should be able to:

- view all traders on the dashboard
- inspect trader status
- view trader logs
- restart a trader
- delete a trader

## Upgrade the App

When a new release is available, the expected upgrade flow is:

```bash
./scripts/upgrade-selfhosted.sh
```

The upgrade script should:

- pull updated images
- apply backend/data changes safely
- restart the stack
- preserve your `SQLite` database and app config

## Back Up the App

The expected backup flow is:

```bash
./scripts/backup-selfhosted.sh
```

At minimum, your backups should include:

- the `SQLite` database file
- your self-hosted environment file
- any persistent trader config data written by the stack

## Troubleshooting

### Check running containers

```bash
docker ps
```

### Check stack logs

```bash
docker compose --env-file .env.selfhosted -f docker-compose.selfhosted.yml logs -f
```

### Check only the API logs

```bash
docker compose --env-file .env.selfhosted -f docker-compose.selfhosted.yml logs -f api
```

### Check only the web logs

```bash
docker compose --env-file .env.selfhosted -f docker-compose.selfhosted.yml logs -f web
```

### Check only the Traefik logs

```bash
docker compose --env-file .env.selfhosted -f docker-compose.selfhosted.yml logs -f traefik
```

### App does not load in the browser

Check:

- the stack is running
- the chosen port is open
- `PUBLIC_PORT` matches the exposed port
- your VPS firewall and cloud firewall allow that port

### Login fails

Check:

- you completed the bootstrap step successfully
- you are using the correct username
- `JWT_SECRET_KEY` is set and stable

### Trader fails to start

Check:

- the trader config is valid
- the wallet address and private key are correct
- the API container can reach the Docker engine
- the API logs for runtime errors

## Recommended First Production Use

For your first real deployment:

- use a fresh VPS
- use a non-default strong password
- generate long random secrets for token and encryption keys
- limit network exposure as much as possible
- start with a small test trader before using larger funds

## Support Notes

If you need to report an issue, include:

- your VPS OS version
- Docker version
- chosen public port
- stack logs from `traefik`, `api`, and `web`
- the exact step where setup failed
