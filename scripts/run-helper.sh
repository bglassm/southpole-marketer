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

KEYWORDS="${1:-kbeauty,oliveyoung}"
DAYS="${2:-7}"
SLUG="${3:-manual}"
SOURCE="${4:-run-helper}"

N8N_URL="${N8N_URL:-http://localhost:${N8N_PORT:-5678}}"
PIPELINE_URL="${PIPELINE_URL:-http://localhost:${PIPELINE_PORT:-8080}}"
DEFAULT_WEBHOOK_PATH="${N8N_WEBHOOK_PATH:-southpole/run-pipeline}"
WORKFLOW_FILE="${N8N_WORKFLOW_FILE:-n8n/workflows/southpole_run_pipeline.json}"
WEBHOOK_DB_PATH="${N8N_DB_PATH:-state/n8n/database.sqlite}"

discover_workflow_id() {
  local workflow_file="$1"
  if [[ ! -f "$workflow_file" ]]; then
    return 0
  fi
  python3 - "$workflow_file" <<'PY'
import json
import sys

path = sys.argv[1]
with open(path, "r", encoding="utf-8") as handle:
    payload = json.load(handle)

workflow_id = payload.get("id", "")
if isinstance(workflow_id, str):
    print(workflow_id)
PY
}

discover_webhook_path_from_db() {
  local db_path="$1"
  local workflow_id="$2"
  if [[ -z "$workflow_id" || ! -f "$db_path" ]]; then
    return 0
  fi
  python3 - "$db_path" "$workflow_id" <<'PY'
import sqlite3
import sys

db_path = sys.argv[1]
workflow_id = sys.argv[2]

conn = sqlite3.connect(db_path)
cur = conn.cursor()
row = cur.execute(
    """
    SELECT webhookPath
    FROM webhook_entity
    WHERE workflowId = ?
      AND method = 'POST'
    ORDER BY rowid DESC
    LIMIT 1
    """,
    (workflow_id,),
).fetchone()
conn.close()

if row and row[0]:
    print(row[0])
PY
}

payload="$(cat <<JSON
{
  "keywords": "$KEYWORDS",
  "days": $DAYS,
  "slug": "$SLUG",
  "source": "$SOURCE"
}
JSON
)"

webhook_path="$DEFAULT_WEBHOOK_PATH"
workflow_id="$(discover_workflow_id "$WORKFLOW_FILE")"
discovered_path="$(discover_webhook_path_from_db "$WEBHOOK_DB_PATH" "$workflow_id")"
if [[ -n "${discovered_path:-}" ]]; then
  webhook_path="$discovered_path"
fi

n8n_webhook_url="${N8N_URL}/webhook/${webhook_path}"
response_file="$(mktemp /tmp/southpole_run_helper_n8n.XXXXXX.json)"
trap 'rm -f "$response_file"' EXIT

n8n_status="$(curl -sS \
  -o "$response_file" \
  -w "%{http_code}" \
  -H "Content-Type: application/json" \
  -X POST "${n8n_webhook_url}" \
  -d "$payload" || true)"

if [[ "$n8n_status" =~ ^2 ]]; then
  cat "$response_file"
  echo
  echo "Triggered via n8n webhook (${n8n_webhook_url})."
  exit 0
fi

echo "n8n webhook returned HTTP ${n8n_status:-unknown} at ${n8n_webhook_url}."
if [[ -s "$response_file" ]]; then
  echo "n8n response: $(cat "$response_file")"
fi
echo "Falling back to direct pipeline execution."
curl -fsS \
  -H "Content-Type: application/json" \
  -X POST "${PIPELINE_URL}/run" \
  -d "$payload"
echo
