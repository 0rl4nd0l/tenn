#!/usr/bin/env python3
import argparse
import json
import re
import socket
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional

from PIL import Image


ASCII_CHARS = " .:-=+*#%@"
ALLOWED_METRICS = {
    "revenue",
    "segment_revenue",
    "gross_profit",
    "gross_margin_pct",
    "ebitda",
    "ebit",
    "operating_margin_pct",
    "net_income",
    "npat",
    "eps",
    "free_cash_flow",
    "operating_cash_flow",
    "cash_and_equivalents",
    "net_debt",
    "total_debt",
    "current_assets",
    "current_liabilities",
    "total_assets",
    "total_liabilities",
    "total_equity",
    "shares_outstanding",
    "roic_pct",
    "capex",
    "guidance",
    "growth_pct",
}
CANONICAL_STATEMENT_SCOPES = {"consolidated_statement", "appendix_statement"}
METRIC_LINE_HINTS = {
    "revenue": [r"\brevenue\b", r"\bturnover\b", r"\btotal income\b"],
    "segment_revenue": [r"\bsegment\b.*\brevenue\b", r"\bdivision\b.*\brevenue\b", r"\bbusiness unit\b.*\brevenue\b"],
    "gross_profit": [r"\bgross\s+(profit|income)\b"],
    "gross_margin_pct": [r"\bgross\s+margin\b"],
    "ebitda": [r"\bebitda\b"],
    "ebit": [r"\bebit\b", r"\boperating\s+(profit|income)\b"],
    "operating_margin_pct": [r"\boperating\s+margin\b", r"\bebit\s+margin\b"],
    "net_income": [
        r"\bnet\s+(income|profit)\b",
        r"\bprofit\s+after\s+tax\b",
        r"\bloss\s+after\s+tax\b",
        r"\bprofit\s*/?\s*\(?loss\)?\b",
    ],
    "npat": [r"\bnpat\b", r"\bnet\s+profit\s+after\s+tax\b"],
    "eps": [r"\beps\b", r"\bearnings\s+per\s+share\b", r"\bloss\s+per\s+share\b"],
    "free_cash_flow": [r"\bfree\s+cash\s+flow\b", r"\bfcf\b"],
    "operating_cash_flow": [r"\boperating\s+cash\s+flow\b", r"\bcash\s+from\s+operations\b"],
    "cash_and_equivalents": [r"\bcash\b", r"\bcash\s+equivalents?\b"],
    "net_debt": [r"\bnet\s+debt\b"],
    "total_debt": [r"\btotal\s+debt\b", r"\btotal\s+borrowings\b", r"\binterest[- ]bearing\s+debt\b", r"\bborrowings\b"],
    "current_assets": [r"\bcurrent\s+assets?\b"],
    "current_liabilities": [r"\bcurrent\s+liabilities?\b"],
    "total_assets": [r"\btotal\s+assets?\b"],
    "total_liabilities": [r"\btotal\s+liabilities?\b"],
    "total_equity": [r"\btotal\s+equity\b", r"\bshareholders'?\s+equity\b", r"\bequity\s+attributable\b", r"\bnet\s+assets\b"],
    "shares_outstanding": [r"\bshares?\b", r"\bon\s+issue\b", r"\bweighted\s+average\b"],
    "roic_pct": [r"\broic\b", r"\breturn\s+on\s+invested\s+capital\b"],
    "capex": [r"\bcapex\b", r"\bcapital\s+expenditure\b"],
    "guidance": [r"\bguidance\b", r"\boutlook\b", r"\bforecast\b", r"\bexpect"],
    "growth_pct": [r"\byoy\b", r"\byear[- ]over[- ]year\b", r"\bqoq\b", r"\bcagr\b"],
}


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def image_to_ascii(path: Path, width: int = 90, max_lines: int = 45) -> str:
    with Image.open(path) as img:
        gray = img.convert("L")
        w, h = gray.size
        if w == 0 or h == 0:
            return "[empty image]"
        aspect = h / w
        out_h = max(10, int(width * aspect * 0.5))
        gray = gray.resize((width, out_h))
        pix = gray.load()
        lines: List[str] = []
        for y in range(min(out_h, max_lines)):
            line_chars = []
            for x in range(width):
                v = pix[x, y]
                idx = int(v / 255 * (len(ASCII_CHARS) - 1))
                line_chars.append(ASCII_CHARS[idx])
            lines.append("".join(line_chars))
        if out_h > max_lines:
            lines.append("[image truncated]")
        return "\n".join(lines)


