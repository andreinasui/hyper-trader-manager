# HyperTrader Manager

Management application for HyperTrader instances, including Backend API and Frontend Web.

> Draft self-hosted v1 quickstart: `docs/SELF_HOSTED_QUICKSTART.md`
>
> Note: the current repository state is still largely K8s/Privy-oriented; the quickstart describes the planned self-hosted v1 delivery model.

## Components
- **api/**: FastAPI backend for trader management and Kubernetes orchestration (includes Jinja2 templates in `api/templates`).
- **web/**: React/Vite frontend for monitoring and controlling traders.

## Overview

This deployment allows you to:
- Run multiple HyperTrader instances (max 1 per address)
- Dynamically add/remove traders via CLI
- Manage configurations and secrets securely
- Monitor trader health and logs
- Distributed tracing via Jaeger (shared across all traders)

## Architecture

### Application Layer
- **StatefulSet per trader**: Ensures stable identity and controlled restarts
- **ConfigMap**: Stores `config.json` per trader
- **Secret**: Stores private keys (base64 encoded)
- **Namespace isolation**: All resources in `hyper-trader` namespace
- **Address uniqueness**: Enforced via labels, prevents duplicate traders

### Observability Infrastructure
- **Jaeger**: Distributed tracing UI (single instance)
- **OpenTelemetry Collector**: Aggregates traces from all traders
- **Auto-configuration**: Traders automatically send traces to OTEL Collector

## Prerequisites

1. **K3s cluster** running and accessible via `kubectl`
2. **kubectl** CLI installed
3. **jq** for JSON processing
4. **Docker registry access** to GHCR (GitHub Container Registry)

## Initial Setup

### 1. Create Namespace

```bash
kubectl apply -f kubernetes/base/namespace.yaml
```

### 2. Start Observability Infrastructure

Deploy Jaeger and OpenTelemetry Collector:

```bash
./scripts/infra-ctl.sh start
```

Verify:
```bash
./scripts/infra-ctl.sh status
```

### 3. Create Image Pull Secret

Since your GHCR is private, create a secret to pull images:

```bash
# Generate GitHub Personal Access Token with 'read:packages' scope
# Then create the secret:

kubectl create secret docker-registry ghcr-secret \
  --docker-server=ghcr.io \
  --docker-username=<your-github-username> \
  --docker-password=<your-github-pat> \
  --namespace=hyper-trader
```

Verify:
```bash
kubectl get secret ghcr-secret -n hyper-trader
```

### 3. Set Environment Variables (Optional)

Export these to customize image repository:

```bash
export GITHUB_REPO="andreinasui/hyper-trader"  # Default
export IMAGE_TAG="latest"                     # Default
```

## Usage

### Add New Trader

```bash
./scripts/trader-ctl.sh add \
  --config ./configs/config.docker.json \
  --private-key ./private-key.txt \
  --image-tag latest
```

**What happens:**
1. Validates address, config.json, and private key
2. Checks address uniqueness (rejects if exists)
3. Creates Secret with private key
4. Creates ConfigMap with config.json
5. Creates StatefulSet with pod

**Files created:**
```
kubernetes/instances/trader-e2214234/
├── config.json
├── configmap.yaml
├── secret.yaml
└── statefulset.yaml
```

### List All Traders

```bash
./scripts/trader-ctl.sh list
```

Output:
```
NAME              ADDRESS                                      REPLICAS   READY   IMAGE
trader-e2214234   0xe2214234114234f8186abf5f9a8c25be9984a140   1          1       ghcr.io/andreihod/hyper-trader:latest
trader-ad963623   0xad963623d67b926810388508abd660c3d96db430   1          1       ghcr.io/andreihod/hyper-trader:latest
```

### Check Trader Status

```bash
# Specific trader
./scripts/trader-ctl.sh status 0xe2214234114234f8186abf5f9a8c25be9984a140

# All traders
./scripts/trader-ctl.sh status
```

Output includes:
- StatefulSet status
- Pod status
- Recent events

### View Logs

```bash
# Last 100 lines
./scripts/trader-ctl.sh logs 0xe2214234114234f8186abf5f9a8c25be9984a140

# Follow logs
./scripts/trader-ctl.sh logs 0xe2214234114234f8186abf5f9a8c25be9984a140 --follow

# Last 500 lines
./scripts/trader-ctl.sh logs 0xe2214234114234f8186abf5f9a8c25be9984a140 --tail 500
```

### Restart Trader

```bash
./scripts/trader-ctl.sh restart 0xe2214234114234f8186abf5f9a8c25be9984a140
```

Deletes pod, StatefulSet recreates it immediately.

### Update Configuration

```bash
./scripts/trader-ctl.sh update \
  --address 0xe2214234114234f8186abf5f9a8c25be9984a140 \
  --config ./configs/new-config.json
```

**What happens:**
1. Validates new config.json
2. Backs up old config to `config.json.backup`
3. Updates ConfigMap
4. Restarts pod to apply changes

### Remove Trader

```bash
./scripts/trader-ctl.sh remove 0xe2214234114234f8186abf5f9a8c25be9984a140
```

**Confirmation required** - deletes:
- StatefulSet
- ConfigMap
- Secret
- Instance directory

## Infrastructure Management

### Start Infrastructure

```bash
./scripts/infra-ctl.sh start
```

Deploys Jaeger and OTEL Collector to the cluster.

### Check Infrastructure Status

```bash
./scripts/infra-ctl.sh status
```

Shows status of Jaeger and OTEL Collector deployments/pods/services.

### Access Jaeger UI

```bash
# Port forward to localhost
./scripts/infra-ctl.sh port-forward

# Open browser: http://localhost:16686
```

### View Infrastructure Logs

```bash
# Jaeger logs
./scripts/infra-ctl.sh logs jaeger

# OTEL Collector logs
./scripts/infra-ctl.sh logs otel-collector --follow
```

### Restart Infrastructure

```bash
./scripts/infra-ctl.sh restart
```

Performs rolling restart of Jaeger and OTEL Collector.

### Stop Infrastructure

```bash
./scripts/infra-ctl.sh stop
```

**Warning**: This stops distributed tracing for all traders.

## File Structure

```
kubernetes/
├── base/                              # Base templates
│   ├── namespace.yaml                 # Namespace definition
│   ├── jaeger.yaml                    # Jaeger deployment & service
│   ├── otel-collector.yaml            # OTEL Collector deployment & service
│   ├── otel-collector-config.yaml     # OTEL Collector configuration
│   ├── statefulset-template.yaml     # StatefulSet template
│   ├── configmap-template.yaml       # ConfigMap template
│   ├── secret-template.yaml          # Secret template
│   └── imagepullsecret.yaml.example  # Image pull secret example
├── instances/                         # Per-trader configs (gitignored)
│   └── trader-<short-address>/
│       ├── config.json
│       ├── configmap.yaml
│       ├── secret.yaml
│       └── statefulset.yaml
└── examples/
    ├── example-config.json
    └── example-private-key.txt
scripts/
   ├── trader-ctl.sh                 # Trader management CLI
   ├── infra-ctl.sh                  # Infrastructure management CLI
   └── setup.sh                      # Initial setup script
```

## Resource Limits

### Per-Trader Resources
Per-trader defaults (configurable in `statefulset-template.yaml`):

```yaml
requests:
  cpu: 100m
  memory: 256Mi
limits:
  cpu: 500m
  memory: 512Mi
```

### Infrastructure Resources
Jaeger:
```yaml
requests:
  cpu: 200m
  memory: 512Mi
limits:
  cpu: 1000m
  memory: 2Gi
```

OTEL Collector:
```yaml
requests:
  cpu: 100m
  memory: 256Mi
limits:
  cpu: 500m
  memory: 512Mi
```

Adjust based on VPS capacity.

## Health Checks

### Liveness Probe
- Checks if `hyper-trader` process is running
- Fails after 3 consecutive failures
- Pod restarts automatically

### Readiness Probe
- Same as liveness (process check)
- Pod removed from service if fails

## Troubleshooting

### Pod Not Starting

```bash
# Check pod events
kubectl describe pod trader-e2214234-0 -n hyper-trader

# Check logs
./scripts/trader-ctl.sh logs 0xe2214234...
```

Common issues:
- **ImagePullBackOff**: Check `ghcr-secret` credentials
- **CrashLoopBackOff**: Check config.json validity, private key
- **ConfigMapNotFound**: Ensure ConfigMap created

### Address Already Exists

```bash
# List existing traders
./scripts/trader-ctl.sh list

# Remove old trader if needed
./scripts/trader-ctl.sh remove 0x...
```

### Check StatefulSet Status

```bash
kubectl get statefulset -n hyper-trader
kubectl describe statefulset trader-e2214234 -n hyper-trader
```

### Manual Resource Inspection

```bash
# View ConfigMap
kubectl get configmap trader-e2214234-config -n hyper-trader -o yaml

# View Secret (base64 encoded)
kubectl get secret trader-e2214234-secret -n hyper-trader -o yaml

# Decode secret
kubectl get secret trader-e2214234-secret -n hyper-trader \
  -o jsonpath='{.data.PRIVATE_KEY}' | base64 -d
```

## Security Notes

1. **Never commit secrets**: `kubernetes/instances/` is gitignored
2. **Rotate private keys**: Remove trader, re-add with new key
3. **Limit kubectl access**: Use RBAC for production
4. **Encrypt etcd at rest**: K3s supports `--secrets-encryption`

## Backup & Recovery

### Backup All Traders

```bash
# Export all configs and secrets
kubectl get configmap,secret -n hyper-trader -o yaml > backup.yaml

# Backup instance directories
tar -czf instances-backup.tar.gz kubernetes/instances/
```

### Restore Traders

```bash
# Recreate namespace
kubectl apply -f kubernetes/base/namespace.yaml

# Recreate ghcr-secret
kubectl apply -f ghcr-secret.yaml

# Restore configs/secrets
kubectl apply -f backup.yaml

# Recreate StatefulSets
for dir in kubernetes/instances/*/; do
  kubectl apply -f "$dir/statefulset.yaml"
