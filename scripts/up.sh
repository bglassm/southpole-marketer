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

show_n8n_startup_diagnostics() {
  echo "n8n diagnostics:"
  "${DC[@]}" ps n8n || true
  "${DC[@]}" logs --tail=120 n8n || true
  if "${DC[@]}" logs --tail=120 n8n 2>/dev/null | grep -q "Mismatching encryption keys"; then
    echo
    echo "Detected n8n encryption key mismatch with persisted state."
    echo "To reset local n8n state for a clean install, run:"
    echo "  bash scripts/down.sh"
    echo "  rm -rf state/n8n/*"
    echo "  touch state/n8n/.gitkeep"
    echo "  bash scripts/up.sh"
  fi
}

mkdir -p outputs/runs state/n8n data

"${DC[@]}" up -d --build

if ! wait_for_http "n8n" "http://localhost:${N8N_PORT:-5678}/healthz" 300 "200"; then
  show_n8n_startup_diagnostics
  exit 1
fi

if ! wait_for_http "pipeline" "http://localhost:${PIPELINE_PORT:-8080}/health" 120 "200"; then
  echo "pipeline diagnostics:"
  "${DC[@]}" ps pipeline || true
  "${DC[@]}" logs --tail=120 pipeline || true
  exit 1
fi

echo "Southpole stack is up."
echo "n8n: http://localhost:${N8N_PORT:-5678}"
echo "pipeline health: http://localhost:${PIPELINE_PORT:-8080}/health"
echo "operator ui: http://localhost:${PIPELINE_PORT:-8080}/ui"
