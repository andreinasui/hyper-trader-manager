#!/bin/bash
# trader-ctl.sh - HyperTrader Kubernetes Management Script
# Manages trader instances on K3s cluster

set -e

# Configuration
NAMESPACE="hyper-trader"
K8S_BASE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)/kubernetes"
INSTANCES_DIR="$K8S_BASE_DIR/instances"
TEMPLATES_DIR="$K8S_BASE_DIR/base"
DEFAULT_IMAGE_TAG="${IMAGE_TAG:-latest}"
GITHUB_REPO="${GITHUB_REPO:-andreinasui/hyper-trader}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Helper functions
log_info() {
  echo -e "${BLUE}[INFO]${NC} $1"
}

log_info_err() {
  echo -e "${BLUE}[INFO]${NC} $1" >&2
}

log_success() {
  echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warn() {
  echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
  echo -e "${RED}[ERROR]${NC} $1" >&2
}

usage() {
  cat <<EOF
HyperTrader Kubernetes Management Script

Usage: $0 <command> [options]

Commands:
  add         Add new trader instance
  remove      Remove trader instance
  list        List all traders
  status      Show trader status
  logs        Show trader logs
  restart     Restart trader
  update      Update trader configuration
  help        Show this help message

Options for 'add':
  --config <path>              Path to config.json (required)
  --private-key <path>         Path to private key file (required)
  --image-tag <tag>            Docker image tag (default: latest)

Options for 'remove':
  <address>                    Ethereum address to remove
  --force, -y                  Skip confirmation prompt

Options for 'status':
  <address>                    Ethereum address (optional, shows all if omitted)

Options for 'logs':
  <address>                    Ethereum address (required)
  --follow, -f                 Follow log output
  --tail <n>                   Number of lines to show (default: 100)

Options for 'restart':
  <address>                    Ethereum address (required)

Options for 'update':
  --address <address>          Ethereum address (required)
  --config <path>              Path to new config.json (required)
  
  Note: Address will be extracted from config.json for 'add' command

Examples:
  # Add new trader (address extracted from config.json)
  $0 add --config ./config.json --private-key ./key.txt

  # List all traders
  $0 list

  # Show trader status
  $0 status 0xe221...

  # View logs
  $0 logs 0xe221... --follow

  # Remove trader
  $0 remove 0xe221...

  # Update config
  $0 update --address 0xe221... --config ./new-config.json

EOF
}

# Validate dependencies
check_dependencies() {
  local missing=()

  command -v kubectl >/dev/null 2>&1 || missing+=("kubectl")
  command -v jq >/dev/null 2>&1 || missing+=("jq")
  command -v base64 >/dev/null 2>&1 || missing+=("base64")

  if [ ${#missing[@]} -gt 0 ]; then
    log_error "Missing required dependencies: ${missing[*]}"
    log_error "Please install them and try again"
    exit 1
  fi
}

# Extract short address (first 8 chars after 0x)
get_short_address() {
  local address="$1"
  echo "${address:2:8}" | tr '[:upper:]' '[:lower:]'
}

# Get trader name from address
get_trader_name() {
  local address="$1"
  echo "trader-$(get_short_address "$address")"
}

# Validate Ethereum address format
validate_address() {
  local address="$1"
  if [[ ! "$address" =~ ^0x[a-fA-F0-9]{40}$ ]]; then
    log_error "Invalid Ethereum address format: $address"
    return 1
  fi
  return 0
}

# Check if trader already exists
trader_exists() {
  local address="$1"
  kubectl get statefulsets -n "$NAMESPACE" \
    -l "trader-address=$address" \
    --no-headers 2>/dev/null | grep -q .
}

# Validate config.json
validate_config() {
  local config_file="$1"

  if [ ! -f "$config_file" ]; then
    log_error "Config file not found: $config_file"
    log_info_err "Provided path: $config_file"
    log_info_err "Current directory: $(pwd)"
    log_info_err "Absolute path would be: $(cd "$(dirname "$config_file")" 2>/dev/null && pwd)/$(basename "$config_file") (if parent dir exists)"
    return 1
  fi

  if ! jq empty "$config_file" 2>/dev/null; then
    log_error "Invalid JSON in config file: $config_file"
    log_info_err "Please check the file syntax with: jq . $config_file"
    return 1
  fi

  # Validate required fields
  local self_address=$(jq -r '.self_account.address // empty' "$config_file")
  if [ -z "$self_address" ]; then
    log_error "Missing self_account.address in config.json"
    log_info_err "Config file must contain: {\"self_account\": {\"address\": \"0x...\"}}"
    return 1
  fi

  if ! validate_address "$self_address"; then
    log_error "The address in config.json failed validation"
    return 1
  fi

  echo "$self_address"
  return 0
}

# Validate private key
validate_private_key() {
  local key_file="$1"

  if [ ! -f "$key_file" ]; then
    log_error "Private key file not found: $key_file"
    log_info_err "Provided path: $key_file"
    log_info_err "Current directory: $(pwd)"
    return 1
  fi

  local key=$(cat "$key_file" | tr -d '[:space:]')
  if [[ ! "$key" =~ ^0x[a-fA-F0-9]{64}$ ]]; then
    log_error "Invalid private key format (expected 0x + 64 hex chars)"
    log_info_err "Found: ${key:0:10}... (${#key} characters)"
    log_info_err "Expected format: 0x followed by exactly 64 hexadecimal characters"
    return 1
  fi

  return 0
}

# Create trader resources
cmd_add() {
  local address=""
  local config_file=""
  local key_file=""
  local image_tag="$DEFAULT_IMAGE_TAG"

  # Parse arguments
  while [[ $# -gt 0 ]]; do
    case $1 in
    --config)
      config_file="$2"
      shift 2
      ;;
    --private-key)
      key_file="$2"
      shift 2
      ;;
    --image-tag)
      image_tag="$2"
      shift 2
      ;;
    *)
      log_error "Unknown option: $1"
      usage
      exit 1
      ;;
    esac
  done

  # Validate required arguments
  if [ -z "$config_file" ] || [ -z "$key_file" ]; then
    log_error "Missing required arguments"
    usage
    exit 1
  fi

  # Validate and extract address from config
  log_info "Validating config.json and extracting address..."
  set +e  # Temporarily disable exit on error
  address=$(validate_config "$config_file")
  local validation_result=$?
  set -e  # Re-enable exit on error
  
  if [ $validation_result -ne 0 ]; then
    log_error "Config validation failed. Please fix the errors above and try again."
    exit 1
  fi

  log_info "Adding trader for address: $address (from config.json)"

  # Check if trader already exists
  if trader_exists "$address"; then
    log_error "Trader already exists for address: $address"
    log_info "Use 'update' command to modify existing trader"
    exit 1
  fi

  # Validate private key
  log_info "Validating private key..."
  if ! validate_private_key "$key_file"; then
    log_error "Private key validation failed. Please fix the errors above and try again."
    exit 1
  fi

  # Generate trader name
  local trader_name=$(get_trader_name "$address")
  local instance_dir="$INSTANCES_DIR/$trader_name"

  log_info "Creating instance directory: $instance_dir"
  mkdir -p "$instance_dir"

  # Copy config to instance directory
  cp "$config_file" "$instance_dir/config.json"

  # Create Secret
  log_info "Creating Secret..."
  local private_key=$(cat "$key_file" | tr -d '[:space:]')
  local private_key_base64=$(echo -n "$private_key" | base64 -w 0)

  sed -e "s|TRADER_NAME|$trader_name|g" \
    -e "s|TRADER_ADDRESS|$address|g" \
    -e "s|PRIVATE_KEY_BASE64|$private_key_base64|g" \
    "$TEMPLATES_DIR/secret-template.yaml" >"$instance_dir/secret.yaml"

  kubectl apply -f "$instance_dir/secret.yaml"

  # Create ConfigMap
  log_info "Creating ConfigMap..."
  local config_json=$(cat "$config_file")

  # Create configmap with proper YAML formatting
  cat >"$instance_dir/configmap.yaml" <<EOF
apiVersion: v1
kind: ConfigMap
metadata:
  name: $trader_name-config
  namespace: hyper-trader
  labels:
    app: hyper-trader
    trader-address: "$address"
    managed-by: trader-ctl
data:
  config.json: |
$(echo "$config_json" | sed 's/^/    /')
EOF

  kubectl apply -f "$instance_dir/configmap.yaml"

  # Create StatefulSet
  log_info "Creating StatefulSet..."
  sed -e "s|TRADER_NAME|$trader_name|g" \
    -e "s|TRADER_ADDRESS|$address|g" \
    -e "s|GITHUB_REPO|$GITHUB_REPO|g" \
    -e "s|IMAGE_TAG|$image_tag|g" \
    "$TEMPLATES_DIR/statefulset-template.yaml" >"$instance_dir/statefulset.yaml"

  kubectl apply -f "$instance_dir/statefulset.yaml"

  log_success "Trader created successfully!"
  log_info "Trader name: $trader_name"
  log_info "Pod name: $trader_name-0"
  log_info ""
  log_info "Check status with: $0 status $address"
  log_info "View logs with: $0 logs $address --follow"
}

# Remove trader
cmd_remove() {
  local address=""
  local force=false

  # Parse arguments
  while [[ $# -gt 0 ]]; do
    case $1 in
    --force | -y)
      force=true
      shift
      ;;
    *)
      if [ -z "$address" ]; then
        address="$1"
        shift
      else
        log_error "Unknown option: $1"
        exit 1
      fi
      ;;
    esac
  done

  if [ -z "$address" ]; then
    log_error "Address required"
    usage
    exit 1
  fi

  if ! validate_address "$address"; then
    exit 1
  fi

  if ! trader_exists "$address"; then
    log_error "Trader not found for address: $address"
    exit 1
  fi

  local trader_name=$(get_trader_name "$address")

  log_warn "Removing trader: $trader_name (address: $address)"
  
  if [ "$force" != true ]; then
    read -p "Are you sure? (yes/no): " confirm
    if [ "$confirm" != "yes" ]; then
      log_info "Aborted"
      exit 0
    fi
  fi

  log_info "Deleting StatefulSet..."
  kubectl delete statefulset "$trader_name" -n "$NAMESPACE" --ignore-not-found=true

  log_info "Deleting ConfigMap..."
  kubectl delete configmap "$trader_name-config" -n "$NAMESPACE" --ignore-not-found=true

  log_info "Deleting Secret..."
  kubectl delete secret "$trader_name-secret" -n "$NAMESPACE" --ignore-not-found=true

  log_info "Removing instance directory..."
  rm -rf "$INSTANCES_DIR/$trader_name"

  log_success "Trader removed successfully"
}

# List all traders
cmd_list() {
  log_info "Listing all traders in namespace: $NAMESPACE"
  echo ""

  kubectl get statefulsets -n "$NAMESPACE" \
    -l "app=hyper-trader" \
    -o custom-columns=NAME:.metadata.name,ADDRESS:.metadata.labels.trader-address,REPLICAS:.spec.replicas,READY:.status.readyReplicas,IMAGE:.spec.template.spec.containers[0].image \
    2>/dev/null || log_warn "No traders found"
}

# Show trader status
cmd_status() {
  local address="$1"

  if [ -z "$address" ]; then
    # Show all traders with enhanced information
    log_info "Listing all traders in namespace: $NAMESPACE"
    echo ""
    
    local traders=$(kubectl get statefulsets -n "$NAMESPACE" -l "app=hyper-trader" -o jsonpath='{.items[*].metadata.name}' 2>/dev/null)
    
    if [ -z "$traders" ]; then
      log_warn "No traders found"
      return
    fi
    
    printf "%-18s %-44s %-12s %-10s %-15s %s\n" "NAME" "ADDRESS" "STATUS" "RESTARTS" "IMAGE" "AGE"
    printf "%-18s %-44s %-12s %-10s %-15s %s\n" "----" "-------" "------" "--------" "-----" "---"
    
    for trader in $traders; do
      local pod_name="${trader}-0"
      local trader_address=$(kubectl get statefulset "$trader" -n "$NAMESPACE" -o jsonpath='{.metadata.labels.trader-address}' 2>/dev/null)
      local pod_status=$(kubectl get pod "$pod_name" -n "$NAMESPACE" -o jsonpath='{.status.phase}' 2>/dev/null || echo "N/A")
      local pod_ready=$(kubectl get pod "$pod_name" -n "$NAMESPACE" -o jsonpath='{.status.conditions[?(@.type=="Ready")].status}' 2>/dev/null || echo "False")
      local restarts=$(kubectl get pod "$pod_name" -n "$NAMESPACE" -o jsonpath='{.status.containerStatuses[0].restartCount}' 2>/dev/null || echo "0")
      local image=$(kubectl get statefulset "$trader" -n "$NAMESPACE" -o jsonpath='{.spec.template.spec.containers[0].image}' 2>/dev/null | sed 's/ghcr.io\///' | cut -d: -f1 | cut -c1-15)
      local age=$(kubectl get statefulset "$trader" -n "$NAMESPACE" -o jsonpath='{.metadata.creationTimestamp}' 2>/dev/null)
      
      # Calculate age
      if [ -n "$age" ]; then
        local now=$(date +%s)
        local created=$(date -d "$age" +%s 2>/dev/null || echo "$now")
        local age_seconds=$((now - created))
        if [ $age_seconds -lt 60 ]; then
          age="${age_seconds}s"
        elif [ $age_seconds -lt 3600 ]; then
          age="$((age_seconds / 60))m"
        elif [ $age_seconds -lt 86400 ]; then
          age="$((age_seconds / 3600))h"
        else
          age="$((age_seconds / 86400))d"
        fi
      else
        age="N/A"
      fi
      
      # Format status with ready indicator
      if [ "$pod_ready" = "True" ]; then
        pod_status="${GREEN}${pod_status}${NC}"
      elif [ "$pod_status" = "Running" ]; then
        pod_status="${YELLOW}${pod_status}${NC}"
      else
        pod_status="${RED}${pod_status}${NC}"
      fi
      
      printf "%-18s %-44s %-22s %-10s %-15s %s\n" "$trader" "$trader_address" "$(echo -e $pod_status)" "$restarts" "$image" "$age"
    done
    
    return
  fi

  if ! validate_address "$address"; then
    exit 1
  fi

  if ! trader_exists "$address"; then
    log_error "Trader not found for address: $address"
    exit 1
  fi

  local trader_name=$(get_trader_name "$address")
  local pod_name="$trader_name-0"

  log_info "Trader: $trader_name (Address: $address)"
  echo ""

  # Get detailed pod information
  local pod_status=$(kubectl get pod "$pod_name" -n "$NAMESPACE" -o jsonpath='{.status.phase}' 2>/dev/null || echo "N/A")
  local pod_ready=$(kubectl get pod "$pod_name" -n "$NAMESPACE" -o jsonpath='{.status.conditions[?(@.type=="Ready")].status}' 2>/dev/null || echo "False")
  local pod_ip=$(kubectl get pod "$pod_name" -n "$NAMESPACE" -o jsonpath='{.status.podIP}' 2>/dev/null || echo "N/A")
  local node=$(kubectl get pod "$pod_name" -n "$NAMESPACE" -o jsonpath='{.spec.nodeName}' 2>/dev/null || echo "N/A")
  local image=$(kubectl get statefulset "$trader_name" -n "$NAMESPACE" -o jsonpath='{.spec.template.spec.containers[0].image}' 2>/dev/null || echo "N/A")
  local restarts=$(kubectl get pod "$pod_name" -n "$NAMESPACE" -o jsonpath='{.status.containerStatuses[0].restartCount}' 2>/dev/null || echo "0")
  local start_time=$(kubectl get pod "$pod_name" -n "$NAMESPACE" -o jsonpath='{.status.startTime}' 2>/dev/null || echo "N/A")

  echo "=== Overview ==="
  echo "Pod Name:     $pod_name"
  echo "Status:       $pod_status"
  echo "Ready:        $pod_ready"
  echo "Restarts:     $restarts"
  echo "Pod IP:       $pod_ip"
  echo "Node:         $node"
  echo "Image:        $image"
  echo "Started:      $start_time"
  echo ""

  echo "=== StatefulSet ==="
  kubectl get statefulset "$trader_name" -n "$NAMESPACE"
  echo ""

  echo "=== Pod Details ==="
  kubectl get pod "$pod_name" -n "$NAMESPACE" -o wide 2>/dev/null || echo "Pod not found"
  echo ""

  # Show container state if not running
  local container_state=$(kubectl get pod "$pod_name" -n "$NAMESPACE" -o jsonpath='{.status.containerStatuses[0].state}' 2>/dev/null)
  if [ -n "$container_state" ] && [[ ! "$container_state" =~ "running" ]]; then
    echo "=== Container State ==="
    kubectl get pod "$pod_name" -n "$NAMESPACE" -o jsonpath='{.status.containerStatuses[0].state}' 2>/dev/null | jq . 2>/dev/null || echo "$container_state"
    echo ""
  fi

  # Show resource usage if metrics-server is available
  local resources=$(kubectl top pod "$pod_name" -n "$NAMESPACE" 2>/dev/null)
  if [ $? -eq 0 ]; then
    echo "=== Resource Usage ==="
    echo "$resources"
    echo ""
  fi

  # Show config summary
  echo "=== Configuration ==="
  local copy_address=$(kubectl get configmap "$trader_name-config" -n "$NAMESPACE" -o jsonpath='{.data.config\.json}' 2>/dev/null | jq -r '.copy_account.address // "N/A"')
  local self_address=$(kubectl get configmap "$trader_name-config" -n "$NAMESPACE" -o jsonpath='{.data.config\.json}' 2>/dev/null | jq -r '.self_account.address // "N/A"')
  local max_size_usd=$(kubectl get configmap "$trader_name-config" -n "$NAMESPACE" -o jsonpath='{.data.config\.json}' 2>/dev/null | jq -r '.order_sizing.max_size_usd // "N/A"')
  
  echo "Self Address:  $self_address"
  echo "Copy From:     $copy_address"
  echo "Max Size USD:  $max_size_usd"
  echo ""

  echo "=== Recent Events ==="
  kubectl get events -n "$NAMESPACE" \
    --field-selector involvedObject.name="$pod_name" \
    --sort-by='.lastTimestamp' \
    2>/dev/null | tail -10
  echo ""
  
  echo "=== Recent Logs (last 20 lines) ==="
  kubectl logs -n "$NAMESPACE" "$pod_name" --tail=20 2>/dev/null || echo "No logs available"
}

# Show trader logs
cmd_logs() {
  local address=""
  local follow=false
  local tail_lines=100

  # Parse arguments
  while [[ $# -gt 0 ]]; do
    case $1 in
    --follow | -f)
      follow=true
      shift
      ;;
    --tail)
      tail_lines="$2"
      shift 2
      ;;
    *)
      if [ -z "$address" ]; then
        address="$1"
        shift
      else
        log_error "Unknown option: $1"
        exit 1
      fi
      ;;
    esac
  done

  if [ -z "$address" ]; then
    log_error "Address required"
    usage
    exit 1
  fi

  if ! validate_address "$address"; then
    exit 1
  fi

  if ! trader_exists "$address"; then
    log_error "Trader not found for address: $address"
    exit 1
  fi

  local trader_name=$(get_trader_name "$address")
  local pod_name="$trader_name-0"

  log_info "Showing logs for: $pod_name"
  echo ""

  if [ "$follow" = true ]; then
    kubectl logs -n "$NAMESPACE" "$pod_name" -f --tail="$tail_lines"
  else
    kubectl logs -n "$NAMESPACE" "$pod_name" --tail="$tail_lines"
  fi
}

