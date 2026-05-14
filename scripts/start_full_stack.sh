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

PYTHON_BIN="$(command -v python3 2>/dev/null || command -v python 2>/dev/null)"
if [[ -z "${PYTHON_BIN}" ]]; then
  echo "ERROR: python3 or python required for Tenn storage guard" >&2
  exit 1
fi
"${PYTHON_BIN}" "${REPO_ROOT}/scripts/storage_guard.py" || exit 1

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
    # Check only LISTEN state — client connections to the port don't count as conflicts
    if lsof -i ":${port}" -sTCP:LISTEN >/dev/null 2>&1; then
      local proc_name
      proc_name="$(lsof -ti ":${port}" -sTCP:LISTEN 2>/dev/null | head -1 | xargs -r ps -o comm= -p 2>/dev/null || true)"
      local label_lower="${label,,}"
      if [[ "${proc_name,,}" == *"${label_lower}"* ]] || [[ "${label_lower}" == "postgres" && "${proc_name,,}" == *"postgres"* ]]; then
        echo "✅  ${label} port ${port} already running (host-native ${proc_name})"
        return 0
      fi
      echo "ERROR: ${label} port ${port} already in use by ${proc_name:-unknown}" >&2
      lsof -i ":${port}" -sTCP:LISTEN || true
      exit 1
    fi
    return 0
  fi
  if command -v ss >/dev/null 2>&1; then
    if ss -ltn 2>/dev/null | awk '{print $4}' | grep -q ":${port}$"; then
      # Check if it's the expected service
      local ss_proc
      ss_proc="$(ss -ltnp 2>/dev/null | grep ":${port} " | grep -oP 'users:\(\("\K[^"]+' || true)"
      local label_lower="${label,,}"
      if [[ "${ss_proc,,}" == *"${label_lower}"* ]] || [[ "${label_lower}" == "postgres" && "${ss_proc,,}" == *"postgres"* ]]; then
        echo "✅  ${label} port ${port} already running (host-native ${ss_proc})"
        return 0
      fi
      echo "ERROR: ${label} port ${port} already in use by ${ss_proc:-unknown}" >&2
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

# Deterministically set container-facing LLM endpoints required for backend startup.
set_env_key() {
  local key="$1"
  local value="$2"
  local file="$3"

  if grep -q "^${key}=" "${file}" 2>/dev/null; then
    sed -i "s|^${key}=.*|${key}=${value}|" "${file}"
  else
    printf '%s=%s\n' "${key}" "${value}" >> "${file}"
  fi
}

env_file_value() {
  local key="$1"
  local file="$2"
  grep -E "^${key}=" "${file}" 2>/dev/null | tail -n 1 | cut -d= -f2- || true
}

compose_images_available_for_services() {
  local -a services=("$@")
  local -a service_list=()
  local -a image_list=()
  local service image
  local i
  local found=0

  mapfile -t service_list < <("${COMPOSE[@]}" config --services)
  mapfile -t image_list < <("${COMPOSE[@]}" config --images)

  if [[ "${#service_list[@]}" -ne "${#image_list[@]}" ]]; then
    # As a safe fallback when compose output changes shape, require every listed image.
    while IFS= read -r image; do
      [[ -z "${image}" ]] && continue
      if ! docker image inspect "${image}" >/dev/null 2>&1; then
        return 1
      fi
    done < <("${COMPOSE[@]}" config --images)
    return 0
  fi

  if [[ "${#services[@]}" -eq 0 ]]; then
    services=("${service_list[@]}")
  fi

  for service in "${services[@]}"; do
    found=0
    for i in "${!service_list[@]}"; do
      if [[ "${service_list[i]}" == "${service}" ]]; then
        image="${image_list[i]}"
        found=1
        break
      fi
    done
    if [[ "${found}" -eq 0 ]]; then
      continue
    fi
    if ! docker image inspect "${image}" >/dev/null 2>&1; then
      return 1
    fi
  done
  return 0
}

compose_up_detached() {
  local -a services=("$@")
  local -a build_args=()
  local mode="${COMPOSE_BUILD_MODE:-auto}"
  case "${mode}" in
    auto|"")
      if compose_images_available_for_services "${services[@]}"; then
        build_args=(--no-build)
      else
        build_args=(--build)
      fi
      ;;
    never|no-build|false)
      build_args=(--no-build)
      ;;
    always|build|true)
      build_args=(--build)
      ;;
    *)
      build_args=(--build)
      ;;
  esac

  "${COMPOSE[@]}" up -d "${build_args[@]}" "${services[@]}"
}

