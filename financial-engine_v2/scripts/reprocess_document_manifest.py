#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
import time
import uuid
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
BACKEND_ROOT = REPO_ROOT / "backend"
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.core.db import SessionLocal  # noqa: E402
from app.models.documents import Document  # noqa: E402
from app.services.announcement_importance import (  # noqa: E402
    NARRATIVE_POLICY_VALUES,
    classify_narrative_extraction_policy,
)
from app.services.pipeline import process_document  # noqa: E402


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _load_manifest(path: Path) -> list[str]:
    doc_ids: list[str] = []
    seen: set[str] = set()
    for raw in path.read_text(encoding="utf-8").splitlines():
        doc_id = raw.strip()
        if not doc_id or doc_id in seen:
            continue
        seen.add(doc_id)
        doc_ids.append(doc_id)
    return doc_ids


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Re-run process_document over a manifest of document IDs with resume support."
    )
    parser.add_argument("--manifest", required=True, help="Path to newline-delimited document IDs.")
    parser.add_argument("--report-json", required=True, help="Progress report JSON path.")
    parser.add_argument(
        "--narrative-policy",
        choices=sorted(NARRATIVE_POLICY_VALUES),
        default="full",
        help="Narrative extraction policy to apply during reprocessing.",
    )
    parser.add_argument(
        "--sample-limit",
        type=int,
        default=200,
        help="Maximum number of non-success sample rows retained in the report.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    manifest_path = Path(args.manifest).expanduser().resolve()
    report_path = Path(args.report_json).expanduser().resolve()
    report_path.parent.mkdir(parents=True, exist_ok=True)
    doc_ids = _load_manifest(manifest_path)

    state: dict[str, object] = {
        "started_at": _utc_now(),
        "updated_at": _utc_now(),
        "completed_at": None,
        "manifest_path": str(manifest_path),
        "total": len(doc_ids),
        "narrative_policy": args.narrative_policy,
        "last_index": 0,
        "counts": {},
        "samples": [],
        "status": "running",
    }
    if report_path.exists():
        try:
            prior = json.loads(report_path.read_text(encoding="utf-8"))
        except Exception:
            prior = None
        if isinstance(prior, dict) and str(prior.get("manifest_path") or "") == str(
            manifest_path
        ):
            state.update(prior)
            state["narrative_policy"] = args.narrative_policy
            state["updated_at"] = _utc_now()
            state["completed_at"] = None
            state["status"] = "running"

    counts = Counter(state.get("counts") or {})
    samples = list(state.get("samples") or [])[: max(0, int(args.sample_limit))]
    last_index = int(state.get("last_index") or 0)
    db = SessionLocal()

    print(f"[start] total={len(doc_ids)} resume_from={last_index}", flush=True)
    try:
        for idx, doc_id in enumerate(doc_ids[last_index:], start=last_index + 1):
            started = time.time()
            try:
                doc = (
                    db.query(Document)
                    .filter(Document.document_id == uuid.UUID(doc_id))
                    .first()
                )
                narrative_policy = classify_narrative_extraction_policy(
                    title=getattr(doc, "title", None),
                    doc_class=getattr(doc, "doc_class", None),
                    doc_subtype=getattr(doc, "doc_subtype", None),
                    policy=args.narrative_policy,
                )
                result = process_document(
                    doc_id,
                    skip_narrative=not bool(
                        narrative_policy.get("extract_narrative")
                    ),
                ) or {}
                extraction_status = str(result.get("extraction_status") or "unknown")
                error_stage = str(
                    ((result.get("method_provenance") or {}).get("error_stage")) or ""
                )
                counts[extraction_status] += 1
                if (
                    extraction_status
                    not in {"ok", "ok_low_confidence", "skipped_extraction"}
                    and len(samples) < int(args.sample_limit)
                ):
                    samples.append(
                        {
                            "index": idx,
                            "document_id": doc_id,
                            "extraction_status": extraction_status,
                            "error_stage": error_stage,
                            "narrative_policy_reason": narrative_policy.get("reason"),
                        }
                    )
                print(
                    f"[{_utc_now()}] {idx}/{len(doc_ids)} {doc_id} "
                    f"status={extraction_status} error_stage={error_stage} "
                    f"narrative={narrative_policy.get('reason')} "
                    f"elapsed_s={time.time() - started:.1f}",
                    flush=True,
                )
            except Exception as exc:
                counts["exception"] += 1
                if len(samples) < int(args.sample_limit):
                    samples.append(
                        {
                            "index": idx,
                            "document_id": doc_id,
                            "extraction_status": "exception",
                            "error": str(exc),
                        }
                    )
                print(
                    f"[{_utc_now()}] {idx}/{len(doc_ids)} {doc_id} "
                    f"status=exception error={exc}",
                    flush=True,
                )

            state["updated_at"] = _utc_now()
            state["last_index"] = idx
            state["counts"] = dict(counts)
            state["samples"] = samples
            state["status"] = "running"
            if idx == len(doc_ids) or idx % 5 == 0:
                report_path.write_text(json.dumps(state, indent=2), encoding="utf-8")
    finally:
        db.close()

    state["updated_at"] = _utc_now()
    state["completed_at"] = _utc_now()
    state["status"] = "completed"
    state["counts"] = dict(counts)
    state["samples"] = samples
    report_path.write_text(json.dumps(state, indent=2), encoding="utf-8")
    print(f"[done] processed={state['last_index']} counts={dict(counts)}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
