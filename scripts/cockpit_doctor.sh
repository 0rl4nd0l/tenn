#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CONFIG_FILE="${REPO_ROOT}/scripts/start_config.env"

if [[ -f "${CONFIG_FILE}" ]]; then
  # shellcheck disable=SC1090
  source "${CONFIG_FILE}"
fi

echo "🩺 Tenn System Doctor"

ENGINE_ROOT="${ENGINE_ROOT:-${REPO_ROOT}/financial-engine_v2}"
COMPOSE_FILE="${COMPOSE_FILE:-${ENGINE_ROOT}/docker-compose.yml}"

COMPOSE_ENV_PATH="${COMPOSE_ENV_FILE:-.env}"
if [[ "${COMPOSE_ENV_PATH}" != /* ]]; then
  COMPOSE_ENV_PATH="${ENGINE_ROOT}/${COMPOSE_ENV_PATH}"
fi

BACKEND_HEALTH_URL="${BACKEND_HEALTH_URL:-http://127.0.0.1:8000/api/health}"
OLLAMA_URL_HOST="${OLLAMA_URL_HOST:-http://127.0.0.1:11434}"

echo ""
echo "⚙️  Config:"
echo "  scripts/start_config.env: ${CONFIG_FILE}"
echo "  ENGINE_ROOT: ${ENGINE_ROOT}"
echo "  COMPOSE_FILE: ${COMPOSE_FILE}"
echo "  COMPOSE_ENV_FILE: ${COMPOSE_ENV_PATH}"
echo "  BACKEND_HEALTH_URL: ${BACKEND_HEALTH_URL}"
echo "  OLLAMA_URL_HOST: ${OLLAMA_URL_HOST}"

echo ""
echo "🐳 Docker:"
if command -v docker >/dev/null 2>&1; then
  echo "✅ Docker installed"
  if docker info >/dev/null 2>&1; then
    echo "✅ Docker daemon reachable"
  else
    echo "❌ Docker daemon not reachable (check permissions / service)"
  fi
else
  echo "❌ Docker missing"
fi

echo ""
echo "📦 Containers:"
if command -v docker >/dev/null 2>&1 && [[ -f "${COMPOSE_FILE}" ]]; then
  (cd "${ENGINE_ROOT}" && docker compose --env-file "${COMPOSE_ENV_PATH}" -f "${COMPOSE_FILE}" ps) || true
else
  echo "⚠️  compose file not found; skipping container status"
fi

echo ""
echo "🌐 Backend:"
if command -v curl >/dev/null 2>&1; then
  if curl -fsS "${BACKEND_HEALTH_URL}" >/dev/null 2>&1; then
    echo "✅ Backend healthy"
  else
    echo "❌ Backend not reachable at ${BACKEND_HEALTH_URL}"
  fi
else
  echo "❌ curl missing (cannot check backend health)"
fi

echo ""
echo "📊 RAG Runtime Check:"
if command -v curl >/dev/null 2>&1; then
  if curl -s http://127.0.0.1:8000/api/health | grep -q '"rag_enabled":'; then
    curl -s http://127.0.0.1:8000/api/health | grep '"rag_enabled"'
  else
    echo "⚠️  Backend does not expose rag_enabled"
  fi
else
  echo "❌ curl missing (cannot check backend health payload)"
fi

echo ""
echo "🧠 Ollama:"
if command -v curl >/dev/null 2>&1; then
  if curl -fsS "${OLLAMA_URL_HOST}" >/dev/null 2>&1; then
    echo "✅ Ollama reachable"
  else
    echo "❌ Ollama not reachable at ${OLLAMA_URL_HOST}"
  fi
else
  echo "❌ curl missing (cannot check Ollama)"
fi

echo ""
echo "🐍 Python:"
if [[ -x "${ENGINE_ROOT}/.venv/bin/python" ]]; then
  echo "✅ Using ${ENGINE_ROOT}/.venv/bin/python"
else
  if command -v python3 >/dev/null 2>&1; then
    echo "⚠️  No ${ENGINE_ROOT}/.venv found; using $(command -v python3)"
  else
    echo "❌ python3 missing"
  fi
fi

echo ""
echo "📊 RAG Status:"
echo "ENABLE_EMBEDDINGS=${ENABLE_EMBEDDINGS_ON_STARTUP:-}"
echo "ENABLE_QDRANT=${ENABLE_QDRANT_ON_STARTUP:-}"

echo ""
echo "🔌 Port conflicts:"
check_port() {
  local port="$1"
  local label="$2"
  if command -v docker >/dev/null 2>&1; then
    if docker ps --format '{{.Names}} {{.Ports}}' 2>/dev/null | grep -E "0\\.0\\.0\\.0:${port}->|\\[::\\]:${port}->" >/dev/null 2>&1; then
      echo "⚠️  ${label} port ${port} published by container"
      docker ps --format '{{.Names}} {{.Ports}}' | grep -E "0\\.0\\.0\\.0:${port}->|\\[::\\]:${port}->" || true
      return
    fi
  fi
  if command -v lsof >/dev/null 2>&1; then
    if lsof -i ":${port}" >/dev/null 2>&1; then
      echo "⚠️  ${label} port ${port} in use"
    else
      echo "✅ ${label} port ${port} free"
    fi
    return
  fi
  if command -v ss >/dev/null 2>&1; then
    if ss -ltn 2>/dev/null | awk '{print $4}' | grep -q ":${port}$"; then
      echo "⚠️  ${label} port ${port} in use"
    else
      echo "✅ ${label} port ${port} free"
    fi
    return
  fi
  echo "⚠️  cannot detect port ${port} usage (missing lsof/ss)"
}

check_port 8000 "Backend"
check_port 5432 "Postgres"
check_port 6379 "Redis"
check_port 6333 "Qdrant"
check_port 11434 "Ollama"

echo ""
echo "🔗 URL sanity (docker vs host):"
if [[ -f "${COMPOSE_ENV_PATH}" ]]; then
  ollama_env="$(grep -E '^[[:space:]]*OLLAMA_URL=' "${COMPOSE_ENV_PATH}" 2>/dev/null | tail -n 1 | cut -d= -f2- || true)"
  llamacpp_env="$(grep -E '^[[:space:]]*LLAMACPP_URL=' "${COMPOSE_ENV_PATH}" 2>/dev/null | tail -n 1 | cut -d= -f2- || true)"
  if [[ -n "${ollama_env}" ]]; then
    echo "  .env OLLAMA_URL=${ollama_env}"
    if [[ "${ollama_env}" == *"127.0.0.1"* || "${ollama_env}" == *"localhost"* ]]; then
      echo "  ⚠️  OLLAMA_URL points to localhost; containers cannot reach host via localhost"
    fi
  else
    echo "  ⚠️  .env missing OLLAMA_URL"
  fi
  if [[ -n "${llamacpp_env}" ]]; then
    echo "  .env LLAMACPP_URL=${llamacpp_env}"
    if [[ "${llamacpp_env}" == *"127.0.0.1"* || "${llamacpp_env}" == *"localhost"* ]]; then
      echo "  ⚠️  LLAMACPP_URL points to localhost; containers cannot reach host via localhost"
    fi
  fi
else
  echo "  ⚠️  env file not found: ${COMPOSE_ENV_PATH}"
fi

