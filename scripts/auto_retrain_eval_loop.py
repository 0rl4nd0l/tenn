#!/usr/bin/env python3
import argparse
import hashlib
import json
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple

CANONICAL_STATEMENT_SCOPES = {"consolidated_statement", "appendix_statement"}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def iter_jsonl(path: Path) -> Iterable[Dict[str, object]]:
    if not path.exists():
        return
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(obj, dict):
                yield obj


def append_jsonl(path: Path, obj: Dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(obj, ensure_ascii=True) + "\n")


def load_state(path: Path) -> Dict[str, object]:
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    if not isinstance(data, dict):
        return {}
    return data


def save_state(path: Path, state: Dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(state, indent=2), encoding="utf-8")


def file_sha1(path: Path) -> str:
    h = hashlib.sha1()
    with path.open("rb") as f:
        while True:
            chunk = f.read(1024 * 1024)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()


def normalize_value(v: object) -> object:
    if isinstance(v, bool):
        return v
    if isinstance(v, (int, float)):
        try:
            return round(float(v), 6)
        except (TypeError, ValueError):
            return v
    if isinstance(v, str):
        s = " ".join(v.strip().split())
        n = s.replace(",", "")
        try:
            return round(float(n), 6)
        except ValueError:
            return s.lower()
    return str(v)


def metric_row_key(row: Dict[str, object]) -> Tuple[object, ...]:
    metric = str(row.get("metric", "")).strip().lower()
    value_type = str(row.get("value_type", "")).strip().lower()
    period = str(row.get("period", "")).strip().lower()
    currency = str(row.get("currency", "")).strip()
    value = normalize_value(row.get("value", ""))
    raw = str(row.get("raw_value", "")).strip().lower()
    return (metric, value_type, period, currency, value, raw)


def target_rows_from_label(row: Dict[str, object]) -> List[Dict[str, object]]:
    verdict = str(row.get("verdict", "")).strip().lower()
    parsed = row.get("parsed_rows", [])
    corrected = row.get("corrected_rows")
    if verdict == "correct" and isinstance(parsed, list):
        return [x for x in parsed if isinstance(x, dict)]
    if verdict == "incorrect" and isinstance(corrected, list):
        return [x for x in corrected if isinstance(x, dict)]
    return []


def is_canonical_training_row(row: Dict[str, object]) -> bool:
    scope = str(row.get("statement_scope", row.get("statement_type", ""))).strip().lower()
    inside_table = bool(row.get("inside_table", False))
    return inside_table and scope in CANONICAL_STATEMENT_SCOPES


def target_rows_for_training(row: Dict[str, object]) -> List[Dict[str, object]]:
    return [r for r in target_rows_from_label(row) if is_canonical_training_row(r)]


def export_training_rows(labels: List[Dict[str, object]], out_path: Path) -> int:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    count = 0
    with out_path.open("w", encoding="utf-8") as out:
        for row in labels:
            target_rows = target_rows_for_training(row)
            if not target_rows:
                continue
            prompt = {
                "pdf": row.get("pdf"),
                "page": row.get("page"),
                "line_no": row.get("line_no"),
                "text": row.get("text"),
                "instruction": "Extract financial metrics as JSON rows.",
            }
            rec = {
                "sample_id": row.get("sample_id"),
                "prompt": prompt,
                "target": target_rows,
                "source_verdict": row.get("verdict"),
                "ai_assisted": bool(row.get("ai_assisted", False)),
            }
            out.write(json.dumps(rec, ensure_ascii=True) + "\n")
            count += 1
    return count


