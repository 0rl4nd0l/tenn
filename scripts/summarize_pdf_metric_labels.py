#!/usr/bin/env python3
import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Dict, Iterable, List


def iter_jsonl(path: Path) -> Iterable[Dict[str, object]]:
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                yield json.loads(line)
            except json.JSONDecodeError:
                continue


def main() -> int:
    ap = argparse.ArgumentParser(description="Summarize terminal review labels for PDF metric extraction.")
    ap.add_argument("--labels", required=True, help="labels.jsonl from review_pdf_metric_terminal.py")
    args = ap.parse_args()

    path = Path(args.labels).resolve()
    if not path.exists():
        print(f"Labels not found: {path}")
        return 2

    rows: List[Dict[str, object]] = list(iter_jsonl(path))
    if not rows:
        print("No labels found.")
        return 1

    verdicts = Counter(str(r.get("verdict", "")) for r in rows)
    by_metric = defaultdict(lambda: Counter())
    for r in rows:
        verdict = str(r.get("verdict", ""))
        parsed_rows = r.get("parsed_rows", [])
        if isinstance(parsed_rows, list):
            seen = set()
            for pr in parsed_rows:
                if not isinstance(pr, dict):
                    continue
                metric = str(pr.get("metric", "unknown"))
                if metric not in seen:
                    by_metric[metric][verdict] += 1
                    seen.add(metric)

    print(f"Total labeled samples: {len(rows)}")
    print(f"Correct: {verdicts.get('correct', 0)}")
    print(f"Incorrect: {verdicts.get('incorrect', 0)}")

    print("\nPer-metric correctness:")
    for metric in sorted(by_metric.keys()):
        c = by_metric[metric].get("correct", 0)
        n = by_metric[metric].get("incorrect", 0)
        t = c + n
        if t == 0:
            continue
        acc = (c / t) * 100.0
        print(f"- {metric}: {c}/{t} correct ({acc:.1f}%)")

    print("\nHow this trains the system:")
    print("- Treat these labels as ground truth.")
    print("- Use low-accuracy metrics to tighten regex/rules and confidence thresholds.")
    print("- Use corrected_rows to build supervised training data for an extraction model.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
