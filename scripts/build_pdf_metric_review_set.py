#!/usr/bin/env python3
import argparse
import html
import hashlib
import importlib.util
import json
import random
import subprocess
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

from PIL import Image


def load_extract_module(repo_root: Path):
    module_path = repo_root / "scripts" / "extract_financial_metrics.py"
    spec = importlib.util.spec_from_file_location("extract_financial_metrics", str(module_path))
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Failed to load parser module at {module_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def local_name(tag: str) -> str:
    return tag.split("}", 1)[-1]


def _is_valid_xml_char(ch: str) -> bool:
    cp = ord(ch)
    return (
        cp == 0x9
        or cp == 0xA
        or cp == 0xD
        or (0x20 <= cp <= 0xD7FF)
        or (0xE000 <= cp <= 0xFFFD)
        or (0x10000 <= cp <= 0x10FFFF)
    )


def sanitize_xml_text(s: str) -> str:
    return "".join(ch for ch in s if _is_valid_xml_char(ch))


def _normalize_timeout_seconds(timeout_sec: Optional[float]) -> Optional[float]:
    if timeout_sec is None:
        return None
    try:
        t = float(timeout_sec)
    except (TypeError, ValueError):
        return None
    if t <= 0:
        return None
    return t


def parse_bbox_lines(pdf: Path, timeout_sec: Optional[float] = None) -> List[Dict[str, object]]:
    timeout = _normalize_timeout_seconds(timeout_sec)
    try:
        cp = subprocess.run(
            ["pdftotext", "-bbox-layout", str(pdf), "-"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=False,
            check=True,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired as exc:
        sec = int(timeout) if timeout is not None else 0
        raise RuntimeError(f"pdftotext timeout after {sec}s") from exc
    xml_text = cp.stdout.decode("utf-8", errors="replace")
    xml_text = sanitize_xml_text(xml_text)
    root = ET.fromstring(xml_text)
    lines: List[Dict[str, object]] = []
    global_line_no = 0

    for page_idx, page in enumerate((e for e in root.iter() if local_name(e.tag) == "page"), start=1):
        page_w = float(page.attrib.get("width", "0"))
        page_h = float(page.attrib.get("height", "0"))
        line_no_on_page = 0
        for line in (e for e in page.iter() if local_name(e.tag) == "line"):
            words = [w for w in line if local_name(w.tag) == "word"]
            if not words:
                continue

            tokens: List[str] = []
            x0 = y0 = float("inf")
            x1 = y1 = float("-inf")
            for w in words:
                text = html.unescape("".join(w.itertext()).strip())
                if not text:
                    continue
                text = "".join(ch for ch in text if ch >= " " or ch in "\t\n\r")
                if not text:
                    continue
                tokens.append(text)
                wx0 = float(w.attrib["xMin"])
                wy0 = float(w.attrib["yMin"])
                wx1 = float(w.attrib["xMax"])
                wy1 = float(w.attrib["yMax"])
                x0 = min(x0, wx0)
                y0 = min(y0, wy0)
                x1 = max(x1, wx1)
                y1 = max(y1, wy1)
            if not tokens:
                continue

            line_text = " ".join(tokens).strip()
            if not line_text:
                continue

            line_no_on_page += 1
            global_line_no += 1
            lines.append(
                {
                    "page": page_idx,
                    "line_no_on_page": line_no_on_page,
                    "line_no": global_line_no,
                    "text": line_text,
                    "bbox": [x0, y0, x1, y1],
                    "page_width": page_w,
                    "page_height": page_h,
                }
            )
    return lines


def build_section_blocks(lines: List[Dict[str, object]]) -> Dict[Tuple[int, int], Dict[str, object]]:
    by_page: Dict[int, List[Dict[str, object]]] = {}
    for line in lines:
        by_page.setdefault(int(line["page"]), []).append(line)

    line_to_block: Dict[Tuple[int, int], Dict[str, object]] = {}
    max_block_lines = 12
    for page, page_lines in by_page.items():
        page_lines = sorted(page_lines, key=lambda x: int(x["line_no_on_page"]))
        block_lines: List[Dict[str, object]] = []

        def flush_block() -> None:
            nonlocal block_lines
            if not block_lines:
                return
            x0 = min(float(x["bbox"][0]) for x in block_lines)
            y0 = min(float(x["bbox"][1]) for x in block_lines)
            x1 = max(float(x["bbox"][2]) for x in block_lines)
            y1 = max(float(x["bbox"][3]) for x in block_lines)
            block = {
                "page": page,
                "start_line_on_page": int(block_lines[0]["line_no_on_page"]),
                "end_line_on_page": int(block_lines[-1]["line_no_on_page"]),
                "bbox": [x0, y0, x1, y1],
                "text": "\n".join(str(x["text"]) for x in block_lines),
            }
            for ln in block_lines:
                key = (page, int(ln["line_no_on_page"]))
                line_to_block[key] = block
            block_lines = []

        for line in page_lines:
            if not block_lines:
                block_lines.append(line)
                continue
            prev = block_lines[-1]
            prev_bottom = float(prev["bbox"][3])
            cur_top = float(line["bbox"][1])
            prev_h = max(1.0, float(prev["bbox"][3]) - float(prev["bbox"][1]))
            gap = cur_top - prev_bottom
            # Start new block when there is a clear vertical break between text lines.
            if gap > max(10.0, prev_h * 1.6) or len(block_lines) >= max_block_lines:
                flush_block()
            block_lines.append(line)
        flush_block()
    return line_to_block


def render_page_image(pdf: Path, page: int, dpi: int, cache_dir: Path) -> Path:
    cache_dir.mkdir(parents=True, exist_ok=True)
    out_prefix = cache_dir / f"{pdf.stem}_p{page}_dpi{dpi}"
    out_png = out_prefix.with_suffix(".png")
    if out_png.exists():
        return out_png
    subprocess.run(
        ["pdftoppm", "-png", "-singlefile", "-r", str(dpi), "-f", str(page), "-l", str(page), str(pdf), str(out_prefix)],
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    return out_png


def crop_snippet(page_png: Path, bbox: List[float], dpi: int, out_path: Path) -> None:
    scale = dpi / 72.0
    pad_x = 24.0
    pad_y = 20.0
    x0, y0, x1, y1 = bbox
    with Image.open(page_png) as img:
        left = max(0, int((x0 - pad_x) * scale))
        top = max(0, int((y0 - pad_y) * scale))
        right = min(img.width, int((x1 + pad_x) * scale))
        bottom = min(img.height, int((y1 + pad_y) * scale))
        crop = img.crop((left, top, right, bottom))
        out_path.parent.mkdir(parents=True, exist_ok=True)
        crop.save(out_path)


def build_html_report(rows: List[Dict[str, object]], out_path: Path) -> None:
    parts = [
        "<!doctype html><html><head><meta charset='utf-8'>",
        "<title>PDF Metric Review</title>",
        "<style>body{font-family:Arial,sans-serif;margin:24px;} .card{border:1px solid #ddd;padding:12px;margin:12px 0;} img{max-width:900px;width:100%;height:auto;border:1px solid #ccc;} pre{background:#f6f8fa;padding:8px;overflow:auto;}</style>",
        "</head><body>",
        "<h1>PDF Metric Review Set</h1>",
    ]
    for i, row in enumerate(rows, start=1):
        parsed = json.dumps(row["parsed_rows"], indent=2)
        parts.append("<div class='card'>")
        parts.append(
            f"<h3>#{i} {html.escape(row['pdf'])} | page {row['page']} | line {row['line_no_on_page']} | section {row['section_start_line_on_page']}-{row['section_end_line_on_page']}</h3>"
        )
        parts.append(f"<p><b>Target line:</b> {html.escape(row['text'])}</p>")
        parts.append(f"<p><b>Section text:</b><br><pre>{html.escape(row['section_text'])}</pre></p>")
        parts.append(f"<img src='{html.escape(row['image_rel'])}' alt='snippet'>")
        parts.append(f"<pre>{html.escape(parsed)}</pre>")
        parts.append("</div>")
    parts.append("</body></html>")
    out_path.write_text("\n".join(parts), encoding="utf-8")


def parse_metric_set(raw: str) -> Set[str]:
    if not raw:
        return set()
    out: Set[str] = set()
    for part in raw.split(","):
        token = part.strip().lower()
        if token:
            out.add(token)
    return out


def metric_counts(rows: List[Dict[str, object]]) -> Dict[str, int]:
    counts: Dict[str, int] = {}
    for row in rows:
        metric = str(row.get("primary_metric", "")).strip().lower() or "unknown"
        counts[metric] = counts.get(metric, 0) + 1
    return counts


def sample_balanced_by_metric(
    candidates: List[Dict[str, object]],
    max_samples: int,
    rng: random.Random,
    max_per_metric: int = 0,
) -> List[Dict[str, object]]:
    by_metric: Dict[str, List[Dict[str, object]]] = {}
    for row in candidates:
        metric = str(row.get("primary_metric", "")).strip().lower() or "unknown"
        by_metric.setdefault(metric, []).append(row)
    metrics = sorted(by_metric.keys())
    for m in metrics:
        rng.shuffle(by_metric[m])

    picked: List[Dict[str, object]] = []
    used_per_metric: Dict[str, int] = {m: 0 for m in metrics}
    while len(picked) < max_samples:
        progress = False
        for m in metrics:
            if len(picked) >= max_samples:
                break
            if max_per_metric > 0 and used_per_metric[m] >= max_per_metric:
                continue
            bucket = by_metric[m]
            if not bucket:
                continue
            picked.append(bucket.pop())
            used_per_metric[m] += 1
            progress = True
        if not progress:
            break
    return picked


def main() -> int:
    ap = argparse.ArgumentParser(description="Create screenshot-based review/training set for PDF metric extraction.")
    ap.add_argument("--pdf-dir", required=True, help="Directory containing PDFs")
    ap.add_argument("--out-dir", default="reports/pdf_metric_review", help="Output directory")
    ap.add_argument("--max-samples", type=int, default=40, help="Max lines with parsed metrics to include")
    ap.add_argument("--dpi", type=int, default=200, help="Render DPI for snippets")
    ap.add_argument("--seed", type=int, default=42, help="Sampling seed")
    ap.add_argument(
        "--include-metrics",
        default="",
        help="Comma-separated metric allowlist (e.g. revenue,ebitda,npat). Empty means all.",
    )
    ap.add_argument(
        "--exclude-metrics",
        default="",
        help="Comma-separated metric denylist (e.g. cash_and_equivalents).",
    )
    ap.add_argument(
        "--balance-by-metric",
        action="store_true",
        help="Round-robin sample across metrics to avoid one metric dominating.",
    )
    ap.add_argument(
        "--max-per-metric",
        type=int,
        default=0,
        help="Optional cap per metric when --balance-by-metric is used (0 = no cap).",
    )
    ap.add_argument(
        "--review-scope",
        choices=["canonical", "context", "all"],
        default="canonical",
        help="Which extracted row scope to include in review samples",
    )
    ap.add_argument(
        "--pdftotext-timeout-sec",
        type=float,
        default=180.0,
        help="Per-file timeout for pdftotext calls in seconds (<=0 disables timeout).",
    )
    args = ap.parse_args()

    if args.max_samples <= 0:
        print("--max-samples must be > 0", file=sys.stderr)
        return 2

    include_metrics = parse_metric_set(args.include_metrics)
    exclude_metrics = parse_metric_set(args.exclude_metrics)
    overlap = include_metrics & exclude_metrics
    if overlap:
        print(f"--include-metrics and --exclude-metrics overlap: {sorted(overlap)}", file=sys.stderr)
        return 2

    repo_root = Path(__file__).resolve().parents[1]
    extract = load_extract_module(repo_root)
    pdf_root = Path(args.pdf_dir).resolve()
    if not pdf_root.exists():
        print(f"PDF directory not found: {pdf_root}", file=sys.stderr)
        return 2

    pdfs = extract.find_pdfs(pdf_root)
    if not pdfs:
        print(f"No PDF files found in: {pdf_root}", file=sys.stderr)
        return 2

    out_dir = Path(args.out_dir)
    images_dir = out_dir / "images"
    page_cache_dir = out_dir / "_page_cache"
    out_dir.mkdir(parents=True, exist_ok=True)

    candidates: List[Dict[str, object]] = []
    for pdf in pdfs:
        try:
            lines = parse_bbox_lines(pdf, timeout_sec=args.pdftotext_timeout_sec)
        except Exception as exc:
            print(f"[warn] failed bbox parse {pdf}: {exc}", file=sys.stderr)
            continue
        table_rows_by_line: Dict[int, List[Dict[str, object]]] = {}
        if hasattr(extract, "extract_table_metrics"):
            source_kind = ""
            if hasattr(extract, "classify_pdf_source_kind"):
                try:
                    source_kind = str(extract.classify_pdf_source_kind(pdf))
                except Exception:
                    source_kind = ""
            try:
                try:
                    table_rows = extract.extract_table_metrics(
                        pdf,
                        strict_metric_rows_only=True,
                        source_kind=source_kind,
                        review_scope=args.review_scope,
                        pdftotext_timeout_sec=args.pdftotext_timeout_sec,
                    )
                except TypeError:
                    table_rows = extract.extract_table_metrics(
                        pdf,
                        strict_metric_rows_only=True,
                        source_kind=source_kind,
                        review_scope=args.review_scope,
                    )
            except Exception as exc:
                print(f"[warn] failed table parse {pdf}: {exc}", file=sys.stderr)
                table_rows = []
            for r in table_rows:
                ln = int(r.get("line_no", 0) or 0)
                if ln <= 0:
                    continue
                table_rows_by_line.setdefault(ln, []).append(r)
        line_to_block = build_section_blocks(lines)
        for line in lines:
            parsed_rows = list(table_rows_by_line.get(int(line["line_no"]), []))
            if not parsed_rows:
                continue
            metrics_on_line = sorted(
                {str(r.get("metric", "")).strip().lower() for r in parsed_rows if str(r.get("metric", "")).strip()}
            )
            if include_metrics and not (set(metrics_on_line) & include_metrics):
                continue
            if exclude_metrics and (set(metrics_on_line) & exclude_metrics):
                continue
            block = line_to_block.get((int(line["page"]), int(line["line_no_on_page"])))
            if block is None:
                block = {
                    "bbox": line["bbox"],
                    "text": str(line["text"]),
                    "start_line_on_page": int(line["line_no_on_page"]),
                    "end_line_on_page": int(line["line_no_on_page"]),
                }
            candidates.append(
                {
                    "pdf": str(pdf),
                    "page": int(line["page"]),
                    "line_no": int(line["line_no"]),
                    "line_no_on_page": int(line["line_no_on_page"]),
                    "text": str(line["text"]),
                    "bbox": line["bbox"],
                    "section_bbox": block["bbox"],
                    "section_text": block["text"],
                    "section_start_line_on_page": int(block["start_line_on_page"]),
                    "section_end_line_on_page": int(block["end_line_on_page"]),
                    "parsed_rows": parsed_rows,
                    "metrics": metrics_on_line,
                    "primary_metric": (metrics_on_line[0] if metrics_on_line else ""),
                    "review_scope": args.review_scope,
                    "statement_scopes": sorted(
                        {
                            str(r.get("statement_scope", r.get("statement_type", ""))).strip()
                            for r in parsed_rows
                            if str(r.get("statement_scope", r.get("statement_type", ""))).strip()
                        }
                    ),
                    "block_ids": sorted({str(r.get("block_id", "")).strip() for r in parsed_rows if str(r.get("block_id", "")).strip()}),
                    "inside_table_all": all(bool(r.get("inside_table", False)) for r in parsed_rows),
                }
            )

    if not candidates:
        print("No parsed metric lines found.", file=sys.stderr)
        return 1

    all_metric_counts = metric_counts(candidates)
    print(
        "Metric distribution (before sampling): "
        + ", ".join(f"{k}={all_metric_counts[k]}" for k in sorted(all_metric_counts.keys()))
    )
    rng = random.Random(args.seed)
    if len(candidates) > args.max_samples:
        if args.balance_by_metric:
            candidates = sample_balanced_by_metric(
                candidates,
                max_samples=args.max_samples,
                rng=rng,
                max_per_metric=args.max_per_metric,
            )
        else:
            candidates = rng.sample(candidates, args.max_samples)
    sampled_counts = metric_counts(candidates)
    print(
        "Metric distribution (sampled): "
        + ", ".join(f"{k}={sampled_counts[k]}" for k in sorted(sampled_counts.keys()))
    )

    rows: List[Dict[str, object]] = []
    for idx, c in enumerate(candidates, start=1):
        pdf_path = Path(c["pdf"])
        page = int(c["page"])
        page_png = render_page_image(pdf_path, page, args.dpi, page_cache_dir)
        image_name = (
            f"{idx:04d}_{pdf_path.stem}_p{page}_s{c['section_start_line_on_page']}-{c['section_end_line_on_page']}"
            f"_l{c['line_no_on_page']}.png"
        )
        image_path = images_dir / image_name
        crop_snippet(page_png, c["section_bbox"], args.dpi, image_path)

        row = dict(c)
        key = f"{row['pdf']}|{row['page']}|{row['line_no']}|{row['line_no_on_page']}|{row['text']}"
        row["sample_id"] = hashlib.sha1(key.encode("utf-8")).hexdigest()[:16]
        row["image"] = str(image_path)
        row["image_rel"] = str(image_path.relative_to(out_dir))
        rows.append(row)

    manifest_path = out_dir / "manifest.json"
    report_path = out_dir / "review.html"
    manifest_path.write_text(json.dumps(rows, indent=2), encoding="utf-8")
    build_html_report(rows, report_path)

    print(f"Created {len(rows)} review samples")
    print(f"Manifest: {manifest_path}")
    print(f"HTML report: {report_path}")
    print(f"Images dir: {images_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
