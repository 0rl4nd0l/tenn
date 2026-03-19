#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Mapping, Sequence


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

    total = 0
    rejected = 0
    docs_with_rejections: list[str] = []

    for document in docs:
        verification = document.get("verification")
        if not isinstance(verification, Mapping):
            continue
        rejected_count = int(verification.get("rejected_count") or 0)
        verified_count = int(verification.get("verified_count") or 0)
        total += verified_count + rejected_count
        rejected += rejected_count
        if rejected_count > 0:
            docs_with_rejections.append(str(document.get("doc_id") or ""))

    rate = float(rejected) / float(max(1, total))
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
