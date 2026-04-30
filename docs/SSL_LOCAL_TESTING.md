# Local SSL Testing with Pebble

This document explains how to manually test the SSL setup wizard end-to-end
without hitting real Let's Encrypt servers (which have rate limits and require
a real DNS-resolvable domain pointing at your machine).

## What this gives you

- The exact same code path that runs in production:
  `POST /api/v1/setup/ssl` → `TraefikConfigWriter.write_domain_config(...)` →
  Traefik restart → ACME HTTP-01 challenge → certificate issued → HTTPS served.
- A throwaway certificate signed by Pebble's local test CA (browser will warn
  about an untrusted issuer — accept the warning for testing).
- No `/etc/hosts` edits required: `*.localtest.me` is a public DNS name that
  always resolves to `127.0.0.1`.

## When to use this

- You changed code in `services/ssl_setup_service.py`,
  `services/traefik_config.py`, `routers/ssl_setup.py`, or
  `web/src/routes/setup/ssl.tsx`.
- You want to manually click through the SSL wizard in the browser.

For unit-level changes you don't need this — `pytest` covers the rendered
Traefik config; vitest covers the redirect guard. Run those first.

## Setup (one-time)

Run from the **repo root**:

```bash
cp deploy/.env.api.pebble.example deploy/.env.api.pebble
cp data/traefik/traefik.template.yml data/traefik-pebble/traefik.yml
touch data/traefik-pebble/acme.json && chmod 600 data/traefik-pebble/acme.json
```

`data/traefik-pebble/traefik.yml` and `acme.json` are gitignored — they're safe to
delete and recreate. `data/traefik/` is never touched by the Pebble stack.

## Run the stack

Use the combined `docker-compose.dev_ssl.yml` file (merges `docker-compose.dev.yml` +
`docker-compose.pebble.yml` into a single file):

```bash
docker compose \
  -f deploy/docker-compose.dev_ssl.yml \
  --env-file deploy/.env \
  up -d --build
```

<details>
<summary>Alternative: two-file overlay approach</summary>

```bash
docker compose \
  -f deploy/docker-compose.dev.yml \
  -f deploy/docker-compose.pebble.yml \
  --env-file deploy/.env \
  up -d --build
```
</details>

Four containers come up:

```
hypertrader-traefik   :80, :443
hypertrader-api       :8000
hypertrader-web       :3000
hypertrader-pebble    :14000 (ACME directory), :15000 (management)
```

## Test the flow

1. Browse to `http://hypertrader.localtest.me/`
   (`localtest.me` → 127.0.0.1; Traefik on :80 routes to web)
2. The boot guard redirects you to `/setup/ssl`.
3. Submit the form with:
   - Domain: `hypertrader.localtest.me`
   - Email: anything valid, e.g. `dev@example.com`
4. The api writes a `traefik.yml` whose ACME resolver has
   `caServer: https://pebble:14000/dir` (Pebble) and triggers a Traefik restart.
5. Pebble issues a cert in ~3 seconds.
6. The browser is sent to `https://hypertrader.localtest.me/` — accept the
   "untrusted issuer" warning (Pebble uses its own throwaway CA).
7. Continue through bootstrap → `/traders` as normal.

### Verifying without a browser

```bash
# from the host
curl -k https://hypertrader.localtest.me/health
# -> {"status":"healthy",...}

# inspect the issued cert
echo | openssl s_client -connect hypertrader.localtest.me:443 \
  -servername hypertrader.localtest.me 2>/dev/null \
  | openssl x509 -noout -issuer
# -> issuer=CN=Pebble Intermediate CA ...
```

If you want curl to validate the chain instead of `-k`, pass
`--cacert deploy/pebble/pebble.minica.pem`.

## How the overlay wires Pebble in

Three things make the e2e work, all defined in `docker-compose.dev_ssl.yml`

1. **Pebble service** — listens on `:14000` (ACME directory) inside the
   `hypertrader` docker network. Image is `ghcr.io/letsencrypt/pebble:latest`
   (NOT `letsencrypt/pebble`, which doesn't exist on Docker Hub).
2. **`hypertrader.localtest.me` network alias on traefik** — when Pebble
   performs the HTTP-01 challenge it does a DNS lookup for the domain. With
   the alias on traefik, Docker's embedded DNS returns traefik's container
   IP, so the challenge HTTP request hits traefik on port 80 (the right
   place) instead of trying to leave the docker network.
3. **`LEGO_CA_CERTIFICATES` on traefik** — Traefik's embedded ACME client
   (Lego) won't talk to a directory whose TLS cert it doesn't trust. We
   mount Pebble's MiniCA root (`deploy/pebble/pebble.minica.pem`, copied
   out of the Pebble image at `/test/certs/pebble.minica.pem`) and point
   Lego at it.

## Reset

Run from the **repo root**:

```bash
docker compose -f deploy/docker-compose.dev_ssl.yml down -v

# Wipe Pebble runtime files
rm -f data/traefik-pebble/traefik.yml \
      data/traefik-pebble/acme.json \
      data/traefik-pebble/dynamic/10-tls.yml

# Re-initialise for the next run
cp data/traefik/traefik.template.yml data/traefik-pebble/traefik.yml
touch data/traefik-pebble/acme.json && chmod 600 data/traefik-pebble/acme.json
```

`data/traefik/` is never modified by the Pebble stack — no `git checkout` needed.

## Why not just run real Let's Encrypt locally?

- Real LE has rate limits (5 cert renewals per registered domain per week).
- Requires a real domain pointed at your machine and ports 80/443 reachable
  from the public internet.
- Generates real certs that get logged in Certificate Transparency logs.

Pebble is Let's Encrypt's **own** test server, written by the same people, and
implements the same ACME protocol — so this exercises the production code
path correctly, just against a throwaway CA.
