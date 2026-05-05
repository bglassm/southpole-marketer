#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT_DIR"

DOCKER_DOWNLOAD_URL="https://www.docker.com/products/docker-desktop/"
DOCKER_WAIT_SECONDS=240

if [[ -f .env ]]; then
  set -a
  # shellcheck disable=SC1091
  source .env
  set +a
fi

PIPELINE_PORT="${PIPELINE_PORT:-8080}"
UI_URL="http://localhost:${PIPELINE_PORT}/ui"

info() {
  printf '%s\n' "$1"
}

open_docker_download() {
  info "Docker Desktop is required but not installed."
  info "Opening Docker Desktop download page..."
  open "$DOCKER_DOWNLOAD_URL" || true
}

if ! command -v docker >/dev/null 2>&1; then
  open_docker_download
  exit 1
fi

if docker compose version >/dev/null 2>&1; then
  :
elif command -v docker-compose >/dev/null 2>&1; then
  :
else
  info "Docker Compose is not available. Please install Docker Desktop."
  open_docker_download
  exit 1
fi

docker_ready() {
  docker info >/dev/null 2>&1
}

if ! docker_ready; then
  info "Docker is installed but not running. Launching Docker Desktop..."
  open -ga Docker >/dev/null 2>&1 || open -a Docker >/dev/null 2>&1 || true

  started_at="$SECONDS"
  while (( SECONDS - started_at < DOCKER_WAIT_SECONDS )); do
    if docker_ready; then
      break
    fi
    sleep 2
  done
fi

if ! docker_ready; then
  info "Docker daemon did not become ready within ${DOCKER_WAIT_SECONDS}s."
  info "Please open Docker Desktop and try again."
  exit 1
fi

info "Docker is ready. Starting Southpole stack..."
if ! bash scripts/up.sh; then
  info "Southpole stack failed to start. Please check scripts/up.sh output."
  exit 1
fi

info "Opening Southpole Operator UI: ${UI_URL}"
open "$UI_URL" || true
info "Southpole is ready."