def append_jsonl(path: Path, obj: Dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(obj, ensure_ascii=True) + "\n")


def load_labeled_ids(path: Path) -> set:
    ids = set()
    if not path.exists():
        return ids
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
                sid = obj.get("sample_id")
                if sid:
                    ids.add(sid)
            except json.JSONDecodeError:
                continue
    return ids


def parse_corrected_rows() -> Optional[List[Dict[str, object]]]:
    print("Paste corrected parsed rows as JSON array, then enter a single '.' line to finish.")
    buf: List[str] = []
    while True:
        line = input()
        if line.strip() == ".":
            break
        buf.append(line)
    raw = "\n".join(buf).strip()
    if not raw:
        return None
    data = json.loads(raw)
    if not isinstance(data, list):
        raise ValueError("Corrected rows must be a JSON array.")
    return data


def extract_json_from_text(s: str) -> Optional[object]:
    raw = s.strip()
    if not raw:
        return None
    raw = re.sub(r"^```(?:json)?\s*", "", raw)
    raw = re.sub(r"\s*```$", "", raw)
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        pass
    m = re.search(r"(\[.*\]|\{.*\})", raw, flags=re.DOTALL)
    if not m:
        return None
    try:
        return json.loads(m.group(1))
    except json.JSONDecodeError:
        return None


def _clip_text(value: object, limit: int) -> str:
    text = str(value or "")
    if limit <= 0 or len(text) <= limit:
        return text
    head = text[:limit]
    return head + "\n...[truncated]..."