export_git_provenance_env() {
  if ! command -v git >/dev/null 2>&1; then
    echo "WARN: git missing on host; backend git provenance env not exported" >&2
    return 0
  fi
  if ! git -C "${REPO_ROOT}" rev-parse --git-dir >/dev/null 2>&1; then
    echo "WARN: ${REPO_ROOT} is not a git checkout; backend git provenance env not exported" >&2
    return 0
  fi

  local head head_short branch status_line_count dirty build_time
  head="$(git -C "${REPO_ROOT}" rev-parse HEAD 2>/dev/null || true)"
  head_short="$(git -C "${REPO_ROOT}" rev-parse --short=12 HEAD 2>/dev/null || true)"
  branch="$(git -C "${REPO_ROOT}" branch --show-current 2>/dev/null || true)"
  if [[ -z "${branch}" ]]; then
    branch="DETACHED_HEAD"
  fi
  status_line_count="$(git -C "${REPO_ROOT}" status --short 2>/dev/null | wc -l | tr -d '[:space:]')"
  if [[ -z "${status_line_count}" ]]; then
    status_line_count="0"
  fi
  if [[ "${status_line_count}" -gt 0 ]]; then
    dirty="true"
  else
    dirty="false"
  fi
  build_time="$(date -u '+%Y-%m-%dT%H:%M:%SZ')"

  export TENN_GIT_HEAD="${TENN_GIT_HEAD:-${head}}"
  export TENN_GIT_HEAD_SHORT="${TENN_GIT_HEAD_SHORT:-${head_short}}"
  export TENN_GIT_BRANCH="${TENN_GIT_BRANCH:-${branch}}"
  export TENN_GIT_DIRTY="${TENN_GIT_DIRTY:-${dirty}}"
  export TENN_GIT_STATUS_LINE_COUNT="${TENN_GIT_STATUS_LINE_COUNT:-${status_line_count}}"
  export TENN_BUILD_TIME="${TENN_BUILD_TIME:-${build_time}}"

  echo "Exported backend git provenance: head=${TENN_GIT_HEAD_SHORT:-DATA_MISSING} branch=${TENN_GIT_BRANCH:-DATA_MISSING} dirty=${TENN_GIT_DIRTY:-DATA_MISSING}"
}

if [[ -n "${LLAMACPP_URL_CONTAINER:-}" ]]; then
  current_llamacpp="$(grep -E '^LLAMACPP_URL=' "${COMPOSE_ENV_PATH}" 2>/dev/null | tail -n 1 | cut -d= -f2- || true)"
  if [[ -z "${current_llamacpp}" || "${current_llamacpp}" != "${LLAMACPP_URL_CONTAINER}" ]]; then
    echo "🔧 Setting ${COMPOSE_ENV_PATH}: LLAMACPP_URL=${LLAMACPP_URL_CONTAINER}"
    set_env_key "LLAMACPP_URL" "${LLAMACPP_URL_CONTAINER}" "${COMPOSE_ENV_PATH}"
  fi
fi