done
```

## Monitoring

### Watch Pod Status

```bash
watch kubectl get pods -n hyper-trader
```

### Stream All Logs

```bash
kubectl logs -n hyper-trader -l app=hyper-trader --all-containers -f
```

### Resource Usage

```bash
kubectl top pod -n hyper-trader
```

## Advanced Operations

### Update Docker Image

```bash
# Update all traders to new image tag
kubectl set image statefulset -n hyper-trader \
  --all trader=ghcr.io/andreihod/hyper-trader:v1.2.3

# Or update specific trader
kubectl set image statefulset trader-e2214234 -n hyper-trader \
  trader=ghcr.io/andreihod/hyper-trader:v1.2.3
```

### Scale Down Trader (Emergency)

```bash
kubectl scale statefulset trader-e2214234 -n hyper-trader --replicas=0
```

### Scale Up

```bash
kubectl scale statefulset trader-e2214234 -n hyper-trader --replicas=1
```

### Delete All Traders

```bash
kubectl delete statefulset -n hyper-trader --all
kubectl delete configmap -n hyper-trader --all
kubectl delete secret -n hyper-trader --all
rm -rf kubernetes/instances/trader-*
```

## CI/CD Integration

When new image is pushed to GHCR (via GitHub Actions), update traders:

```bash
# Pull latest image
kubectl rollout restart statefulset -n hyper-trader --all

# Or via trader-ctl
for addr in $(kubectl get sts -n hyper-trader -o jsonpath='{.items[*].metadata.labels.trader-address}'); do
  ./scripts/trader-ctl.sh restart "$addr"
done
```

## Next Steps

1. **Add monitoring**: Prometheus metrics exporter
2. **Log aggregation**: Loki + Grafana
3. **Alerting**: Prometheus Alertmanager + Discord
4. **Auto-updates**: ArgoCD for GitOps
5. **Multi-cluster**: Federate across regions
