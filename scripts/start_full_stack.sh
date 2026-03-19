#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CONFIG_FILE="${REPO_ROOT}/scripts/start_config.env"

if [[ ! -f "${CONFIG_FILE}" ]]; then
  echo "ERROR: missing config: ${CONFIG_FILE}" >&2
  exit 1
fi

# shellcheck disable=SC1090
source "${CONFIG_FILE}"

echo "🔍 Running preflight checks..."

command -v docker >/dev/null || { echo "ERROR: docker missing"; exit 1; }
command -v curl >/dev/null || { echo "ERROR: curl missing"; exit 1; }

if ! docker info >/dev/null 2>&1; then
  echo "ERROR: docker daemon not running or not accessible" >&2
  exit 1
fi

check_port_free() {
  local port="$1"
  local label="$2"
  local expected_container="${3:-}"
  if command -v docker >/dev/null 2>&1; then
    if docker ps --format '{{.Names}} {{.Ports}}' 2>/dev/null | grep -E "0\\.0\\.0\\.0:${port}->|\\[::\\]:${port}->" >/dev/null 2>&1; then
      # If the port is already published by the expected docker service container, don't fail.
      if [[ -n "${expected_container}" ]] && docker ps --format '{{.Names}} {{.Ports}}' 2>/dev/null | grep -E "^${expected_container} " >/dev/null 2>&1; then
        echo "⚠️  ${label} port ${port} already published by ${expected_container} (continuing)"
        return 0
      fi
      echo "ERROR: ${label} port ${port} already published by an unexpected container" >&2
      docker ps --format '{{.Names}} {{.Ports}}' | grep -E "0\\.0\\.0\\.0:${port}->|\\[::\\]:${port}->" || true
      exit 1
    fi
  fi
  if command -v lsof >/dev/null 2>&1; then
    if lsof -i ":${port}" >/dev/null 2>&1; then
      echo "ERROR: ${label} port ${port} already in use" >&2
      lsof -i ":${port}" || true
      exit 1
    fi
    return 0
  fi
  if command -v ss >/dev/null 2>&1; then
    if ss -ltn 2>/dev/null | awk '{print $4}' | grep -q ":${port}$"; then
      echo "ERROR: ${label} port ${port} already in use" >&2
      ss -ltnp 2>/dev/null | grep ":${port} " || true
      exit 1
    fi
    return 0
  fi
  echo "⚠️  cannot detect port ${port} usage (missing lsof/ss); proceeding" >&2
  return 0
}

if [[ -z "${ENGINE_ROOT:-}" ]]; then
  echo "ERROR: ENGINE_ROOT is empty (set in scripts/start_config.env)" >&2
  exit 1
fi
if [[ ! -d "${ENGINE_ROOT}" ]]; then
  echo "ERROR: ENGINE_ROOT not found: ${ENGINE_ROOT}" >&2
  exit 1
fi
if [[ -z "${COMPOSE_FILE:-}" ]]; then
  echo "ERROR: COMPOSE_FILE is empty (set in scripts/start_config.env)" >&2
  exit 1
fi
if [[ ! -f "${COMPOSE_FILE}" ]]; then
  echo "ERROR: compose file not found: ${COMPOSE_FILE}" >&2
  exit 1
fi

COMPOSE_ENV_PATH="${COMPOSE_ENV_FILE:-.env}"
if [[ "${COMPOSE_ENV_PATH}" != /* ]]; then
  COMPOSE_ENV_PATH="${ENGINE_ROOT}/${COMPOSE_ENV_PATH}"
fi

if [[ ! -f "${COMPOSE_ENV_PATH}" ]]; then
  EXAMPLE="${ENGINE_ROOT}/.env.example"
  if [[ -f "${EXAMPLE}" ]]; then
    cp "${EXAMPLE}" "${COMPOSE_ENV_PATH}"
    echo "created ${COMPOSE_ENV_PATH} from .env.example"
  else
    echo "ERROR: missing env file ${COMPOSE_ENV_PATH} (and no .env.example found)" >&2
    exit 1
  fi
fi

# Fail fast on common host port conflicts (compose publishes these).
check_port_free 8000 "Backend" "fe_backend"
check_port_free 5432 "Postgres" "fe_postgres"
check_port_free 6379 "Redis" "fe_redis"
check_port_free 6333 "Qdrant" "fe_qdrant"

if [[ -n "${OLLAMA_URL_HOST:-}" ]]; then
  if ! curl -fsS "${OLLAMA_URL_HOST}" >/dev/null 2>&1; then
    echo "⚠️  Ollama not reachable at ${OLLAMA_URL_HOST}"
  fi
fi

COMPOSE=(docker compose --env-file "${COMPOSE_ENV_PATH}" -f "${COMPOSE_FILE}")
if [[ -n "${COMPOSE_EXTRA_ARGS:-}" ]]; then
  # shellcheck disable=SC2206
  COMPOSE+=(${COMPOSE_EXTRA_ARGS})
fi

SERVICES_ARG=()
if [[ -n "${COMPOSE_SERVICES:-}" ]]; then
  IFS=',' read -r -a _SVC <<< "${COMPOSE_SERVICES}"
  for s in "${_SVC[@]}"; do
    s="$(echo "${s}" | xargs)"
    [[ -n "${s}" ]] && SERVICES_ARG+=("${s}")
  done
fi

cd "${ENGINE_ROOT}"

echo "starting full stack via docker compose..."
if [[ "${#SERVICES_ARG[@]}" -gt 0 ]]; then
  "${COMPOSE[@]}" up -d --build "${SERVICES_ARG[@]}"
else
  "${COMPOSE[@]}" up -d --build
fi

echo "running migrations..."
if "${COMPOSE[@]}" ps backend >/dev/null 2>&1; then
  "${COMPOSE[@]}" exec -T backend alembic upgrade head
else
  echo "ERROR: backend service missing from compose; cannot run migrations" >&2
  exit 1
fi

echo "waiting for backend health..."
deadline=$(( $(date +%s) + ${BACKEND_START_TIMEOUT:-60} ))
while true; do
  if curl -fsS "${BACKEND_HEALTH_URL}" >/dev/null 2>&1; then
    echo "✅ Backend healthy: ${BACKEND_HEALTH_URL}"
    break
  fi
  if [[ "$(date +%s)" -ge "${deadline}" ]]; then
    echo "ERROR: backend did not become healthy within ${BACKEND_START_TIMEOUT:-60}s: ${BACKEND_HEALTH_URL}" >&2
    exit 1
  fi
  sleep 1
done

