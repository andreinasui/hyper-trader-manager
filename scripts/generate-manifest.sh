#!/usr/bin/env bash
# scripts/generate-manifest.sh
# Generates environments/prod/manifest.json describing the host files
# that the update helper should manage.
#
# Usage:
#   scripts/generate-manifest.sh <version>
#     where <version> is the bare version number, e.g. 0.2.7 (no leading 'v').
set -euo pipefail

VERSION="${1:?usage: $0 <version>}"

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
OUT="${REPO_ROOT}/environments/prod/manifest.json"

# Canonical host-file list. Each row: <repo-source>|<install-path>|<mode>|<owner-tag>
# - repo-source : path within this repo at the release tag.
# - install-path: path under /opt/hyper-trader on the VPS.
# - mode        : octal mode the file should have on disk.
# - owner-tag   : "user" (resolved at runtime to install-dir owner) or "uid:1000".
FILES=(
  "environments/prod/docker-compose.yml|docker-compose.yml|0644|user"
  "environments/prod/traefik/traefik.template.yml|traefik/traefik.yml|0644|uid:1000"
  "environments/prod/traefik/dynamic/00-bootstrap.yml|traefik/dynamic/00-bootstrap.yml|0644|uid:1000"
  "scripts/hyper-trader-manager.sh|bin/hyper-trader-manager|0755|user"
)

ENV_SCHEMAS=(
  ".env|environments/prod/.env.example"
  "api.env|environments/prod/api.env.example"
)

sha256() {
  # Portable: use shasum if available, else sha256sum.
  if command -v sha256sum >/dev/null 2>&1; then
    sha256sum "$1" | awk '{print $1}'
  else
    shasum -a 256 "$1" | awk '{print $1}'
  fi
}

files_json="["
first=1
for row in "${FILES[@]}"; do
  IFS='|' read -r src path mode owner <<< "$row"
  abs="${REPO_ROOT}/${src}"
  [[ -f "$abs" ]] || { echo "missing: $abs" >&2; exit 1; }
  hash="$(sha256 "$abs")"
  [[ $first -eq 1 ]] || files_json+=","
  first=0
  files_json+=$(printf '\n    {"path":"%s","source":"%s","sha256":"%s","mode":"%s","owner":"%s"}' \
    "$path" "$src" "$hash" "$mode" "$owner")
done
files_json+="\n  ]"

env_json="["
first=1
for row in "${ENV_SCHEMAS[@]}"; do
  IFS='|' read -r path src <<< "$row"
  abs="${REPO_ROOT}/${src}"
  [[ -f "$abs" ]] || { echo "missing: $abs" >&2; exit 1; }
  [[ $first -eq 1 ]] || env_json+=","
  first=0
  env_json+=$(printf '\n    {"path":"%s","source":"%s"}' "$path" "$src")
done
env_json+="\n  ]"

mkdir -p "$(dirname "$OUT")"
printf '{\n  "version": "%s",\n  "files": %b,\n  "env_schemas": %b\n}\n' \
  "$VERSION" "$files_json" "$env_json" > "$OUT"

echo "wrote $OUT"
