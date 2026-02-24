#!/usr/bin/env python3
import argparse
import hashlib
import importlib.util
import json
import re
import subprocess
import sys
import time
import urllib.error
import urllib.request
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple


OLLAMA_URL = "http://127.0.0.1:11434/api/generate"

TARGET_METRICS = [
    "revenue",
    "segment_revenue",
    "gross_profit",
    "ebitda",
    "ebit",
    "npat",
    "net_income",
    "free_cash_flow",
    "operating_cash_flow",
    "roic_pct",
    "net_debt",
    "total_debt",
    "current_assets",
    "current_liabilities",
    "total_assets",
    "total_liabilities",
    "total_equity",
    "shares_outstanding",
    "cash_and_equivalents",
    "cash_and_equivalents_opening",
    "cash_and_equivalents_closing",
    "eps",
    "capex",
    "growth_pct",
    "guidance",
]

PDF_KEYWORDS = (
    "financial",
    "results",
    "appendix 4c",
    "4c",
    "quarterly",
    "cash flow",
)
APPENDIX_4C_RE = re.compile(r"(appendix[\s\-_]*4c|\b4c\b|quarterly cash flow|cashflow report)", re.IGNORECASE)
APPENDIX_DOC_RE = re.compile(
    r"(appendix[\s\-_]*(4c|4d|4e|5b)(?:$|[^a-z0-9])|quarterly[\s\-_]*(cash[\s\-_]*flow|cashflow)(?:$|[^a-z0-9]))",
    re.IGNORECASE,
)
CANONICAL_DOC_RE = re.compile(
    r"(appendix[\s\-_]*(4c|4d|4e|5b)(?:$|[^a-z0-9])|"
    r"quarterly[\s\-_]*(cash[\s\-_]*flow|cashflow)(?:$|[^a-z0-9])|"
    r"annual[\s\-_]*report(?:$|[^a-z0-9])|"
    r"half[\s\-_]*year(?:ly)?[\s\-_]*(report|results|accounts)?(?:$|[^a-z0-9])|"
    r"interim[\s\-_]*(report|financial)(?:$|[^a-z0-9])|"
    r"financial[\s\-_]*(report|statements?|accounts)(?:$|[^a-z0-9])|"
    r"preliminary[\s\-_]*final[\s\-_]*report(?:$|[^a-z0-9])|"
    r"(?:^|[^a-z0-9])accounts?(?:$|[^a-z0-9])|"
    r"audited[\s\-_]*financial|unaudited[\s\-_]*financial)",
    re.IGNORECASE,
)
CONTEXT_DOC_RE = re.compile(
    r"(quarterly[\s\-_]*activities?|activity[\s\-_]*report|presentation|media[\s\-_]*release|webcast|"
    r"notice[\s\-_]*of|results[\s\-_]*of[\s\-_]*meeting|chair|investor|update|letter[\s\-_]*to[\s\-_]*shareholders|"
    r"conference[\s\-_]*call)",
    re.IGNORECASE,
)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def load_extract_module(repo_root: Path):
    module_path = repo_root / "scripts" / "extract_financial_metrics.py"
    spec = importlib.util.spec_from_file_location("extract_financial_metrics", str(module_path))
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Failed to load parser module at {module_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def append_jsonl(path: Path, rec: Dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(rec, ensure_ascii=True) + "\n")


def load_state(path: Path) -> Dict[str, object]:
    if not path.exists():
        return {"processed": {}}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {"processed": {}}


def save_state(path: Path, state: Dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(state, indent=2), encoding="utf-8")


def file_fingerprint(path: Path) -> str:
    st = path.stat()
    return f"{int(st.st_mtime)}:{st.st_size}"


def find_candidate_pdfs(root: Path) -> List[Path]:
    out = []
    for p in sorted(root.rglob("*.pdf")):
        if not p.is_file():
            continue
        full = str(p).lower()
        name = p.name
        in_financial_perf = "/financial_performance/" in full
        is_appendix_4c = bool(APPENDIX_4C_RE.search(name)) or bool(APPENDIX_4C_RE.search(full))
        if in_financial_perf or is_appendix_4c:
            out.append(p)
    return out


def classify_pdf_source(pdf: Path) -> Tuple[str, int, bool]:
    text = f"{str(pdf).lower()} {pdf.name.lower()}"
    if APPENDIX_DOC_RE.search(text):
        return "appendix_report", 110, True
    if CANONICAL_DOC_RE.search(text):
        return "canonical_report", 100, True
    if CONTEXT_DOC_RE.search(text):
        return "context_update", 30, False
    return "other", 20, False


def extract_pdf_text(pdf: Path) -> str:
    cp = subprocess.run(
        ["pdftotext", "-layout", str(pdf), "-"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=True,
    )
    return cp.stdout.replace("\r", "\n")


def chunk_text(text: str, max_chars: int = 7000, overlap: int = 600) -> List[str]:
    text = re.sub(r"\n{3,}", "\n\n", text).strip()
    if not text:
        return []
    chunks: List[str] = []
    i = 0
    n = len(text)
    while i < n:
        j = min(n, i + max_chars)
        chunks.append(text[i:j])
        if j >= n:
            break
        i = max(i + 1, j - overlap)
    return chunks


def extract_json_from_text(s: str) -> Optional[object]:
    raw = s.strip()
    if not raw:
        return None
    raw = re.sub(r"^```(?:json)?\s*", "", raw)
    raw = re.sub(r"\s*```$", "", raw)
    # Try full parse first.
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        pass
    # Fallback: parse largest bracketed block.
    m = re.search(r"(\[.*\]|\{.*\})", raw, flags=re.DOTALL)
    if not m:
        return None
    try:
        return json.loads(m.group(1))
    except json.JSONDecodeError:
        return None


def ollama_generate(model: str, prompt: str, keep_alive: str, timeout_sec: int, retries: int = 2) -> str:
    payload = json.dumps({"model": model, "prompt": prompt, "stream": False, "keep_alive": keep_alive}).encode(
        "utf-8"
    )
    req = urllib.request.Request(
        OLLAMA_URL,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    last_err: Optional[Exception] = None
    for _ in range(retries + 1):
        try:
            with urllib.request.urlopen(req, timeout=timeout_sec) as r:
                body = json.loads(r.read().decode("utf-8"))
                return str(body.get("response", "")).strip()
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as e:
            last_err = e
            time.sleep(2)
    raise RuntimeError(f"Ollama call failed: {last_err}")


def parse_rows_by_line(rows: List[Dict[str, object]]) -> Dict[int, List[Dict[str, object]]]:
    out: Dict[int, List[Dict[str, object]]] = defaultdict(list)
    for r in rows:
        ln = int(r.get("line_no", 0))
        if ln > 0:
            out[ln].append(r)
    return out


def ai_extract_from_chunk(model: str, text_chunk: str, timeout_sec: int, keep_alive: str) -> List[Dict[str, object]]:
    prompt = (
        "You extract financial metrics from report text.\n"
        "Return JSON array only. No markdown.\n"
        f"Only metrics from this set: {', '.join(TARGET_METRICS)}.\n"
        "Prefer explicit table/report figures. Avoid event cash receipts/proceeds unless guidance explicitly states target balance.\n"
        "Schema per item: metric, value_type(amount|percent|text), raw_value, value, currency, period, source_text.\n\n"
        f"TEXT:\n{text_chunk}"
    )
    out = ollama_generate(model, prompt, keep_alive=keep_alive, timeout_sec=timeout_sec)
    obj = extract_json_from_text(out)
    if not isinstance(obj, list):
        return []
    clean = []
    for r in obj:
        if not isinstance(r, dict):
            continue
        metric = str(r.get("metric", "")).strip()
        if metric not in TARGET_METRICS:
            continue
        clean.append(
            {
                "metric": metric,
                "value_type": str(r.get("value_type", "text")),
                "raw_value": str(r.get("raw_value", "")),
                "value": r.get("value", ""),
                "currency": str(r.get("currency", "")),
                "period": str(r.get("period", "")),
                "source_text": str(r.get("source_text", "")),
            }
        )
    return clean


def ai_review_parser_line(
    model: str,
    line: str,
    parser_rows: List[Dict[str, object]],
    context_prev: str,
    context_next: str,
    timeout_sec: int,
    keep_alive: str,
) -> Dict[str, object]:
    prompt = (
        "You review parser output for financial metrics.\n"
        "Decide if parser rows are correct for this line.\n"
        "Reject narrative cash events as cash balance.\n"
        "Return JSON object only with keys: verdict(approved|corrected|rejected), corrected_rows(array), note.\n"
        f"Allowed metrics: {', '.join(TARGET_METRICS)}.\n\n"
        f"PREV LINE: {context_prev}\n"
        f"LINE: {line}\n"
        f"NEXT LINE: {context_next}\n"
        f"PARSER_ROWS: {json.dumps(parser_rows, ensure_ascii=True)}\n"
    )
    out = ollama_generate(model, prompt, keep_alive=keep_alive, timeout_sec=timeout_sec)
    obj = extract_json_from_text(out)
    if not isinstance(obj, dict):
        return {"verdict": "rejected", "corrected_rows": [], "note": "invalid_ai_json"}
    verdict = str(obj.get("verdict", "rejected")).lower().strip()
    if verdict not in {"approved", "corrected", "rejected"}:
        verdict = "rejected"
    corrected_rows = obj.get("corrected_rows", [])
    if not isinstance(corrected_rows, list):
        corrected_rows = []
    note = str(obj.get("note", ""))
    return {"verdict": verdict, "corrected_rows": corrected_rows, "note": note}


def dedupe_rows(rows: Iterable[Dict[str, object]]) -> List[Dict[str, object]]:
    seen = set()
    out = []
    for r in rows:
        key = (
            r.get("metric", ""),
            r.get("value_type", ""),
            str(r.get("raw_value", "")),
            str(r.get("period", "")),
            str(r.get("source_text", r.get("line", ""))),
        )
        if key in seen:
            continue
        seen.add(key)
        out.append(r)
    return out


def process_pdf(
    pdf: Path,
    extract_mod,
    model: str,
    out_dir: Path,
    timeout_sec: int,
    keep_alive: str,
    max_reviews: int,
    enable_ai_direct_extraction: bool,
    canonical_metrics_only: bool,
    metrics_db_path: Optional[Path],
) -> None:
    pdf_id = hashlib.sha1(str(pdf).encode("utf-8")).hexdigest()[:16]
    source_kind, source_priority, is_canonical = classify_pdf_source(pdf)
    text = extract_pdf_text(pdf)
    lines = text.splitlines()

    parser_rows: List[Dict[str, object]] = []
    context_rows: List[Dict[str, object]] = []
    rejected_rows: List[Dict[str, object]] = []
    statement_blocks: List[Dict[str, object]] = []
    statement_blocks_summary: Dict[str, object] = {"total_blocks": 0, "by_scope": {}}
    metrics_allowed = (not canonical_metrics_only) or is_canonical
    if metrics_allowed:
        if hasattr(extract_mod, "extract_table_metrics"):
            try:
                _, statement_blocks, split = extract_mod.extract_table_metrics(
                    pdf,
                    strict_metric_rows_only=True,
                    source_kind=source_kind,
                    review_scope="all",
                    include_blocks=True,
                )
            except Exception:
                statement_blocks = []
                split = {"canonical_rows": [], "context_rows": [], "rejected_rows": []}
            parser_rows = list(split.get("canonical_rows", []))
            context_rows = list(split.get("context_rows", []))
            rejected_rows = list(split.get("rejected_rows", []))
            if hasattr(extract_mod, "summarize_statement_blocks"):
                try:
                    statement_blocks_summary = dict(extract_mod.summarize_statement_blocks(statement_blocks))
                except Exception:
                    statement_blocks_summary = {"total_blocks": len(statement_blocks), "by_scope": {}}
            else:
                statement_blocks_summary = {"total_blocks": len(statement_blocks), "by_scope": {}}
        elif hasattr(extract_mod, "parse_line"):
            # Compatibility fallback if table API is unavailable.
            active_section = ""
            for i, line in enumerate(lines, start=1):
                if hasattr(extract_mod, "detect_section_heading"):
                    try:
                        heading = str(extract_mod.detect_section_heading(line))
                    except Exception:
                        heading = ""
                    if heading:
                        active_section = heading
                parsed = extract_mod.parse_line(
                    pdf,
                    i,
                    line,
                    strict_table_only=True,
                    active_section=active_section,
                )
                parser_rows.extend(parsed)
    parser_rows = extract_mod.dedupe(parser_rows)
    context_rows = extract_mod.dedupe(context_rows) if hasattr(extract_mod, "dedupe") else context_rows
    rejected_rows = extract_mod.dedupe(rejected_rows) if hasattr(extract_mod, "dedupe") else rejected_rows
    for r in parser_rows:
        r["source_kind"] = source_kind
        r["source_priority"] = source_priority
        r["is_canonical_source"] = is_canonical
        r["confidence"] = extract_mod.score_confidence(r)
    for r in context_rows:
        r["source_kind"] = source_kind
        r["source_priority"] = source_priority
        r["is_canonical_source"] = is_canonical
        r["confidence"] = extract_mod.score_confidence(r)
    for r in rejected_rows:
        r["source_kind"] = source_kind
        r["source_priority"] = source_priority
        r["is_canonical_source"] = is_canonical
        r["confidence"] = extract_mod.score_confidence(r)

    db_rows_written = 0
    if metrics_db_path and parser_rows and hasattr(extract_mod, "store_metrics_sqlite"):
        try:
            db_rows_written = int(extract_mod.store_metrics_sqlite(parser_rows, metrics_db_path))
        except Exception as exc:
            append_jsonl(
                out_dir / "errors.jsonl",
                {
                    "timestamp_utc": utc_now(),
                    "pdf": str(pdf),
                    "error": f"metrics_db_upsert_failed: {exc}",
                },
            )

    parser_by_line = parse_rows_by_line(parser_rows)
    line_numbers = sorted(parser_by_line.keys())[:max_reviews]

    ai_reviews = []
    approved_or_fixed = []
    for ln in line_numbers:
        cur = lines[ln - 1] if 0 <= ln - 1 < len(lines) else ""
        prev = lines[ln - 2] if 0 <= ln - 2 < len(lines) else ""
        nxt = lines[ln] if 0 <= ln < len(lines) else ""
        review = ai_review_parser_line(
            model=model,
            line=cur,
            parser_rows=parser_by_line[ln],
            context_prev=prev,
            context_next=nxt,
            timeout_sec=timeout_sec,
            keep_alive=keep_alive,
        )
        rec = {
            "timestamp_utc": utc_now(),
            "pdf": str(pdf),
            "pdf_id": pdf_id,
            "line_no": ln,
            "line": cur,
            "parser_rows": parser_by_line[ln],
            "ai_review": review,
        }
        ai_reviews.append(rec)
        if review["verdict"] == "approved":
            approved_or_fixed.extend(parser_by_line[ln])
        elif review["verdict"] == "corrected":
            base_row = parser_by_line[ln][0] if parser_by_line.get(ln) else {}
            for rr in review.get("corrected_rows", []):
                if isinstance(rr, dict):
                    rr = dict(rr)
                    rr.setdefault("file", str(pdf))
                    rr.setdefault("line_no", ln)
                    rr.setdefault("line", cur)
                    rr.setdefault("inside_table", bool(base_row.get("inside_table", True)))
                    rr.setdefault("statement_scope", str(base_row.get("statement_scope", "consolidated_statement")))
                    rr.setdefault("statement_type", str(base_row.get("statement_type", rr.get("statement_scope", ""))))
                    rr.setdefault("statement_title", str(base_row.get("statement_title", "")))
                    rr.setdefault("statement_scope_reason", str(base_row.get("statement_scope_reason", "ai_corrected")))
                    rr.setdefault("block_id", str(base_row.get("block_id", "")))
                    rr.setdefault("page_number", int(base_row.get("page_number", ln) or ln))
                    approved_or_fixed.append(rr)

    ai_chunk_rows = []
    if enable_ai_direct_extraction:
        for idx, chunk in enumerate(chunk_text(text), start=1):
            rows = ai_extract_from_chunk(model=model, text_chunk=chunk, timeout_sec=timeout_sec, keep_alive=keep_alive)
            for r in rows:
                rec = {
                    "timestamp_utc": utc_now(),
                    "pdf": str(pdf),
                    "pdf_id": pdf_id,
                    "chunk_idx": idx,
                    **r,
                }
                ai_chunk_rows.append(rec)

    approved_or_fixed = dedupe_rows(approved_or_fixed)

    per_pdf = out_dir / "per_pdf" / f"{pdf_id}.json"
    per_pdf.parent.mkdir(parents=True, exist_ok=True)
    per_pdf.write_text(
        json.dumps(
            {
                "timestamp_utc": utc_now(),
                "pdf": str(pdf),
                "pdf_id": pdf_id,
                "source_kind": source_kind,
                "source_priority": source_priority,
                "is_canonical_source": is_canonical,
                "metrics_skipped_non_canonical": (canonical_metrics_only and not is_canonical),
                "parser_rows": parser_rows,
                "context_rows": context_rows,
                "rejected_rows": rejected_rows,
                "statement_blocks_summary": statement_blocks_summary,
                "statement_blocks": statement_blocks,
                "metrics_db_path": (str(metrics_db_path) if metrics_db_path else ""),
                "metrics_db_rows_upserted": db_rows_written,
                "ai_parser_reviews": ai_reviews,
                "ai_direct_rows": ai_chunk_rows,
                "approved_or_fixed_rows": approved_or_fixed,
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    for r in parser_rows:
        append_jsonl(out_dir / "parser_raw.jsonl", {"timestamp_utc": utc_now(), "pdf": str(pdf), **r})
        append_jsonl(out_dir / "parser_canonical.jsonl", {"timestamp_utc": utc_now(), "pdf": str(pdf), **r})
    for r in context_rows:
        append_jsonl(out_dir / "parser_context.jsonl", {"timestamp_utc": utc_now(), "pdf": str(pdf), **r})
    for r in rejected_rows:
        append_jsonl(out_dir / "parser_rejected.jsonl", {"timestamp_utc": utc_now(), "pdf": str(pdf), **r})
    for r in ai_reviews:
        append_jsonl(out_dir / "ai_parser_reviews.jsonl", r)
    for r in ai_chunk_rows:
        append_jsonl(out_dir / "ai_direct_extractions.jsonl", r)
    for r in approved_or_fixed:
        append_jsonl(
            out_dir / "training_from_ai_review.jsonl",
            {
                "timestamp_utc": utc_now(),
                "pdf": str(pdf),
                "instruction": "Extract financial metrics as JSON rows from line-level report text.",
                "target": r,
            },
        )

    print(
        f"[done] {pdf} | source={source_kind} canonical={is_canonical} "
        f"parser_rows={len(parser_rows)} context_rows={len(context_rows)} rejected_rows={len(rejected_rows)} "
        f"ai_reviewed_lines={len(ai_reviews)} ai_direct={len(ai_chunk_rows)} db_upserted={db_rows_written}"
    )


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Autonomous long-running loop: parser extraction + AI extraction + AI review/fix of parser outputs."
    )
    ap.add_argument("--pdf-dir", required=True, help="Root folder containing company reports/PDFs")
    ap.add_argument("--out-dir", default="reports/auto_self_train", help="Output folder for artifacts/state")
    ap.add_argument("--model", default="qwen2.5:32b", help="Ollama model name for extraction/review")
    ap.add_argument("--keep-alive", default="2h", help="Ollama keep_alive")
    ap.add_argument("--timeout-sec", type=int, default=240, help="Per AI request timeout")
    ap.add_argument("--max-pdfs-per-pass", type=int, default=30, help="Limit processed PDFs per pass")
    ap.add_argument("--max-reviews-per-pdf", type=int, default=80, help="Max parser lines AI reviews per PDF")
    ap.add_argument("--sleep-seconds", type=int, default=300, help="Sleep between passes")
    ap.add_argument("--passes", type=int, default=0, help="Number of passes (0 means run forever)")
    ap.add_argument(
        "--metrics-db",
        default="reports/financial_metrics.sqlite",
        help="SQLite DB path for canonical metric rows (set empty to disable)",
    )
    ap.add_argument(
        "--allow-context-metrics",
        action="store_true",
        help=(
            "By default, only canonical reports (Appendix 4C/4D/4E/5B and financial reports/statements) "
            "contribute metric rows. Set this flag to also allow metrics from activity/announcement docs."
        ),
    )
    ap.add_argument(
        "--enable-ai-direct-extraction",
        action="store_true",
        help="Allow free-text AI extraction chunks. Default off to keep table-only policy.",
    )
    args = ap.parse_args()

    root = Path(args.pdf_dir).resolve()
    if not root.exists():
        print(f"PDF directory not found: {root}", file=sys.stderr)
        return 2

    out_dir = Path(args.out_dir).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    metrics_db_path = Path(args.metrics_db).resolve() if str(args.metrics_db).strip() else None
    state_path = out_dir / "state.json"
    state = load_state(state_path)
    processed = state.setdefault("processed", {})

    repo_root = Path(__file__).resolve().parents[1]
    extract_mod = load_extract_module(repo_root)

    pass_no = 0
    while True:
        pass_no += 1
        start = utc_now()
        pdfs = find_candidate_pdfs(root)
        todo = []
        for pdf in pdfs:
            fp = file_fingerprint(pdf)
            if processed.get(str(pdf)) != fp:
                todo.append(pdf)
        if args.max_pdfs_per_pass > 0:
            todo = todo[: args.max_pdfs_per_pass]

        append_jsonl(
            out_dir / "run_log.jsonl",
            {
                "timestamp_utc": start,
                "pass": pass_no,
                "found_pdfs": len(pdfs),
                "todo": len(todo),
                "model": args.model,
                "canonical_metrics_only": (not args.allow_context_metrics),
                "metrics_db": (str(metrics_db_path) if metrics_db_path else ""),
            },
        )

        for pdf in todo:
            try:
                process_pdf(
                    pdf=pdf,
                    extract_mod=extract_mod,
                    model=args.model,
                    out_dir=out_dir,
                    timeout_sec=args.timeout_sec,
                    keep_alive=args.keep_alive,
                    max_reviews=args.max_reviews_per_pdf,
                    enable_ai_direct_extraction=args.enable_ai_direct_extraction,
                    canonical_metrics_only=(not args.allow_context_metrics),
                    metrics_db_path=metrics_db_path,
                )
                processed[str(pdf)] = file_fingerprint(pdf)
                save_state(state_path, state)
            except Exception as exc:
                append_jsonl(
                    out_dir / "errors.jsonl",
                    {"timestamp_utc": utc_now(), "pdf": str(pdf), "error": str(exc), "pass": pass_no},
                )
                print(f"[error] {pdf}: {exc}", file=sys.stderr)

        if args.passes > 0 and pass_no >= args.passes:
            break
        if args.sleep_seconds <= 0:
            break
        print(f"[sleep] {args.sleep_seconds}s before next pass")
        time.sleep(args.sleep_seconds)

    print(f"Finished after {pass_no} pass(es). Out dir: {out_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
