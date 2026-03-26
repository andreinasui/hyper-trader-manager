# Quick Start

Get HyperTrader Manager running on a VPS in minutes.

## What You Get

HyperTrader Manager v1 is a single-VPS Docker Compose deployment:

- Web dashboard at `http://your-server[:port]`
- Local admin account (username + password)
- Trader creation and management from the UI
- Per-trader logs, restart, and delete actions
- Stack: Traefik + web (nginx) + API (FastAPI) + SQLite

## V1 Limitations

- **HTTP only** — credentials are not encrypted in transit
- Single VPS only
- Single local admin account
- SQLite (not PostgreSQL)

## Security Warning

V1 serves **plain HTTP**. Login credentials and app traffic are not encrypted in transit.

Recommended usage for v1:

- Run on a private network, or
- Restrict access with a firewall to trusted IPs, or
- Place behind your own HTTPS reverse proxy or VPN

Do not expose it to the public Internet without one of the above safeguards.

## Prerequisites

- A Linux VPS (Ubuntu 22.04+ recommended)
- Docker installed — [get Docker](https://docs.docker.com/engine/install/)
- Docker Compose plugin (`docker compose version` should work)
- SSH access to the VPS
- One open TCP port for HTTP (e.g. `80` or `8080`)

Optional: a hostname / domain pointed at your VPS.

## Step 1: SSH into Your VPS

```bash
ssh your-user@your-vps-ip
```

Verify Docker works:

```bash
docker --version
docker compose version
```

## Step 2: Clone the Repository

```bash
git clone https://github.com/yourorg/hyper-trader-manager.git
cd hyper-trader-manager
```

Or download and extract the release archive, then `cd` into it.

## Step 3: Configure Environment

Copy the example config file:

```bash
cp deploy/.env.example .env
```

Edit it:

```bash
nano .env
```

**Required values to set:**

| Variable        | How to generate / choose               |
|-----------------|----------------------------------------|
| `SECRET_KEY`    | `openssl rand -hex 32`                 |
| `ADMIN_EMAIL`   | Any email address for your admin login |
| `ADMIN_PASSWORD`| A strong password                      |
| `DOCKER_GID`    | `getent group docker \| cut -d: -f3`   |

Optional — change `PUBLIC_PORT` if you don't want port 80:

```env
PUBLIC_PORT=8080
```

Example minimal config:

```env
PUBLIC_PORT=8080
SECRET_KEY=a1b2c3d4e5f6...    # output of: openssl rand -hex 32
ADMIN_EMAIL=admin@example.com
ADMIN_PASSWORD=StrongP@ssw0rd
DOCKER_GID=1001                # your server's docker group GID
```

## Step 4: Open Firewall Port

Allow traffic on the chosen port:

```bash
# UFW (Ubuntu)
sudo ufw allow 8080/tcp
sudo ufw reload
```

If you use a cloud provider (AWS, GCP, DigitalOcean…), also open the port in the cloud firewall / security group.

## Step 5: Run the Installer

```bash
./scripts/install.sh
```

The script will:
1. Check Docker is available
2. Build the `api` and `web` images
3. Start the full stack (`traefik`, `api`, `web`)
4. Wait for the API health check to pass
5. Print the dashboard URL

Or start manually:

```bash
docker compose up -d --build
```

## Step 6: Open the Dashboard

In your browser, visit:

```
http://YOUR_VPS_IP:PORT
```

Examples:
- `http://203.0.113.10:8080`
- `http://trader.example.com:8080`

## Step 7: Complete First-Run Setup

On the first visit, the app shows a **Setup** screen.

Enter your chosen admin **email** and **password** and click **Create Account**.

After setup, you are redirected to the login screen.

## Step 8: Log In

Sign in with the email and password you just created.

After login you land on the trader dashboard.

## Step 9: Create Your First Trader

From the dashboard, click **Add Trader** and provide:

- Wallet address
- Private key
- Copy-trading source account
- Network and strategy settings

The backend will:
1. Store the configuration (private key encrypted at rest)
2. Launch the trader container
3. Show status and logs in the UI

## Common Operations

From the dashboard you can:

- View all traders and their status
- Inspect trader logs
- Restart a trader
- Delete a trader

## Upgrade

When a new version is available:

```bash
./scripts/upgrade.sh
```

This will rebuild images, restart the stack, and run a health check.  
Your SQLite database and env config are preserved.

## Backup

```bash
./scripts/backup.sh
```

Saves a timestamped archive to `./backups/` containing:
- `data/db.sqlite` — the SQLite database
- `data/traders/` — trader config files
- `env.backup` — env config (secrets redacted)

See [OPERATIONS.md](OPERATIONS.md) for restore instructions.

## Troubleshooting

### Check running containers

```bash
docker compose ps
```

### Check stack logs

```bash
docker compose logs -f
```

### Check API health

```bash
curl http://localhost:${PUBLIC_PORT}/health
```

### Check setup status

```bash
curl http://localhost:${PUBLIC_PORT}/api/v1/auth/setup-status
```

### App does not load in the browser

- Check the stack is running: `docker compose ps`
- Check the port is open: `sudo ufw status` or cloud firewall rules
- Confirm `PUBLIC_PORT` in `.env` matches the port you opened

### Login fails

- Make sure you completed the bootstrap step
- Double-check username and password
- `SECRET_KEY` must remain stable — changing it invalidates all sessions

### Trader fails to start

- Check the API logs for errors
- Verify `DOCKER_GID` is correct on your host
- Confirm the API container can reach the Docker socket

## Support

When reporting an issue, include:

- VPS OS and version (`lsb_release -a`)
- Docker version (`docker --version`)
- Docker Compose version (`docker compose version`)
- Public port used
- Logs from all services: `docker compose logs`
- The exact step where the problem occurred
