#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DOCKER_DIR="$ROOT/docker"

cd "$DOCKER_DIR"

# Reuse existing external volumes when present.
# If missing, create empty volumes with the same names (data reset for instance #2).
for v in n8n_instance2_n8n2_data n8n_instance2_postgres2_data; do
  if ! docker volume inspect "$v" >/dev/null 2>&1; then
    echo "[WARN] Volume $v not found. Creating empty volume (instance #2 data will be fresh)."
    docker volume create "$v" >/dev/null
  fi
done

docker compose -f docker-compose.instance2.yml up -d
