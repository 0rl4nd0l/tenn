#!/usr/bin/env python3
"""Lint gold label files for schema and quality constraints."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict, List, Tuple


REQUIRED_TOP = ("doc_id", "ticker", "pdf_sha256", "published_at", "fields")
REQUIRED_FIELD = ("metric", "period_end", "period_type", "value", "unit_scale", "currency", "scope")


def _issue(path: Path, issue_type: str, message: str, pointer: str = "") -> Dict[str, object]:
    return {
        "file": str(path),
        "type": issue_type,
        "message": message,
        "pointer": pointer,
    }


def _is_blank(value: object) -> bool:
    return str(value or "").strip() == ""


def lint_gold_dir(gold_dir: Path) -> Dict[str, object]:
    issues: List[Dict[str, object]] = []
    files = []
    for candidate in sorted(gold_dir.rglob("*.json")):
        rel_parts = candidate.relative_to(gold_dir).parts
        if not rel_parts:
            continue
        if rel_parts[0].lower() == "schema":
            continue
        if candidate.name == "lint_report.json":
            continue
        files.append(candidate)
    docs_checked = 0
    fields_checked = 0

    for path in files:
        docs_checked += 1
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except Exception as exc:  # noqa: BLE001
            issues.append(_issue(path, "invalid_json", f"Failed to parse JSON: {exc}"))
            continue

        if not isinstance(payload, dict):
            issues.append(_issue(path, "invalid_type", "Top-level JSON must be object"))
            continue

        for key in REQUIRED_TOP:
            if key not in payload:
                issues.append(_issue(path, "missing_top_field", f"Missing required top field '{key}'", f"/{key}"))

        fields = payload.get("fields", [])
        if not isinstance(fields, list):
            issues.append(_issue(path, "invalid_fields_type", "fields must be an array", "/fields"))
            continue

        seen = set()
        for idx, field in enumerate(fields):
            fields_checked += 1
            pointer = f"/fields/{idx}"
            if not isinstance(field, dict):
                issues.append(_issue(path, "invalid_field_type", "field entry must be object", pointer))
                continue
            for req in REQUIRED_FIELD:
                if req not in field:
                    issues.append(_issue(path, "missing_field_key", f"Missing required key '{req}'", f"{pointer}/{req}"))
                    continue
                if req in {"metric", "period_end", "period_type", "currency", "scope"} and _is_blank(field.get(req)):
                    issues.append(_issue(path, "blank_field_value", f"Blank value for '{req}'", f"{pointer}/{req}"))

            currency = str(field.get("currency", "")).strip().upper()
            if not currency or currency == "UNKNOWN":
                issues.append(
                    _issue(path, "unknown_currency", "Gold labels must not use UNKNOWN currency", f"{pointer}/currency")
                )

            dedupe_key = (
                str(field.get("metric", "")).strip().lower(),
                str(field.get("period_end", "")).strip(),
                str(field.get("scope", "")).strip().lower(),
            )
            if dedupe_key in seen:
                issues.append(
                    _issue(
                        path,
                        "duplicate_metric_period_scope",
                        "Duplicate (metric, period_end, scope) in one gold file",
                        pointer,
                    )
                )
            seen.add(dedupe_key)

    report = {
        "gold_dir": str(gold_dir),
        "files_found": len(files),
        "docs_checked": docs_checked,
        "fields_checked": fields_checked,
        "issues_count": len(issues),
        "ok": len(issues) == 0,
        "issues": issues,
    }
    return report


def main() -> int:
    ap = argparse.ArgumentParser(description="Lint gold JSON labels.")
    ap.add_argument("--gold-dir", required=True, help="Directory containing gold label files.")
    ap.add_argument(
        "--out-json",
        default="",
        help="Optional output path for lint report JSON. Default: <gold-dir>/lint_report.json",
    )
    args = ap.parse_args()

    gold_dir = Path(args.gold_dir).expanduser().resolve()
    out_json = (
        Path(args.out_json).expanduser().resolve()
        if str(args.out_json).strip()
        else gold_dir / "lint_report.json"
    )

    report = lint_gold_dir(gold_dir)
    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_json.write_text(json.dumps(report, indent=2), encoding="utf-8")

    print(f"Gold docs checked: {report['docs_checked']}")
    print(f"Fields checked: {report['fields_checked']}")
    print(f"Issues: {report['issues_count']}")
    print(f"Output: {out_json}")

    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
