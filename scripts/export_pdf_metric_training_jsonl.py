#!/usr/bin/env python3
import argparse
import json
from pathlib import Path
from typing import Dict, Iterable


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
    ap = argparse.ArgumentParser(description="Export labeled PDF metric samples to training JSONL.")
    ap.add_argument("--labels", required=True, help="labels.jsonl from review_pdf_metric_terminal.py")
    ap.add_argument("--out", required=True, help="Output training JSONL")
    args = ap.parse_args()

    labels_path = Path(args.labels).resolve()
    if not labels_path.exists():
        print(f"Labels not found: {labels_path}")
        return 2

    out_path = Path(args.out).resolve()
    out_path.parent.mkdir(parents=True, exist_ok=True)

    count = 0
    with out_path.open("w", encoding="utf-8") as out:
        for row in iter_jsonl(labels_path):
            verdict = row.get("verdict")
            parsed = row.get("parsed_rows", [])
            corrected = row.get("corrected_rows")
            if verdict == "correct":
                target = parsed
            elif verdict == "incorrect" and isinstance(corrected, list):
                target = corrected
            else:
                continue

            prompt = {
                "pdf": row.get("pdf"),
                "page": row.get("page"),
                "line_no": row.get("line_no"),
                "text": row.get("text"),
                "instruction": "Extract financial metrics as JSON rows.",
            }
            rec = {"sample_id": row.get("sample_id"), "prompt": prompt, "target": target}
            out.write(json.dumps(rec, ensure_ascii=True) + "\n")
            count += 1

    print(f"Wrote {count} training rows to {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