def evaluate_labels(labels: List[Dict[str, object]]) -> Dict[str, object]:
    total = len(labels)
    correct = 0
    incorrect = 0
    ai_assisted = 0
    trainable = 0
    trainable_canonical = 0
    excluded_non_canonical = 0
    exact_match = 0
    precision_sum = 0.0
    recall_sum = 0.0
    f1_sum = 0.0

    for row in labels:
        verdict = str(row.get("verdict", "")).strip().lower()
        if verdict == "correct":
            correct += 1
        elif verdict == "incorrect":
            incorrect += 1
        if row.get("ai_assisted"):
            ai_assisted += 1

        parser_rows_raw = row.get("parsed_rows", [])
        if not isinstance(parser_rows_raw, list):
            parser_rows_raw = []
        parser_rows = [x for x in parser_rows_raw if isinstance(x, dict) and is_canonical_training_row(x)]
        parser_keys = {metric_row_key(x) for x in parser_rows}
        target_rows_raw = target_rows_from_label(row)
        if not target_rows_raw:
            continue
        target_rows = [x for x in target_rows_raw if is_canonical_training_row(x)]
        if not target_rows:
            excluded_non_canonical += 1
            continue
        trainable += 1
        trainable_canonical += 1
        target_keys = {metric_row_key(x) for x in target_rows}
        if parser_keys == target_keys:
            exact_match += 1

        inter = len(parser_keys & target_keys)
        p = inter / len(parser_keys) if parser_keys else (1.0 if not target_keys else 0.0)
        r = inter / len(target_keys) if target_keys else (1.0 if not parser_keys else 0.0)
        f1 = (2 * p * r / (p + r)) if (p + r) > 0 else 0.0
        precision_sum += p
        recall_sum += r
        f1_sum += f1

    macro_precision = precision_sum / trainable if trainable else 0.0
    macro_recall = recall_sum / trainable if trainable else 0.0
    macro_f1 = f1_sum / trainable if trainable else 0.0
    exact_acc = exact_match / trainable if trainable else 0.0

    return {
        "timestamp_utc": utc_now(),
        "total_labels": total,
        "correct": correct,
        "incorrect": incorrect,
        "ai_assisted_labels": ai_assisted,
        "trainable_labels": trainable,
        "trainable_canonical_labels": trainable_canonical,
        "excluded_non_canonical_labels": excluded_non_canonical,
        "parser_exact_match_count": exact_match,
        "parser_exact_match_rate": round(exact_acc, 6),
        "parser_macro_precision": round(macro_precision, 6),
        "parser_macro_recall": round(macro_recall, 6),
        "parser_macro_f1": round(macro_f1, 6),
    }


