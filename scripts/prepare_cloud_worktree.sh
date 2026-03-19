#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(git -C "${SCRIPT_DIR}/.." rev-parse --show-toplevel)"

WORKTREE_PATH=""
WORKTREE_BRANCH=""
SNAPSHOT_BRANCH=""
APPLY_LOCAL_EXCLUDES=0
DRY_RUN=0

LOCAL_EXCLUDE_PATTERNS=(
  ".venv-docling-gpu-repair/"
  "backups/"
  "failed/"
  "models/"
  "processed/"
  "reports/"
  "financial-engine_v2/reports/"
  "financial-engine_v2/config/system.env"
)

usage() {
  cat <<'EOF'
Usage: bash scripts/prepare_cloud_worktree.sh [options]

Create a clean sibling worktree from the current HEAD for Cursor Cloud or
isolated PR review without touching the dirty main worktree.

Options:
  --path <path>                 Worktree path. Default: ../tenn-cloud-<timestamp>
  --branch <branch>             New branch for the clean worktree.
                                Default: cloud/<current-branch>-<timestamp>
  --snapshot-branch <branch>    Backup branch pinned to current HEAD.
                                Default: backup/pre-cloud-<timestamp>
  --apply-local-excludes        Append recommended local-only patterns to
                                .git/info/exclude if missing.
  --dry-run                     Print the planned actions without changing git.
  --help                        Show this help text.
EOF
}

log() {
  echo "[prepare_cloud_worktree] $*"
}

fail() {
  echo "[prepare_cloud_worktree] FAIL: $*" >&2
  exit 1
}

branch_exists() {
  git show-ref --verify --quiet "refs/heads/$1"
}

append_local_excludes() {
  local exclude_file added=0 pattern
  exclude_file="${REPO_ROOT}/.git/info/exclude"
  touch "${exclude_file}"

  for pattern in "${LOCAL_EXCLUDE_PATTERNS[@]}"; do
    if ! grep -Fqx "${pattern}" "${exclude_file}"; then
      printf '%s\n' "${pattern}" >>"${exclude_file}"
      added=1
      log "exclude added: ${pattern}"
    fi
  done

  if [[ "${added}" -eq 0 ]]; then
    log "local exclude patterns already present"
  fi
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --path)
      [[ $# -ge 2 ]] || fail "--path requires a value"
      WORKTREE_PATH="$2"
      shift 2
      ;;
    --branch)
      [[ $# -ge 2 ]] || fail "--branch requires a value"
      WORKTREE_BRANCH="$2"
      shift 2
      ;;
    --snapshot-branch)
      [[ $# -ge 2 ]] || fail "--snapshot-branch requires a value"
      SNAPSHOT_BRANCH="$2"
      shift 2
      ;;
    --apply-local-excludes)
      APPLY_LOCAL_EXCLUDES=1
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
      fail "unknown argument: $1"
      ;;
  esac
done

cd "${REPO_ROOT}"

CURRENT_BRANCH="$(git symbolic-ref --quiet --short HEAD || true)"
[[ -n "${CURRENT_BRANCH}" ]] || fail "detached HEAD is not supported"

HEAD_SHA="$(git rev-parse HEAD)"
TIMESTAMP="$(date +%Y%m%d-%H%M%S)"

if [[ -z "${WORKTREE_BRANCH}" ]]; then
  SANITIZED_BRANCH="${CURRENT_BRANCH//\//-}"
  WORKTREE_BRANCH="cloud/${SANITIZED_BRANCH}-${TIMESTAMP}"
fi

if [[ -z "${SNAPSHOT_BRANCH}" ]]; then
  SNAPSHOT_BRANCH="backup/pre-cloud-${TIMESTAMP}"
fi

if [[ -z "${WORKTREE_PATH}" ]]; then
  WORKTREE_PATH="${REPO_ROOT}/../tenn-cloud-${TIMESTAMP}"
fi

WORKTREE_PATH_ABS="$(python3 -c 'import os,sys; print(os.path.abspath(sys.argv[1]))' "${WORKTREE_PATH}")"

if branch_exists "${WORKTREE_BRANCH}"; then
  fail "branch already exists: ${WORKTREE_BRANCH}"
fi

if branch_exists "${SNAPSHOT_BRANCH}"; then
  fail "snapshot branch already exists: ${SNAPSHOT_BRANCH}"
fi

if [[ -e "${WORKTREE_PATH_ABS}" ]]; then
  fail "worktree path already exists: ${WORKTREE_PATH_ABS}"
fi

DIRTY_SUMMARY="$(git status --short)"
if [[ -n "${DIRTY_SUMMARY}" ]]; then
  log "warning: current worktree is dirty; only committed HEAD ${HEAD_SHA} goes into the clean worktree"
else
  log "current worktree is clean"
fi

if [[ "${DRY_RUN}" -eq 1 ]]; then
  log "dry run: no changes made"
else
  git branch "${SNAPSHOT_BRANCH}" "${HEAD_SHA}"
  log "snapshot branch created: ${SNAPSHOT_BRANCH} -> ${HEAD_SHA}"

  if [[ "${APPLY_LOCAL_EXCLUDES}" -eq 1 ]]; then
    append_local_excludes
  fi

  git worktree add -b "${WORKTREE_BRANCH}" "${WORKTREE_PATH_ABS}" "${HEAD_SHA}"
  log "clean worktree created: ${WORKTREE_PATH_ABS} (${WORKTREE_BRANCH})"
fi

if [[ "${APPLY_LOCAL_EXCLUDES}" -eq 0 ]]; then
  log "local excludes not modified"
  log "recommended local-only excludes:"
  for pattern in "${LOCAL_EXCLUDE_PATTERNS[@]}"; do
    echo "  - ${pattern}"
  done
fi

cat <<EOF

Cloud base prepared
repo_root: ${REPO_ROOT}
source_branch: ${CURRENT_BRANCH}
source_commit: ${HEAD_SHA}
snapshot_branch: ${SNAPSHOT_BRANCH}
clean_worktree_branch: ${WORKTREE_BRANCH}
clean_worktree_path: ${WORKTREE_PATH_ABS}

Next steps:
  cd ${WORKTREE_PATH_ABS}
  git status --short
  git push -u origin ${WORKTREE_BRANCH}
  git rev-parse HEAD

Cursor Cloud handoff:
  branch: ${WORKTREE_BRANCH}
  commit: ${HEAD_SHA}
  working directory: repo root
  start: bash scripts/start_system.sh
  validate: bash scripts/validate_system.sh
EOF
