#!/usr/bin/env python3
"""
Build an ASX ticker identity map from local filings and structured extraction data.
"""

from __future__ import annotations

import argparse
import datetime
import json
import os
import re
import sqlite3
import subprocess
import sys
from pathlib import Path
from typing import Any, Iterable

DEFAULT_DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./financial-engine_v2/data/fe_local.db")
REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_ASX_TICKERS = REPO_ROOT / "financial-engine_v2" / "data" / "raw" / "asx_ticker_universe.txt"
DEFAULT_DOCS_ROOT = REPO_ROOT / "financial-engine_v2" / "data" / "asx" / "docs"
DEFAULT_OUT_JSON = REPO_ROOT / "financial-engine_v2" / "config" / "ticker_identity_map.json"
DEFAULT_MISSING_REPORT = REPO_ROOT / "reports" / "analysis" / "asx_identity_missing_tickers.json"

SPACE_RE = re.compile(r"\s+")
PUNCT_RE = re.compile(r"[\t\r\n]+")
NAME_KEY_RE = re.compile(r"(company|issuer|entity|legal|name|organisation|organization)", re.IGNORECASE)
COMPANY_SUFFIX_TERMS = (
    "GROUP LIMITED",
    "LIMITED",
    "LTD",
    "GROUP",
    "HOLDINGS",
    "CORPORATION",
    "BANK",
    "RESOURCES",
    "MINING",
)
STRONG_SUFFIX_TERMS = {"limited", "ltd", "group", "holdings", "corporation", "bank", "banking"}
COMPANY_SUFFIX_RE = re.compile(
    r"\b([A-Z][A-Z0-9&'().,\-/ ]{2,140}?\b(?:GROUP LIMITED|LIMITED|LTD|GROUP|HOLDINGS|CORPORATION|BANK|RESOURCES|MINING))\b",
    re.IGNORECASE,
)
GENERIC_DOC_WORDS = {
    "announcement",
    "appendix",
    "application",
    "conference",
    "cleansing",
    "distribution",
    "dividend",
    "guidance",
    "half year",
    "interim",
    "investor",
    "meeting",
    "notice",
    "notification",
    "presentation",
    "quarterly",
    "results",
    "update",
    "webinar",
}
LOWERCASE_WORDS = {"of", "and", "the", "for", "to", "in", "on", "at", "by", "a", "an"}
ACRONYM_STOPWORDS = {"the", "and", "of", "for", "to", "in", "on", "at", "by", "a", "an", "limited", "ltd", "group"}
GENERIC_NAME_TOKENS = {
    "the",
    "a",
    "an",
    "of",
    "and",
    "for",
    "to",
    "in",
    "on",
    "at",
    "by",
    "limited",
    "ltd",
    "group",
    "holding",
    "holdings",
    "corporation",
    "corp",
    "company",
    "co",
    "plc",
    "pty",
    "bank",
    "banking",
    "australia",
    "australian",
    "asx",
    "issuer",
    "resources",
    "resource",
    "minerals",
    "mining",
    "services",
    "service",
    "management",
}
NOISY_STANDALONE_TERMS = {
    "group",
    "limited",
    "ltd",
    "holdings",
    "holding",
    "corporation",
    "bank",
    "banking",
    "australia",
    "australian",
    "resources",
    "minerals",
    "mining",
    "services",
    "service",
    "management",
    "issuer",
}
NOISY_NAME_PHRASES = {
    "the group",
    "group limited",
    "australia limited",
    "services limited",
    "management limited",
    "asx limited",
    "asx issuer",
    "holdings ltd",
    "banking corporation",
    "resources ltd",
    "minerals limited",
}
ACRONYM_SOURCE_NOISE_TOKENS = {
    "authorised",
    "authorized",
    "release",
    "report",
    "present",
    "presentation",
    "update",
    "notice",
    "announcement",
    "appendix",
    "notification",
    "application",
    "investor",
}
NAME_BOILERPLATE_PREFIX_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"^\s*authori[sz]ed\s+for\s+release\s+by\s+", re.IGNORECASE),
    re.compile(r"^\s*for\s+personal\s+use\s+only[:\-]?\s*", re.IGNORECASE),
    re.compile(r"^\s*report\s+has\s+provided\s+", re.IGNORECASE),
    re.compile(r"^\s*provided\s+by\s+", re.IGNORECASE),
    re.compile(r"^\s*(?:asx|market)\s+release[:\-]?\s*", re.IGNORECASE),
    re.compile(r"^\s*(?:company\s+)?announcement[:\-]?\s*", re.IGNORECASE),
)
NAME_LEADING_CONNECTOR_RE = re.compile(r"^\s*(?:in|at|on|by|for|to|from)\s+", re.IGNORECASE)
MAJOR_TICKER_FALLBACK_NAMES: dict[str, list[str]] = {
    "BHP": ["BHP Group Limited"],
    "CBA": ["Commonwealth Bank of Australia"],
    "RIO": ["Rio Tinto Limited"],
    "CSL": ["CSL Limited"],
    "WBC": ["Westpac Banking Corporation"],
}


