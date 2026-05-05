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

"${DC[@]}" config >/dev/null
"${DC[@]}" build pipeline >/dev/null

verify_output_file="$(mktemp /tmp/southpole_verify_output.XXXXXX.json)"
trap 'rm -f "$verify_output_file"' EXIT

"${DC[@]}" run --rm pipeline \
  python -m southpole_pipeline.cli run \
  --keywords "kbeauty,oliveyoung" \
  --days 7 \
  --slug verify \
  --mock-file /app/fixtures/mock_apify_items.json >"$verify_output_file"

latest_run_dir="$(python3 - "$verify_output_file" <<'PY'
import json
import sys

with open(sys.argv[1], "r", encoding="utf-8") as handle:
    payload = json.load(handle)

run_dir = payload.get("files", {}).get("runDir", "")
print(run_dir)
PY
)"

if [[ -z "${latest_run_dir:-}" ]]; then
  echo "No run directory was reported by pipeline output."
  exit 1
fi

if [[ ! -d "$latest_run_dir" ]]; then
  echo "Reported run directory does not exist: $latest_run_dir"
  exit 1
fi

required_files=(
  "report.html"
  "summary.json"
  "keyword_totals.csv"
  "creators.csv"
  "daily_metrics.csv"
  "raw_events.jsonl"
  "raw_events.csv"
  "raw/source_items.jsonl"
  "normalized/content_items.csv"
  "normalized/creator_profiles.csv"
)

for f in "${required_files[@]}"; do
  if [[ ! -f "$latest_run_dir/$f" ]]; then
    echo "Missing required output: $latest_run_dir/$f"
    exit 1
  fi
done

if ! ls "$latest_run_dir"/southpole_run_*.xlsx >/dev/null 2>&1; then
  echo "Missing workbook output in $latest_run_dir"
  exit 1
fi

echo "Verification passed."
echo "Latest run: $latest_run_dir"