if [[ -n "${OLLAMA_URL_CONTAINER:-}" ]]; then
  current_ollama="$(grep -E '^OLLAMA_URL=' "${COMPOSE_ENV_PATH}" 2>/dev/null | tail -n 1 | cut -d= -f2- || true)"
  if [[ -z "${current_ollama}" || "${current_ollama}" != "${OLLAMA_URL_CONTAINER}" ]]; then
    echo "🔧 Setting ${COMPOSE_ENV_PATH}: OLLAMA_URL=${OLLAMA_URL_CONTAINER}"
    set_env_key "OLLAMA_URL" "${OLLAMA_URL_CONTAINER}" "${COMPOSE_ENV_PATH}"
  fi
fi

if [[ -n "${EMBED_MODEL_ON_STARTUP:-}" ]]; then
  current_embed_model="$(grep -E '^EMBED_MODEL=' "${COMPOSE_ENV_PATH}" 2>/dev/null | tail -n 1 | cut -d= -f2- || true)"
  if [[ -z "${current_embed_model}" || "${current_embed_model}" != "${EMBED_MODEL_ON_STARTUP}" ]]; then
    echo "🔧 Setting ${COMPOSE_ENV_PATH}: EMBED_MODEL=${EMBED_MODEL_ON_STARTUP}"
    set_env_key "EMBED_MODEL" "${EMBED_MODEL_ON_STARTUP}" "${COMPOSE_ENV_PATH}"
  fi
fi

# Backend startup embeds/probes need EMBEDDING_API_KEY; default it to LLM_API_KEY if missing.
llm_api_key="$(grep -E '^LLM_API_KEY=' "${COMPOSE_ENV_PATH}" 2>/dev/null | tail -n 1 | cut -d= -f2- || true)"
if [[ -n "${llm_api_key}" ]]; then
  current_embedding_api_key="$(grep -E '^EMBEDDING_API_KEY=' "${COMPOSE_ENV_PATH}" 2>/dev/null | tail -n 1 | cut -d= -f2- || true)"
  if [[ -z "${current_embedding_api_key}" ]]; then
    echo "🔧 Setting ${COMPOSE_ENV_PATH}: EMBEDDING_API_KEY=${llm_api_key}"
    set_env_key "EMBEDDING_API_KEY" "${llm_api_key}" "${COMPOSE_ENV_PATH}"
  fi
fi

# Deterministic boot: write the requested runtime feature flags into the compose env file.
if [[ -n "${ENABLE_EMBEDDINGS_ON_STARTUP:-}" ]]; then
  echo "🔧 Setting ${COMPOSE_ENV_PATH}: ENABLE_EMBEDDINGS=${ENABLE_EMBEDDINGS_ON_STARTUP}"
  set_env_key "ENABLE_EMBEDDINGS" "${ENABLE_EMBEDDINGS_ON_STARTUP}" "${COMPOSE_ENV_PATH}"
fi
if [[ -n "${ENABLE_QDRANT_ON_STARTUP:-}" ]]; then
  echo "🔧 Setting ${COMPOSE_ENV_PATH}: ENABLE_QDRANT=${ENABLE_QDRANT_ON_STARTUP}"
  set_env_key "ENABLE_QDRANT" "${ENABLE_QDRANT_ON_STARTUP}" "${COMPOSE_ENV_PATH}"
fi
if [[ -n "${ENABLE_EXTRACTION_ON_STARTUP:-}" ]]; then
  echo "🔧 Setting ${COMPOSE_ENV_PATH}: ENABLE_EXTRACTION=${ENABLE_EXTRACTION_ON_STARTUP}"
  set_env_key "ENABLE_EXTRACTION" "${ENABLE_EXTRACTION_ON_STARTUP}" "${COMPOSE_ENV_PATH}"
fi
if [[ -n "${COCKPIT_STATE_DB_ON_STARTUP:-}" ]]; then
  echo "🔧 Setting ${COMPOSE_ENV_PATH}: COCKPIT_STATE_DB=${COCKPIT_STATE_DB_ON_STARTUP}"
  set_env_key "COCKPIT_STATE_DB" "${COCKPIT_STATE_DB_ON_STARTUP}" "${COMPOSE_ENV_PATH}"
