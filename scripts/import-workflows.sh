#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

if [[ -f .env ]]; then
  set -a
  # shellcheck disable=SC1091
  source .env
  set +a
fi

WORKFLOW_MOUNT_DIR="${N8N_WORKFLOW_MOUNT_DIR:-/workspace/n8n/workflows}"

if docker compose version >/dev/null 2>&1; then
  DC=(docker compose)
elif command -v docker-compose >/dev/null 2>&1; then
  DC=(docker-compose)
else
  echo "Docker Compose is not available."
  exit 1
fi

wait_for_http() {
  local name="$1"
  local url="$2"
  local timeout_seconds="$3"
  local accepted_codes="$4"
  local started_at="$SECONDS"
  local code=""

  while (( SECONDS - started_at < timeout_seconds )); do
    code="$(curl -sS -o /dev/null -w "%{http_code}" "$url" || true)"
    for accepted in $accepted_codes; do
      if [[ "$code" == "$accepted" ]]; then
        return 0
      fi
    done
    sleep 2
  done

  echo "$name was not ready within ${timeout_seconds}s (last HTTP status: ${code:-none})."
  return 1
}

show_n8n_diagnostics() {
  echo "n8n diagnostics:"
  "${DC[@]}" ps n8n || true
  "${DC[@]}" logs --tail=120 n8n || true
  if "${DC[@]}" logs --tail=120 n8n 2>/dev/null | grep -q "Mismatching encryption keys"; then
    echo
    echo "Detected n8n encryption key mismatch with persisted state."
    echo "Reset local n8n state, then start/import again:"
    echo "  bash scripts/down.sh"
    echo "  rm -rf state/n8n/*"
    echo "  touch state/n8n/.gitkeep"
    echo "  bash scripts/up.sh"
    echo "  bash scripts/import-workflows.sh"
  fi
}

if ! "${DC[@]}" ps --services 2>/dev/null | grep -qx "n8n"; then
  echo "n8n container is not available. Run scripts/up.sh first."
  exit 1
fi

if ! wait_for_http "n8n" "http://localhost:${N8N_PORT:-5678}/healthz" 300 "200"; then
  show_n8n_diagnostics
  exit 1
fi

container_state="$(docker inspect -f '{{.State.Status}}' southpole-n8n 2>/dev/null || true)"
if [[ "$container_state" != "running" ]]; then
  echo "n8n container is not running (state: ${container_state:-unknown})."
  show_n8n_diagnostics
  exit 1
fi

import_one() {
  local file="$1"
  local attempt=1
  local max_attempts=5
  local container_file="${WORKFLOW_MOUNT_DIR}/$(basename "$file")"

  while (( attempt <= max_attempts )); do
    if "${DC[@]}" exec -T n8n n8n import:workflow --input="$container_file"; then
      return 0
    fi
    if (( attempt == max_attempts )); then
      return 1
    fi
    sleep 3
    attempt=$((attempt + 1))
  done
}

extract_workflow_id() {
  local file="$1"
  python3 - "$file" <<'PY'
import json
import sys

path = sys.argv[1]
with open(path, "r", encoding="utf-8") as handle:
    payload = json.load(handle)

workflow_id = payload.get("id", "")
print(workflow_id if isinstance(workflow_id, str) else "")
PY
}

publish_workflow() {
  local workflow_id="$1"
  local attempt=1
  local max_attempts=5

  while (( attempt <= max_attempts )); do
    if "${DC[@]}" exec -T n8n n8n publish:workflow --id="$workflow_id"; then
      return 0
    fi
    if (( attempt == max_attempts )); then
      return 1
    fi
    sleep 3
    attempt=$((attempt + 1))
  done
}

shopt -s nullglob
workflow_files=(n8n/workflows/*.json)
if [[ "${#workflow_files[@]}" -eq 0 ]]; then
  echo "No workflow JSON files found in n8n/workflows."
  exit 1
fi

published_any=0
for file in "${workflow_files[@]}"; do
  echo "Importing $file"
  if ! import_one "$file"; then
    echo "Failed to import $file after retries."
    show_n8n_diagnostics
    exit 1
  fi

  workflow_id="$(extract_workflow_id "$file")"
  if [[ -n "$workflow_id" ]]; then
    echo "Publishing workflow $workflow_id"
    if ! publish_workflow "$workflow_id"; then
      echo "Failed to publish workflow $workflow_id after retries."
      show_n8n_diagnostics
      exit 1
    fi
    published_any=1
  fi
done

if [[ "$published_any" -eq 1 ]]; then
  echo "Restarting n8n to apply published workflow webhooks."
  "${DC[@]}" restart n8n >/dev/null
  if ! wait_for_http "n8n" "http://localhost:${N8N_PORT:-5678}/healthz" 300 "200"; then
    show_n8n_diagnostics
    exit 1
  fi
fi

echo "Workflow import complete."
