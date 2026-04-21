#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(git -C "${SCRIPT_DIR}/.." rev-parse --show-toplevel)"
PREPARE_SCRIPT="${SCRIPT_DIR}/prepare_cloud_worktree.sh"

DATE_STAMP="$(date +%Y%m%d)"
TIME_STAMP="$(date +%H%M%S)"
ROOT_PATH="${REPO_ROOT}/../tenn-codex-cloud-${DATE_STAMP}-${TIME_STAMP}"
APPLY_LOCAL_EXCLUDES=1
DRY_RUN=0

TASKS=(
  "c1:extraction-quality-gap-audit"
  "c2:cockpit-routing-regression-tests"
  "c3:extraction-truth-real-gold-eval"
  "c4:system-contract-conformance-matrix"
  "c5:multipass-extraction-performance-profile"
)

usage() {
  cat <<'EOF'
Usage: bash scripts/setup_codex_cloud_queue.sh [options]

Create 5 pre-scoped cloud worktrees/branches for the Codex Cloud queue.

Options:
  --root <path>                Parent path for generated worktrees
  --date <yyyymmdd>            Override date stamp in names
  --time <hhmmss>              Override time stamp in names
  --no-apply-local-excludes    Do not append local-only excludes
  --dry-run                    Print planned actions without creating worktrees
  --help                       Show this help text
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --root)
      [[ $# -ge 2 ]] || { echo "--root requires a value" >&2; exit 1; }
      ROOT_PATH="$2"
      shift 2
      ;;
    --date)
      [[ $# -ge 2 ]] || { echo "--date requires a value" >&2; exit 1; }
      DATE_STAMP="$2"
      shift 2
      ;;
    --time)
      [[ $# -ge 2 ]] || { echo "--time requires a value" >&2; exit 1; }
      TIME_STAMP="$2"
      shift 2
      ;;
    --no-apply-local-excludes)
      APPLY_LOCAL_EXCLUDES=0
      shift
      ;;
    --dry-run)
      DRY_RUN=1
      shift
      ;;
    --help|-h)
      usage
      exit 0
      ;;
    *)
      echo "Unknown argument: $1" >&2
      usage
      exit 1
      ;;
  esac
done

if [[ ! -x "${PREPARE_SCRIPT}" ]]; then
  echo "Missing executable: ${PREPARE_SCRIPT}" >&2
  exit 1
fi

echo "[setup_codex_cloud_queue] repo_root=${REPO_ROOT}"
echo "[setup_codex_cloud_queue] root_path=${ROOT_PATH}"
echo "[setup_codex_cloud_queue] dry_run=${DRY_RUN}"

for entry in "${TASKS[@]}"; do
  task_id="${entry%%:*}"
  task_slug="${entry#*:}"
  branch="cloud/${task_id}-${task_slug}-${DATE_STAMP}-${TIME_STAMP}"
  snapshot="backup/pre-cloud-${task_id}-${DATE_STAMP}-${TIME_STAMP}"
  worktree_path="${ROOT_PATH}/${task_id}-${task_slug}"

  cmd=(
    bash "${PREPARE_SCRIPT}"
    --path "${worktree_path}"
    --branch "${branch}"
    --snapshot-branch "${snapshot}"
  )

  if [[ "${APPLY_LOCAL_EXCLUDES}" -eq 1 ]]; then
    cmd+=(--apply-local-excludes)
  fi
  if [[ "${DRY_RUN}" -eq 1 ]]; then
    cmd+=(--dry-run)
  fi

  echo
  echo "[setup_codex_cloud_queue] preparing ${task_id} -> ${branch}"
  "${cmd[@]}"
done

echo
echo "[setup_codex_cloud_queue] queue setup complete"
