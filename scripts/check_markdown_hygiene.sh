#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TMP_LINKS="$(mktemp)"
TMP_BROKEN="$(mktemp)"
trap 'rm -f "$TMP_LINKS" "$TMP_BROKEN"' EXIT

rg --files "$REPO_ROOT" -g '*.md' -g '!.git/**' -g '!node_modules/**' | while read -r f; do
  perl -ne 'while (/\\[[^\\]]+\\]\\(([^)#\\s]+)\\)/g) { my $url = $1; print "$ARGV|$url\\n" if $url !~ m{^(https?://|mailto:|#)}; }' "$f"
done > "$TMP_LINKS"

while IFS='|' read -r src url; do
  [ -z "$src" ] && continue
  base_dir="$(dirname "$src")"
  if [[ "$url" == /* ]]; then
    target="$url"
  else
    target="$base_dir/$url"
  fi
  norm="$(realpath -m "$target" 2>/dev/null || true)"
  if [[ ! -e "$norm" ]]; then
    echo "$src|$url|$norm" >> "$TMP_BROKEN"
  fi
done < "$TMP_LINKS"

if [[ -s "$TMP_BROKEN" ]]; then
  echo "[markdown-hygiene] Broken internal markdown links found:"
  while IFS='|' read -r src url norm; do
    rel_src="${src#$REPO_ROOT/}"
    rel_norm="${norm#$REPO_ROOT/}"
    if [[ "$url" == /* ]]; then
      printf "  - %s -> %s (resolved %s)\\n" "$rel_src" "$url" "$rel_norm"
    else
      printf "  - %s -> %s\\n" "$rel_src" "$url"
    fi
  done < "$TMP_BROKEN"
  echo "[markdown-hygiene] Please fix links before merge."
  exit 1
fi

echo "[markdown-hygiene] Internal markdown link scan passed."
