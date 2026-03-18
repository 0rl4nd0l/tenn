from __future__ import annotations

from pathlib import Path
from typing import Any

from app.services.framework_classifier import load_framework_records, resolve_frameworks_path


class FrameworkRetriever:
    def __init__(self, *, frameworks_path: str | Path | None = None) -> None:
        self.frameworks_path = resolve_frameworks_path(frameworks_path)
        self.framework_records = load_framework_records(self.frameworks_path)

    def retrieve(self, framework_families: list[str] | None) -> list[dict[str, Any]]:
        if framework_families is not None and not framework_families:
            return []

        requested_order = list(dict.fromkeys(str(family or "").strip() for family in (framework_families or []) if str(family or "").strip()))
        wanted = set(requested_order)

        filtered: list[dict[str, Any]] = []
        for record in self.framework_records:
            family = str(record.get("framework_family") or "").strip()
            if wanted and family not in wanted:
                continue
            filtered.append(record)

        def _sort_key(record: dict[str, Any]) -> tuple[int, str, str]:
            family = str(record.get("framework_family") or "")
            family_index = requested_order.index(family) if family in wanted else len(requested_order)
            return (family_index, family, str(record.get("title") or ""))

        projected: list[dict[str, Any]] = []
        seen = set()
        for record in sorted(filtered, key=_sort_key):
            framework_id = str(record.get("framework_id") or "")
            title = str(record.get("title") or "")
            dedupe_key = framework_id or f"{record.get('framework_family')}::{title}"
            if dedupe_key in seen:
                continue
            seen.add(dedupe_key)
            projected.append(
                {
                    "framework_id": framework_id,
                    "framework_family": str(record.get("framework_family") or ""),
                    "title": title,
                    "principles": list(record.get("principles") or []),
                    "decision_rules": list(record.get("decision_rules") or []),
                    "risk_notes": list(record.get("risk_notes") or []),
                }
            )
        return projected