fi
if [[ -n "${MARKETPLACE_BROWSER_RUNTIME_ON_STARTUP:-}" ]]; then
  echo "🔧 Setting ${COMPOSE_ENV_PATH}: MARKETPLACE_BROWSER_RUNTIME=${MARKETPLACE_BROWSER_RUNTIME_ON_STARTUP}"
  set_env_key "MARKETPLACE_BROWSER_RUNTIME" "${MARKETPLACE_BROWSER_RUNTIME_ON_STARTUP}" "${COMPOSE_ENV_PATH}"
fi
if [[ -n "${MARKETPLACE_BROWSER_PROFILE_DIR_ON_STARTUP:-}" ]]; then
  echo "🔧 Setting ${COMPOSE_ENV_PATH}: MARKETPLACE_BROWSER_PROFILE_DIR=${MARKETPLACE_BROWSER_PROFILE_DIR_ON_STARTUP}"
  set_env_key "MARKETPLACE_BROWSER_PROFILE_DIR" "${MARKETPLACE_BROWSER_PROFILE_DIR_ON_STARTUP}" "${COMPOSE_ENV_PATH}"
fi
if [[ -n "${MARKETPLACE_BROWSER_XDG_RUNTIME_DIR_ON_STARTUP:-}" ]]; then
  echo "🔧 Setting ${COMPOSE_ENV_PATH}: MARKETPLACE_BROWSER_XDG_RUNTIME_DIR=${MARKETPLACE_BROWSER_XDG_RUNTIME_DIR_ON_STARTUP}"
  set_env_key "MARKETPLACE_BROWSER_XDG_RUNTIME_DIR" "${MARKETPLACE_BROWSER_XDG_RUNTIME_DIR_ON_STARTUP}" "${COMPOSE_ENV_PATH}"
fi

current_database_url="$(grep -E '^DATABASE_URL=' "${COMPOSE_ENV_PATH}" 2>/dev/null | tail -n 1 | cut -d= -f2- || true)"
if [[ -z "${current_database_url}" || "${current_database_url}" == sqlite* ]]; then
  postgres_user="${POSTGRES_USER:-$(env_file_value POSTGRES_USER "${COMPOSE_ENV_PATH}")}"
  postgres_password="${POSTGRES_PASSWORD:-$(env_file_value POSTGRES_PASSWORD "${COMPOSE_ENV_PATH}")}"
  postgres_db="${POSTGRES_DB:-$(env_file_value POSTGRES_DB "${COMPOSE_ENV_PATH}")}"
  [[ -z "${postgres_user}" ]] && postgres_user="fe"
  [[ -z "${postgres_password}" ]] && postgres_password="fe"
  [[ -z "${postgres_db}" ]] && postgres_db="fe"
  database_url="postgresql+psycopg://${postgres_user}:${postgres_password}@127.0.0.1:5432/${postgres_db}"
  echo "🔧 Setting ${COMPOSE_ENV_PATH}: DATABASE_URL=${database_url}"
  set_env_key "DATABASE_URL" "${database_url}" "${COMPOSE_ENV_PATH}"
  current_database_url="${database_url}"
fi

if [[ -n "${current_database_url}" ]]; then
  export DATABASE_URL="${current_database_url}"
fi
if [[ -n "${MARKETPLACE_BROWSER_EXECUTABLE_PATH_ON_STARTUP:-}" ]]; then
  echo "🔧 Setting ${COMPOSE_ENV_PATH}: MARKETPLACE_BROWSER_EXECUTABLE_PATH=${MARKETPLACE_BROWSER_EXECUTABLE_PATH_ON_STARTUP}"
  set_env_key "MARKETPLACE_BROWSER_EXECUTABLE_PATH" "${MARKETPLACE_BROWSER_EXECUTABLE_PATH_ON_STARTUP}" "${COMPOSE_ENV_PATH}"
fi

