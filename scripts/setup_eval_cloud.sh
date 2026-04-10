#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VENV_DIR="${ROOT_DIR}/financial-engine_v2/.venv"
PYTHON_BIN=""
WITH_DEV=0
WITH_PLAYWRIGHT=0
SKIP_INSTALL=0
SKIP_VALIDATE=0

usage() {
  cat <<'EOF'
Usage: bash scripts/setup_eval_cloud.sh [options]

Prepare the existing Tenn evaluation lane in a cloud/dev environment.

This script is intentionally eval-only:
- installs the repo's authoritative Python manifests
- optionally installs dev-only eval helpers (DuckDB / MLflow)
- optionally installs Playwright Chromium
- validates targeted extraction-eval tests and scorecard CLI entrypoints

It does NOT start or configure the full extraction runtime (llama.cpp, Qdrant,
Redis, Postgres, host-local models, or secrets).

Options:
  --venv <path>         Override venv path. Default: financial-engine_v2/.venv
  --with-dev            Install financial-engine_v2/backend/requirements-dev.txt
  --with-playwright     Install Chromium via Playwright after pip install
  --skip-install        Reuse the existing venv without running pip install
  --skip-validate       Skip the targeted eval validation commands
  --help                Show this help text
EOF
}

log() {
  printf '[setup_eval_cloud] %s\n' "$*"
}

fail() {
  printf '[setup_eval_cloud] FAIL: %s\n' "$*" >&2
  exit 1
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --venv)
      [[ $# -ge 2 ]] || fail "--venv requires a value"
      VENV_DIR="$2"
      shift 2
      ;;
    --with-dev)
      WITH_DEV=1
      shift
      ;;
    --with-playwright)
      WITH_PLAYWRIGHT=1
      shift
      ;;
    --skip-install)
      SKIP_INSTALL=1
      shift
      ;;
    --skip-validate)
      SKIP_VALIDATE=1
      shift
      ;;
    --help|-h)
      usage
      exit 0
      ;;
    *)
      fail "unknown argument: $1"
      ;;
  esac
done

if command -v python3 >/dev/null 2>&1; then
  PYTHON_BIN="$(command -v python3)"
elif command -v python >/dev/null 2>&1; then
  PYTHON_BIN="$(command -v python)"
else
  fail "python3 or python is required"
fi

log "repo_root=${ROOT_DIR}"
log "venv=${VENV_DIR}"
log "python=${PYTHON_BIN}"

if [[ ! -x "${VENV_DIR}/bin/python" ]]; then
  log "creating virtualenv"
  "${PYTHON_BIN}" -m venv "${VENV_DIR}"
fi

if [[ "${SKIP_INSTALL}" != "1" ]]; then
  log "installing authoritative manifests"
  "${VENV_DIR}/bin/python" -m pip install --upgrade pip
  "${VENV_DIR}/bin/pip" install -r "${ROOT_DIR}/requirements.txt"

  if [[ "${WITH_DEV}" == "1" ]]; then
    log "installing dev-only eval helpers"
    "${VENV_DIR}/bin/pip" install -r "${ROOT_DIR}/financial-engine_v2/backend/requirements-dev.txt"
  fi

  if [[ "${WITH_PLAYWRIGHT}" == "1" ]]; then
    log "installing playwright chromium"
    "${VENV_DIR}/bin/playwright" install chromium
  fi
else
  log "skipping pip install"
fi

if [[ "${SKIP_VALIDATE}" != "1" ]]; then
  log "running targeted extraction-eval tests"
  "${VENV_DIR}/bin/python" -m pytest -c "${ROOT_DIR}/pytest.ini" \
    "${ROOT_DIR}/financial-engine_v2/backend/tests/test_extraction_eval_harness.py" -q
  "${VENV_DIR}/bin/python" -m pytest -c "${ROOT_DIR}/pytest.ini" \
    "${ROOT_DIR}/financial-engine_v2/backend/tests/test_extraction_gold_eval.py" -q
  "${VENV_DIR}/bin/python" -m pytest -c "${ROOT_DIR}/pytest.ini" \
    "${ROOT_DIR}/scripts/test_run_real_extraction_eval.py" -q

  log "running deterministic scorecard cli"
  "${VENV_DIR}/bin/python" \
    "${ROOT_DIR}/financial-engine_v2/scripts/extraction_eval_scorecard.py" \
    --indent 0 >/dev/null

  log "validation complete"
else
  log "skipping validation"
fi

cat <<EOF

Eval cloud setup complete
venv: ${VENV_DIR}
python: ${VENV_DIR}/bin/python

Supported next steps:
  ${VENV_DIR}/bin/python -m pytest -c ${ROOT_DIR}/pytest.ini ${ROOT_DIR}/financial-engine_v2/backend/tests/test_extraction_eval.py -q
  ${VENV_DIR}/bin/python ${ROOT_DIR}/financial-engine_v2/scripts/extraction_eval_scorecard.py --indent 2

Optional eval helpers:
  --with-dev         enables DuckDB / MLflow helpers for existing eval artifacts
  --with-playwright  installs Chromium for broader repo workflows

Intentionally excluded:
  full extraction runtime bootstrap (llama.cpp, host-local models, secrets, PDFs, GPU topology)
EOF
