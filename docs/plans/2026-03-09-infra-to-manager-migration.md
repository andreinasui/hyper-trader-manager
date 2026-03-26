# Infra To Manager Migration Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Consolidate `hyper-trader-infra` into `hyper-trader-manager` so the manager repo becomes the single self-hosted control-plane and deployment repo for v1.

**Architecture:** Keep `hyper-trader-manager` as the only product/control-plane repo and absorb only the deployable operational assets from `hyper-trader-infra`. Do not blindly copy the K8s-era structure; move the useful pieces into a new self-hosted layout, rewrite scripts/docs around `Docker Compose + Traefik + SQLite`, and explicitly retire the Kubernetes-only assets.

**Tech Stack:** FastAPI, React/Vite, Docker Compose, Traefik, SQLite, shell scripts, Markdown docs.

---

## Migration Principles

- `hyper-trader-manager` becomes the source of truth for product + self-hosted deployment.
- `hyper-trader-infra` is treated as an extraction source, not as a structure to preserve.
- Move operational concepts, not K8s baggage.
- Prefer rewrite over porting when a file is tightly coupled to Kubernetes, PostgreSQL, or SaaS/Privy assumptions.
- Keep `hyper-trader` separate.

## Proposed Target Layout In `hyper-trader-manager`

```text
hyper-trader-manager/
├── api/
├── web/
├── deploy/
│   ├── compose/
│   ├── traefik/
│   ├── env/
│   └── examples/
├── scripts/
├── docs/
│   ├── self-hosted/
│   └── plans/
└── docker-compose.selfhosted.yml
```

## Source Inventory From `hyper-trader-infra`

### Likely To Migrate In Some Form

- `scripts/deploy.sh`
- `scripts/setup-vps.sh`
- `scripts/setup.sh`
- `scripts/trader-ctl.sh`
- `justfile`
- `DEV_SETUP.md`
- `docs/QUICKSTART.md`
- `docs/OBSERVABILITY.md`
- `docker-compose.dev.yml`
- `kubernetes/examples/example-config.json`
- `kubernetes/examples/example-private-key.txt`

### Likely To Retire Or Archive

- `scripts/infra-ctl.sh`
- `scripts/export-traces.sh`
- `kubernetes/base/api-deployment.yaml`
- `kubernetes/base/api-rbac.yaml`
- `kubernetes/base/api-secret.yaml.example`
- `kubernetes/base/api-service.yaml`
- `kubernetes/base/namespace.yaml`
- `kubernetes/base/postgresql.yaml`
- `kubernetes/base/postgres-secret.yaml.example`
- `kubernetes/base/web-deployment.yaml`
- `kubernetes/base/loki.yaml`
- `kubernetes/base/loki-config.yaml`
- `kubernetes/base/promtail.yaml`
- `kubernetes/base/promtail-config.yaml`
- `kubernetes/base/otel-collector.yaml`
- `kubernetes/base/grafana.yaml`
- `kubernetes/base/grafana-config.yaml`
- `kubernetes/base/tempo.yaml`
- `kubernetes/base/tempo-config.yaml`
- `docs/cluster-architecture.md`
- `docs/managed_kubernetes_external_ip_and_autoscaling_nodes.md`
- `docs/grafana-usage-guide.md`
- `docs/exporting-traces.md`
- `docs/migration_to_saas.md`

### Re-evaluate Before Deciding

- `kubernetes/base/configmap-template.yaml`
- `kubernetes/base/secret-template.yaml`
- `kubernetes/base/statefulset-template.yaml`
- `schema.sql`
- `test-config.yaml`
- `docs/future_dev_env.md`

These files should not be moved 1:1. They should be mined for concepts or example values only.

---

### Task 1: Create the migration map and retirement ledger

**Files:**
- Create: `docs/plans/2026-03-09-infra-to-manager-file-map.md`
- Modify: `docs/plans/2026-03-09-infra-to-manager-migration.md`

**Step 1: Write the file-by-file move table**

Create a machine- and human-readable ledger with columns:
- source path
- destination path
- action (`move`, `rewrite`, `archive`, `drop`)
- rationale

Example rows:

```markdown
| Source | Destination | Action | Rationale |
| --- | --- | --- | --- |
| hyper-trader-infra/scripts/setup-vps.sh | scripts/install-selfhosted.sh | rewrite | VPS setup concept survives, K8s logic does not |
| hyper-trader-infra/kubernetes/base/web-deployment.yaml | none | drop | replaced by Traefik + Compose packaging |
```

**Step 2: Verify the ledger covers all top-level `infra` assets**

Run: `ls hyper-trader-infra`

Expected: every meaningful file family is accounted for in the ledger.

**Step 3: Commit**

```bash
git add docs/plans/2026-03-09-infra-to-manager-file-map.md docs/plans/2026-03-09-infra-to-manager-migration.md
git commit -m "docs: add infra-to-manager migration ledger"
```