# Explicit runtime mapping: propagate startup config flags into the docker compose
# environment as well (in case compose relies on shell env rather than env_file).
if [[ -n "${ENABLE_EMBEDDINGS_ON_STARTUP:-}" ]]; then
  export ENABLE_EMBEDDINGS="${ENABLE_EMBEDDINGS_ON_STARTUP}"
fi
if [[ -n "${ENABLE_QDRANT_ON_STARTUP:-}" ]]; then
  export ENABLE_QDRANT="${ENABLE_QDRANT_ON_STARTUP}"
fi
if [[ -n "${ENABLE_EXTRACTION_ON_STARTUP:-}" ]]; then
  export ENABLE_EXTRACTION="${ENABLE_EXTRACTION_ON_STARTUP}"
fi
if [[ -n "${COCKPIT_STATE_DB_ON_STARTUP:-}" ]]; then
  export COCKPIT_STATE_DB="${COCKPIT_STATE_DB_ON_STARTUP}"
fi
if [[ -n "${MARKETPLACE_BROWSER_RUNTIME_ON_STARTUP:-}" ]]; then
  export MARKETPLACE_BROWSER_RUNTIME="${MARKETPLACE_BROWSER_RUNTIME_ON_STARTUP}"
fi
if [[ -n "${MARKETPLACE_BROWSER_PROFILE_DIR_ON_STARTUP:-}" ]]; then
  export MARKETPLACE_BROWSER_PROFILE_DIR="${MARKETPLACE_BROWSER_PROFILE_DIR_ON_STARTUP}"
fi
if [[ -n "${MARKETPLACE_BROWSER_XDG_RUNTIME_DIR_ON_STARTUP:-}" ]]; then
  export MARKETPLACE_BROWSER_XDG_RUNTIME_DIR="${MARKETPLACE_BROWSER_XDG_RUNTIME_DIR_ON_STARTUP}"
fi
if [[ -n "${MARKETPLACE_BROWSER_EXECUTABLE_PATH_ON_STARTUP:-}" ]]; then
  export MARKETPLACE_BROWSER_EXECUTABLE_PATH="${MARKETPLACE_BROWSER_EXECUTABLE_PATH_ON_STARTUP}"
fi

export_git_provenance_env

# Preflight probe: verify llama.cpp models endpoint is reachable from Docker network.
if [[ -n "${LLAMACPP_URL_CONTAINER:-}" ]]; then
  compose_network="$(basename "${ENGINE_ROOT}")_default"
  models_url="${LLAMACPP_URL_CONTAINER%/}/models"
  echo "🔍 Preflight (compose net): GET ${models_url}"
  if docker network inspect "${compose_network}" >/dev/null 2>&1; then
    if ! docker run --rm --network "${compose_network}" curlimages/curl:8.5.0 sh -lc "curl -fsS -m 5 -H 'Authorization: Bearer ${llm_api_key}' '${models_url}' >/dev/null"; then
      echo "ERROR: llamacpp models endpoint not reachable from compose network: ${models_url}" >&2
      exit 1
    fi
  else
    echo "⚠️  compose network '${compose_network}' not present yet; skipping early probe"
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

if [[ "${ENABLE_EMBEDDINGS_ON_STARTUP:-}" == "true" || "${ENABLE_EMBEDDINGS_ON_STARTUP:-}" == "1" ]]; then
  embed_model="${EMBED_MODEL_ON_STARTUP:-nomic-embed-text}"
  if command -v ollama >/dev/null 2>&1; then
    while IFS= read -r loaded_model; do
      [[ -n "${loaded_model}" ]] || continue
      if [[ ! "${loaded_model}" =~ ^${embed_model}(:|$) ]]; then
        echo "🧹 Stopping loaded Ollama model ${loaded_model} to free resources for ${embed_model}..."
        ollama stop "${loaded_model}" >/dev/null 2>&1 || true
      fi
    done < <(ollama ps | awk 'NR>1 {print $1}')
    if ! ollama list | awk 'NR>1 {print $1}' | grep -Eq "^${embed_model}(:|$)"; then
      echo "⬇️  Pulling Ollama embedding model ${embed_model}..."
      ollama pull "${embed_model}"
    fi
  else
    echo "⚠️  ollama CLI not found; cannot ensure embedding model ${embed_model} is installed"
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

