#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
OUT_DIR="$REPO_ROOT/reports"
OUT_FILE="$OUT_DIR/stewardship_audit_$(date +%Y%m%d_%H%M%S).md"
SCAN_PATHS=(
  "$REPO_ROOT/docs"
  "$REPO_ROOT/scripts"
  "$REPO_ROOT/financial-engine_v2"
  "$REPO_ROOT/.github"
  "$REPO_ROOT/README.md"
  "$REPO_ROOT/runbook.md"
)

mkdir -p "$OUT_DIR"

KEEP_LIST=(
  "check_markdown_hygiene.sh"
  "openclaw-autodev"
  "run_news_pipeline.py"
  "fetch_daily_news.py"
  "backfill_news.py"
  "validate_news_jsonl_schema.py"
  "verify_news_context_db.py"
  "detect_news_context_drift.py"
  "build_news_chunks.py"
  "build_news_context_db.py"
  "extract_financial_metrics.py"
  "query_financial_metrics.py"
  "validate_financial_coverage_gates.py"
  "validate_financial_metrics_gates.py"
  "run.py"
)

CANDIDATE_SUPPRESSION_PREFIXES=(
  "test_"
)

CANDIDATE_SUPPRESSION_EXACT=(
  "scrape-claude-usage.sh"
  "scrape-claude-usage.py"
  "start_local_codex.sh"
  "run_stewardship_audit.sh"
)

ARCHITECTURAL_KEEP_EXACT=(
  "start_local_codex.sh"
  "check_markdown_hygiene.sh"
  "run_stewardship_audit.sh"
)

ARCHITECTURAL_KEEP_PREFIXES=(
  "bootstrap_"
)

is_architectural_keep() {
  local target="$1"
  local item
  local prefix
  for prefix in "${ARCHITECTURAL_KEEP_PREFIXES[@]}"; do
    if [[ "$target" == "${prefix}"* ]]; then
      return 0
    fi
  done
  for item in "${ARCHITECTURAL_KEEP_EXACT[@]}"; do
    if [[ "$target" == "$item" ]]; then
      return 0
    fi
  done
  return 1
}

is_suppressed_candidate() {
  local target="$1"
  local item
  local prefix
  for prefix in "${CANDIDATE_SUPPRESSION_PREFIXES[@]}"; do
    if [[ "$target" == "${prefix}"* ]]; then
      return 0
    fi
  done
  for item in "${CANDIDATE_SUPPRESSION_EXACT[@]}"; do
    if [[ "$target" == "$item" ]]; then
      return 0
    fi
  done
  return 1
}

is_kept() {
  local target="$1"
  local item
  for item in "${KEEP_LIST[@]}"; do
    if [[ "$target" == "$item" ]]; then
      return 0
    fi
  done
  return 1
}

TMP_ACTIVE="$(mktemp)"
TMP_CANDIDATE="$(mktemp)"
TMP_SUPPRESSED="$(mktemp)"
TMP_ARCH_KEEP="$(mktemp)"
TMP_MINIMAL_CANDIDATE="$(mktemp)"
trap 'rm -f "$TMP_ACTIVE" "$TMP_CANDIDATE" "$TMP_SUPPRESSED" "$TMP_ARCH_KEEP" "$TMP_MINIMAL_CANDIDATE"' EXIT

