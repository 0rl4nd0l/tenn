from __future__ import annotations

import hashlib
import json
import re
from functools import lru_cache
from datetime import datetime, timezone, date
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Mapping, Sequence
from uuid import UUID

import fitz
from sqlalchemy.orm import Session

try:
    from PIL import Image, ImageDraw
except ImportError:  # pragma: no cover - optional dependency in restricted envs
    Image = None
    ImageDraw = None

from app.core.config import PROJECT_ROOT
from app.models.documents import Document
from app.models.extractions import ExtractionRun
from app.services.multipass_extraction import METRIC_FIELDS
from app.services.provenance import from_extraction_provenance

REVIEW_ROOT = PROJECT_ROOT / "reports" / "extraction_review"
SESSIONS_ROOT = REVIEW_ROOT / "sessions"
SNIPPETS_ROOT = REVIEW_ROOT / "snippets"
ERROR_QUEUE_PATH = REVIEW_ROOT / "wrong_metric_queue.json"
REAL_GOLD_REVIEW_DIR = PROJECT_ROOT / "data" / "extraction_gold_real"

VALID_REVIEW_STATUSES = {"approved", "wrong", "abstain"}
_GOLD_METRIC_ALIASES = {
    "operating_cf": "operating_cash_flow",
    "operating_cash_flow": "operating_cf",
}
_PAGE_RE = re.compile(r"page_(\d+)")
_WHITESPACE_RE = re.compile(r"\s+")
_ASCII_CHARS = " .:-=+*#%@"


from sqlalchemy import desc
from app.models.asx_financials import ASXPeriodicFinancial


def _previous_period_value(
    db: Session | None, ticker: str, metric: str, period_end: str | date | None, period_type: str | None
) -> float | None:
    if db is None or not ticker or not period_end or not period_type:
        return None
    
    # Find the most recent record for the same ticker and type before the current period_end
    prev = (
        db.query(ASXPeriodicFinancial)
        .filter(
            ASXPeriodicFinancial.ticker == ticker,
            ASXPeriodicFinancial.period_type == period_type,
            ASXPeriodicFinancial.period_end < period_end,
        )
        .order_by(desc(ASXPeriodicFinancial.period_end))
        .first()
    )
    
    if prev:
        val = getattr(prev, metric, None)
        return float(val) if val is not None else None
    return None


def _row_reference_for_metric(payload: Mapping[str, Any], metric: str) -> str | None:
    row_refs = payload.get("row_refs")
    if isinstance(row_refs, Mapping):
        value = str(row_refs.get(metric) or "").strip()
        return value or None
    return None


def _thinking_for_metric(payload: Mapping[str, Any], metric: str) -> str | None:
    thinking = payload.get("thinking")
    if isinstance(thinking, Mapping):
        value = str(thinking.get(metric) or "").strip()
        return value or None
    return None


def _markdown_for_metric(payload: Mapping[str, Any], metric: str) -> str | None:
    markdowns = payload.get("markdown_tables")
    if isinstance(markdowns, Mapping):
        value = str(markdowns.get(metric) or "").strip()
        return value or None
    return None


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _clean_requested_ids(values: Sequence[str] | None) -> list[str]:
    cleaned: list[str] = []
    for value in values or []:
        raw = str(value or "").strip()
        if raw and raw not in cleaned:
            cleaned.append(raw)
    return cleaned


def _session_path(session_id: str) -> Path:
    return SESSIONS_ROOT / f"{session_id}.json"


