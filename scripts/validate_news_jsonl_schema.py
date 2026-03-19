#!/usr/bin/env python3
"""
Validate a news JSONL file against the canonical article schema.

Use before feeding JSONL into build_news_context_db to ensure all rows
conform to Layer 2. See docs/architecture/15_news_substrate.md.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from news_pipeline.canonical_article_schema import validate_canonical_article  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Validate news JSONL against canonical article schema")
    ap.add_argument("input_jsonl", nargs="?", default="", help="Path to JSONL file (stdin if omitted)")
    ap.add_argument("--strict", action="store_true", help="Require both title and body")
    ap.add_argument("--max-errors", type=int, default=50, help="Stop after this many validation errors (0 = all)")
    ap.add_argument("--out-json", default="", help="Write validation report JSON here")
    args = ap.parse_args(argv)

    if args.input_jsonl:
        path = Path(args.input_jsonl).expanduser().resolve()
        if not path.exists():
            print(f"[validate_news_jsonl_schema] File not found: {path}", file=sys.stderr)
            return 2
        lines = path.read_text(encoding="utf-8").splitlines()
    else:
        lines = sys.stdin.read().splitlines()

    total = 0
    invalid = 0
    errors_by_row: list[dict] = []
    max_errors = max(0, args.max_errors)

    for line_no, line in enumerate(lines, start=1):
        line = line.strip()
        if not line:
            continue
        total += 1
        try:
            row = json.loads(line)
        except json.JSONDecodeError as e:
            invalid += 1
            errors_by_row.append({"line": line_no, "error": f"invalid JSON: {e}"})
            if max_errors and len(errors_by_row) >= max_errors:
                break
            continue
        if not isinstance(row, dict):
            invalid += 1
            errors_by_row.append({"line": line_no, "error": "row is not a dict"})
            if max_errors and len(errors_by_row) >= max_errors:
                break
            continue
        ok, errs = validate_canonical_article(row, strict=args.strict)
        if not ok:
            invalid += 1
            errors_by_row.append({"line": line_no, "errors": errs})
            if max_errors and len(errors_by_row) >= max_errors:
                break

    report = {
        "total_rows": total,
        "invalid_rows": invalid,
        "valid_rows": total - invalid,
        "ok": invalid == 0,
        "error_sample": errors_by_row,
    }

    if args.out_json:
        out_path = Path(args.out_json).expanduser().resolve()
        out_path.parent.mkdir(parents=True, exist_ok=True)
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2, sort_keys=True)
        print(f"[validate_news_jsonl_schema] Wrote report to {out_path}")

    print(json.dumps(report, indent=2, sort_keys=True))
    if invalid > 0:
        print(f"[validate_news_jsonl_schema] {invalid}/{total} rows failed validation", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
