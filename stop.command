#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT_DIR"

if ! command -v docker >/dev/null 2>&1; then
  printf '%s\n' "Docker CLI is not installed. Nothing to stop."
  exit 1
fi

printf '%s\n' "Stopping Southpole stack..."
if bash scripts/down.sh; then
  printf '%s\n' "Southpole stack stopped successfully."
else
  printf '%s\n' "Failed to stop Southpole stack."
  exit 1
fi