# Restart trader
cmd_restart() {
  local address="$1"

  if [ -z "$address" ]; then
    log_error "Address required"
    usage
    exit 1
  fi

  if ! validate_address "$address"; then
    exit 1
  fi

  if ! trader_exists "$address"; then
    log_error "Trader not found for address: $address"
    exit 1
  fi

  local trader_name=$(get_trader_name "$address")
  local pod_name="$trader_name-0"

  log_info "Restarting trader: $trader_name"
  kubectl delete pod "$pod_name" -n "$NAMESPACE"

  log_success "Pod deleted, StatefulSet will recreate it"
  log_info "Check status with: $0 status $address"
}

# Update trader configuration
cmd_update() {
  local address=""
  local config_file=""

  # Parse arguments
  while [[ $# -gt 0 ]]; do
    case $1 in
    --address)
      address="$2"
      shift 2
      ;;
    --config)
      config_file="$2"
      shift 2
      ;;
    *)
      log_error "Unknown option: $1"
      usage
      exit 1
      ;;
    esac
  done

  if [ -z "$address" ] || [ -z "$config_file" ]; then
    log_error "Missing required arguments"
    usage
    exit 1
  fi

  if ! validate_address "$address"; then
    exit 1
  fi

  if ! trader_exists "$address"; then
    log_error "Trader not found for address: $address"
    exit 1
  fi

  # Validate config
  log_info "Validating new config..."
  set +e  # Temporarily disable exit on error
  local config_address=$(validate_config "$config_file")
  local validation_result=$?
  set -e  # Re-enable exit on error
  
  if [ $validation_result -ne 0 ]; then
    log_error "Config validation failed. Please fix the errors above and try again."
    exit 1
  fi

  if [ "$config_address" != "$address" ]; then
    log_error "Address mismatch: --address=$address but config has $config_address"
    exit 1
  fi

  local trader_name=$(get_trader_name "$address")
  local instance_dir="$INSTANCES_DIR/$trader_name"

  log_info "Updating ConfigMap for trader: $trader_name"

  # Backup old config
  if [ -f "$instance_dir/config.json" ]; then
    cp "$instance_dir/config.json" "$instance_dir/config.json.backup"
  fi

  # Update config
  cp "$config_file" "$instance_dir/config.json"

  # Recreate ConfigMap
  local config_json=$(cat "$config_file")

  cat >"$instance_dir/configmap.yaml" <<EOF
