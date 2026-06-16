#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Usage: scripts/sync_codex_skills.sh [--apply]

Dry-run by default. Lists repo-backed Tenn skills under .agents/skills and the
host links that would be created under $CODEX_HOME/skills.

Use --apply only when the current task card and user approval explicitly allow
host $CODEX_HOME mutation.
EOF
}

APPLY=0
if [[ "${1:-}" == "--help" || "${1:-}" == "-h" ]]; then
  usage
  exit 0
elif [[ "${1:-}" == "--apply" ]]; then
  APPLY=1
elif [[ $# -gt 0 ]]; then
  usage >&2
  exit 2
fi

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SOURCE_DIR="${REPO_ROOT}/.agents/skills"
CODEX_HOME="${CODEX_HOME:-${HOME}/.codex}"
DEST_DIR="${CODEX_HOME}/skills"

if [[ ! -d "${SOURCE_DIR}" ]]; then
  echo "[sync_codex_skills] no repo-backed skills found at ${SOURCE_DIR}"
  exit 0
fi

linked=0
would_link=0
skipped=0

if [[ "${APPLY}" -eq 1 ]]; then
  mkdir -p "${DEST_DIR}"
else
  echo "[sync_codex_skills] dry run: pass --apply to mutate ${DEST_DIR}"
fi

while IFS= read -r -d '' skill_dir; do
  skill_name="$(basename "${skill_dir}")"
  skill_file="${skill_dir}/SKILL.md"
  target="${DEST_DIR}/${skill_name}"

  if [[ ! -f "${skill_file}" ]]; then
    echo "[sync_codex_skills] skip ${skill_name}: missing SKILL.md"
    skipped=$((skipped + 1))
    continue
  fi

  if [[ -L "${target}" ]]; then
    current_target="$(readlink -f "${target}" || true)"
    if [[ "${current_target}" == "${skill_dir}" ]]; then
      echo "[sync_codex_skills] already linked: ${skill_name}"
      continue
    fi
    echo "[sync_codex_skills] skip ${skill_name}: ${target} already points to ${current_target}"
    skipped=$((skipped + 1))
    continue
  fi

  if [[ -e "${target}" ]]; then
    echo "[sync_codex_skills] skip ${skill_name}: ${target} already exists"
    skipped=$((skipped + 1))
    continue
  fi

  if [[ "${APPLY}" -eq 1 ]]; then
    ln -s "${skill_dir}" "${target}"
    echo "[sync_codex_skills] linked: ${skill_name} -> ${target}"
    linked=$((linked + 1))
  else
    echo "[sync_codex_skills] would link: ${skill_name} -> ${target}"
    would_link=$((would_link + 1))
  fi
done < <(find "${SOURCE_DIR}" -mindepth 1 -maxdepth 1 -type d -print0 | sort -z)

echo "[sync_codex_skills] complete: linked=${linked} would_link=${would_link} skipped=${skipped}"
