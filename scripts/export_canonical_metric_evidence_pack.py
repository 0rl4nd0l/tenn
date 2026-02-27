#!/usr/bin/env python3
"""Export canonical metric-period rows with source screenshots for review."""

from __future__ import annotations

import argparse
import csv
import hashlib
import html
import json
import shutil
import subprocess
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple

from PIL import Image


def _local_name(tag: str) -> str:
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


def _sanitize_xml_text(s: str) -> str:
    return "".join(ch for ch in s if _is_valid_xml_char(ch))


def _to_int(value: object, default: int = 0) -> int:
    try:
        if value is None:
            return default
        text = str(value).strip()
        if not text:
            return default
        return int(float(text))
    except (TypeError, ValueError):
        return default


def _to_float(value: object, default: float = 0.0) -> float:
    try:
        if value is None:
            return default
        text = str(value).strip()
        if not text:
            return default
        return float(text)
    except (TypeError, ValueError):
        return default


def _parse_metric_set(raw: str) -> set[str]:
    out: set[str] = set()
    for part in str(raw or "").split(","):
        token = part.strip().lower()
        if token:
            out.add(token)
    return out


def _parse_bbox_lines(pdf: Path, timeout_sec: Optional[float]) -> List[Dict[str, object]]:
    cmd = ["pdftotext", "-bbox-layout", str(pdf), "-"]
    cp = subprocess.run(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=False,
        check=False,
        timeout=timeout_sec if timeout_sec and timeout_sec > 0 else None,
    )
    if cp.returncode != 0:
        stderr = cp.stderr.decode("utf-8", errors="replace")
        raise RuntimeError(f"pdftotext failed ({cp.returncode}): {stderr.strip()[:240]}")

    xml_text = cp.stdout.decode("utf-8", errors="replace")
    xml_text = _sanitize_xml_text(xml_text)
    root = ET.fromstring(xml_text)
    lines: List[Dict[str, object]] = []
    global_line_no = 0

    for page_idx, page in enumerate((e for e in root.iter() if _local_name(e.tag) == "page"), start=1):
        page_w = float(page.attrib.get("width", "0"))
        page_h = float(page.attrib.get("height", "0"))
        line_no_on_page = 0
        for line in (e for e in page.iter() if _local_name(e.tag) == "line"):
            words = [w for w in line if _local_name(w.tag) == "word"]
            if not words:
                continue
            x0 = y0 = float("inf")
            x1 = y1 = float("-inf")
            tokens: List[str] = []
            for w in words:
                text = html.unescape("".join(w.itertext()).strip())
                if not text:
                    continue
                tokens.append(text)
                wx0 = float(w.attrib.get("xMin", "0"))
                wy0 = float(w.attrib.get("yMin", "0"))
                wx1 = float(w.attrib.get("xMax", "0"))
                wy1 = float(w.attrib.get("yMax", "0"))
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