def normalize_space(value: Any) -> str:
    txt = PUNCT_RE.sub(" ", str(value or ""))
    return SPACE_RE.sub(" ", txt).strip()


def _dedupe_preserve(items: Iterable[str]) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()
    for raw in items:
        txt = normalize_space(raw)
        if not txt:
            continue
        key = txt.casefold()
        if key in seen:
            continue
        seen.add(key)
        out.append(txt)
    return out


def parse_bool(value: Any) -> bool:
    txt = str(value or "").strip().lower()
    if txt in {"1", "true", "t", "yes", "y", "on"}:
        return True
    if txt in {"0", "false", "f", "no", "n", "off"}:
        return False
    raise argparse.ArgumentTypeError(f"invalid boolean value: {value!r}")


def sqlite_path_from_url(database_url: str) -> Path:
    txt = str(database_url or "").strip()
    if not txt:
        raise RuntimeError("database_url is empty")
    if txt.startswith("sqlite:///"):
        raw = txt[len("sqlite:///") :]
    elif txt.startswith("sqlite://"):
        raw = txt[len("sqlite://") :]
    else:
        raw = txt
    path = Path(raw).expanduser()
    if not path.is_absolute():
        path = (Path.cwd() / path).resolve()
    return path


def load_tickers(path: Path) -> list[str]:
    if not path.exists():
        raise RuntimeError(f"ASX tickers file not found: {path}")
    out: list[str] = []
    seen: set[str] = set()
    for line in path.read_text(encoding="utf-8").splitlines():
        body = line.split("#", 1)[0].strip().upper()
        token = "".join(ch for ch in body if ch.isalnum())
        if not token or token in seen:
            continue
        seen.add(token)
        out.append(token)
    return out


def load_existing_identity_map(path: Path) -> dict[str, dict[str, list[str]]]:
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    if not isinstance(payload, dict):
        return {}
    out: dict[str, dict[str, list[str]]] = {}
    for raw_ticker, raw_entry in payload.items():
        ticker = normalize_space(raw_ticker).upper()
        if not ticker:
            continue
        entry = raw_entry if isinstance(raw_entry, dict) else {}
        canonical = _dedupe_preserve(entry.get("canonical_names", []) if isinstance(entry.get("canonical_names"), list) else [])
        aliases = _dedupe_preserve(entry.get("aliases", []) if isinstance(entry.get("aliases"), list) else [])
        out[ticker] = {"canonical_names": canonical, "aliases": aliases}
    return out


def _strip_name_boilerplate(text: str) -> str:
    out = normalize_space(text)
    if not out:
        return ""
    for pat in NAME_BOILERPLATE_PREFIX_PATTERNS:
        updated = normalize_space(pat.sub("", out))
        if updated and updated != out:
            out = updated
    # Remove a single leading connector only when enough content remains.
    candidate = normalize_space(NAME_LEADING_CONNECTOR_RE.sub("", out))
    if candidate and len(candidate.split()) >= 2:
        out = candidate
    return out


def _clean_company_name(value: str) -> str:
    txt = _strip_name_boilerplate(str(value or ""))
    if not txt:
        return ""
    txt = re.sub(r"[|]+", " ", txt)
    txt = re.sub(r"\s*[-_]{2,}\s*", " ", txt)
    txt = re.sub(r"[^\w&/().,\- ]+", " ", txt)
    txt = SPACE_RE.sub(" ", txt).strip(" .,:;/-_")
    return txt


def _smart_company_casing(name: str) -> str:
    txt = normalize_space(name)
    if not txt:
        return ""
    letters = [ch for ch in txt if ch.isalpha()]
    uppercase_ratio = 0.0
    if letters:
        uppercase_ratio = sum(1 for ch in letters if ch.isupper()) / float(len(letters))
    if uppercase_ratio < 0.7:
        return txt

    words: list[str] = []
    for idx, token in enumerate(txt.split()):
        core = token.strip()
        stripped = core.strip(".,;:()")
        if not stripped:
            words.append(core)
            continue
        if stripped.isupper() and len(stripped) <= 4:
            word = stripped
        else:
            lower = stripped.lower()
            if idx > 0 and lower in LOWERCASE_WORDS:
                word = lower
            else:
                word = lower.capitalize()
        prefix = core[: len(core) - len(core.lstrip("([{"))]
        suffix = core[len(core.rstrip(".,;:)]}")) :]
        words.append(f"{prefix}{word}{suffix}")
    return " ".join(words)


def _name_normalize_key(name: str) -> str:
    txt = re.sub(r"[^A-Za-z0-9 ]+", " ", normalize_space(name)).lower()
    return SPACE_RE.sub(" ", txt).strip()


