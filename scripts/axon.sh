#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
IMAGE_NAME="${AXON_IMAGE_NAME:-tenn-axon:latest}"
SCOPE_DIR="${AXON_SCOPE_DIR:-${ROOT_DIR}/.axon_scope}"
SCOPE_PATH_IN_CONTAINER="/workspace/.axon_scope"
SCOPE_MODE="${AXON_SCOPE_MODE:-core}"

print_usage() {
  cat <<'EOF'
Usage: ./scripts/axon.sh <command> [args]

Commands:
  install                 Build the Axon Docker image.
  prepare                 Build/update the scoped Axon workspace snapshot.
  analyze [--full]        Index the scoped workspace.
  watch                   Watch the scoped workspace for changes.
  query "<prompt>"        Query indexed code in the scoped workspace.
  mcp                     Start Axon MCP server on stdio for the scoped workspace.
  raw ...                 Run any raw Axon command inside the container.
  help                    Show this help.
EOF
}

ensure_image() {
  if ! docker image inspect "${IMAGE_NAME}" >/dev/null 2>&1; then
    docker build -t "${IMAGE_NAME}" -f "${ROOT_DIR}/tools/axon/Dockerfile" "${ROOT_DIR}/tools/axon"
  fi
}

prepare_scope() {
  mkdir -p "${SCOPE_DIR}"
  find "${SCOPE_DIR}" -mindepth 1 -maxdepth 1 ! -name '.axon' ! -name '.cache' -exec rm -rf {} +
  mkdir -p "${SCOPE_DIR}/.cache/huggingface"

  sync_dir() {
    local src_rel="$1"
    local dest_rel="$2"
    if [[ -d "${ROOT_DIR}/${src_rel}" ]]; then
      mkdir -p "${SCOPE_DIR}/${dest_rel}"
      rsync -a --delete \
        --exclude '__pycache__/' \
        --exclude '.pytest_cache/' \
        --exclude '.mypy_cache/' \
        --exclude '*.pyc' \
        "${ROOT_DIR}/${src_rel}/" "${SCOPE_DIR}/${dest_rel}/"
    fi
  }

  sync_dir "financial-engine_v2/backend" "financial-engine_v2/backend"
  sync_dir "financial-engine_v2/cockpit" "financial-engine_v2/cockpit"
  sync_dir "financial-engine_v2/config" "financial-engine_v2/config"
  sync_dir "docs" "docs"

  if [[ "${SCOPE_MODE}" == "full" ]]; then
    sync_dir "financial-engine_v2/scripts" "financial-engine_v2/scripts"
    sync_dir "scripts" "scripts"
  fi

  if [[ -f "${ROOT_DIR}/README.md" ]]; then
    cp -f "${ROOT_DIR}/README.md" "${SCOPE_DIR}/README.md"
  fi
  if [[ -f "${ROOT_DIR}/runbook.md" ]]; then
    cp -f "${ROOT_DIR}/runbook.md" "${SCOPE_DIR}/runbook.md"
  fi

  while IFS= read -r py_file; do
    cp -f "${ROOT_DIR}/${py_file}" "${SCOPE_DIR}/${py_file}"
  done < <(find "${ROOT_DIR}" -maxdepth 1 -type f -name '*.py' -printf '%f\n' | sort)
}

run_axon() {
  local container_workdir="$1"
  shift

  local tty_args=("-i")
  if [[ -t 0 && -t 1 ]]; then
    tty_args+=("-t")
  fi

  local env_args=(
    "-e" "HOME=${SCOPE_PATH_IN_CONTAINER}"
    "-e" "XDG_CACHE_HOME=${SCOPE_PATH_IN_CONTAINER}/.cache"
    "-e" "HF_HOME=${SCOPE_PATH_IN_CONTAINER}/.cache/huggingface"
  )
  if [[ -n "${HF_TOKEN:-}" ]]; then
    env_args+=("-e" "HF_TOKEN=${HF_TOKEN}")
  fi

  docker run --rm "${tty_args[@]}" \
    --user "$(id -u):$(id -g)" \
    "${env_args[@]}" \
    -v "${ROOT_DIR}:/workspace" \
    -w "${container_workdir}" \
    "${IMAGE_NAME}" "$@"
}

main() {
  local cmd="${1:-help}"

  case "${cmd}" in
    install)
      ensure_image
      ;;
    prepare)
      prepare_scope
      ;;
    analyze)
      shift || true
      prepare_scope
      ensure_image
      run_axon "${SCOPE_PATH_IN_CONTAINER}" analyze "$@"
      ;;
    watch)
      shift || true
      prepare_scope
      ensure_image
      run_axon "${SCOPE_PATH_IN_CONTAINER}" watch "$@"
      ;;
    query)
      shift || true
      if [[ $# -lt 1 ]]; then
        echo "query requires a prompt string"
        exit 1
      fi
      ensure_image
      run_axon "${SCOPE_PATH_IN_CONTAINER}" query "$1"
      ;;
    mcp)
      shift || true
      ensure_image
      run_axon "${SCOPE_PATH_IN_CONTAINER}" mcp "$@"
      ;;
    raw)
      shift || true
      if [[ $# -lt 1 ]]; then
        echo "raw requires at least one argument"
        exit 1
      fi
      ensure_image
      run_axon "/workspace" "$@"
      ;;
    help|-h|--help)
      print_usage
      ;;
    *)
      echo "Unknown command: ${cmd}"
      print_usage
      exit 1
      ;;
  esac
}

main "$@"