---

### Task 2: Create the target deployment and docs directories in manager

**Files:**
- Create: `deploy/compose/.gitkeep`
- Create: `deploy/traefik/.gitkeep`
- Create: `deploy/env/.gitkeep`
- Create: `deploy/examples/.gitkeep`
- Create: `scripts/.gitkeep`
- Create: `docs/self-hosted/.gitkeep`
- Modify: `.gitignore`

**Step 1: Create the failing structural check**

Use a simple shell-based verification command that asserts the new directories exist.

```bash
test -d deploy/compose && test -d deploy/traefik && test -d docs/self-hosted
```

**Step 2: Run the check and verify failure**

Run: `test -d deploy/compose && test -d deploy/traefik && test -d docs/self-hosted`

Expected: FAIL because those directories do not exist yet.

**Step 3: Create the minimal directory structure**

Use `.gitkeep` placeholders so the structure lands before content migration.

**Step 4: Re-run the structural check**

Run: `test -d deploy/compose && test -d deploy/traefik && test -d docs/self-hosted`

Expected: PASS

**Step 5: Commit**

```bash
git add deploy/compose/.gitkeep deploy/traefik/.gitkeep deploy/env/.gitkeep deploy/examples/.gitkeep scripts/.gitkeep docs/self-hosted/.gitkeep .gitignore
git commit -m "chore: add self-hosted deployment layout to manager"
```

---

### Task 3: Migrate and rewrite operator scripts from infra into manager

**Files:**
- Create: `scripts/install-selfhosted.sh`
- Create: `scripts/upgrade-selfhosted.sh`
- Create: `scripts/backup-selfhosted.sh`
- Create: `scripts/dev-stack.sh`
- Modify: `justfile`
- Reference: `../hyper-trader-infra/scripts/setup-vps.sh`
- Reference: `../hyper-trader-infra/scripts/setup.sh`
- Reference: `../hyper-trader-infra/scripts/deploy.sh`
- Reference: `../hyper-trader-infra/scripts/trader-ctl.sh`

**Step 1: Write failing smoke tests for the scripts**

Create a shell smoke test or documented check for:
- install script exists and is executable
- upgrade script exists and is executable
- backup script exists and is executable

```bash
test -x scripts/install-selfhosted.sh
test -x scripts/upgrade-selfhosted.sh
test -x scripts/backup-selfhosted.sh
```

**Step 2: Run the smoke checks and verify failure**

Run: `test -x scripts/install-selfhosted.sh`

Expected: FAIL

**Step 3: Rewrite the scripts around the new product**

Do not preserve old semantics like:
- `kubectl`
- K8s namespaces
- cluster secrets
- remote rsync image deployment pipeline

Replace them with:

```bash
docker compose --env-file .env.selfhosted -f docker-compose.selfhosted.yml up -d --build
```

Suggested responsibilities:
- `install-selfhosted.sh`: bootstrap env + start stack
- `upgrade-selfhosted.sh`: pull/build updated images + restart stack
- `backup-selfhosted.sh`: archive SQLite DB + env + persistent data
- `dev-stack.sh`: local bring-up for self-hosted packaging verification

Update `justfile` to point to the new scripts instead of the K8s-era `infra-ctl.sh`/`trader-ctl.sh` flows.

**Step 4: Run the smoke checks and a `just --list` check**

Run:
- `test -x scripts/install-selfhosted.sh`
- `test -x scripts/upgrade-selfhosted.sh`
- `test -x scripts/backup-selfhosted.sh`
- `just --list`

Expected: PASS

**Step 5: Commit**

```bash
git add scripts/install-selfhosted.sh scripts/upgrade-selfhosted.sh scripts/backup-selfhosted.sh scripts/dev-stack.sh justfile
git commit -m "feat: migrate operational scripts into manager self-hosted flow"
```

---

### Task 4: Replace infra deployment assets with Compose and Traefik assets inside manager

**Files:**
- Create: `docker-compose.selfhosted.yml`
- Create: `deploy/traefik/traefik.yml`
- Create: `deploy/traefik/dynamic.yml`
- Create: `deploy/env/.env.selfhosted.example`
- Create: `deploy/examples/example-config.json`
- Modify: `docker-compose.dev.yml`
- Reference: `../hyper-trader-infra/docker-compose.dev.yml`
- Reference: `../hyper-trader-infra/kubernetes/examples/example-config.json`
- Reference: `../hyper-trader-infra/kubernetes/examples/example-private-key.txt`

**Step 1: Write the failing config validation check**

Run a Compose config render command:

```bash
docker compose -f docker-compose.selfhosted.yml config
```

**Step 2: Run it and verify failure**

Expected: FAIL because the self-hosted Compose file does not exist yet.