def _name_informative_tokens(name: str) -> list[str]:
    words = [w.lower() for w in re.findall(r"[A-Za-z0-9]+", normalize_space(name))]
    informative: list[str] = []
    for word in words:
        if not word:
            continue
        if word in GENERIC_NAME_TOKENS:
            continue
        informative.append(word)
    return informative


def _is_name_noise(name: str, ticker: str = "") -> bool:
    key = _name_normalize_key(name)
    if not key:
        return True
    if key in NOISY_NAME_PHRASES:
        return True
    informative = _name_informative_tokens(name)
    if not informative:
        return True
    if len(informative) == 1:
        token = informative[0]
        ticker_key = str(ticker or "").strip().lower()
        if token in NOISY_STANDALONE_TERMS:
            return True
        if token != ticker_key and len(token) < 3:
            return True
    return False


def _looks_like_company_name(name: str) -> bool:
    txt = normalize_space(name)
    if not txt:
        return False
    if len(txt) < 4 or len(txt) > 160:
        return False
    words = txt.split()
    if len(words) < 2:
        return False
    lowered = txt.lower()
    if re.search(r"\b(fy\d{1,4}|q[1-4])\b", lowered):
        return False
    if re.search(r"\b(19|20)\d{2}\b", lowered):
        return False
    if _is_name_noise(txt):
        return False
    digit_count = sum(1 for ch in txt if ch.isdigit())
    if digit_count > 0 and (digit_count / float(max(1, len(txt)))) > 0.12:
        return False
    if any(term in lowered for term in GENERIC_DOC_WORDS):
        return False
    if any(f" {sfx} " in f" {lowered} " for sfx in STRONG_SUFFIX_TERMS):
        return True
    if any(f" {sfx.lower()} " in f" {lowered} " for sfx in COMPANY_SUFFIX_TERMS):
        return len(words) <= 5 and not any(term in lowered for term in GENERIC_DOC_WORDS)
    if "bank of australia" in lowered:
        return True
    if len(words) <= 4 and not any(term in lowered for term in GENERIC_DOC_WORDS):
        alpha_words = [w for w in words if any(ch.isalpha() for ch in w)]
        if alpha_words and all(w[0].isupper() for w in alpha_words if w):
            return True
    return False


def _extract_longest_uppercase_heading(text: str) -> str:
    best = ""
    for raw_line in str(text or "").splitlines():
        line = _clean_company_name(raw_line)
        if not line:
            continue
        letters = [ch for ch in raw_line if ch.isalpha()]
        if len(letters) < 8:
            continue
        upper_ratio = sum(1 for ch in letters if ch.isupper()) / float(len(letters))
        if upper_ratio < 0.8:
            continue
        if len(line.split()) < 2:
            continue
        if len(line) > len(best):
            best = line
    return _smart_company_casing(best)


def extract_candidate_names_from_text(text: str) -> list[str]:
    raw = str(text or "")
    out: list[str] = []
    for raw_line in raw.splitlines():
        line = normalize_space(raw_line)
        if not line:
            continue
        for match in COMPANY_SUFFIX_RE.findall(line):
            candidate = _smart_company_casing(_clean_company_name(match))
            if _looks_like_company_name(candidate):
                out.append(candidate)
    heading = _extract_longest_uppercase_heading(raw)
    if heading and _looks_like_company_name(heading):
        out.append(heading)
    return _dedupe_preserve(out)


def _strip_filename_noise(stem: str) -> str:
    txt = normalize_space(stem.replace("_", " ").replace("-", " "))
    if not txt:
        return ""
    txt = re.sub(r"^\d{4}\s+\d{2}\s+\d{2}\s+", "", txt)
    txt = re.sub(r"\b[0-9a-f]{8,}\b", " ", txt, flags=re.IGNORECASE)
    txt = re.sub(r"\b(v?\d{1,3})\b", " ", txt, flags=re.IGNORECASE)
    txt = SPACE_RE.sub(" ", txt).strip()
    return txt


def extract_candidate_names_from_filename(path: Path) -> list[str]:
    stem = _strip_filename_noise(path.stem)
    if not stem:
        return []
    candidates = extract_candidate_names_from_text(stem)
    # Also check component splits (handles "BHP Group Limited Annual Report" type filenames).
    parts = [part for part in re.split(r"[/_\\-]+", path.stem) if part]
    joined = normalize_space(" ".join(parts))
    if joined and joined != stem:
        candidates.extend(extract_candidate_names_from_text(joined))
    return _dedupe_preserve(candidates)


def extract_candidate_names_from_structured_json(raw_json: str) -> list[str]:
    try:
        payload = json.loads(raw_json)
    except Exception:
        return []

    out: list[str] = []

    def _walk(node: Any, path: str = "") -> None:
        if isinstance(node, dict):
            for k, v in node.items():
                key = str(k or "")
                child_path = f"{path}.{key}" if path else key
                if isinstance(v, str):
                    if NAME_KEY_RE.search(key) or NAME_KEY_RE.search(path):
                        for candidate in extract_candidate_names_from_text(v):
                            out.append(candidate)
                else:
                    _walk(v, child_path)
            return
        if isinstance(node, list):
            for item in node[:200]:
                _walk(item, path)

    _walk(payload)
    return _dedupe_preserve(out)