def run_cmd(cmd: str, timeout_sec: int) -> Dict[str, object]:
    start = time.time()
    cp = subprocess.run(
        cmd,
        shell=True,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=timeout_sec,
    )
    elapsed = time.time() - start
    return {
        "cmd": cmd,
        "returncode": int(cp.returncode),
        "elapsed_sec": round(elapsed, 3),
        "stdout_tail": cp.stdout[-4000:],
        "stderr_tail": cp.stderr[-4000:],
    }


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Auto loop: labels -> training JSONL export -> eval summary -> optional retrain command."
    )
    ap.add_argument("--labels", required=True, help="labels.jsonl from review_pdf_metric_terminal.py")
    ap.add_argument("--training-out", default="", help="Training JSONL output path (default: alongside labels)")
    ap.add_argument("--eval-out", default="", help="Eval summary JSON path (default: alongside labels)")
    ap.add_argument("--loop-log", default="", help="Loop log JSONL path (default: alongside labels)")
    ap.add_argument("--state", default="", help="State JSON path (default: alongside labels)")
    ap.add_argument("--retrain-cmd", default="", help="Optional retrain command to run when labels change")
    ap.add_argument("--eval-cmd", default="", help="Optional eval command to run after retrain command")
    ap.add_argument("--cmd-timeout-sec", type=int, default=7200, help="Timeout per external command")
    ap.add_argument("--interval-sec", type=int, default=300, help="Sleep between loop passes")
    ap.add_argument("--passes", type=int, default=0, help="Number of passes (0 = forever)")
    ap.add_argument("--min-new-labels", type=int, default=1, help="Minimum new labels before retrain triggers")
    args = ap.parse_args()

    labels_path = Path(args.labels).resolve()
    if not labels_path.exists():
        print(f"Labels not found: {labels_path}")
        return 2

    base_dir = labels_path.parent
    training_out = Path(args.training_out).resolve() if args.training_out else (base_dir / "training_from_labels.jsonl")
    eval_out = Path(args.eval_out).resolve() if args.eval_out else (base_dir / "eval_summary.json")
    loop_log = Path(args.loop_log).resolve() if args.loop_log else (base_dir / "retrain_eval_loop.jsonl")
    state_path = Path(args.state).resolve() if args.state else (base_dir / "retrain_eval_state.json")

    state = load_state(state_path)
    pass_no = 0

    while True:
        pass_no += 1
        labels = list(iter_jsonl(labels_path))
        fp = file_sha1(labels_path)
        prev_fp = str(state.get("labels_sha1", ""))
        prev_count = int(state.get("label_count", 0) or 0)
        changed = fp != prev_fp
        new_labels = max(0, len(labels) - prev_count)

        training_count = export_training_rows(labels, training_out)
        summary = evaluate_labels(labels)
        summary["labels_path"] = str(labels_path)
        summary["training_out"] = str(training_out)
        summary["training_rows"] = training_count
        summary["labels_sha1"] = fp
        summary["pass"] = pass_no
        summary["changed_since_last"] = changed
        summary["new_labels_since_last"] = new_labels

        eval_out.parent.mkdir(parents=True, exist_ok=True)
        eval_out.write_text(json.dumps(summary, indent=2), encoding="utf-8")

        retrain_result: Optional[Dict[str, object]] = None
        eval_cmd_result: Optional[Dict[str, object]] = None
        retrain_due = changed and new_labels >= max(1, args.min_new_labels)
        retrain_triggered = retrain_due and bool(args.retrain_cmd)
        if retrain_triggered and args.retrain_cmd:
            try:
                retrain_result = run_cmd(args.retrain_cmd, timeout_sec=args.cmd_timeout_sec)
            except subprocess.TimeoutExpired as exc:
                retrain_result = {
                    "cmd": args.retrain_cmd,
                    "returncode": -1,
                    "elapsed_sec": float(args.cmd_timeout_sec),
                    "stdout_tail": (exc.stdout or "")[-4000:],
                    "stderr_tail": (exc.stderr or "")[-4000:],
                    "error": "timeout",
                }
            if args.eval_cmd:
                try:
                    eval_cmd_result = run_cmd(args.eval_cmd, timeout_sec=args.cmd_timeout_sec)
                except subprocess.TimeoutExpired as exc:
                    eval_cmd_result = {
                        "cmd": args.eval_cmd,
                        "returncode": -1,
                        "elapsed_sec": float(args.cmd_timeout_sec),
                        "stdout_tail": (exc.stdout or "")[-4000:],
                        "stderr_tail": (exc.stderr or "")[-4000:],
                        "error": "timeout",
                    }

        log_row = dict(summary)
        log_row["retrain_due"] = retrain_due
        log_row["retrain_triggered"] = retrain_triggered
        if retrain_result is not None:
            log_row["retrain_result"] = retrain_result
        if eval_cmd_result is not None:
            log_row["eval_cmd_result"] = eval_cmd_result
        append_jsonl(loop_log, log_row)

        state["labels_sha1"] = fp
        state["label_count"] = len(labels)
        state["last_pass"] = pass_no
        state["last_pass_utc"] = utc_now()
        if retrain_triggered:
            state["last_retrain_utc"] = utc_now()
        save_state(state_path, state)

        print(
            f"[pass {pass_no}] labels={len(labels)} trainable={summary['trainable_labels']} "
            f"exact={summary['parser_exact_match_rate']:.3f} changed={changed} new={new_labels} retrain={retrain_triggered}"
        )
        print(f"Eval summary: {eval_out}")
        print(f"Training JSONL: {training_out}")

        if args.passes > 0 and pass_no >= args.passes:
            break
        if args.interval_sec <= 0:
            break
        time.sleep(args.interval_sec)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