compose_includes_backend="false"
backend_services=()
infra_services=()

if [[ "${#SERVICES_ARG[@]}" -gt 0 ]]; then
  for s in "${SERVICES_ARG[@]}"; do
    if [[ "${s}" == "backend" ]]; then
      compose_includes_backend="true"
      backend_services+=("${s}")
    else
      infra_services+=("${s}")
    fi
  done
else
  # Default full-stack mode: start infra first, then backend.
  infra_services=(postgres redis qdrant worker)
  backend_services=(backend)
  compose_includes_backend="true"
fi

echo "starting full stack infra via docker compose..."
if [[ "${#infra_services[@]}" -gt 0 ]]; then
  compose_up_detached "${infra_services[@]}"
else
  compose_up_detached
fi

# Re-probe llamacpp immediately before starting backend.
if [[ "${compose_includes_backend}" == "true" && -n "${LLAMACPP_URL_CONTAINER:-}" && -n "${llm_api_key:-}" ]]; then
  compose_network="$(basename "${ENGINE_ROOT}")_default"
  models_url="${LLAMACPP_URL_CONTAINER%/}/models"
  echo "🔍 Preflight (compose net, just-before-backend): GET ${models_url}"
  embeddings_url="${LLAMACPP_URL_CONTAINER%/}/embeddings"

  # Readiness gate: llama.cpp can report /v1/models successfully while still
  # loading model weights, then briefly reject requests once the load completes
  # and the server re-binds. Requiring 3 consecutive successes (not just 1)
  # guards against this flapping window — a single OK during the transient
  # ready phase would let the backend start and immediately hit 503s.
  gate_deadline=$(( $(date +%s) + 60 ))
  ok_models=0
  ok_embeddings=0
  sleep_s=1

  while true; do
    now=$(date +%s)
    if (( now > gate_deadline )); then
      echo "ERROR: llama.cpp readiness gate timed out (models_ok=${ok_models} embeddings_ok=${ok_embeddings})" >&2
      echo "  models_url=${models_url}" >&2
      echo "  embeddings_url=${embeddings_url}" >&2
      exit 1
    fi

    if docker run --rm --network "${compose_network}" curlimages/curl:8.5.0 sh -lc "curl -fsS -m 5 -H 'Authorization: Bearer ${llm_api_key}' '${models_url}' >/dev/null"; then
      ok_models=$(( ok_models + 1 ))
    else
      ok_models=0
    fi

    if docker run --rm --network "${compose_network}" curlimages/curl:8.5.0 sh -lc "curl -fsS -m 8 -H 'Content-Type: application/json' -H 'Authorization: Bearer ${llm_api_key}' -d '{\"model\":\"${EMBED_MODEL:-sentence-transformers/all-MiniLM-L6-v2}\",\"input\":[\"hello\"]}' '${embeddings_url}' >/dev/null"; then
      ok_embeddings=$(( ok_embeddings + 1 ))
    else
      ok_embeddings=0
    fi

    if (( ok_models >= 3 && ok_embeddings >= 3 )); then
      echo "✅ llama.cpp readiness gate passed (models+embeddings)"
      break
    fi

    sleep "${sleep_s}"
    if (( sleep_s < 5 )); then
      sleep_s=$(( sleep_s + 1 ))
    fi
  done
fi

echo "running migrations..."
if [[ "${compose_includes_backend}" == "true" ]]; then
  "${COMPOSE[@]}" run --rm -T backend alembic upgrade head
else
  echo "ERROR: backend service missing from compose; cannot run migrations" >&2
  exit 1
fi

echo "starting backend via docker compose..."
compose_up_detached "${backend_services[@]}"

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