def _render_page_image(pdf: Path, page: int, dpi: int, cache_dir: Path) -> Path:
    cache_dir.mkdir(parents=True, exist_ok=True)
    out_prefix = cache_dir / f"{pdf.stem}_p{page}_dpi{dpi}"
    out_png = out_prefix.with_suffix(".png")
    if out_png.exists():
        return out_png
    cp = subprocess.run(
        [
            "pdftoppm",
            "-png",
            "-singlefile",
            "-r",
            str(dpi),
            "-f",
            str(page),
            "-l",
            str(page),
            str(pdf),
            str(out_prefix),
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=False,
    )
    if cp.returncode != 0:
        raise RuntimeError(f"pdftoppm failed ({cp.returncode}): {cp.stderr.strip()[:240]}")
    return out_png


def _crop_snippet(page_png: Path, bbox: Sequence[float], dpi: int, out_path: Path) -> None:
    x0, y0, x1, y1 = [float(v) for v in bbox]
    scale = float(dpi) / 72.0
    pad_x = 24.0
    pad_y = 20.0
    with Image.open(page_png) as img:
        left = max(0, int((x0 - pad_x) * scale))
        top = max(0, int((y0 - pad_y) * scale))
        right = min(img.width, int((x1 + pad_x) * scale))
        bottom = min(img.height, int((y1 + pad_y) * scale))
        if right <= left or bottom <= top:
            crop = img
        else:
            crop = img.crop((left, top, right, bottom))
        out_path.parent.mkdir(parents=True, exist_ok=True)
        crop.save(out_path)


def _csv_read(path: Path) -> List[Dict[str, str]]:
    with path.open("r", newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def _norm_metric(row: Dict[str, str]) -> str:
    return str(row.get("metric_base", row.get("metric", ""))).strip().lower()


def _norm_period_end(row: Dict[str, str]) -> str:
    return str(row.get("statement_period_end", row.get("period_end", ""))).strip()


def _pick_best_metric_period(rows: List[Dict[str, str]]) -> List[Dict[str, str]]:
    by_key: Dict[Tuple[str, str], List[Dict[str, str]]] = {}
    for r in rows:
        metric = _norm_metric(r)
        period_end = _norm_period_end(r)
        if not metric or not period_end:
            continue
        by_key.setdefault((metric, period_end), []).append(r)

    out: List[Dict[str, str]] = []
    for key in sorted(by_key.keys()):
        candidates = by_key[key]
        best = sorted(
            candidates,
            key=lambda r: (
                _to_int(r.get("canonical_confidence_score"), 0),
                _to_float(r.get("confidence"), 0.0),
                int(bool(str(r.get("table_id", "")).strip())),
                int(_to_int(r.get("line_no"), 0) > 0),
                str(r.get("file", "")),
                _to_int(r.get("line_no"), 0),
            ),
            reverse=True,
        )[0]
        out.append(best)
    return out


def _build_html(rows: List[Dict[str, str]], out_path: Path) -> None:
    parts = [
        "<!doctype html><html><head><meta charset='utf-8'>",
        "<title>Canonical Metric Evidence Pack</title>",
        "<style>body{font-family:Arial,sans-serif;margin:24px;} .card{border:1px solid #ddd;padding:12px;margin:12px 0;} img{max-width:1100px;width:100%;height:auto;border:1px solid #ccc;} .meta{display:grid;grid-template-columns:220px 1fr;gap:6px;} .k{font-weight:700;} code{background:#f6f8fa;padding:2px 4px;}</style>",
        "</head><body>",
        "<h1>Canonical Metric Evidence Pack</h1>",
    ]
    for i, r in enumerate(rows, start=1):
        parts.append("<div class='card'>")
        parts.append(f"<h3>#{i} {html.escape(r.get('metric_base', ''))} | {html.escape(r.get('statement_period_end', ''))}</h3>")
        parts.append("<div class='meta'>")
        pairs = [
            ("Value", r.get("value", "")),
            ("Currency", r.get("currency", "")),
            ("Statement Period", r.get("statement_period", "")),
            ("File", r.get("file", "")),
            ("Page", r.get("page_number", "")),
            ("Line No", r.get("line_no", "")),
            ("Line Text", r.get("line_text", "")),
            ("Confidence", r.get("canonical_confidence_score", "")),
            ("Table ID", r.get("table_id", "")),
        ]
        for k, v in pairs:
            parts.append(f"<div class='k'>{html.escape(k)}</div><div>{html.escape(str(v))}</div>")
        parts.append("</div>")
        snippet = str(r.get("screenshot_snippet", ""))
        page = str(r.get("screenshot_page", ""))
        if snippet:
            parts.append(f"<p><b>Snippet:</b> <code>{html.escape(snippet)}</code></p>")
            parts.append(f"<img src='{html.escape(snippet)}' alt='snippet'>")
        if page:
            parts.append(f"<p><b>Full page:</b> <a href='{html.escape(page)}'>{html.escape(page)}</a></p>")
        parts.append("</div>")
    parts.append("</body></html>")
    out_path.write_text("\n".join(parts), encoding="utf-8")


def main() -> int:
    ap = argparse.ArgumentParser(description="Export canonical metric-period evidence with screenshots.")
    ap.add_argument("--canonical-csv", required=True, help="Canonical CSV path (e.g., canonical_section_capture.csv).")
    ap.add_argument("--out-dir", required=True, help="Output directory for manifest + images.")
    ap.add_argument("--ticker", default="", help="Optional ticker label for output metadata.")
    ap.add_argument(
        "--row-mode",
        choices=["best_by_metric_period", "all"],
        default="best_by_metric_period",
        help="Row selection mode.",
    )
    ap.add_argument("--include-metrics", default="", help="Optional metric_base allowlist (comma separated).")
    ap.add_argument("--dpi", type=int, default=200, help="Screenshot DPI.")
    ap.add_argument("--pdftotext-timeout-sec", type=float, default=180.0, help="Per PDF bbox parse timeout.")
    args = ap.parse_args()

    canonical_csv = Path(args.canonical_csv).expanduser().resolve()
    if not canonical_csv.exists():
        print(f"Canonical CSV not found: {canonical_csv}", file=sys.stderr)
        return 2

    out_dir = Path(args.out_dir).expanduser().resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    snippets_dir = out_dir / "images" / "snippets"
    pages_dir = out_dir / "images" / "pages"
    cache_dir = out_dir / "_page_cache"

    include_metrics = _parse_metric_set(args.include_metrics)
    raw_rows = _csv_read(canonical_csv)
    filtered: List[Dict[str, str]] = []
    for r in raw_rows:
        metric = _norm_metric(r)
        period_end = _norm_period_end(r)
        if not metric or not period_end:
            continue
        if include_metrics and metric not in include_metrics:
            continue
        file_path = str(r.get("file", "")).strip()
        if not file_path:
            continue
        if not Path(file_path).exists():
            continue
        filtered.append(r)

    if not filtered:
        print("No eligible canonical rows found after filtering.", file=sys.stderr)
        return 1

    if args.row_mode == "best_by_metric_period":
        selected_rows = _pick_best_metric_period(filtered)
    else:
        selected_rows = list(filtered)

    bbox_cache: Dict[str, Dict[int, Dict[str, object]]] = {}
    output_rows: List[Dict[str, str]] = []

    for idx, row in enumerate(selected_rows, start=1):
        pdf = Path(str(row.get("file", "")).strip())
        if not pdf.exists():
            continue

        key_pdf = str(pdf)
        if key_pdf not in bbox_cache:
            lines = _parse_bbox_lines(pdf, timeout_sec=args.pdftotext_timeout_sec)
            bbox_cache[key_pdf] = {int(x["line_no"]): x for x in lines}
        line_lookup = bbox_cache[key_pdf]

        line_no = _to_int(row.get("line_no"), 0)
        line_match = line_lookup.get(line_no)
        page = _to_int(row.get("page_number"), 0)
        if page <= 0:
            page = _to_int(row.get("table_page"), 0)
        if page <= 0 and line_match is not None:
            page = _to_int(line_match.get("page"), 1)
        if page <= 0:
            page = 1

        page_png = _render_page_image(pdf, page, int(max(72, args.dpi)), cache_dir)
        page_name = f"{pdf.stem}_p{page}.png"
        page_out = pages_dir / page_name
        if not page_out.exists():
            page_out.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(page_png, page_out)

        snippet_rel = ""
        line_text = str(row.get("line", "")).strip()
        line_no_on_page = 0
        if line_match is not None:
            line_text = str(line_match.get("text", "")).strip() or line_text
            line_no_on_page = _to_int(line_match.get("line_no_on_page"), 0)
            snippet_name = f"{idx:04d}_{pdf.stem}_p{page}_l{line_no_on_page or line_no}.png"
            snippet_out = snippets_dir / snippet_name
            _crop_snippet(page_png, list(line_match.get("bbox", [])), int(max(72, args.dpi)), snippet_out)
            snippet_rel = str(snippet_out.relative_to(out_dir))

        metric = _norm_metric(row)
        period_end = _norm_period_end(row)
        row_key = f"{pdf}|{metric}|{period_end}|{line_no}"
        sample_id = hashlib.sha1(row_key.encode("utf-8")).hexdigest()[:16]

        output_rows.append(
            {
                "sample_id": sample_id,
                "ticker": str(args.ticker or "").strip().upper(),
                "metric_base": metric,
                "statement_period_end": period_end,
                "statement_period": str(row.get("statement_period", "")).strip(),
                "value": str(row.get("value", "")).strip(),
                "raw_value": str(row.get("raw_value", "")).strip(),
                "value_type": str(row.get("value_type", "")).strip(),
                "currency": str(row.get("currency", "")).strip(),
                "file": str(pdf),
                "page_number": str(page),
                "line_no": str(line_no),
                "line_no_on_page": str(line_no_on_page),
                "line_text": line_text,
                "table_id": str(row.get("table_id", "")).strip(),
                "statement_family": str(row.get("statement_family", "")).strip(),
                "statement_scope": str(row.get("statement_scope", "")).strip(),
                "canonical_confidence_score": str(row.get("canonical_confidence_score", "")).strip(),
                "confidence": str(row.get("confidence", "")).strip(),
                "screenshot_snippet": snippet_rel,
                "screenshot_page": str(page_out.relative_to(out_dir)),
            }
        )

    output_rows = sorted(
        output_rows,
        key=lambda r: (r["metric_base"], r["statement_period_end"], r["file"], _to_int(r["line_no"], 0)),
    )

    manifest_json = out_dir / "evidence_manifest.json"
    manifest_csv = out_dir / "evidence_manifest.csv"
    review_html = out_dir / "review.html"

    manifest_json.write_text(json.dumps(output_rows, indent=2), encoding="utf-8")
    if output_rows:
        with manifest_csv.open("w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=list(output_rows[0].keys()))
            writer.writeheader()
            writer.writerows(output_rows)

    _build_html(output_rows, review_html)

    print(f"Rows exported: {len(output_rows)}")
    print(f"Manifest CSV: {manifest_csv}")
    print(f"Manifest JSON: {manifest_json}")
    print(f"Review HTML: {review_html}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