**Step 3: Create self-hosted deploy assets**

Move concepts, not files:
- replace K8s `api-deployment.yaml` + `web-deployment.yaml` with Compose services
- replace cluster ingress with Traefik routing
- replace PostgreSQL secret examples with self-hosted env examples
- carry over config examples into `deploy/examples/`

Keep `docker-compose.dev.yml` only for local development; do not overload it with production deployment semantics.

**Step 4: Run deploy config validation**

Run:
- `docker compose -f docker-compose.selfhosted.yml config`
- `docker compose -f docker-compose.dev.yml config`

Expected: PASS

**Step 5: Commit**

```bash
git add docker-compose.selfhosted.yml deploy/traefik/traefik.yml deploy/traefik/dynamic.yml deploy/env/.env.selfhosted.example deploy/examples/example-config.json docker-compose.dev.yml
git commit -m "feat: replace infra deployment assets with compose and traefik"
```

---

### Task 5: Migrate useful docs into manager and rewrite them for self-hosted v1

**Files:**
- Create: `docs/self-hosted/QUICKSTART.md`
- Create: `docs/self-hosted/OPERATIONS.md`
- Create: `docs/self-hosted/OBSERVABILITY.md`
- Modify: `README.md`
- Modify: `DEV_SETUP.md`
- Reference: `../hyper-trader-infra/docs/QUICKSTART.md`
- Reference: `../hyper-trader-infra/docs/OBSERVABILITY.md`
- Reference: `../hyper-trader-infra/DEV_SETUP.md`

**Step 1: Write failing documentation checks**

Use existence checks:

```bash
test -f docs/self-hosted/QUICKSTART.md
test -f docs/self-hosted/OPERATIONS.md
test -f docs/self-hosted/OBSERVABILITY.md
```

**Step 2: Run and verify failure**

Run: `test -f docs/self-hosted/QUICKSTART.md`

Expected: FAIL

**Step 3: Rewrite, don’t port**

Map old docs to new docs like this:
- `hyper-trader-infra/docs/QUICKSTART.md` -> `docs/self-hosted/QUICKSTART.md`
- `hyper-trader-infra/docs/OBSERVABILITY.md` -> `docs/self-hosted/OBSERVABILITY.md`
- `hyper-trader-infra/DEV_SETUP.md` -> `DEV_SETUP.md`

Drop Kubernetes-specific docs or archive their concepts only.

Update `README.md` to make `hyper-trader-manager` the canonical self-hosted entrypoint.

**Step 4: Re-run the documentation checks**

Run:
- `test -f docs/self-hosted/QUICKSTART.md`
- `test -f docs/self-hosted/OPERATIONS.md`
- `test -f docs/self-hosted/OBSERVABILITY.md`

Expected: PASS

**Step 5: Commit**

```bash
git add docs/self-hosted/QUICKSTART.md docs/self-hosted/OPERATIONS.md docs/self-hosted/OBSERVABILITY.md README.md DEV_SETUP.md
git commit -m "docs: migrate self-hosted docs from infra into manager"
```

---

### Task 6: Remove or archive Kubernetes-only references from manager

**Files:**
- Modify: `README.md`
- Modify: `DEV_SETUP.md`
- Modify: `api/README.md`
- Modify: `api/docker/Dockerfile.api`
- Modify: `api/hyper_trader_api/services/k8s_controller.py`
- Modify: `api/hyper_trader_api/services/trader_service.py`
- Modify: `api/templates/statefulset.yaml.j2`
- Modify: `api/templates/configmap.yaml.j2`

**Step 1: Write a failing grep-based check for K8s-era language in manager docs/root paths**

Run:

```bash
rg "Kubernetes|kubectl|StatefulSet|ConfigMap|namespace|Privy|PostgreSQL" README.md DEV_SETUP.md api/README.md
```

**Step 2: Verify it fails**

Expected: matches are found.

**Step 3: Remove or quarantine outdated references**

Rules:
- if the file is part of the new self-hosted flow, rewrite it
- if the file is only useful as historical reference, move it under `docs/archive/` or delete it in a later cleanup task
- if the Python code is still temporarily K8s-based, mark it clearly as transitional until the runtime migration lands

Do not leave the repo in a state where `manager` claims to be the self-hosted source of truth while the top-level docs still describe K8s cluster bootstrapping.

**Step 4: Re-run the grep check**

Run:

```bash
rg "Kubernetes|kubectl|StatefulSet|ConfigMap|namespace|PostgreSQL" README.md DEV_SETUP.md api/README.md
```

Expected: no stale top-level self-hosted contradictions remain, or only explicitly marked transitional references remain.

**Step 5: Commit**

```bash
git add README.md DEV_SETUP.md api/README.md api/docker/Dockerfile.api api/hyper_trader_api/services/k8s_controller.py api/hyper_trader_api/services/trader_service.py api/templates/statefulset.yaml.j2 api/templates/configmap.yaml.j2
git commit -m "refactor: remove stale infra-era kubernetes references from manager"
```