def ollama_generate(
    ollama_url: str,
    model: str,
    prompt: str,
    keep_alive: str,
    timeout_sec: int,
    retries: int = 1,
) -> str:
    payload = json.dumps({"model": model, "prompt": prompt, "stream": False, "keep_alive": keep_alive}).encode("utf-8")
    req = urllib.request.Request(
        ollama_url,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    last_err: Optional[Exception] = None
    for attempt in range(retries + 1):
        try:
            with urllib.request.urlopen(req, timeout=timeout_sec) as r:
                body = json.loads(r.read().decode("utf-8"))
                return str(body.get("response", "")).strip()
        except (urllib.error.URLError, TimeoutError, socket.timeout, json.JSONDecodeError) as e:
            last_err = e
            if attempt < retries:
                time.sleep(min(4, 1 + attempt))
    raise RuntimeError(f"Ollama call failed: {last_err}")


def line_supports_metric(metric: str, line: str) -> bool:
    text = line.lower()
    for pat in METRIC_LINE_HINTS.get(metric, []):
        if re.search(pat, text, flags=re.IGNORECASE):
            return True
    return False


def raw_appears_in_line(raw_value: str, line: str) -> bool:
    raw = raw_value.strip()
    if not raw:
        return True
    norm_raw = re.sub(r"\s+", "", raw).lower()
    norm_line = re.sub(r"\s+", "", line).lower()
    if norm_raw in norm_line:
        return True
    comp_raw = re.sub(r"[^0-9.\-()%]", "", raw).lower()
    comp_line = re.sub(r"[^0-9.\-()%]", "", line).lower()
    return bool(comp_raw) and comp_raw in comp_line


def normalize_ai_rows(rows: List[object], sample: Dict[str, object]) -> List[Dict[str, object]]:
    out: List[Dict[str, object]] = []
    for item in rows:
        if not isinstance(item, dict):
            continue
        metric = str(item.get("metric", "")).strip()
        if not metric or metric not in ALLOWED_METRICS:
            continue
        value_type = str(item.get("value_type", "")).strip().lower()
        if value_type not in {"amount", "percent", "text"}:
            value_type = "amount" if item.get("value", "") not in {"", None} else "text"
        line_text = str(item.get("line", sample.get("text", "")))
        raw_value = str(item.get("raw_value", ""))
        if line_text and not line_supports_metric(metric, line_text):
            continue
        if value_type in {"amount", "percent"} and not raw_appears_in_line(raw_value, line_text):
            continue
        rec = {
            "file": str(item.get("file", sample.get("pdf", ""))),
            "line_no": int(item.get("line_no", sample.get("line_no", 0) or 0)),
            "metric": metric,
            "value_type": value_type,
            "raw_value": raw_value,
            "value": item.get("value", ""),
            "currency": str(item.get("currency", "")),
            "period": str(item.get("period", "")),
            "confidence": float(item.get("confidence", 0.0) or 0.0),
            "line": line_text,
            "statement_scope": str(item.get("statement_scope", "")),
            "statement_title": str(item.get("statement_title", "")),
            "statement_scope_reason": str(item.get("statement_scope_reason", "")),
            "block_id": str(item.get("block_id", "")),
            "inside_table": bool(item.get("inside_table", False)),
            "page_number": int(item.get("page_number", sample.get("page", 0) or 0)),
            "note_number": str(item.get("note_number", "")),
        }
        out.append(rec)
    return out


def enforce_corrected_scope(rows: List[Dict[str, object]], sample: Dict[str, object]) -> List[Dict[str, object]]:
    review_scope = str(sample.get("review_scope", "canonical")).strip().lower()
    if review_scope != "canonical":
        return rows
    parsed_rows = [r for r in sample.get("parsed_rows", []) if isinstance(r, dict)]
    defaults = parsed_rows[0] if parsed_rows else {}
    default_scope = str(defaults.get("statement_scope", defaults.get("statement_type", "consolidated_statement"))).strip()
    if default_scope not in CANONICAL_STATEMENT_SCOPES:
        default_scope = "consolidated_statement"
    out: List[Dict[str, object]] = []
    for row in rows:
        rr = dict(row)
        rr["inside_table"] = True
        scope = str(rr.get("statement_scope", rr.get("statement_type", default_scope))).strip()
        if not scope:
            scope = default_scope
        if scope not in CANONICAL_STATEMENT_SCOPES:
            continue
        rr["statement_scope"] = scope
        rr.setdefault("statement_type", scope)
        rr.setdefault("statement_title", str(defaults.get("statement_title", defaults.get("statement_scope_header", ""))))
        rr.setdefault("statement_scope_reason", str(defaults.get("statement_scope_reason", "ai_corrected")))
        rr.setdefault("block_id", str(defaults.get("block_id", "")))
        rr.setdefault("page_number", int(defaults.get("page_number", sample.get("page", 0) or 0)))
        rr.setdefault("note_number", str(defaults.get("note_number", "")))
        out.append(rr)
    return out


def ai_suggest_corrected_rows(
    sample: Dict[str, object],
    ollama_url: str,
    model: str,
    keep_alive: str,
    timeout_sec: int,
    reviewer_prompt: str = "",
    retries: int = 2,
    max_section_chars: int = 4000,
    max_parser_rows: int = 12,
) -> List[Dict[str, object]]:
    reviewer_prompt = reviewer_prompt.strip()
    parser_rows = sample.get("parsed_rows", [])
    if isinstance(parser_rows, list):
        parser_rows = parser_rows[: max(1, int(max_parser_rows))]
    section_text = _clip_text(sample.get("section_text", ""), max(500, int(max_section_chars)))
    prompt = (
        "You review parser output for one financial report snippet and return corrected metric rows.\n"
        "Return JSON array only. No markdown.\n"
        "Use only these metrics: "
        + ", ".join(sorted(ALLOWED_METRICS))
        + ".\n"
        "Only output rows where metric label and numeric value are from the same table row.\n"
        "Do not borrow values from adjacent rows with different labels (for example NPAT values cannot be EBITDA).\n"
        "If TEXT is only a heading/footnote marker with no numeric value cell (for example 'EBITDA 1, 2'), return [].\n"
        "If there are comparative periods (for example 31 December and 30 June), emit separate rows for each period.\n"
        "Schema per row: metric, value_type(amount|percent|text), raw_value, value, currency, period, line, line_no, file, "
        "statement_scope, statement_title, block_id, inside_table, page_number.\n\n"
        f"PDF: {sample.get('pdf','')}\n"
        f"LINE_NO: {sample.get('line_no','')}\n"
        f"TEXT: {sample.get('text','')}\n"
        f"SECTION_TEXT: {section_text}\n"
        f"PARSER_ROWS: {json.dumps(parser_rows, ensure_ascii=True)}\n"
    )
    if reviewer_prompt:
        prompt += f"\nREVIEWER_INSTRUCTION: {reviewer_prompt}\n"
    raw = ollama_generate(
        ollama_url=ollama_url,
        model=model,
        prompt=prompt,
        keep_alive=keep_alive,
        timeout_sec=timeout_sec,
        retries=retries,
    )
    obj = extract_json_from_text(raw)
    if isinstance(obj, dict) and isinstance(obj.get("corrected_rows"), list):
        obj = obj.get("corrected_rows")
    if not isinstance(obj, list):
        return []
    rows = normalize_ai_rows(obj, sample)
    return enforce_corrected_scope(rows, sample)


def main() -> int:
    ap = argparse.ArgumentParser(description="Terminal review UI for PDF metric extraction samples.")
    ap.add_argument("--manifest", required=True, help="Path to review manifest.json")
    ap.add_argument("--labels-out", default="reports/pdf_metric_review/labels.jsonl", help="Output labels JSONL")
    ap.add_argument("--only-unlabeled", action="store_true", help="Skip samples already labeled in --labels-out")
    ap.add_argument("--show-image", action="store_true", help="Render image preview as ASCII in terminal")
    ap.add_argument("--image-width", type=int, default=90, help="ASCII image width")
    ap.add_argument("--ai-model", default="qwen2.5:32b", help="Ollama model for AI-assisted correction")
    ap.add_argument("--ai-url", default="http://127.0.0.1:11434/api/generate", help="Ollama generate endpoint URL")
    ap.add_argument("--ai-keep-alive", default="30m", help="Ollama keep_alive value")
    ap.add_argument("--ai-timeout-sec", type=int, default=300, help="Ollama request timeout")
    ap.add_argument("--ai-retries", type=int, default=2, help="Retry count for AI assist on timeout/network error")
    ap.add_argument(
        "--ai-max-section-chars",
        type=int,
        default=4000,
        help="Max section_text characters included in AI prompt",
    )
    ap.add_argument(
        "--ai-max-parser-rows",
        type=int,
        default=12,
        help="Max parser rows included in AI prompt",
    )
    ap.add_argument("--disable-ai", action="store_true", help="Disable 'a' AI-assist command")
    args = ap.parse_args()

    manifest_path = Path(args.manifest).resolve()
    if not manifest_path.exists():
        print(f"Manifest not found: {manifest_path}")
        return 2

    labels_out = Path(args.labels_out).resolve()
    rows = load_json(manifest_path)
    if not isinstance(rows, list) or not rows:
        print("Manifest is empty or invalid.")
        return 2

    labeled_ids = load_labeled_ids(labels_out) if args.only_unlabeled else set()
    total = len(rows)
    labeled_now = 0

    print("Commands: y=correct, n=incorrect, a=ask-ai-fix, p=prompt-ai, s=skip, q=quit")
    print(f"Samples in manifest: {total}")
    print(f"Labels file: {labels_out}")

    for idx, row in enumerate(rows, start=1):
        sample_id = str(row.get("sample_id") or f"sample-{idx}")
        if args.only_unlabeled and sample_id in labeled_ids:
            continue

        print("\n" + "=" * 100)
        print(f"[{idx}/{total}] sample_id={sample_id}")
        print(
            f"pdf={row.get('pdf')}  page={row.get('page')}  line={row.get('line_no_on_page')}  "
            f"section={row.get('section_start_line_on_page')}-{row.get('section_end_line_on_page')}"
        )
        print(
            f"review_scope={row.get('review_scope', 'canonical')}  "
            f"statement_scopes={row.get('statement_scopes', [])}  "
            f"inside_table_all={row.get('inside_table_all', '')}"
        )
        if row.get("block_ids"):
            print(f"block_ids={row.get('block_ids')}")
        print(f"image={row.get('image')}")
        print("-" * 100)
        if args.show_image:
            image_path = (manifest_path.parent / row["image_rel"]).resolve()
            if image_path.exists():
                print(image_to_ascii(image_path, width=args.image_width))
            else:
                print("[image missing]")
            print("-" * 100)
        print("TEXT:")
        print(row.get("text", ""))
        section_text = row.get("section_text")
        if section_text:
            print("-" * 100)
            print("SECTION TEXT:")
            print(section_text)
        print("-" * 100)
        print("PARSED:")
        print(json.dumps(row.get("parsed_rows", []), indent=2))

        cmd = ""
        inline_note = ""
        corrected_rows: Optional[List[Dict[str, object]]] = None
        ai_assisted = False
        ai_prompt = ""
        while True:
            raw = input("label [y/n/a/p/s/q]: ").strip()
            if not raw:
                print("Invalid command.")
                continue
            first = raw.lstrip().lower()[0]
            if first in {"a", "p"}:
                if args.disable_ai:
                    print("AI assist is disabled (--disable-ai).")
                    continue
                reviewer_prompt = ""
                if first == "p":
                    reviewer_prompt = input("AI instruction: ").strip()
                    if not reviewer_prompt:
                        print("No instruction entered.")
                        continue
                try:
                    print("[ai] querying model...")
                    ai_rows = ai_suggest_corrected_rows(
                        sample=row,
                        ollama_url=args.ai_url,
                        model=args.ai_model,
                        keep_alive=args.ai_keep_alive,
                        timeout_sec=args.ai_timeout_sec,
                        reviewer_prompt=reviewer_prompt,
                        retries=max(0, int(args.ai_retries)),
                        max_section_chars=max(500, int(args.ai_max_section_chars)),
                        max_parser_rows=max(1, int(args.ai_max_parser_rows)),
                    )
                except Exception as exc:
                    print(f"[ai] failed: {exc}")
                    continue
                if not ai_rows:
                    print("[ai] no corrected rows returned")
                    continue
                print("[ai] suggested corrected rows:")
                print(json.dumps(ai_rows, indent=2))
                ai_apply = input("Apply AI suggestion? [Y/n/e=edit-json]: ").strip().lower()
                ai_choice = (ai_apply[:1] if ai_apply else "y")
                if ai_choice == "y":
                    cmd = "n"
                    corrected_rows = ai_rows
                    ai_assisted = True
                    ai_prompt = reviewer_prompt
                    break
                if ai_choice == "e":
                    try:
                        manual_rows = parse_corrected_rows()
                        cmd = "n"
                        corrected_rows = enforce_corrected_scope(manual_rows if manual_rows is not None else ai_rows, row)
                        if not corrected_rows:
                            print("[ai] corrected rows rejected by scope policy.")
                            continue
                        ai_assisted = True
                        ai_prompt = reviewer_prompt
                        break
                    except Exception as exc:
                        print(f"[ai] invalid JSON; keeping AI rows un-applied: {exc}")
                continue
            if first in {"y", "n", "s", "q"}:
                cmd = first
                inline_note = raw[1:].strip()
                break
            print("Invalid command.")

        if cmd == "q":
            break
        if cmd == "s":
            continue

        notes = inline_note
        if cmd == "n":
            if corrected_rows is None:
                add_fix = input("Add corrected parsed rows JSON? [y/N]: ").strip().lower()
                if add_fix == "y":
                    try:
                        corrected_rows = enforce_corrected_scope(parse_corrected_rows() or [], row)
                        if not corrected_rows:
                            print("No accepted corrected rows after scope validation.")
                    except Exception as exc:
                        print(f"Invalid corrected JSON, storing none: {exc}")
            extra_note = input("Optional note: ").strip()
            if extra_note:
                notes = extra_note

        rec = {
            "sample_id": sample_id,
            "timestamp_utc": datetime.now(timezone.utc).isoformat(),
            "pdf": row.get("pdf"),
            "page": row.get("page"),
            "line_no": row.get("line_no"),
            "line_no_on_page": row.get("line_no_on_page"),
            "text": row.get("text"),
            "image": row.get("image"),
            "review_scope": row.get("review_scope", "canonical"),
            "verdict": "correct" if cmd == "y" else "incorrect",
            "parsed_rows": row.get("parsed_rows", []),
            "corrected_rows": corrected_rows,
            "note": notes,
            "ai_assisted": ai_assisted,
            "ai_model": args.ai_model if ai_assisted else "",
            "ai_prompt": ai_prompt,
        }
        append_jsonl(labels_out, rec)
        labeled_now += 1

    print(f"\nSaved {labeled_now} new labels to {labels_out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