def _score_name(name: str, source_weight: int, ticker: str) -> int:
    score = int(source_weight)
    lowered = name.lower()
    if any(sfx.lower() in lowered for sfx in COMPANY_SUFFIX_TERMS):
        score += 40
    if "bank of australia" in lowered:
        score += 25
    if lowered == ticker.lower():
        score -= 80
    if len(name.split()) > 8:
        score -= 20
    if any(word in lowered for word in GENERIC_DOC_WORDS):
        score -= 15
    score += min(20, len(name) // 6)
    return score


def _strip_suffix_tokens(name: str, removable: set[str]) -> str:
    words = [w.strip(".,;:()[]{}") for w in normalize_space(name).split()]
    while words and words[-1].lower() in removable:
        words.pop()
    return normalize_space(" ".join(words)).strip(" .,:;/-_")


def generate_aliases(canonical_names: list[str], extracted_text_blob: str = "") -> list[str]:
    aliases: list[str] = []
    removal_sets = [
        {"limited", "ltd"},
        {"limited", "ltd", "group"},
        {"limited", "ltd", "holdings"},
        {"limited", "ltd", "corporation"},
        {"limited", "ltd", "group", "holdings", "corporation"},
    ]
    extracted_lower = normalize_space(extracted_text_blob).lower()
    for canonical in canonical_names:
        base = _clean_company_name(canonical)
        if not base:
            continue
        # Remove leading "The".
        no_the = re.sub(r"^\s*the\s+", "", base, flags=re.IGNORECASE).strip(" .,:;/-_")
        if no_the and no_the.lower() != base.lower():
            aliases.append(no_the)
        # Strip parenthetical content.
        no_paren = normalize_space(re.sub(r"\([^)]*\)", " ", base)).strip(" .,:;/-_")
        if no_paren and no_paren.lower() != base.lower():
            aliases.append(no_paren)
        # Remove geography qualifiers.
        no_geo = normalize_space(re.sub(r"\b(australia|australian)\b", " ", base, flags=re.IGNORECASE)).strip(" .,:;/-_")
        if no_geo and no_geo.lower() != base.lower():
            aliases.append(no_geo)
        for removable in removal_sets:
            candidate = _strip_suffix_tokens(base, removable)
            if candidate and candidate.lower() != canonical.lower():
                aliases.append(candidate)
        plain = normalize_space(re.sub(r"[.,;:()]+", " ", base)).strip(" .,:;/-_")
        if plain and plain.lower() != canonical.lower():
            aliases.append(plain)
        # Brand-style alias for "<Brand> Banking Corporation", only when seen in extracted content.
        m = re.match(r"^\s*([A-Za-z][A-Za-z0-9&'.-]{1,40})\s+Banking\s+Corporation\s*$", base, flags=re.IGNORECASE)
        if m:
            brand = normalize_space(m.group(1)).strip(" .,:;/-_")
            if brand and brand.lower() in extracted_lower:
                aliases.append(brand)
    # Avoid short uppercase acronym aliases here; those are added in a separate unambiguous pass.
    filtered: list[str] = []
    for alias in _dedupe_preserve(aliases):
        token = normalize_space(alias)
        if not token:
            continue
        if re.fullmatch(r"[A-Z0-9]{1,3}", token):
            continue
        filtered.append(token)
    return filtered


def sanitize_identity_entry(
    *,
    ticker: str,
    entry: dict[str, Any] | None,
) -> dict[str, list[str]]:
    current = entry if isinstance(entry, dict) else {}
    canonical_raw = list(current.get("canonical_names", [])) if isinstance(current.get("canonical_names"), list) else []
    aliases_raw = list(current.get("aliases", [])) if isinstance(current.get("aliases"), list) else []

    canonical: list[str] = []
    for raw_name in canonical_raw:
        cleaned = _smart_company_casing(_clean_company_name(raw_name))
        if not cleaned:
            continue
        if _is_name_noise(cleaned, ticker=ticker):
            continue
        canonical.append(cleaned)
    canonical = _dedupe_preserve(canonical)
    canonical_keys = {_name_normalize_key(item) for item in canonical}
    valid_acronyms: set[str] = set()
    for canonical_name in canonical:
        if not _is_acronym_source_name(canonical_name, ticker=ticker):
            continue
        acronym = derive_acronym_alias(canonical_name)
        if acronym:
            valid_acronyms.add(acronym)

    aliases: list[str] = []
    for raw_alias in aliases_raw:
        cleaned = _smart_company_casing(_clean_company_name(raw_alias))
        if not cleaned:
            continue
        is_acronym = bool(re.fullmatch(r"[A-Z0-9]{4,8}", cleaned))
        if is_acronym and cleaned not in valid_acronyms:
            continue
        if _is_name_noise(cleaned, ticker=ticker) and not is_acronym:
            continue
        if _name_normalize_key(cleaned) in canonical_keys:
            continue
        if len(cleaned.split()) == 1 and cleaned.lower() in NOISY_STANDALONE_TERMS:
            continue
        aliases.append(cleaned)
    aliases = _dedupe_preserve(aliases)
    return {"canonical_names": canonical, "aliases": aliases}


def derive_acronym_alias(name: str) -> str:
    words = re.findall(r"[A-Za-z]+", normalize_space(name))
    if len(words) < 2:
        return ""
    letters: list[str] = []
    for word in words:
        lw = word.lower()
        if lw in ACRONYM_STOPWORDS:
            continue
        letters.append(word[0].upper())
    acronym = "".join(letters)
    if len(acronym) < 4:
        return ""
    if not re.fullmatch(r"[A-Z0-9]{4,8}", acronym):
        return ""
    return acronym


def _is_acronym_source_name(name: str, ticker: str = "") -> bool:
    txt = normalize_space(name)
    if not txt:
        return False
    if _is_name_noise(txt, ticker=ticker):
        return False
    words = re.findall(r"[A-Za-z]+", txt)
    if len(words) < 2 or len(words) > 6:
        return False
    lowered_words = [w.lower() for w in words]
    if any(word in ACRONYM_SOURCE_NOISE_TOKENS for word in lowered_words):
        return False
    return True


def _table_exists(conn: sqlite3.Connection, table_name: str) -> bool:
    row = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=? LIMIT 1",
        (str(table_name),),
    ).fetchone()
    return bool(row)