---

### Task 7: Define the infra repository end-state and deprecation path

**Files:**
- Create: `docs/self-hosted/INFRA_REPO_DEPRECATION.md`
- Reference: `../hyper-trader-infra/README.md`

**Step 1: Write the deprecation decision doc**

It must answer:
- when `hyper-trader-infra` is frozen
- what content was migrated
- what content was intentionally dropped
- where users should go now

**Step 2: Add the exact freeze/archive checklist**

Include steps such as:
- update `hyper-trader-infra/README.md` to point to `hyper-trader-manager`
- archive old issues/labels if needed
- stop publishing `infra` as the deploy entrypoint

**Step 3: Verify the doc exists**

Run: `test -f docs/self-hosted/INFRA_REPO_DEPRECATION.md`

Expected: PASS

**Step 4: Commit**

```bash
git add docs/self-hosted/INFRA_REPO_DEPRECATION.md
git commit -m "docs: define infra repository deprecation path"
```

---

### Task 8: Run final migration verification

**Files:**
- Test: `justfile`
- Test: `docker-compose.selfhosted.yml`
- Test: `docs/self-hosted/QUICKSTART.md`
- Test: `docs/self-hosted/OPERATIONS.md`

**Step 1: Run structure verification**

Run:

```bash
test -d deploy/compose
test -d deploy/traefik
test -d docs/self-hosted
test -d scripts
```

Expected: PASS

**Step 2: Run command and config verification**

Run:
- `just --list`
- `docker compose -f docker-compose.selfhosted.yml config`

Expected: PASS

**Step 3: Run documentation verification**

Read the top-level docs in order:
- `README.md`
- `DEV_SETUP.md`
- `docs/self-hosted/QUICKSTART.md`
- `docs/self-hosted/OPERATIONS.md`

Expected: all point to `hyper-trader-manager` as the self-hosted source of truth.

**Step 4: Commit the final migration state**

```bash
git add .
git commit -m "chore: consolidate infra delivery into manager"
```

---

## Concrete Move/Rewrite Recommendations

### Move And Rewrite Into `manager`

- `hyper-trader-infra/scripts/setup-vps.sh` -> `hyper-trader-manager/scripts/install-selfhosted.sh`
- `hyper-trader-infra/scripts/deploy.sh` -> `hyper-trader-manager/scripts/upgrade-selfhosted.sh`
- `hyper-trader-infra/scripts/setup.sh` -> `hyper-trader-manager/scripts/dev-stack.sh`
- `hyper-trader-infra/docs/QUICKSTART.md` -> `hyper-trader-manager/docs/self-hosted/QUICKSTART.md`
- `hyper-trader-infra/docs/OBSERVABILITY.md` -> `hyper-trader-manager/docs/self-hosted/OBSERVABILITY.md`
- `hyper-trader-infra/DEV_SETUP.md` -> concepts only into `hyper-trader-manager/DEV_SETUP.md`
- `hyper-trader-infra/kubernetes/examples/example-config.json` -> `hyper-trader-manager/deploy/examples/example-config.json`

### Drop Instead Of Move

- all K8s deployment YAMLs under `hyper-trader-infra/kubernetes/base/`
- `hyper-trader-infra/scripts/infra-ctl.sh`
- `hyper-trader-infra/scripts/export-traces.sh`
- cluster-specific docs under `hyper-trader-infra/docs/`

### Mine For Concepts Only

- `hyper-trader-infra/scripts/trader-ctl.sh`
- `hyper-trader-infra/schema.sql`
- `hyper-trader-infra/test-config.yaml`
- `hyper-trader-infra/kubernetes/base/statefulset-template.yaml`
- `hyper-trader-infra/kubernetes/base/configmap-template.yaml`
- `hyper-trader-infra/kubernetes/base/secret-template.yaml`

These are useful for understanding naming, config shape, lifecycle, and secret flow, but should not survive as first-class files in the v1 self-hosted repo.

## Risks

- Accidental file copying may preserve K8s assumptions you are trying to kill.
- Docs may temporarily contradict the product if top-level README is not rewritten early.
- Script names like `deploy.sh` and `setup.sh` can import hidden K8s/rsync/GHCR assumptions if not rewritten from scratch.
- The manager repo still contains K8s runtime code, so repo migration must be coordinated with the runtime migration plan already written in `docs/plans/2026-03-08-self-hosted-v1-implementation.md`.

## Recommended Execution Order

1. create target layout
2. create migration ledger
3. move/rewrite scripts
4. move/rewrite deploy assets
5. move/rewrite docs
6. remove stale infra/K8s references
7. publish infra deprecation note
8. verify and freeze `hyper-trader-infra`