while IFS= read -r file; do
  base="$(basename "$file")"

  ref_files=()
  while IFS= read -r ref_file; do
    if [[ -n "$ref_file" ]]; then
      ref_files+=("$ref_file")
    fi
  done < <(rg -l -uu -g '*.md' -g '*.py' -g '*.sh' -g '*.yml' -g '*.yaml' -g '*.txt' -g '*.json' -g '*.toml' \
    -g '!.git/**' -g '!scripts/archive/**' -g '!autodev/cache/**' -g '!backups/**' -g '!reports/**' -F \
    -- "$base" "${SCAN_PATHS[@]}" || true)

  if [[ ${#ref_files[@]} -eq 0 ]]; then
    if is_kept "$base"; then
      printf '%s\n' "- $base (kept canonical)" >> "$TMP_ACTIVE"
    elif is_architectural_keep "$base"; then
      printf '%s\n' "- $base (architectural keep)" >> "$TMP_ARCH_KEEP"
    elif is_suppressed_candidate "$base"; then
      printf '%s\n' "- $base" >> "$TMP_SUPPRESSED"
    else
      printf '%s\n' "- $base" >> "$TMP_CANDIDATE"
      printf '%s\n' "- $base" >> "$TMP_MINIMAL_CANDIDATE"
    fi
    continue
  fi

  filtered_refs=()
  for ref_file in "${ref_files[@]}"; do
    if [[ "$ref_file" != "$file" ]]; then
      filtered_refs+=("$ref_file")
    fi
  done

  if [[ ${#filtered_refs[@]} -eq 0 ]]; then
    if is_kept "$base"; then
      printf '%s\n' "- $base (kept canonical)" >> "$TMP_ACTIVE"
    elif is_architectural_keep "$base"; then
      printf '%s\n' "- $base (architectural keep)" >> "$TMP_ARCH_KEEP"
    elif is_suppressed_candidate "$base"; then
      printf '%s\n' "- $base" >> "$TMP_SUPPRESSED"
    else
      printf '%s\n' "- $base" >> "$TMP_CANDIDATE"
      printf '%s\n' "- $base" >> "$TMP_MINIMAL_CANDIDATE"
    fi
    continue
  fi

  ref_count="${#filtered_refs[@]}"
  {
    printf '%s\n' "- $base"
    printf '%s\n' "  - ref-count: $ref_count"
    printf '%s\n' "  - refs:"
  } >> "$TMP_ACTIVE"
  for ref_file in "${filtered_refs[@]}"; do
    printf '%s\n' "    - $ref_file" >> "$TMP_ACTIVE"
  done

done < <(find "$REPO_ROOT/scripts" -maxdepth 1 -type f \( -name '*.py' -o -name '*.sh' \) -print)

cat > "$OUT_FILE" <<EOF
# Stewardship Audit

Generated: $(date -Iseconds)

## Active references

EOF
cat "$TMP_ACTIVE" >> "$OUT_FILE"

cat >> "$OUT_FILE" <<'EOF'

## Suspected archive candidates

If no references are found outside archive and autodev cache:

EOF
if [[ -s "$TMP_CANDIDATE" ]]; then
  cat "$TMP_CANDIDATE" >> "$OUT_FILE"
else
  echo "- (none detected)" >> "$OUT_FILE"
fi

cat >> "$OUT_FILE" <<'EOF'

## Suppressed archive candidates

Filtered by strict allowlist (non-user-facing utility scripts), keep these in scope if you want full inventory:

EOF
if [[ -s "$TMP_SUPPRESSED" ]]; then
  cat "$TMP_SUPPRESSED" >> "$OUT_FILE"
else
  echo "- (none suppressed)" >> "$OUT_FILE"
fi

cat >> "$OUT_FILE" <<'EOF'

## Architectural keep scripts

Low-visibility but active operational entrypoints intentionally excluded from candidate movement.

EOF
if [[ -s "$TMP_ARCH_KEEP" ]]; then
  cat "$TMP_ARCH_KEEP" >> "$OUT_FILE"
else
  echo "- (none)" >> "$OUT_FILE"
fi

cat >> "$OUT_FILE" <<'EOF'

## Minimal candidates

Strictly unreferenced and not suppressed by keep/suppression policy.

EOF
if [[ -s "$TMP_MINIMAL_CANDIDATE" ]]; then
  cat "$TMP_MINIMAL_CANDIDATE" >> "$OUT_FILE"
else
  echo "- (none detected)" >> "$OUT_FILE"
fi

echo "Stewardship audit generated: $OUT_FILE"
