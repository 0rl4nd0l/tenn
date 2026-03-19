#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Mapping, Sequence

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from services.evaluation.evidence import verify_metrics


def _documents(payload: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    routing = payload.get("routing")
    if isinstance(routing, Mapping):
        docs = routing.get("documents")
        if isinstance(docs, Sequence):
            return [doc for doc in docs if isinstance(doc, Mapping)]
    docs = payload.get("documents")
    if isinstance(docs, Sequence):
        return [doc for doc in docs if isinstance(doc, Mapping)]
    return []


def run(path: str) -> None:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    docs = _documents(payload)

    total_metrics = 0
    total_rejected = 0
    docs_with_rejections: list[str] = []

    for document in docs:
        metrics = document.get("metrics")
        if not isinstance(metrics, Mapping):
            metrics = {}
        raw_text = document.get("raw_text")
        if not raw_text:
            raw_text = document.get("text")
        if not raw_text:
            raw_text = ""
        verification = verify_metrics(metrics, raw_text)
        rejected_count = int(verification.get("rejected_count") or 0)
        total_metrics += len(metrics)
        total_rejected += rejected_count
        if rejected_count > 0:
            docs_with_rejections.append(str(document.get("doc_id") or ""))

    rate = float(total_rejected) / float(max(1, total_metrics))
    print(
        json.dumps(
            {
                "hallucination_rate": rate,
                "documents_with_issues": [doc_id for doc_id in docs_with_rejections if doc_id],
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    args = parser.parse_args()
    run(args.input)