apiVersion: v1
kind: ConfigMap
metadata:
  name: $trader_name-config
  namespace: hyper-trader
  labels:
    app: hyper-trader
    trader-address: "$address"
    managed-by: trader-ctl
data:
  config.json: |
$(echo "$config_json" | sed 's/^/    /')
EOF

  kubectl apply -f "$instance_dir/configmap.yaml"

  log_success "ConfigMap updated"
  log_info "Restarting pod to apply changes..."

  kubectl delete pod "$trader_name-0" -n "$NAMESPACE"

  log_success "Update complete"
  log_info "Check status with: $0 status $address"
}

# Main command dispatcher
main() {
  if [ $# -eq 0 ]; then
    usage
    exit 1
  fi

  local command="$1"
  shift

  # Allow help command without checking dependencies
  case "$command" in
  help | --help | -h)
    usage
    exit 0
    ;;
  esac

  # Check dependencies for all other commands
  check_dependencies

  case "$command" in
  add)
    cmd_add "$@"
    ;;
  remove)
    cmd_remove "$@"
    ;;
  list)
    cmd_list "$@"
    ;;
  status)
    cmd_status "$@"
    ;;
  logs)
    cmd_logs "$@"
    ;;
  restart)
    cmd_restart "$@"
    ;;
  update)
    cmd_update "$@"
    ;;
  *)
    log_error "Unknown command: $command"
    usage
    exit 1
    ;;
  esac
}

main "$@"