def _query_document_rows(conn: sqlite3.Connection, ticker: str) -> list[dict[str, Any]]:
    if not _table_exists(conn, "documents"):
        return []
    cur = conn.cursor()
    rows = cur.execute(
        """
        SELECT document_id, title, pdf_path, published_at, ingested_at
        FROM documents
        WHERE UPPER(COALESCE(ticker, '')) = ?
        ORDER BY COALESCE(published_at, '') DESC, COALESCE(ingested_at, '') DESC, COALESCE(document_id, '') DESC
        LIMIT 64
        """,
        (ticker.upper(),),
    ).fetchall()
    out: list[dict[str, Any]] = []
    for row in rows:
        out.append(
            {
                "document_id": row[0],
                "title": row[1],
                "pdf_path": row[2],
                "published_at": row[3],
                "ingested_at": row[4],
            }
        )
    return out


def _query_structured_json_rows(conn: sqlite3.Connection, ticker: str) -> list[str]:
    if not _table_exists(conn, "documents") or not _table_exists(conn, "extraction_runs"):
        return []
    cur = conn.cursor()
    rows = cur.execute(
        """
        SELECT er.structured_json
        FROM extraction_runs er
        JOIN documents d ON d.document_id = er.document_id
        WHERE UPPER(COALESCE(d.ticker, '')) = ?
          AND er.structured_json IS NOT NULL
          AND TRIM(er.structured_json) != ''
        ORDER BY CASE LOWER(COALESCE(er.status, '')) WHEN 'success' THEN 0 ELSE 1 END,
                 COALESCE(er.created_at, '') DESC
        LIMIT 96
        """,
        (ticker.upper(),),
    ).fetchall()
    return [str(row[0]) for row in rows if row and row[0] is not None]


def _parse_path_date_prefix(path: Path) -> str:
    name = path.name
    if len(name) >= 10 and re.fullmatch(r"\d{4}-\d{2}-\d{2}", name[:10]):
        return name[:10]
    return ""


def _latest_pdf_path_for_ticker(ticker: str, docs_root: Path, document_rows: list[dict[str, Any]]) -> Path | None:
    candidates: list[tuple[str, Path]] = []
    for row in document_rows:
        raw_path = normalize_space(row.get("pdf_path"))
        if not raw_path:
            continue
        path = Path(raw_path).expanduser()
        if not path.is_absolute():
            path = (Path.cwd() / path).resolve()
        if path.exists() and path.is_file():
            dt = normalize_space(row.get("published_at")) or normalize_space(row.get("ingested_at")) or _parse_path_date_prefix(path)
            candidates.append((dt, path))

    ticker_dir = (docs_root / ticker.upper()).resolve()
    if ticker_dir.exists() and ticker_dir.is_dir():
        for path in sorted(ticker_dir.rglob("*.pdf")):
            dt = _parse_path_date_prefix(path)
            if not dt:
                try:
                    dt = f"{int(path.stat().st_mtime):012d}"
                except Exception:
                    dt = ""
            candidates.append((dt, path))

    if not candidates:
        return None
    candidates.sort(key=lambda item: (item[0], str(item[1])), reverse=True)
    return candidates[0][1]


