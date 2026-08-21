#!/usr/bin/env bash
# Runline full-stack development launcher.
#
# Usage:
#   ./dev.sh            # start the complete stack
#   ./dev.sh up         # same as above
#   ./dev.sh down       # stop the stack, keep database/Redis volumes
#   ./dev.sh restart    # restart the stack
#   ./dev.sh rebuild    # rebuild images without cache, then start
#   ./dev.sh reset      # delete local volumes and start from a clean state
#   ./dev.sh status     # service status
#   ./dev.sh logs       # follow all logs
#   ./dev.sh logs api   # follow one service
#   ./dev.sh doctor     # connectivity diagnostics
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

COMMAND="${1:-up}"
SERVICE="${2:-}"
COMPOSE=(docker compose -f "$SCRIPT_DIR/docker-compose.yml")

require_docker() {
  if ! command -v docker >/dev/null 2>&1; then
    echo "ERROR: docker is not installed or not in PATH." >&2
    exit 1
  fi
  if ! docker info >/dev/null 2>&1; then
    echo "ERROR: Docker Desktop is not running." >&2
    exit 1
  fi
  if ! docker compose version >/dev/null 2>&1; then
    echo "ERROR: Docker Compose v2 is required (docker compose ...)." >&2
    exit 1
  fi
}

wait_for_url() {
  local name="$1"
  local url="$2"
  local attempts="${3:-60}"

  if ! command -v curl >/dev/null 2>&1; then
    echo "curl is unavailable; skipping host-side $name readiness check."
    return 0
  fi

  printf 'Waiting for %s' "$name"
  for ((i=1; i<=attempts; i++)); do
    if curl -fsS --max-time 2 "$url" >/dev/null 2>&1; then
      echo " ready"
      return 0
    fi
    printf '.'
    sleep 1
  done
  echo
  echo "ERROR: $name did not become ready: $url" >&2
  return 1
}

print_urls() {
  cat <<'MSG'

Runline is up:
  UI:        http://localhost:3000
  API:       http://localhost:8000
  API ready: http://localhost:8000/ready

Useful commands:
  ./dev.sh status
  ./dev.sh logs api
  ./dev.sh logs worker
  ./dev.sh down
MSG
}

start_stack() {
  local build_mode="${1:-normal}"
  if [[ "$build_mode" == "nocache" ]]; then
    "${COMPOSE[@]}" build --no-cache
    "${COMPOSE[@]}" up -d --remove-orphans
  else
    "${COMPOSE[@]}" up --build -d --remove-orphans
  fi

  if ! wait_for_url "API" "http://127.0.0.1:8000/ready" 60; then
    "${COMPOSE[@]}" ps >&2 || true
    "${COMPOSE[@]}" logs --tail=120 postgres redis seed api >&2 || true
    exit 1
  fi

  if ! wait_for_url "console" "http://127.0.0.1:3000" 90; then
    "${COMPOSE[@]}" ps >&2 || true
    "${COMPOSE[@]}" logs --tail=120 console api >&2 || true
    exit 1
  fi

  print_urls
}

require_docker

case "$COMMAND" in
  up|start)
    start_stack normal
    ;;
  down|stop)
    "${COMPOSE[@]}" down --remove-orphans
    ;;
  restart)
    "${COMPOSE[@]}" down --remove-orphans
    start_stack normal
    ;;
  rebuild)
    start_stack nocache
    ;;
  reset)
    echo "Removing Runline containers and local development volumes..."
    "${COMPOSE[@]}" down -v --remove-orphans
    start_stack normal
    ;;
  status|ps)
    "${COMPOSE[@]}" ps
    ;;
  logs)
    if [[ -n "$SERVICE" ]]; then
      "${COMPOSE[@]}" logs -f --tail=200 "$SERVICE"
    else
      "${COMPOSE[@]}" logs -f --tail=200
    fi
    ;;
  doctor)
    echo "== Docker Compose config =="
    "${COMPOSE[@]}" config --quiet
    echo "OK"
    echo
    echo "== Services =="
    "${COMPOSE[@]}" ps
    echo
    echo "== API =="
    if command -v curl >/dev/null 2>&1; then
      curl -fsS --max-time 3 http://127.0.0.1:8000/live || true
      echo
      curl -fsS --max-time 3 http://127.0.0.1:8000/ready || true
      echo
    else
      echo "curl not installed; skipping host HTTP checks"
    fi
    echo
    echo "== Recent API logs =="
    "${COMPOSE[@]}" logs --tail=50 api || true
    echo
    echo "== Recent worker logs =="
    "${COMPOSE[@]}" logs --tail=50 worker || true
    ;;
  help|-h|--help)
    sed -n '2,14p' "$0" | sed 's/^# \{0,1\}//'
    ;;
  *)
    echo "Unknown command: $COMMAND" >&2
    echo "Usage: ./dev.sh [up|down|restart|rebuild|reset|status|logs [service]|doctor]" >&2
    exit 2
    ;;
esac
