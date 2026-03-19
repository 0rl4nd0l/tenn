#!/usr/bin/env python3
from __future__ import annotations

import re
import subprocess
from pathlib import Path
from typing import Dict, List, Tuple


MAX_PAGES = 2
MAX_CHARS = 16000

_SPACE_RE = re.compile(r"[\s\-_]+")

FINANCIAL_KEYWORDS: Dict[str, Tuple[Tuple[str, int], ...]] = {
    "appendix_report": (
        ("appendix 4d", 6),
        ("appendix 4e", 6),
    ),
    "financial_report": (
        ("half year financial report", 5),
        ("half yearly financial report", 5),
        ("half yearly report and accounts", 5),
        ("half yearly report", 4),
        ("annual report", 4),
        ("interim report", 4),
        ("financial report", 4),
        ("consolidated financial statements", 5),
        ("statement of financial position", 5),
        ("income statement", 4),
        ("cash flow statement", 4),
        ("statement of cash flows", 4),
        ("statement of profit or loss", 4),
    ),
}

NON_FINANCIAL_KEYWORDS: Dict[str, Tuple[Tuple[str, int], ...]] = {
    "presentation": (
        ("investor presentation", 5),
        ("results presentation", 5),
        ("presentation", 4),
        ("slides", 3),
    ),
    "conference": (
        ("conference", 4),
        ("webinar", 3),
    ),
    "announcement": (
        ("announcement", 4),
        ("media release", 3),
        ("asx release", 3),
    ),
    "investor_update": (
        ("investor update", 4),
        ("corporate update", 3),
        ("trading update", 3),
    ),
    "timetable": (
        ("timetable", 4),
        ("calendar", 2),
        ("schedule", 2),
    ),
}


def _normalize_text(value: str) -> str:
    return _SPACE_RE.sub(" ", (value or "").strip().lower()).strip()


def _read_first_pages_with_fitz(pdf_path: Path, max_pages: int = MAX_PAGES, max_chars: int = MAX_CHARS) -> str:
    try:
        import fitz  # type: ignore[import-not-found]
    except Exception:
        return ""

    chunks: List[str] = []
    total = 0
    with fitz.open(str(pdf_path)) as doc:
        page_count = min(max_pages, doc.page_count)
        for page_index in range(page_count):
            text = str(doc.load_page(page_index).get_text("text") or "")
            if not text:
                continue
            remaining = max_chars - total
            if remaining <= 0:
                break
            take = text[:remaining]
            chunks.append(take)
            total += len(take)
            if total >= max_chars:
                break
    return "\n".join(chunks)


def _read_first_pages_with_pdftotext(pdf_path: Path, max_pages: int = MAX_PAGES, max_chars: int = MAX_CHARS) -> str:
    try:
        proc = subprocess.run(
            [
                "pdftotext",
                "-f",
                "1",
                "-l",
                str(max_pages),
                str(pdf_path),
                "-",
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=20,
            check=False,
        )
    except Exception:
        return ""
    if proc.returncode != 0:
        return ""
    return str(proc.stdout or "")[:max_chars]


def extract_document_preview(pdf_path: Path, max_pages: int = MAX_PAGES, max_chars: int = MAX_CHARS) -> str:
    path = Path(pdf_path).expanduser().resolve()
    if not path.exists() or not path.is_file():
        return ""

    text = _read_first_pages_with_fitz(path, max_pages=max_pages, max_chars=max_chars)
    if text.strip():
        return text
    return _read_first_pages_with_pdftotext(path, max_pages=max_pages, max_chars=max_chars)


def _match_keywords(text: str, keyword_map: Dict[str, Tuple[Tuple[str, int], ...]]) -> Dict[str, Dict[str, object]]:
    results: Dict[str, Dict[str, object]] = {}
    for document_type, weighted_keywords in keyword_map.items():
        hits: List[str] = []
        score = 0
        for keyword, weight in weighted_keywords:
            if keyword in text:
                hits.append(keyword)
                score += weight
        if hits:
            results[document_type] = {
                "score": score,
                "hits": hits,
            }
    return results


def _best_match(matches: Dict[str, Dict[str, object]]) -> Tuple[str, int, List[str]]:
    if not matches:
        return "", 0, []
    best_type = max(
        matches,
        key=lambda item: (
            int(matches[item].get("score", 0) or 0),
            len(list(matches[item].get("hits", []) or [])),
            item,
        ),
    )
    best = matches[best_type]
    return (
        best_type,
        int(best.get("score", 0) or 0),
        list(best.get("hits", []) or []),
    )


def classify_document(pdf_path) -> Dict[str, object]:
    path = Path(pdf_path).expanduser()
    preview = extract_document_preview(path)
    text = _normalize_text(f"{path.name} {preview}")
    financial_matches = _match_keywords(text, FINANCIAL_KEYWORDS)
    nonfinancial_matches = _match_keywords(text, NON_FINANCIAL_KEYWORDS)

    best_financial_type, financial_score, financial_hits = _best_match(financial_matches)
    best_nonfinancial_type, nonfinancial_score, _ = _best_match(nonfinancial_matches)
    appendix_hits = list(financial_matches.get("appendix_report", {}).get("hits", []) or [])

    if appendix_hits:
        best_financial_type = "appendix_report"
        financial_hits = list(dict.fromkeys(appendix_hits + financial_hits))

    strong_financial_hit = any(
        hit in {
            "appendix 4d",
            "appendix 4e",
            "half year financial report",
            "consolidated financial statements",
            "statement of financial position",
            "annual report",
        }
        for hit in financial_hits
    )

    if financial_score == 0 and nonfinancial_score == 0:
        return {
            "is_financial": not bool(preview.strip()),
            "document_type": "unknown",
        }
    if strong_financial_hit or financial_score >= nonfinancial_score:
        return {
            "is_financial": True,
            "document_type": best_financial_type or "financial_report",
        }
    return {
        "is_financial": False,
        "document_type": best_nonfinancial_type or "other",
    }


__all__ = [
    "classify_document",
    "extract_document_preview",
]