def _ensure_parent(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def _project_relative(path: Path | None) -> str | None:
    if path is None:
        return None
    try:
        return str(path.resolve().relative_to(PROJECT_ROOT))
    except Exception:
        return str(path.resolve())


@lru_cache(maxsize=1)
def _load_real_gold_by_source() -> dict[str, dict[str, Any]]:
    records: dict[str, dict[str, Any]] = {}
    if not REAL_GOLD_REVIEW_DIR.exists():
        return records
    for path in sorted(REAL_GOLD_REVIEW_DIR.glob("*.json")):
        payload = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(payload, Mapping):
            continue
        source_file = str(payload.get("source_file") or "").strip()
        if source_file:
            records[source_file] = dict(payload)
    return records


def _gold_payload_for_document(
    document: Document, pdf_path: Path | None
) -> dict[str, Any] | None:
    records = _load_real_gold_by_source()
    candidates = {
        str(getattr(document, "pdf_path", "") or "").strip(),
        _project_relative(pdf_path) or "",
    }
    for candidate in candidates:
        if candidate and candidate in records:
            return records[candidate]
    return None


def _gold_metric_value(gold_metrics: Mapping[str, Any], metric: str) -> Any:
    for key in (metric, _GOLD_METRIC_ALIASES.get(metric)):
        if key and key in gold_metrics:
            return gold_metrics.get(key)
    return None


def _coerce_pdf_path(document: Document, payload: Mapping[str, Any]) -> Path | None:
    repro = payload.get("_reproducibility")
    if isinstance(repro, Mapping):
        candidate = str(repro.get("resolved_pdf_path") or "").strip()
        if candidate:
            path = Path(candidate)
            if path.exists():
                return path.resolve()

    candidate = str(getattr(document, "pdf_path", "") or "").strip()
    if not candidate:
        return None
    path = Path(candidate)
    if not path.is_absolute():
        path = (PROJECT_ROOT / path).resolve()
    return path if path.exists() else None


def _parse_page_number(location_ref: str | None) -> int | None:
    raw = str(location_ref or "").strip()
    if not raw:
        return None
    match = _PAGE_RE.search(raw)
    if not match:
        return None
    return int(match.group(1))


def _normalize_text(value: str | None) -> str:
    text = str(value or "").strip().lower()
    text = _WHITESPACE_RE.sub(" ", text)
    return re.sub(r"[^a-z0-9 ]+", "", text).strip()


def _parse_bbox_lines(
    pdf_path: Path, *, timeout_seconds: int = 20
) -> list[dict[str, Any]]:
    lines: list[dict[str, Any]] = []
    try:
        with fitz.open(pdf_path) as document:
            for page_idx, page in enumerate(document, start=1):
                page_lines: dict[tuple[int, int], dict[str, Any]] = {}
                words = page.get_text("words", sort=True)
                for word in words:
                    if len(word) < 8:
                        continue
                    x0, y0, x1, y1, token, block_no, line_no, _word_no = word[:8]
                    token = str(token or "").strip()
                    if not token:
                        continue
                    key = (int(block_no), int(line_no))
                    entry = page_lines.get(key)
                    if entry is None:
                        entry = {
                            "tokens": [],
                            "x0": float(x0),
                            "y0": float(y0),
                            "x1": float(x1),
                            "y1": float(y1),
                            "sort_y": float(y0),
                            "sort_x": float(x0),
                        }
                        page_lines[key] = entry
                    entry["tokens"].append(token)
                    entry["x0"] = min(float(entry["x0"]), float(x0))
                    entry["y0"] = min(float(entry["y0"]), float(y0))
                    entry["x1"] = max(float(entry["x1"]), float(x1))
                    entry["y1"] = max(float(entry["y1"]), float(y1))

                for line_no_on_page, entry in enumerate(
                    sorted(
                        page_lines.values(),
                        key=lambda item: (float(item["sort_y"]), float(item["sort_x"])),
                    ),
                    start=1,
                ):
                    line_text = " ".join(
                        str(token) for token in entry["tokens"]
                    ).strip()
                    if not line_text:
                        continue
                    lines.append(
                        {
                            "page": page_idx,
                            "line_no_on_page": line_no_on_page,
                            "text": line_text,
                            "bbox": [
                                float(entry["x0"]),
                                float(entry["y0"]),
                                float(entry["x1"]),
                                float(entry["y1"]),
                            ],
                        }
                    )
    except RuntimeError:
        raise
    except Exception as exc:
        raise RuntimeError(f"pymupdf line extraction failed: {exc}") from exc
    return lines


def _select_context_lines(
    page_lines: Sequence[Mapping[str, Any]],
    center_line_no: int,
    *,
    window: int = 1,
) -> list[Mapping[str, Any]]:
    return [
        line
        for line in page_lines
        if abs(int(line.get("line_no_on_page", 0)) - center_line_no) <= window
    ]


def _merge_bbox(lines: Sequence[Mapping[str, Any]]) -> list[float] | None:
    boxes = [line.get("bbox") for line in lines if isinstance(line.get("bbox"), list)]
    if not boxes:
        return None
    x0 = min(float(box[0]) for box in boxes)
    y0 = min(float(box[1]) for box in boxes)
    x1 = max(float(box[2]) for box in boxes)
    y1 = max(float(box[3]) for box in boxes)
    return [x0, y0, x1, y1]


def _find_best_line(
    lines: Sequence[Mapping[str, Any]],
    *,
    page_number: int | None,
    evidence_text: str | None,
) -> Mapping[str, Any] | None:
    needle = _normalize_text(evidence_text)
    if not needle:
        return None

    best: tuple[float, Mapping[str, Any] | None] = (0.0, None)
    needle_tokens = set(needle.split())
    for line in lines:
        if page_number is not None and int(line.get("page", 0) or 0) != page_number:
            continue
        hay = _normalize_text(str(line.get("text") or ""))
        if not hay:
            continue
        score = 0.0
        if hay == needle:
            score = 3.0
        elif needle in hay:
            score = 2.0
        else:
            hay_tokens = set(hay.split())
            overlap = len(needle_tokens & hay_tokens)
            if overlap:
                score = overlap / max(len(needle_tokens), 1)
        if score > best[0]:
            best = (score, line)
    return best[1] if best[0] >= 0.5 else None


def _render_page_image(pdf_path: Path, page_number: int, *, dpi: int = 144) -> Path:
    cache_dir = SNIPPETS_ROOT / "page_cache"
    _ensure_parent(cache_dir / "placeholder")
    out_prefix = cache_dir / f"{pdf_path.stem}_p{page_number}_dpi{dpi}"
    out_png = out_prefix.with_suffix(".png")
    if out_png.exists():
        return out_png
    scale = float(dpi) / 72.0
    try:
        with fitz.open(pdf_path) as document:
            if page_number < 1 or page_number > len(document):
                raise RuntimeError(f"page {page_number} out of range for {pdf_path}")
            page = document.load_page(page_number - 1)
            pixmap = page.get_pixmap(matrix=fitz.Matrix(scale, scale), alpha=False)
            _ensure_parent(out_png)
            pixmap.save(out_png)
    except RuntimeError:
        raise
    except Exception as exc:
        raise RuntimeError(f"pymupdf page render failed: {exc}") from exc
    return out_png


def _crop_snippet_image(
    page_png: Path, bbox: Sequence[float], out_path: Path, *, dpi: int = 144
) -> Path:
    if Image is None:
        raise RuntimeError("Pillow not installed")
    scale = float(dpi) / 72.0
    pad_x = 24.0
    pad_y = 18.0
    x0, y0, x1, y1 = [float(value) for value in bbox]
    with Image.open(page_png) as image:
        left = max(0, int((x0 - pad_x) * scale))
        top = max(0, int((y0 - pad_y) * scale))
        right = min(image.width, int((x1 + pad_x) * scale))
        bottom = min(image.height, int((y1 + pad_y) * scale))
        cropped = (
            image
            if right <= left or bottom <= top
            else image.crop((left, top, right, bottom))
        )
        _ensure_parent(out_path)
        cropped.save(out_path)
    return out_path


def _render_page_preview(
    page_png: Path, bbox: Sequence[float] | None, out_path: Path, *, dpi: int = 144
) -> Path:
    if Image is None or ImageDraw is None:
        raise RuntimeError("Pillow not installed")
    scale = float(dpi) / 72.0
    with Image.open(page_png) as image:
        preview = image.copy()
        if bbox is not None:
            draw = ImageDraw.Draw(preview)
            x0, y0, x1, y1 = [float(value) for value in bbox]
            draw.rectangle(
                [
                    int(x0 * scale),
                    int(y0 * scale),
                    int(x1 * scale),
                    int(y1 * scale),
                ],
                outline=(255, 80, 80),
                width=5,
            )
        preview.thumbnail((640, 900))
        _ensure_parent(out_path)
        preview.save(out_path)
    return out_path


def _image_to_ascii(path: Path, *, width: int = 64, max_lines: int = 22) -> str | None:
    if Image is None:
        return None
    try:
        with Image.open(path) as image:
            grayscale = image.convert("L")
            img_width, img_height = grayscale.size
            if img_width <= 0 or img_height <= 0:
                return None
            aspect = img_height / img_width
            out_height = max(8, int(width * aspect * 0.5))
            grayscale = grayscale.resize((width, out_height))
            pixels = grayscale.load()
            lines: list[str] = []
            for y in range(min(out_height, max_lines)):
                chars: list[str] = []
                for x in range(width):
                    value = pixels[x, y]
                    idx = int(value / 255 * (len(_ASCII_CHARS) - 1))
                    chars.append(_ASCII_CHARS[idx])
                lines.append("".join(chars))
            if out_height > max_lines:
                lines.append("[preview truncated]")
            return "\n".join(lines)
    except Exception:
        return None


def _snippet_artifact_name(item_id: str, suffix: str) -> Path:
    digest = hashlib.sha1(item_id.encode("utf-8")).hexdigest()[:16]
    return SNIPPETS_ROOT / f"{digest}_{suffix}.png"


def _text_only_snippet(
    *,
    status: str,
    page_number: int | None,
    reason: str,
    evidence_text: str | None,
    matched_text: str | None = None,
) -> dict[str, Any]:
    fallback_text = str(matched_text or evidence_text or "").strip() or None
    return {
        "kind": "text_only",
        "evidence_quality": "missing",
        "status": status,
        "image_path": None,
        "ascii_preview": None,
        "matched_text": fallback_text,
        "page_number": page_number,
        "reason": reason,
    }


def _normalize_evidence_text(value: str | None) -> str | None:
    text = str(value or "").strip()
    if not text:
        return None
    if text.lower() == "unknown":
        return None
    return text


def _evidence_quality_for_snippet(snippet: Mapping[str, Any]) -> str:
    has_image = bool(snippet.get("image_path") or snippet.get("image_url"))
    matched_text = _normalize_evidence_text(
        str(snippet.get("matched_text") or "").strip() or None
    )
    has_bbox = snippet.get("bbox") is not None
    if has_image and has_bbox and matched_text:
        return "precise"
    if has_image:
        return "approximate"
    return "missing"


def build_metric_snippet(
    *,
    item_id: str,
    pdf_path: Path | None,
    page_number: int | None,
    evidence_text: str | None,
) -> dict[str, Any]:
    if pdf_path is None:
        return _text_only_snippet(
            status="missing_pdf",
            page_number=page_number,
            reason="PDF unavailable for snippet generation.",
            evidence_text=evidence_text,
        )

    try:
        lines = _parse_bbox_lines(pdf_path)
    except Exception as exc:
        return _text_only_snippet(
            status="bbox_unavailable",
            page_number=page_number,
            reason=str(exc),
            evidence_text=evidence_text,
        )

    matched = _find_best_line(
        lines, page_number=page_number, evidence_text=evidence_text
    )
    bbox: list[float] | None = None
    matched_text: str | None = None
    if matched is not None:
        page_number = int(matched.get("page", 0) or 0) or page_number
        page_lines = [
            line for line in lines if int(line.get("page", 0) or 0) == page_number
        ]
        focus_lines = _select_context_lines(
            page_lines, int(matched.get("line_no_on_page", 0) or 0)
        )
        bbox = _merge_bbox(focus_lines) or (
            matched.get("bbox") if isinstance(matched.get("bbox"), list) else None
        )
        matched_text = (
            "\n".join(str(line.get("text") or "") for line in focus_lines).strip()
            or str(matched.get("text") or "").strip()
        )

    if page_number is None:
        return _text_only_snippet(
            status="missing_page",
            page_number=None,
            reason="No page reference available in provenance.",
            evidence_text=evidence_text,
            matched_text=matched_text,
        )

    try:
        page_png = _render_page_image(pdf_path, page_number)
    except Exception as exc:
        return _text_only_snippet(
            status="render_failed",
            page_number=page_number,
            reason=str(exc),
            evidence_text=evidence_text,
            matched_text=matched_text,
        )

    try:
        # We always want the full page preview with highlighting now, rather than a crop.
        # This provides better context for verification (dates, periods, etc).
        out_path = _snippet_artifact_name(item_id, "page_highlight")
        image_path = _render_page_preview(page_png, bbox, out_path)
        kind = "page_preview"
    except Exception as exc:
        return _text_only_snippet(
            status="image_failed",
            page_number=page_number,
            reason=str(exc),
            evidence_text=evidence_text,
            matched_text=matched_text,
        )

    snippet = {
        "kind": kind,
        "status": "ok",
        "image_path": _project_relative(image_path),
        "image_name": image_path.name,
        "image_url": f"/api/extraction-review/snippets/{image_path.name}",
        "ascii_preview": _image_to_ascii(image_path),
        "matched_text": matched_text,
        "page_number": page_number,
        "bbox": bbox,
        "reason": None,
    }
    snippet["evidence_quality"] = _evidence_quality_for_snippet(snippet)
    return snippet


def _count_reviewable_metrics(payload: Mapping[str, Any]) -> int:
    metrics = (
        payload.get("metrics") if isinstance(payload.get("metrics"), Mapping) else {}
    )
    return sum(1 for value in metrics.values() if value is not None)


def _review_diagnostic(status: str, metrics_count: int) -> tuple[bool, str]:
    normalized_status = str(status or "unknown").strip() or "unknown"
    if metrics_count > 0:
        return True, "reviewable"
    if normalized_status in {"ok", "ok_low_confidence"}:
        return False, "persisted_but_no_metrics"
    if normalized_status == "parser_error":
        return True, "reviewable_parser_error"
    if normalized_status == "failed":
        return False, "run_not_persisted"
    return False, normalized_status


def _load_error_queue() -> dict[str, Any]:
    if not ERROR_QUEUE_PATH.exists():
        return {"updated_at": None, "items": []}
    return json.loads(ERROR_QUEUE_PATH.read_text(encoding="utf-8"))


def _save_error_queue(payload: Mapping[str, Any]) -> None:
    _ensure_parent(ERROR_QUEUE_PATH)
    ERROR_QUEUE_PATH.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _latest_review_run(db: Session, document_id: str) -> ExtractionRun | None:
    run = (
        db.query(ExtractionRun)
        .filter(ExtractionRun.document_id == document_id)
        .filter(ExtractionRun.status.in_(["ok", "ok_low_confidence", "parser_error"]))
        .order_by(ExtractionRun.created_at.desc())
        .first()
    )
    if run is not None:
        return run
    return (
        db.query(ExtractionRun)
        .filter(ExtractionRun.document_id == document_id)
        .order_by(ExtractionRun.created_at.desc())
        .first()
    )


def list_review_runs(
    db: Session,
    *,
    ticker: str | None = None,
    limit: int = 50,
) -> dict[str, Any]:
    normalized_ticker = str(ticker or "").strip().upper() or None
    query = db.query(ExtractionRun, Document).join(
        Document, Document.document_id == ExtractionRun.document_id
    )
    if normalized_ticker:
        query = query.filter(Document.ticker == normalized_ticker)

    rows = (
        query.order_by(ExtractionRun.created_at.desc())
        .limit(max(1, min(int(limit), 200)))
        .all()
    )

    items: list[dict[str, Any]] = []
    for run, document in rows:
        payload = (
            run.structured_json if isinstance(run.structured_json, Mapping) else {}
        )
        metrics = (
            payload.get("metrics")
            if isinstance(payload.get("metrics"), Mapping)
            else {}
        )
        items.append(
            {
                "run_id": str(run.run_id),
                "document_id": str(document.document_id),
                "ticker": str(document.ticker or "").strip(),
                "title": str(document.title or "").strip() or None,
                "published_at": (
                    str(document.published_at)
                    if document.published_at is not None
                    else None
                ),
                "status": str(run.status or "unknown"),
                "created_at": str(run.created_at),
                "confidence_overall": run.confidence_overall,
                "model_name": str(run.model_name or "").strip() or None,
                "extractor_version": str(run.extractor_version or "").strip() or None,
                "requested_method": (
                    payload.get("_method_provenance", {}).get("requested_method")
                    if isinstance(payload.get("_method_provenance"), Mapping)
                    else None
                ),
                "actual_method": (
                    payload.get("_method_provenance", {}).get("actual_method")
                    if isinstance(payload.get("_method_provenance"), Mapping)
                    else None
                ),
                "strict_method": (
                    payload.get("_method_provenance", {}).get("strict_method")
                    if isinstance(payload.get("_method_provenance"), Mapping)
                    else None
                ),
                "error": str(run.error or "").strip() or None,
                "metrics_count": sum(
                    1 for value in metrics.values() if value is not None
                ),
            }
        )

    return {
        "ticker": normalized_ticker,
        "count": len(items),
        "items": items,
    }


def _item_summary(items: Sequence[Mapping[str, Any]]) -> dict[str, int]:
    summary = {
        "total": len(items),
        "approved": 0,
        "wrong": 0,
        "abstain": 0,
        "pending": 0,
    }
    for item in items:
        status = str(item.get("review_status") or "pending")
        if status in summary:
            summary[status] += 1
        else:
            summary["pending"] += 1
    return summary


def build_review_item(
    db: Session | None, document: Document, run: ExtractionRun, metric: str
) -> dict[str, Any] | None:
    payload = run.structured_json or {}
    metrics = payload.get("metrics")
    if not isinstance(metrics, Mapping):
        return None

    value = metrics.get(metric)
    # If the parser failed, we still want to show the item so the human can manually extract.
    # Otherwise, if the value is None, we skip it.
    if value is None and run.status != "parser_error":
        return None

    period_end = str(payload.get("period_end") or "").strip() or None
    period_type = str(payload.get("period_type") or "").strip() or None
    source_document_id = str(getattr(document, "document_id", "") or "").strip()
    raw_provenance = (
        payload.get("provenance")
        if isinstance(payload.get("provenance"), Mapping)
        else {}
    )
    record = from_extraction_provenance(
        metric_name=metric,
        provenance=str(raw_provenance.get(metric) or "").strip() or None,
        source_document_id=source_document_id or None,
        period_ref=f"{period_end}:{period_type}"
        if period_end and period_type
        else (period_end or period_type),
        confidence=payload.get("confidence_metrics"),
    )
    page_number = _parse_page_number(record.location_ref)
    item_id = f"{run.run_id}:{metric}"
    pdf_path = _coerce_pdf_path(document, payload)
    matched_text = str(record.evidence_text or "").strip() or None
    row_ref = _row_reference_for_metric(payload, metric)
    thinking = _thinking_for_metric(payload, metric)
    markdown = _markdown_for_metric(payload, metric)
    
    historical_value = _previous_period_value(
        db,
        ticker=str(getattr(document, "ticker", "") or "").strip(),
        metric=metric,
        period_end=payload.get("period_end"),
        period_type=payload.get("period_type"),
    )
    
    # Use row_ref as primary evidence for highlighting if available, 
    # as it's the most specific anchor in the table.
    highlight_text = row_ref or matched_text
    
    period_col = str(payload.get("period_col") or "").strip() or None
    method_provenance = payload.get("_method_provenance")
    method_provenance = (
        dict(method_provenance) if isinstance(method_provenance, Mapping) else {}
    )
    gold_payload = _gold_payload_for_document(document, pdf_path)
    gold_metrics = (
        gold_payload.get("metrics") if isinstance(gold_payload, Mapping) else {}
    )
    gold_metrics = gold_metrics if isinstance(gold_metrics, Mapping) else {}
    gold_expected_value = _gold_metric_value(gold_metrics, metric)
    snippet = build_metric_snippet(
        item_id=item_id,
        pdf_path=pdf_path,
        page_number=page_number,
        evidence_text=highlight_text,
    )
    evidence_quality = str(
        snippet.get("evidence_quality") or _evidence_quality_for_snippet(snippet)
    )
    snippet["evidence_quality"] = evidence_quality
    method_label = (
        str(method_provenance.get("actual_method") or "").strip()
        or str(method_provenance.get("requested_method") or "").strip()
        or None
    )
    return {
        "item_id": item_id,
        "run_id": str(run.run_id),
        "document_id": source_document_id,
        "ticker": str(getattr(document, "ticker", "") or "").strip(),
        "title": str(getattr(document, "title", "") or "").strip() or None,
        "file_path": _project_relative(pdf_path),
        "metric_name": metric,
        "extracted_value": value,
        "period_end": period_end,
        "period_type": period_type,
        "currency": str(payload.get("currency") or "").strip() or None,
        "scale": str(payload.get("scale") or "").strip() or None,
        "page_number": page_number,
        "metric_value": value,
        "matched_text": matched_text,
        "image_url": snippet.get("image_url"),
        "image_path": snippet.get("image_path"),
        "evidence_quality": evidence_quality,
        "method_provenance": method_label,
        "row_refs": {metric: row_ref} if row_ref else {},
        "table_type": record.source_label,
        "period_col": period_col,
        "confidence_metrics": payload.get("confidence_metrics"),
        "evidence_reference": record.raw_reference,
        "evidence_text": highlight_text,
        "evidence_summary": record.evidence_summary,
        "provenance_status": record.provenance_status,
        "source_label": record.source_label,
        "location_ref": record.location_ref,
        "thinking": thinking,
        "raw_markdown": markdown,
        "historical_value": historical_value,
        "requested_method": method_provenance.get("requested_method"),
        "actual_method": method_provenance.get("actual_method"),
        "strict_method": method_provenance.get("strict_method"),
        "parser_id": method_provenance.get("parser_id"),
        "model_id": method_provenance.get("model_id"),
        "runtime_id": method_provenance.get("runtime_id"),
        "fallback_used": method_provenance.get("fallback_used"),
        "error_stage": method_provenance.get("error_stage"),
        "method_warnings": method_provenance.get("warnings") or [],
        "gold_document_id": gold_payload.get("document_id")
        if isinstance(gold_payload, Mapping)
        else None,
        "gold_expected_trust": gold_payload.get("expected_trust")
        if isinstance(gold_payload, Mapping)
        else None,
        "bbox": snippet.get("bbox"),
        "snippet": snippet,
        "review_status": "pending",
        "reviewed_at": None,
        "expected_value": gold_expected_value,
        "reviewer_note": "",
    }


def _append_review_items(
    db: Session | None,
    items: list[dict[str, Any]],
    document_summaries: list[dict[str, Any]],
    *,
    document: Document,
    run: ExtractionRun,
) -> None:
    item_count_before = len(items)
    payload = run.structured_json if isinstance(run.structured_json, Mapping) else {}
    for metric in METRIC_FIELDS:
        item = build_review_item(db, document, run, metric)
        if item is not None:
            items.append(item)

    metrics_count = _count_reviewable_metrics(payload)
    review_ready, reason = _review_diagnostic(
        str(run.status or "unknown"), metrics_count
    )
    method_provenance = payload.get("_method_provenance")
    method_provenance = (
        dict(method_provenance) if isinstance(method_provenance, Mapping) else {}
    )

    document_summaries.append(
        {
            "document_id": str(document.document_id),
            "ticker": str(document.ticker or "").strip(),
            "title": str(document.title or "").strip() or None,
            "status": str(run.status or "unknown"),
            "run_id": str(run.run_id),
            "items_count": len(items) - item_count_before,
            "metrics_count": metrics_count,
            "review_ready": review_ready,
            "reason": reason,
            "requested_method": method_provenance.get("requested_method"),
            "actual_method": method_provenance.get("actual_method"),
            "strict_method": method_provenance.get("strict_method"),
            "created_at": str(run.created_at),
        }
    )


def create_review_session(
    db: Session,
    document_ids: Sequence[str],
    run_ids: Sequence[str] | None = None,
) -> dict[str, Any]:
    cleaned_ids = _clean_requested_ids(document_ids)
    cleaned_run_ids = _clean_requested_ids(run_ids)
    if not cleaned_ids and not cleaned_run_ids:
        raise ValueError("document_ids or run_ids must not be empty")

    items: list[dict[str, Any]] = []
    document_summaries: list[dict[str, Any]] = []
    missing_document_ids: list[str] = []
    missing_run_ids: list[str] = []

    if cleaned_run_ids:
        normalized_run_ids: dict[str, str] = {}
        parsed_run_ids: list[UUID] = []
        for run_id in cleaned_run_ids:
            try:
                parsed = UUID(run_id)
            except ValueError:
                missing_run_ids.append(run_id)
                continue
            normalized_run_ids[str(parsed)] = run_id
            parsed_run_ids.append(parsed)

        runs = []
        if parsed_run_ids:
            runs = (
                db.query(ExtractionRun)
                .filter(ExtractionRun.run_id.in_(parsed_run_ids))
                .all()
            )

        run_by_id = {str(run.run_id): run for run in runs}
        documents = []
        if runs:
            documents = (
                db.query(Document)
                .filter(Document.document_id.in_([run.document_id for run in runs]))
                .all()
            )
        document_by_id = {str(document.document_id): document for document in documents}

        for normalized_run_id, requested_run_id in normalized_run_ids.items():
            run = run_by_id.get(normalized_run_id)
            if run is None:
                missing_run_ids.append(requested_run_id)
                continue
            document = document_by_id.get(str(run.document_id))
            if document is None:
                missing_document_ids.append(str(run.document_id))
                continue
            _append_review_items(
                db,
                items,
                document_summaries,
                document=document,
                run=run,
            )

        if not document_summaries:
            raise ValueError("no extraction runs found for requested run_ids")
    else:
        documents = (
            db.query(Document).filter(Document.document_id.in_(cleaned_ids)).all()
        )
        document_by_id = {str(document.document_id): document for document in documents}
        missing_document_ids = [
            document_id
            for document_id in cleaned_ids
            if document_id not in document_by_id
        ]

        for document_id in cleaned_ids:
            document = document_by_id.get(document_id)
            if document is None:
                continue
            run = _latest_review_run(db, document_id)
            if run is None:
                document_summaries.append(
                    {
                        "document_id": document_id,
                        "ticker": str(document.ticker or "").strip(),
                        "title": str(document.title or "").strip() or None,
                        "status": "missing_extraction_run",
                        "review_ready": False,
                        "reason": "run_not_found",
                        "metrics_count": 0,
                    }
                )
                continue
            _append_review_items(
                db,
                items,
                document_summaries,
                document=document,
                run=run,
            )

    resolved_document_ids = _clean_requested_ids(
        [summary.get("document_id") for summary in document_summaries]
    )
    resolved_run_ids = _clean_requested_ids(
        [summary.get("run_id") for summary in document_summaries]
    )
    digest_source = cleaned_run_ids or cleaned_ids or resolved_run_ids
    digest = hashlib.sha1("|".join(digest_source).encode("utf-8")).hexdigest()[:10]
    session_id = (
        f"manual-review-{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}-{digest}"
    )
    session = {
        "session_id": session_id,
        "created_at": utc_now_iso(),
        "document_ids": resolved_document_ids,
        "run_ids": resolved_run_ids,
        "missing_document_ids": _clean_requested_ids(missing_document_ids),
        "missing_run_ids": _clean_requested_ids(missing_run_ids),
        "documents": document_summaries,
        "items": items,
        "summary": _item_summary(items),
    }
    save_review_session(session)
    return session


def create_review_session_from_payload(
    *,
    document_id: str,
    ticker: str | None,
    title: str | None,
    pdf_path: str | None,
    status: str,
    payload: Mapping[str, Any],
    run_id: str | None = None,
    created_at: str | None = None,
    diagnostics: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    resolved_document_id = str(document_id or "").strip()
    if not resolved_document_id:
        raise ValueError("document_id is required")

    resolved_payload = dict(payload) if isinstance(payload, Mapping) else {}
    resolved_run_id = str(run_id or "").strip()
    if not resolved_run_id:
        suffix = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        resolved_run_id = f"real-gold-{resolved_document_id}-{suffix}"

    synthetic_document = SimpleNamespace(
        document_id=resolved_document_id,
        ticker=str(ticker or "").strip() or None,
        title=str(title or "").strip() or None,
        pdf_path=str(pdf_path or "").strip() or None,
    )
    synthetic_run = SimpleNamespace(
        run_id=resolved_run_id,
        structured_json=resolved_payload,
        status=str(status or "unknown").strip() or "unknown",
        created_at=str(created_at or utc_now_iso()),
    )

    items: list[dict[str, Any]] = []
    document_summaries: list[dict[str, Any]] = []
    _append_review_items(
        None,
        items,
        document_summaries,
        document=synthetic_document,
        run=synthetic_run,
    )

    digest = hashlib.sha1(
        f"{resolved_document_id}|{resolved_run_id}".encode("utf-8")
    ).hexdigest()[:10]
    session = {
        "session_id": f"real-gold-review-{digest}",
        "created_at": utc_now_iso(),
        "session_status": "real_gold_eval",
        "document_ids": [resolved_document_id],
        "run_ids": [resolved_run_id],
        "missing_document_ids": [],
        "missing_run_ids": [],
        "documents": document_summaries,
        "items": items,
        "diagnostics": (
            dict(diagnostics)
            if isinstance(diagnostics, Mapping)
            else {
                "code": "real_gold_eval",
                "message": "Generated from /api/extraction-eval/real-gold.",
            }
        ),
        "summary": _item_summary(items),
    }
    save_review_session(session)
    return session


def save_review_session(session: Mapping[str, Any]) -> None:
    session_id = str(session.get("session_id") or "").strip()
    if not session_id:
        raise ValueError("session_id is required")
    path = _session_path(session_id)
    _ensure_parent(path)
    payload = dict(session)
    payload["summary"] = _item_summary(payload.get("items") or [])
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def load_review_session(session_id: str) -> dict[str, Any]:
    path = _session_path(session_id)
    if not path.exists():
        raise FileNotFoundError(f"review session not found: {session_id}")
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["summary"] = _item_summary(payload.get("items") or [])
    return payload


def submit_review_decision(
    session_id: str,
    *,
    item_id: str,
    status: str,
    expected_value: Any = None,
    reviewer_note: str | None = None,
) -> dict[str, Any]:
    normalized_status = str(status or "").strip().lower()
    if normalized_status not in VALID_REVIEW_STATUSES:
        raise ValueError(f"unsupported review status: {status}")

    session = load_review_session(session_id)
    items = session.get("items")
    if not isinstance(items, list):
        raise ValueError("review session items are invalid")

    updated_item: dict[str, Any] | None = None
    reviewed_at = utc_now_iso()
    for item in items:
        if str(item.get("item_id") or "") != item_id:
            continue
        item["review_status"] = normalized_status
        item["reviewed_at"] = reviewed_at
        item["expected_value"] = expected_value
        item["reviewer_note"] = str(reviewer_note or "")
        updated_item = dict(item)
        break

    if updated_item is None:
        raise KeyError(item_id)

    session["updated_at"] = reviewed_at
    save_review_session(session)
    _update_error_queue(session_id=session_id, item=updated_item)
    return {
        "session_id": session_id,
        "item": updated_item,
        "summary": _item_summary(items),
    }


def _update_error_queue(*, session_id: str, item: Mapping[str, Any]) -> None:
    payload = _load_error_queue()
    queue_items = payload.get("items")
    queue_by_id = {
        str(entry.get("item_id") or ""): dict(entry)
        for entry in (queue_items if isinstance(queue_items, list) else [])
        if isinstance(entry, Mapping)
    }
    queue_item = dict(item)
    queue_item["session_id"] = session_id
    queue_item["review_timestamp"] = item.get("reviewed_at")
    item_id = str(item.get("item_id") or "")
    if str(item.get("review_status") or "") == "wrong":
        queue_by_id[item_id] = queue_item
    else:
        queue_by_id.pop(item_id, None)

    output = {
        "updated_at": utc_now_iso(),
        "items": sorted(
            queue_by_id.values(),
            key=lambda entry: str(entry.get("review_timestamp") or ""),
            reverse=True,
        ),
    }
    _save_error_queue(output)


def get_error_queue(*, limit: int = 200) -> dict[str, Any]:
    payload = _load_error_queue()
    items = payload.get("items")
    items = items if isinstance(items, list) else []
    return {
        "updated_at": payload.get("updated_at"),
        "count": len(items),
        "items": items[:limit],
    }