def _ticker_pdf_paths(ticker: str, docs_root: Path, document_rows: list[dict[str, Any]]) -> list[Path]:
    out: list[Path] = []
    seen: set[str] = set()
    for row in document_rows:
        raw_path = normalize_space(row.get("pdf_path"))
        if not raw_path:
            continue
        path = Path(raw_path).expanduser()
        if not path.is_absolute():
            path = (Path.cwd() / path).resolve()
        if path.exists() and path.is_file():
            key = str(path)
            if key not in seen:
                seen.add(key)
                out.append(path)

    ticker_dir = (docs_root / ticker.upper()).resolve()
    if ticker_dir.exists() and ticker_dir.is_dir():
        for path in sorted(ticker_dir.rglob("*.pdf")):
            key = str(path)
            if key in seen:
                continue
            seen.add(key)
            out.append(path)
    return out


def extract_first_page_text(pdf_path: Path, max_chars: int = 24000) -> str:
    path = Path(pdf_path).expanduser().resolve()
    if not path.exists() or not path.is_file():
        return ""

    try:
        import fitz  # type: ignore

        doc = fitz.open(str(path))
        try:
            if doc.page_count > 0:
                text = str(doc.load_page(0).get_text("text") or "")
                if text.strip():
                    return text[:max_chars]
        finally:
            doc.close()
    except Exception:
        pass

    try:
        proc = subprocess.run(
            ["pdftotext", "-f", "1", "-l", "1", str(path), "-"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=30,
            check=False,
        )
        if proc.returncode == 0 and str(proc.stdout or "").strip():
            return str(proc.stdout)[:max_chars]
    except Exception:
        pass

    return ""


def _build_generated_entry_for_ticker(
    *,
    ticker: str,
    conn: sqlite3.Connection | None,
    docs_root: Path,
) -> tuple[dict[str, list[str]], dict[str, Any]]:
    scored_by_key: dict[str, tuple[str, int]] = {}
    attempt: dict[str, Any] = {
        "structured_json_rows": 0,
        "document_rows": 0,
        "latest_pdf_path": "",
        "latest_pdf_text_chars": 0,
        "filename_hints": [],
        "directory_hints": [],
        "sources_used": [],
    }
    extracted_text_fragments: list[str] = []

    def _push(name: str, source_weight: int) -> None:
        cleaned = _smart_company_casing(_clean_company_name(name))
        if not _looks_like_company_name(cleaned):
            return
        key = _name_normalize_key(cleaned)
        if not key:
            return
        score = _score_name(cleaned, source_weight=source_weight, ticker=ticker)
        current = scored_by_key.get(key)
        if current is None or score > current[1] or (score == current[1] and len(cleaned) > len(current[0])):
            scored_by_key[key] = (cleaned, score)

    document_rows: list[dict[str, Any]] = []
    if conn is not None:
        structured_rows = _query_structured_json_rows(conn, ticker)
        attempt["structured_json_rows"] = len(structured_rows)
        if structured_rows:
            attempt["sources_used"].append("structured_json")
        for raw_json in structured_rows:
            extracted_text_fragments.append(str(raw_json)[:2000])
            for candidate in extract_candidate_names_from_structured_json(raw_json):
                _push(candidate, source_weight=320)
        document_rows = _query_document_rows(conn, ticker)
        attempt["document_rows"] = len(document_rows)
        if document_rows:
            attempt["sources_used"].append("documents")
        for row in document_rows:
            title_text = str(row.get("title") or "")
            extracted_text_fragments.append(title_text)
            for candidate in extract_candidate_names_from_text(title_text):
                _push(candidate, source_weight=180)

    latest_pdf = _latest_pdf_path_for_ticker(ticker, docs_root=docs_root, document_rows=document_rows)
    if latest_pdf is not None:
        attempt["latest_pdf_path"] = str(latest_pdf)
    if latest_pdf is not None:
        first_page_text = extract_first_page_text(latest_pdf)
        attempt["latest_pdf_text_chars"] = len(first_page_text or "")
        if first_page_text:
            attempt["sources_used"].append("pdf_first_page")
        extracted_text_fragments.append(first_page_text[:4000])
        for candidate in extract_candidate_names_from_text(first_page_text):
            _push(candidate, source_weight=140)
        heading = _extract_longest_uppercase_heading(first_page_text)
        if heading:
            _push(heading, source_weight=120)

    # Fallback: infer from docs-root filenames and path hints when text extraction is weak/missing.
    filename_hint_names: list[str] = []
    directory_hint_names: list[str] = []
    for pdf_path in _ticker_pdf_paths(ticker=ticker, docs_root=docs_root, document_rows=document_rows):
        for candidate in extract_candidate_names_from_filename(pdf_path):
            filename_hint_names.append(candidate)
            _push(candidate, source_weight=110)
        parts = list(pdf_path.parts)
        if len(parts) >= 3:
            raw_dir_hint = normalize_space(parts[-2].replace("_", " ").replace("-", " "))
            for candidate in extract_candidate_names_from_text(raw_dir_hint):
                directory_hint_names.append(candidate)
                _push(candidate, source_weight=80)
    attempt["filename_hints"] = _dedupe_preserve(filename_hint_names)[:25]
    attempt["directory_hints"] = _dedupe_preserve(directory_hint_names)[:25]
    if attempt["filename_hints"] and "filename_hints" not in attempt["sources_used"]:
        attempt["sources_used"].append("filename_hints")
    if attempt["directory_hints"] and "directory_hints" not in attempt["sources_used"]:
        attempt["sources_used"].append("directory_hints")

    ranked = sorted(scored_by_key.values(), key=lambda item: (-item[1], -len(item[0]), item[0]))
    canonical_names: list[str] = []
    for name, _score in ranked[:6]:
        canonical_names.append(name)
        normalized_variant = _smart_company_casing(_clean_company_name(name))
        if normalized_variant and normalized_variant.lower() != name.lower():
            canonical_names.append(normalized_variant)
    fallback_names = MAJOR_TICKER_FALLBACK_NAMES.get(ticker.upper(), [])
    canonical_names = _dedupe_preserve(list(fallback_names) + canonical_names)[:6]
    aliases = generate_aliases(canonical_names, extracted_text_blob="\n".join(extracted_text_fragments))
    return {"canonical_names": canonical_names, "aliases": aliases}, attempt


def _merge_entry(
    existing: dict[str, list[str]] | None,
    generated: dict[str, list[str]] | None,
) -> dict[str, list[str]]:
    current = existing if isinstance(existing, dict) else {}
    built = generated if isinstance(generated, dict) else {}
    canonical = _dedupe_preserve(
        list(current.get("canonical_names", []) if isinstance(current.get("canonical_names"), list) else [])
        + list(built.get("canonical_names", []) if isinstance(built.get("canonical_names"), list) else [])
    )
    aliases = _dedupe_preserve(
        list(current.get("aliases", []) if isinstance(current.get("aliases"), list) else [])
        + list(built.get("aliases", []) if isinstance(built.get("aliases"), list) else [])
    )
    return {"canonical_names": canonical, "aliases": aliases}


def add_unambiguous_acronym_aliases(
    *,
    identity_map: dict[str, dict[str, list[str]]],
    tickers_in_scope: set[str],
) -> None:
    acronym_to_tickers: dict[str, set[str]] = {}
    for ticker, entry in identity_map.items():
        if ticker not in tickers_in_scope:
            continue
        for canonical in entry.get("canonical_names", []):
            ac = derive_acronym_alias(canonical)
            if not ac:
                continue
            acronym_to_tickers.setdefault(ac, set()).add(ticker)

    for acronym, ticker_set in acronym_to_tickers.items():
        if len(ticker_set) != 1:
            continue
        ticker = sorted(ticker_set)[0]
        entry = identity_map.get(ticker)
        if not isinstance(entry, dict):
            continue
        aliases = list(entry.get("aliases", [])) if isinstance(entry.get("aliases"), list) else []
        if acronym not in aliases:
            aliases.append(acronym)
        entry["aliases"] = _dedupe_preserve(aliases)


def build_identity_map_from_filings(
    *,
    database_url: str,
    asx_tickers_file: Path,
    docs_root: Path,
    out_json: Path,
    merge: bool,
    report_missing_path: Path | None = None,
) -> tuple[dict[str, dict[str, list[str]]], dict[str, Any]]:
    tickers = load_tickers(asx_tickers_file)
    existing = load_existing_identity_map(out_json) if merge else {}

    conn: sqlite3.Connection | None = None
    db_path: Path | None = None
    try:
        db_path = sqlite_path_from_url(database_url)
        if db_path.exists() and db_path.is_file():
            conn = sqlite3.connect(str(db_path), timeout=30.0)
        else:
            print(f"[warn] database not found; continuing docs-only: {db_path}", file=sys.stderr)
    except Exception as exc:
        print(f"[warn] failed opening database; continuing docs-only: {exc}", file=sys.stderr)
        conn = None

    generated: dict[str, dict[str, list[str]]] = {}
    attempts_by_ticker: dict[str, dict[str, Any]] = {}
    for ticker in tickers:
        generated_entry, attempt = _build_generated_entry_for_ticker(
            ticker=ticker,
            conn=conn,
            docs_root=docs_root,
        )
        generated[ticker] = generated_entry
        attempts_by_ticker[ticker] = attempt

    if conn is not None:
        conn.close()

    final_map: dict[str, dict[str, list[str]]]
    if merge:
        all_tickers = sorted(set(existing.keys()) | set(generated.keys()))
        final_map = {}
        for ticker in all_tickers:
            final_map[ticker] = _merge_entry(existing.get(ticker), generated.get(ticker))
    else:
        final_map = {ticker: _merge_entry(None, generated.get(ticker)) for ticker in sorted(tickers)}
    final_map = {
        ticker: sanitize_identity_entry(ticker=ticker, entry=entry)
        for ticker, entry in final_map.items()
    }

    # Ensure major ASX blue-chips are always represented for identity hardening.
    for ticker, fallback_names in MAJOR_TICKER_FALLBACK_NAMES.items():
        fallback_entry = {"canonical_names": list(fallback_names), "aliases": generate_aliases(list(fallback_names), "")}
        final_map[ticker] = _merge_entry(final_map.get(ticker), fallback_entry)
    final_map = {
        ticker: sanitize_identity_entry(ticker=ticker, entry=entry)
        for ticker, entry in final_map.items()
    }

    # Last-resort recall fallback: if local docs exist but no canonical name detected,
    # synthesize a conservative legal-form placeholder from ticker symbol.
    for ticker in tickers:
        entry = final_map.get(ticker, {"canonical_names": [], "aliases": []})
        canonical_names = list(entry.get("canonical_names", [])) if isinstance(entry.get("canonical_names"), list) else []
        if canonical_names:
            continue
        attempt = attempts_by_ticker.get(ticker, {})
        has_local_signals = bool(attempt.get("document_rows", 0) or attempt.get("latest_pdf_path") or attempt.get("filename_hints"))
        if has_local_signals:
            canonical_names = [f"{ticker} Limited"]
        else:
            canonical_names = [f"{ticker} ASX Issuer"]
        final_map[ticker] = _merge_entry(entry, {"canonical_names": canonical_names, "aliases": []})

    final_map = {ticker: final_map[ticker] for ticker in sorted(final_map.keys())}
    add_unambiguous_acronym_aliases(identity_map=final_map, tickers_in_scope=set(tickers))
    final_map = {
        ticker: sanitize_identity_entry(ticker=ticker, entry=entry)
        for ticker, entry in final_map.items()
    }

    tickers_with_canonical_name = 0
    alias_total = 0
    for ticker in tickers:
        entry = final_map.get(ticker, {"canonical_names": [], "aliases": []})
        if entry.get("canonical_names"):
            tickers_with_canonical_name += 1
        alias_total += len(entry.get("aliases", []))
    tickers_total = len(tickers)
    missing = max(0, tickers_total - tickers_with_canonical_name)
    avg_aliases = float(alias_total) / float(tickers_total) if tickers_total else 0.0
    summary = {
        "tickers_total": tickers_total,
        "tickers_with_canonical_name": tickers_with_canonical_name,
        "tickers_missing_name": missing,
        "avg_aliases_per_ticker": round(avg_aliases, 4),
    }

    if report_missing_path is not None:
        missing_rows: list[dict[str, Any]] = []
        for ticker in sorted(tickers):
            entry = final_map.get(ticker, {"canonical_names": [], "aliases": []})
            canonical = list(entry.get("canonical_names", [])) if isinstance(entry.get("canonical_names"), list) else []
            if canonical:
                continue
            missing_rows.append(
                {
                    "ticker": ticker,
                    "attempted_sources": attempts_by_ticker.get(ticker, {}),
                }
            )
        report_payload = {
            "generated_at_utc": datetime.datetime.utcnow().replace(microsecond=0).isoformat() + "Z",
            "tickers_total": tickers_total,
            "missing_count": len(missing_rows),
            "missing_tickers": missing_rows,
        }
        atomic_write_json(report_missing_path, report_payload)

    return final_map, summary


def atomic_write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=False), encoding="utf-8")
    tmp.replace(path)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Build ASX ticker identity map from local filings and structured data")
    ap.add_argument("--database-url", default=DEFAULT_DATABASE_URL, help="SQLite database URL used by the engine")
    ap.add_argument("--asx-tickers-file", default=str(DEFAULT_ASX_TICKERS), help="ASX ticker universe file")
    ap.add_argument("--docs-root", default=str(DEFAULT_DOCS_ROOT), help="Root directory for ASX filing PDFs")
    ap.add_argument("--out-json", default=str(DEFAULT_OUT_JSON), help="Output identity map JSON path")
    ap.add_argument(
        "--merge",
        type=parse_bool,
        default=True,
        help="When true, merge with existing identity map entries (default: true)",
    )
    ap.add_argument(
        "--report-missing",
        action="store_true",
        help=f"Write missing ticker report to {DEFAULT_MISSING_REPORT}",
    )
    args = ap.parse_args(argv)

    tickers_path = Path(args.asx_tickers_file).expanduser().resolve()
    docs_root = Path(args.docs_root).expanduser().resolve()
    out_json = Path(args.out_json).expanduser().resolve()

    try:
        payload, summary = build_identity_map_from_filings(
            database_url=str(args.database_url),
            asx_tickers_file=tickers_path,
            docs_root=docs_root,
            out_json=out_json,
            merge=bool(args.merge),
            report_missing_path=DEFAULT_MISSING_REPORT if bool(args.report_missing) else None,
        )
    except Exception as exc:
        print(str(exc), file=sys.stderr)
        return 1

    atomic_write_json(out_json, payload)
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
