#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SOURCE_DIR="${REPO_ROOT}/.codex/skills"
CODEX_HOME="${CODEX_HOME:-${HOME}/.codex}"
DEST_DIR="${CODEX_HOME}/skills"

if [[ ! -d "${SOURCE_DIR}" ]]; then
  echo "[sync_codex_skills] no repo-local skills found at ${SOURCE_DIR}"
  exit 0
fi

mkdir -p "${DEST_DIR}"

linked=0
skipped=0

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

  ln -s "${skill_dir}" "${target}"
  echo "[sync_codex_skills] linked: ${skill_name} -> ${target}"
  linked=$((linked + 1))
done < <(find "${SOURCE_DIR}" -mindepth 1 -maxdepth 1 -type d -print0 | sort -z)

echo "[sync_codex_skills] complete: linked=${linked} skipped=${skipped}"
