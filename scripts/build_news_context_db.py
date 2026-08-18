#!/usr/bin/env python3
"""
Experimental news corpus builder for qualitative context retrieval.

This script is intentionally isolated from the filing metric extraction path.
It ingests a news dataset, normalizes metadata, applies quality/duplicate gates,
embeds chunks, and stores an independent news DB artifact.
"""

import argparse
import datetime
import difflib
import hashlib
import json
import os
import re
import sqlite3
import shutil
import sys
import time
import tempfile
from dataclasses import asdict, dataclass, replace
from pathlib import Path
from typing import Any, Dict, Iterable, Iterator, List, Optional, Sequence, Set, Tuple
from urllib.parse import urlparse

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))
import build_qualitative_context_db as ctx  # noqa: E402
from health_guard import assert_healthy, get_overall_status, load_health_snapshot  # noqa: E402
from news_pipeline.cli_common import DEFAULT_NEWS_CONTEXT_DB, resolve_path  # noqa: E402
from news_pipeline.entity_linker import EntityLinker  # noqa: E402
from news_pipeline.relevance import choose_primary_ticker, infer_ticker_relevance_from_text, serialize_ticker_relevance  # noqa: E402


DEFAULT_DATASET_ID = "Brianferrell787/financial-news-multisource"
DEFAULT_ASX_ALLOWLIST_RELATIVE = "financial-engine_v2/data/raw/asx_ticker_universe.txt"


def serialize_ticker_blob(values: Sequence[str]) -> str:
    serialize = getattr(ctx, "serialize_ticker_blob", None)
    if callable(serialize):
        return serialize(values)
    fallback = getattr(ctx, "serialize_tickers", None)
    if callable(fallback):
        return fallback(values)
    raise AttributeError(
        "build_qualitative_context_db is missing ticker serialization helpers "
        "(expected serialize_ticker_blob or serialize_tickers)"
    )

COMPLIANCE_NOTICE = (
    "Compliance notice: This dataset is gated on Hugging Face with license='other'. "
    "The dataset card states that each article retains the original publisher's copyright "
    "and terms (for example Reuters/CNBC/Investing.com/Yahoo). Treat this pipeline as "
    "research-only by default unless legal review explicitly approves your production use."
)

WORD_RE = re.compile(r"[A-Za-z]+")
TICKER_PATTERNS = [
    re.compile(r"\$([A-Z]{1,6})\b"),
    re.compile(r"\b(?:NYSE|NASDAQ|ASX|LSE|TSX|HKEX|TSE)\s*[:\-]\s*([A-Z]{1,6})\b"),
    re.compile(r"(?<![A-Za-z0-9])([A-Z]{1,6})\.AX(?![A-Za-z0-9])"),
]
TICKER_STOPWORDS = {
    "CEO",
    "CFO",
    "EPS",
    "USD",
    "GDP",
    "ETF",
    "IPO",
    "Q1",
    "Q2",
    "Q3",
    "Q4",
}
EN_STOPWORDS = {
    "a",
    "an",
    "and",
    "are",
    "as",
    "at",
    "be",
    "by",
    "for",
    "from",
    "has",
    "in",
    "is",
    "it",
    "of",
    "on",
    "that",
    "the",
    "to",
    "was",
    "were",
    "will",
    "with",
}
ALLOWLIST_TOKEN_RE = re.compile(r"[A-Za-z0-9.\-]{1,12}")
ASX_TICKER_TOKEN_RE = re.compile(r"(?<![A-Za-z0-9])([A-Z][A-Z0-9]{1,11})(?:\.AX)?(?![A-Za-z0-9])")
ASX_HEADLINE_PRIORITY_PATTERNS = [
    re.compile(r"\bASX\b", re.IGNORECASE),
    re.compile(r"\bASX:", re.IGNORECASE),
    re.compile(r"\.AX\b"),
    re.compile(r"\bshares\b", re.IGNORECASE),
    re.compile(r"\bearnings\b", re.IGNORECASE),
    re.compile(r"\bdividend\b", re.IGNORECASE),
    re.compile(r"\bguidance\b", re.IGNORECASE),
]
COMPANY_NAME_STOPWORDS = {
    "limited",
    "ltd",
    "inc",
    "corp",
    "corporation",
    "plc",
    "group",
    "holdings",
    "holding",
    "pty",
    "company",
    "co",
}


@dataclass
class NormalizedNewsRecord:
    record_id: str
    source: str
    published_at: str
    doc_date: str
    title: str
    body: str
    ticker: str
    topic: str
    url: str


def normalize_space(value: Any) -> str:
    txt = str(value or "").replace("\r", " ").replace("\n", " ")
    txt = re.sub(r"\s+", " ", txt).strip()
    return txt


def normalize_text_for_dedupe(value: str) -> str:
    txt = normalize_space(value).lower()
    txt = re.sub(r"[^a-z0-9 ]+", " ", txt)
    txt = re.sub(r"\s+", " ", txt).strip()
    return txt


def normalize_url(value: Any) -> str:
    raw = str(value or "").strip()
    if not raw:
        return ""
    # Keep URL normalization conservative.
    raw = raw.replace(" ", "")
    raw = raw.rstrip("/")
    return raw


def parse_extra_fields(value: Any) -> Dict[str, Any]:
    if isinstance(value, dict):
        return value
    if isinstance(value, str):
        text = value.strip()
        if not text:
            return {}
        try:
            parsed = json.loads(text)
            if isinstance(parsed, dict):
                return parsed
        except Exception:
            return {}
    return {}


def parse_domain(value: Any) -> str:
    raw = normalize_space(value).strip().lower()
    if not raw:
        return ""
    candidate = raw
    if "://" not in candidate and not candidate.startswith("//"):
        candidate = "https://" + candidate
    try:
        host = str(urlparse(candidate).netloc or "").strip().lower()
    except Exception:
        host = ""
    if not host:
        host = raw.split("/")[0].strip().lower()
    if host.startswith("www."):
        host = host[4:]
    return host


def asx_headline_priority_score(title: Any) -> int:
    text = normalize_space(title)
    if not text:
        return 0
    return sum(1 for pat in ASX_HEADLINE_PRIORITY_PATTERNS if pat.search(text))


def normalize_company_name_for_match(value: Any) -> str:
    text = normalize_space(value).lower()
    if not text:
        return ""
    text = re.sub(r"[^a-z0-9 ]+", " ", text)
    tokens = [tok for tok in text.split() if tok and tok not in COMPANY_NAME_STOPWORDS]
    if not tokens:
        return ""
    return " ".join(tokens)


def default_asx_allowlist_path() -> Path:
    # Resolve relative to repo root (this script lives under ./scripts).
    return Path(__file__).resolve().parents[1] / DEFAULT_ASX_ALLOWLIST_RELATIVE


def _add_allowlist_symbol(candidate: Any, out: Set[str]) -> None:
    text = str(candidate or "").strip().strip("\"'")
    if not text:
        return
    sym = ctx.normalize_ticker_symbol(text)
    if not sym:
        return
    if not re.search(r"[A-Z]", sym):
        return
    out.add(sym)


def _collect_allowlist_tokens(value: Any, out: Set[str]) -> None:
    if value is None:
        return
    if isinstance(value, dict):
        for v in value.values():
            _collect_allowlist_tokens(v, out)
        return
    if isinstance(value, (list, tuple, set)):
        for item in value:
            _collect_allowlist_tokens(item, out)
        return

    text = str(value).strip()
    if not text:
        return
    if "#" in text:
        text = text.split("#", 1)[0].strip()
    if not text:
        return
    cells = [cell.strip() for cell in re.split(r"[|,;\t]+", text) if str(cell or "").strip()]
    if not cells:
        return
    if len(cells) == 1:
        cell = cells[0]
        if " " in cell and re.fullmatch(r"[A-Z0-9.\- ]+", cell):
            for part in cell.split():
                _add_allowlist_symbol(part, out)
            return
        _add_allowlist_symbol(cell, out)
        return
    for cell in cells:
        _add_allowlist_symbol(cell, out)


def load_ticker_allowlist(path: Path) -> Set[str]:
    if not path.exists():
        raise RuntimeError(f"Ticker allowlist path does not exist: {path}")
    out: Set[str] = set()
    suffix = path.suffix.lower()

    if suffix == ".json":
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
            _collect_allowlist_tokens(payload, out)
            return out
        except Exception:
            pass
    if suffix == ".jsonl":
        for row in iter_jsonl(path):
            _collect_allowlist_tokens(row, out)
        return out

    with path.open("r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            _collect_allowlist_tokens(line, out)
    return out


def first_non_empty(*values: Any) -> str:
    for value in values:
        if value is None:
            continue
        if isinstance(value, str):
            txt = value.strip()
            if txt:
                return txt
        else:
            txt = normalize_space(value)
            if txt:
                return txt
    return ""


def normalize_datetime(value: Any) -> str:
    raw = str(value or "").strip()
    if not raw:
        return ""
    raw = raw.replace("/", "-")
    if raw.endswith("Z"):
        raw = raw[:-1] + "+00:00"
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", raw):
        return raw

    candidates = [raw]
    if " " in raw and "T" not in raw:
        candidates.append(raw.replace(" ", "T"))
    for candidate in candidates:
        try:
            dt = datetime.datetime.fromisoformat(candidate)
            if dt.tzinfo is not None and dt.utcoffset() == datetime.timedelta(0):
                return dt.isoformat().replace("+00:00", "Z")
            return dt.isoformat()
        except ValueError:
            pass
    return ""


def iso_date(value: str) -> str:
    txt = str(value or "").strip()
    if not txt:
        return ""
    try:
        if "T" in txt:
            dt = datetime.datetime.fromisoformat(txt.replace("Z", "+00:00"))
            return dt.date().isoformat()
        return datetime.date.fromisoformat(txt).isoformat()
    except ValueError:
        return ""


def normalize_topic(value: Any) -> str:
    if isinstance(value, list):
        entries = [normalize_space(v) for v in value if normalize_space(v)]
        return ", ".join(entries[:3])
    return normalize_space(value)


def split_title_body(raw_text: str, explicit_title: str) -> Tuple[str, str]:
    text = str(raw_text or "").replace("\r", "\n")
    text = re.sub(r"\n{3,}", "\n\n", text).strip()
    title = normalize_space(explicit_title)
    if not text:
        return title, ""

    if not title:
        lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
        if lines:
            first = lines[0]
            if 20 <= len(first) <= 220:
                title = first
                text = "\n".join(lines[1:]).strip()
            else:
                title = first[:220]
                text = "\n".join(lines[1:]).strip()

    body = text
    if title:
        lower_title = normalize_text_for_dedupe(title)
        lower_body = normalize_text_for_dedupe(body[: max(500, len(title) * 2)])
        if lower_title and lower_title in lower_body:
            body = body.replace(title, "", 1).strip()

    body = normalize_space(body)
    title = normalize_space(title)
    return title, body


def looks_english(text: str) -> bool:
    if not text:
        return False
    ascii_ratio = sum(1 for ch in text if ch.isascii()) / max(1, len(text))
    if ascii_ratio < 0.85:
        return False
    words = [w.lower() for w in WORD_RE.findall(text)]
    if len(words) < 25:
        return True
    stop_hits = sum(1 for w in words[:200] if w in EN_STOPWORDS)
    return stop_hits >= 5


def extract_tickers_from_value(value: Any) -> List[str]:
    if value is None:
        return []
    raw_values: List[str] = []
    if isinstance(value, list):
        raw_values = [str(v) for v in value]
    elif isinstance(value, dict):
        raw_values = [str(v) for v in value.values()]
    else:
        txt = str(value).strip()
        if not txt:
            raw_values = []
        else:
            if txt.startswith("[") and txt.endswith("]"):
                try:
                    parsed = json.loads(txt)
                    if isinstance(parsed, list):
                        raw_values = [str(v) for v in parsed]
                    else:
                        raw_values = [txt]
                except Exception:
                    raw_values = [txt]
            else:
                raw_values = re.split(r"[,\s;/|]+", txt)

    out: List[str] = []
    for entry in raw_values:
        sym = ctx.normalize_ticker_symbol(entry)
        if not sym:
            continue
        if sym in TICKER_STOPWORDS:
            continue
        out.append(sym)
    return out


def infer_tickers(
    title: str,
    body: str,
    existing: Sequence[str],
    allowlist: Optional[Set[str]] = None,
    ticker_name_linker: Optional[EntityLinker] = None,
) -> str:
    out = list(existing)
    merged_text = f"{title} {body[:2000]}"
    for pat in TICKER_PATTERNS:
        for match in pat.findall(merged_text):
            sym = ctx.normalize_ticker_symbol(match)
            if not sym or sym in TICKER_STOPWORDS:
                continue
            out.append(sym)
    if allowlist:
        for match in ASX_TICKER_TOKEN_RE.findall(merged_text):
            sym = ctx.normalize_ticker_symbol(match)
            if not sym or sym in TICKER_STOPWORDS:
                continue
            if sym in allowlist:
                out.append(sym)
    out.extend(infer_company_name_tickers(title=title, body=body, ticker_name_linker=ticker_name_linker))
    return serialize_ticker_blob(out)


def normalize_news_row(
    row: Dict[str, Any],
    min_text_chars: int,
    keep_non_english: bool,
    ticker_allowlist: Optional[Set[str]] = None,
    ticker_name_linker: Optional[EntityLinker] = None,
    drop_ticker_nonmatching_rows: bool = False,
    skip_ticker_inference: bool = False,
) -> Tuple[Optional[NormalizedNewsRecord], str]:
    extra = parse_extra_fields(row.get("extra_fields"))
    raw_text = first_non_empty(
        row.get("text"),
        row.get("body"),
        row.get("content"),
        extra.get("text"),
        extra.get("body"),
        extra.get("content"),
    )
    explicit_title = first_non_empty(
        row.get("title"),
        row.get("headline"),
        extra.get("title"),
        extra.get("headline"),
    )
    title, body = split_title_body(raw_text, explicit_title)
    if not body or len(body) < min_text_chars:
        return None, "short_text"
    if not keep_non_english and not looks_english(body):
        return None, "non_english"

    published_at = normalize_datetime(
        first_non_empty(
            row.get("published_at"),
            row.get("publish_date"),
            row.get("date"),
            extra.get("published_at"),
            extra.get("publish_date"),
            extra.get("date"),
        )
    )
    doc_date = iso_date(published_at)
    source = normalize_space(
        first_non_empty(
            row.get("source"),
            row.get("publisher"),
            extra.get("source"),
            extra.get("publisher"),
            extra.get("publisher_name"),
            extra.get("site_name"),
            "unknown",
        )
    )
    topic = normalize_topic(
        first_non_empty(
            row.get("topic"),
            row.get("category"),
            extra.get("topic"),
            extra.get("category"),
            extra.get("categories"),
        )
    )
    url = normalize_url(
        first_non_empty(
            row.get("url"),
            row.get("link"),
            extra.get("url"),
            extra.get("link"),
            extra.get("article_url"),
        )
    )
    row_id = first_non_empty(
        row.get("id"),
        row.get("_id"),
        row.get("guid"),
        extra.get("id"),
        extra.get("guid"),
        url,
    )
    if not row_id:
        row_id = hashlib.sha1(f"{title}\n{body}".encode("utf-8")).hexdigest()
    row_id = re.sub(r"[^A-Za-z0-9._\-:]+", "_", row_id)[:180]

    tickers = []
    tickers.extend(extract_tickers_from_value(row.get("ticker")))
    tickers.extend(extract_tickers_from_value(row.get("tickers")))
    tickers.extend(extract_tickers_from_value(row.get("stocks")))
    tickers.extend(extract_tickers_from_value(extra.get("ticker")))
    tickers.extend(extract_tickers_from_value(extra.get("tickers")))
    tickers.extend(extract_tickers_from_value(extra.get("stocks")))
    if skip_ticker_inference:
        ticker_blob = serialize_ticker_blob(tickers)
    else:
        ticker_blob = infer_tickers(
            title=title,
            body=body,
            existing=tickers,
            allowlist=ticker_allowlist,
            ticker_name_linker=ticker_name_linker,
        )
    if ticker_allowlist:
        inferred = ctx.parse_ticker_blob(ticker_blob)
        if inferred:
            allowed = [sym for sym in inferred if sym in ticker_allowlist]
            ticker_blob = serialize_ticker_blob(allowed)
            if not ticker_blob and drop_ticker_nonmatching_rows:
                return None, "ticker_not_allowlisted"

    return (
        NormalizedNewsRecord(
            record_id=row_id,
            source=source,
            published_at=published_at,
            doc_date=doc_date,
            title=title,
            body=body,
            ticker=ticker_blob,
            topic=topic,
            url=url,
        ),
        "ok",
    )


def iter_jsonl(
    path: Path,
    invalid_counter: Optional[Dict[str, int]] = None,
) -> Iterator[Dict[str, Any]]:
    with path.open("r", encoding="utf-8") as fh:
        for line_no, line in enumerate(fh, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                parsed = json.loads(line)
            except json.JSONDecodeError:
                if invalid_counter is not None:
                    invalid_counter["invalid_jsonl_lines"] = invalid_counter.get("invalid_jsonl_lines", 0) + 1
                print(f"[warn] invalid JSONL at {path}:{line_no}", file=sys.stderr)
                continue
            if isinstance(parsed, dict):
                yield parsed


def count_jsonl_rows(path: Path) -> int:
    count = 0
    with path.open("r", encoding="utf-8") as fh:
        for line in fh:
            if line.strip():
                count += 1
    return count


def _collect_allowlist_company_names(value: Any, out: Set[str]) -> None:
    if value is None:
        return
    if isinstance(value, dict):
        for key, nested in value.items():
            key_text = str(key or "").strip().lower()
            if any(tok in key_text for tok in ("name", "alias", "issuer", "company")):
                _collect_allowlist_company_names(nested, out)
            elif isinstance(nested, (dict, list, tuple, set)):
                _collect_allowlist_company_names(nested, out)
        return
    if isinstance(value, (list, tuple, set)):
        for item in value:
            _collect_allowlist_company_names(item, out)
        return

    text = normalize_space(value)
    if not text:
        return
    for part in re.split(r"[|,;\t]+", text):
        normalized = normalize_company_name_for_match(part)
        if not normalized:
            continue
        if re.fullmatch(r"[a-z0-9]{1,6}", normalized):
            continue
        if len(normalized) < 4:
            continue
        out.add(normalized)


def load_allowlist_company_names(path: Path) -> Set[str]:
    if not path.exists():
        raise RuntimeError(f"Ticker allowlist path does not exist: {path}")
    out: Set[str] = set()
    suffix = path.suffix.lower()

    if suffix == ".json":
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
            _collect_allowlist_company_names(payload, out)
            return out
        except Exception:
            pass
    if suffix == ".jsonl":
        for row in iter_jsonl(path):
            _collect_allowlist_company_names(row, out)
        return out

    with path.open("r", encoding="utf-8") as fh:
        for line in fh:
            _collect_allowlist_company_names(line, out)
    return out


def asx_priority_headline(row: Dict[str, Any]) -> str:
    extra = parse_extra_fields(row.get("extra_fields"))
    return first_non_empty(
        row.get("title"),
        row.get("headline"),
        extra.get("title"),
        extra.get("headline"),
    )


def iter_asx_prioritized_rows(rows: Iterable[Dict[str, Any]]) -> Iterator[Dict[str, Any]]:
    deferred: List[Dict[str, Any]] = []
    for row in rows:
        if asx_headline_priority_score(asx_priority_headline(row)) > 0:
            yield row
        else:
            deferred.append(row)
    for row in deferred:
        yield row


def row_matches_australia_country_or_au_domain(
    *,
    row: Dict[str, Any],
    normalized: NormalizedNewsRecord,
) -> bool:
    extra = parse_extra_fields(row.get("extra_fields"))
    country_candidates = [
        row.get("source_country"),
        row.get("sourcecountry"),
        row.get("sourceCountry"),
        row.get("country"),
        extra.get("source_country"),
        extra.get("sourcecountry"),
        extra.get("sourceCountry"),
        extra.get("country"),
    ]
    for value in country_candidates:
        country = normalize_space(value).lower()
        if not country:
            continue
        if country in {"australia", "au", "aus"} or "australia" in country:
            return True

    domain_candidates = [
        row.get("domain"),
        extra.get("domain"),
        row.get("source"),
        extra.get("source"),
        row.get("publisher"),
        extra.get("publisher"),
        row.get("url"),
        extra.get("url"),
        normalized.source,
        normalized.url,
    ]
    for value in domain_candidates:
        domain = parse_domain(value)
        if domain.endswith(".au"):
            return True
    return False


def match_asx_allowlisted_tickers(
    *,
    normalized: NormalizedNewsRecord,
    ticker_allowlist: Set[str],
) -> Set[str]:
    if not ticker_allowlist:
        return set()
    out: Set[str] = {sym for sym in ctx.parse_ticker_blob(normalized.ticker) if sym in ticker_allowlist}
    payload = f"{normalized.title}\n{normalized.body[:3000]}"
    for match in ASX_TICKER_TOKEN_RE.findall(payload):
        sym = ctx.normalize_ticker_symbol(match)
        if sym and sym in ticker_allowlist:
            out.add(sym)
    return out


def match_asx_company_names(
    *,
    normalized: NormalizedNewsRecord,
    company_names: Set[str],
) -> bool:
    if not company_names:
        return False
    haystack = normalize_company_name_for_match(f"{normalized.title}\n{normalized.body[:3000]}")
    if not haystack:
        return False
    padded = f" {haystack} "
    for name in company_names:
        if not name:
            continue
        if f" {name} " in padded:
            return True
    return False


def match_asx_company_name_tickers(
    *,
    normalized: NormalizedNewsRecord,
    ticker_name_linker: Optional[EntityLinker],
) -> Set[str]:
    return set(
        infer_company_name_tickers(
            title=normalized.title,
            body=normalized.body,
            ticker_name_linker=ticker_name_linker,
        )
    )


def iter_local_rows(
    path: Path,
    invalid_counter: Optional[Dict[str, int]] = None,
) -> Iterator[Dict[str, Any]]:
    if path.is_file():
        if path.suffix.lower() != ".jsonl":
            raise RuntimeError(f"Expected .jsonl file: {path}")
        yield from iter_jsonl(path, invalid_counter=invalid_counter)
        return
    if not path.is_dir():
        raise RuntimeError(f"Input path does not exist: {path}")
    files = sorted(path.rglob("*.jsonl"))
    if not files:
        raise RuntimeError(f"No .jsonl files found under: {path}")
    for file_path in files:
        yield from iter_jsonl(file_path, invalid_counter=invalid_counter)


def iter_hf_rows(
    dataset_id: str,
    split: str,
    cache_dir: str,
    token_env: str,
    dataset_config: str,
) -> Iterator[Dict[str, Any]]:
    try:
        from datasets import load_dataset
    except ImportError as exc:
        msg = str(exc)
        if "insecure_hashlib" in msg or "huggingface_hub" in msg:
            raise RuntimeError(
                "Incompatible 'datasets' / 'huggingface_hub' versions in your environment. "
                "For this repo's current dependency set, repair with: "
                "financial-engine_v2/.venv/bin/pip install --upgrade "
                "\"huggingface-hub>=0.25,<0.26\""
            ) from exc
        raise RuntimeError("Missing dependency: datasets. Install with: pip install datasets") from exc

    kwargs: Dict[str, Any] = {}
    if cache_dir:
        kwargs["cache_dir"] = cache_dir
    token = os.getenv(token_env.strip()) if token_env.strip() else ""
    if token:
        kwargs["token"] = token

    try:
        if dataset_config.strip():
            ds = load_dataset(dataset_id, dataset_config.strip(), split=split, **kwargs)
        else:
            ds = load_dataset(dataset_id, split=split, **kwargs)
    except Exception as exc:
        raise RuntimeError(
            f"Failed to load dataset '{dataset_id}' split='{split}'. "
            "For this gated dataset you may need approved access + HF token, "
            "or use --input-path with local JSONL exports."
        ) from exc

    for row in ds:
        if isinstance(row, dict):
            yield row


def resolve_rss_identity_map_path(raw: str) -> Path:
    txt = str(raw or "").strip()
    if not txt:
        return (Path(__file__).resolve().parents[1] / "financial-engine_v2" / "config" / "ticker_identity_map.json").resolve()
    path = Path(txt).expanduser()
    if path.is_absolute():
        return path.resolve()
    cwd_path = (Path.cwd() / path).resolve()
    if cwd_path.exists():
        return cwd_path
    return (Path(__file__).resolve().parents[1] / path).resolve()


def build_ticker_name_linker(
    *,
    ticker_allowlist_path: Path,
    identity_map_path: Path,
) -> Optional[EntityLinker]:
    allowlist_resolved = Path(ticker_allowlist_path).expanduser().resolve()
    identity_resolved = Path(identity_map_path).expanduser().resolve()
    if not allowlist_resolved.exists() or not identity_resolved.exists():
        return None
    linker = EntityLinker(
        ticker_universe_path=allowlist_resolved,
        identity_map_path=identity_resolved,
    )
    if not linker.identity_map:
        return None
    return linker


def infer_company_name_tickers(
    *,
    title: str,
    body: str,
    ticker_name_linker: Optional[EntityLinker],
) -> List[str]:
    if ticker_name_linker is None:
        return []
    links = ticker_name_linker.link_article(
        article_id="",
        title=title,
        description="",
        body=body[:3000],
        published_at_utc="",
    )
    out: List[str] = []
    for link in links:
        if str(link.lane or "") != "high_precision":
            continue
        sym = ctx.normalize_ticker_symbol(str(link.ticker or ""))
        if not sym or sym in TICKER_STOPWORDS:
            continue
        if str(link.method or "") == "alias_strict":
            matched_alias = normalize_space(str(link.matched_alias or ""))
            alias_tokens = re.findall(r"[A-Za-z0-9]+", matched_alias)
            if ctx.normalize_ticker_symbol(matched_alias) == sym:
                continue
            if len(alias_tokens) < 2:
                continue
        out.append(sym)
    return sorted(set(out))


def prepare_rss_input_jsonl(
    *,
    args: argparse.Namespace,
    ticker_allowlist_path: Path,
) -> Tuple[Path, Optional[Path], Dict[str, Any]]:
    feed_list_path = Path(str(args.input_rss_feeds_file or "").strip()).expanduser().resolve()
    if not feed_list_path.exists():
        raise RuntimeError(f"RSS feeds file not found: {feed_list_path}")

    try:
        import ingest_asx_rss_headlines as rss_ingest
    except Exception as exc:
        raise RuntimeError(f"Unable to import RSS ingester module: {exc}") from exc

    temp_dir: Optional[Path] = None
    rss_out_jsonl_arg = str(getattr(args, "rss_out_jsonl", "") or "").strip()
    if rss_out_jsonl_arg:
        out_jsonl = Path(rss_out_jsonl_arg).expanduser().resolve()
    else:
        temp_dir = Path(tempfile.mkdtemp(prefix="asx_rss_ingest_", dir="/tmp"))
        out_jsonl = temp_dir / "rss_headlines.jsonl"

    try:
        report = rss_ingest.ingest_asx_rss_headlines(
            feed_urls=[],
            feeds_file=feed_list_path,
            out_jsonl=out_jsonl,
            asx_tickers_file=ticker_allowlist_path,
            identity_map_path=resolve_rss_identity_map_path(getattr(args, "rss_identity_map_path", "")),
            corpus=str(getattr(args, "corpus", "") or "news_asx_rss"),
            topic=str(getattr(args, "rss_topic", "") or "asx_rss_headline"),
            request_timeout=float(getattr(args, "rss_request_timeout", 15.0)),
            http_retries=int(getattr(args, "rss_http_retries", 2)),
            user_agent=str(getattr(args, "rss_user_agent", "tenn-asx-rss-ingest/1.0")),
        )
    except Exception:
        if temp_dir is not None and temp_dir.exists() and not bool(getattr(args, "rss_keep_temp", False)):
            shutil.rmtree(temp_dir, ignore_errors=True)
        raise
    return out_jsonl, temp_dir, report


def normalize_records(
    rows: Iterable[Dict[str, Any]],
    min_text_chars: int,
    keep_non_english: bool,
    max_rows: int,
    ticker_allowlist: Optional[Set[str]] = None,
    drop_ticker_nonmatching_rows: bool = False,
    skip_ticker_inference: bool = False,
) -> Tuple[List[NormalizedNewsRecord], Dict[str, int]]:
    stats: Dict[str, int] = {
        "input_rows": 0,
        "kept_rows": 0,
        "dropped_short_text": 0,
        "dropped_non_english": 0,
        "dropped_ticker_not_allowlisted": 0,
        "dropped_duplicate_url": 0,
        "dropped_duplicate_exact": 0,
        "dropped_duplicate_near": 0,
    }

    seen_url_hashes = set()
    seen_exact_hashes = set()
    near_by_title: Dict[str, List[str]] = {}

    out: List[NormalizedNewsRecord] = []
    for row in rows:
        stats["input_rows"] += 1
        if max_rows > 0 and len(out) >= max_rows:
            break

        normalized, reason = normalize_news_row(
            row=row,
            min_text_chars=min_text_chars,
            keep_non_english=keep_non_english,
            ticker_allowlist=ticker_allowlist,
            drop_ticker_nonmatching_rows=drop_ticker_nonmatching_rows,
            skip_ticker_inference=skip_ticker_inference,
        )
        if not normalized:
            key = f"dropped_{reason}"
            stats[key] = stats.get(key, 0) + 1
            continue

        if normalized.url:
            url_key = hashlib.sha1(normalized.url.lower().encode("utf-8")).hexdigest()
            if url_key in seen_url_hashes:
                stats["dropped_duplicate_url"] += 1
                continue
            seen_url_hashes.add(url_key)

        exact_key = hashlib.sha1(
            normalize_text_for_dedupe(f"{normalized.title}\n{normalized.body}").encode("utf-8")
        ).hexdigest()
        if exact_key in seen_exact_hashes:
            stats["dropped_duplicate_exact"] += 1
            continue
        seen_exact_hashes.add(exact_key)

        title_key = normalize_text_for_dedupe(normalized.title)[:220]
        body_fp = normalize_text_for_dedupe(normalized.body)[:1800]
        candidates = near_by_title.setdefault(title_key, [])
        is_near_dup = False
        for prev in candidates[-12:]:
            if body_fp[:320] and body_fp[:320] == prev[:320]:
                is_near_dup = True
                break
            if difflib.SequenceMatcher(None, body_fp, prev).ratio() >= 0.95:
                is_near_dup = True
                break
        if is_near_dup:
            stats["dropped_duplicate_near"] += 1
            continue
        candidates.append(body_fp)

        out.append(normalized)

    stats["kept_rows"] = len(out)
    return out, stats


def init_stats() -> Dict[str, int]:
    return {
        "input_rows": 0,
        "invalid_jsonl_lines": 0,
        "kept_rows": 0,
        "dropped_short_text": 0,
        "dropped_non_english": 0,
        "dropped_ticker_not_allowlisted": 0,
        "dropped_missing_doc_date": 0,
        "dropped_before_min_doc_date": 0,
        "dropped_after_max_doc_date": 0,
        "dropped_asx_country_or_domain": 0,
        "dropped_asx_missing_entity_match": 0,
        "dropped_duplicate_url": 0,
        "dropped_duplicate_exact": 0,
        "dropped_duplicate_near": 0,
        "kept_rows_with_ticker": 0,
        "kept_rows_with_doc_date": 0,
        "output_chunks": 0,
        "flush_batches": 0,
    }


def atomic_write_json(path: Path, payload: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_suffix(path.suffix + ".tmp")
    tmp_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    tmp_path.replace(path)


def read_dedupe_counts(path: Path) -> Dict[str, int]:
    if not path.exists():
        return {"seen_url": 0, "seen_exact": 0, "seen_near": 0}
    conn: Optional[sqlite3.Connection] = None
    try:
        conn = sqlite3.connect(str(path), timeout=10.0)
        cur = conn.cursor()
        out: Dict[str, int] = {}
        for table in ("seen_url", "seen_exact", "seen_near"):
            try:
                row = cur.execute(f"SELECT COUNT(*) FROM {table}").fetchone()
                out[table] = int((row or [0])[0] or 0)
            except Exception:
                out[table] = 0
        return out
    except Exception:
        return {"seen_url": 0, "seen_exact": 0, "seen_near": 0}
    finally:
        if conn is not None:
            try:
                conn.close()
            except Exception:
                pass


class ManifestWriter:
    def __init__(
        self,
        *,
        path: Path,
        write_every: int,
        args: argparse.Namespace,
        out_path: Path,
        dedupe_path: Path,
        ticker_allowlist_size: int,
    ) -> None:
        self.path = path
        self.write_every = int(max(1, write_every))
        self.args = args
        self.out_path = out_path
        self.dedupe_path = dedupe_path
        self.ticker_allowlist_size = int(max(0, ticker_allowlist_size))
        self.started_at = datetime.datetime.utcnow().replace(microsecond=0).isoformat() + "Z"

    def _payload(
        self,
        *,
        stats: Dict[str, int],
        elapsed_seconds: float,
        status: str,
        error: str = "",
        extra: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        dropped = {
            key: int(value)
            for key, value in stats.items()
            if key.startswith("dropped_")
        }
        keep_metrics = {
            "input_rows": int(stats.get("input_rows", 0)),
            "kept_rows": int(stats.get("kept_rows", 0)),
            "kept_rows_with_ticker": int(stats.get("kept_rows_with_ticker", 0)),
            "kept_rows_with_doc_date": int(stats.get("kept_rows_with_doc_date", 0)),
            "unique_tickers": int(stats.get("unique_tickers", 0)),
        }
        payload: Dict[str, Any] = {
            "status": status,
            "error": str(error or ""),
            "started_at_utc": self.started_at,
            "updated_at_utc": datetime.datetime.utcnow().replace(microsecond=0).isoformat() + "Z",
            "elapsed_seconds": round(float(max(0.0, elapsed_seconds)), 3),
            "input": {
                "input_path": str(getattr(self.args, "input_path", "") or ""),
                "dataset_id": str(getattr(self.args, "dataset_id", "") or ""),
                "split": str(getattr(self.args, "split", "") or ""),
            },
            "output": {
                "db": str(getattr(self.args, "db", "") or ""),
                "out_path": str(self.out_path),
                "dedupe_path": str(self.dedupe_path),
                "corpus": str(getattr(self.args, "corpus", "") or ""),
                "doc_type": str(getattr(self.args, "doc_type", "") or ""),
                "embed_backend": str(getattr(self.args, "embed_backend", "") or ""),
                "embed_model": str(getattr(self.args, "embed_model", "") or ""),
            },
            "quality_gates": {
                "min_text_chars": int(getattr(self.args, "min_text_chars", 0) or 0),
                "min_doc_date": str(getattr(self.args, "min_doc_date", "") or ""),
                "max_doc_date": str(getattr(self.args, "max_doc_date", "") or ""),
                "keep_non_english": bool(getattr(self.args, "keep_non_english", False)),
                "asx_optimised_mode": bool(getattr(self.args, "asx_optimised_mode", False)),
                "ticker_allowlist_enabled": bool(getattr(self.args, "_ticker_allowlist", None)),
                "ticker_allowlist_size": self.ticker_allowlist_size,
                "asx_company_name_allowlist_size": int(
                    len(getattr(self.args, "_asx_company_names", set()) or set())
                ),
                "ticker_allowlist_drop_nonmatching": bool(
                    getattr(self.args, "ticker_allowlist_drop_nonmatching", False)
                ),
            },
            "stats": {
                **keep_metrics,
                "invalid_jsonl_lines": int(stats.get("invalid_jsonl_lines", 0)),
                "rows_dropped": dropped,
                "output_chunks": int(stats.get("output_chunks", 0)),
                "flush_batches": int(stats.get("flush_batches", 0)),
                "dedupe_db_counts": read_dedupe_counts(self.dedupe_path),
            },
        }
        if extra:
            payload["extra"] = extra
        return payload

    def write(
        self,
        *,
        stats: Dict[str, int],
        elapsed_seconds: float,
        status: str,
        force: bool = False,
        error: str = "",
        extra: Optional[Dict[str, Any]] = None,
    ) -> None:
        if not force:
            flush_batches = int(stats.get("flush_batches", 0))
            if flush_batches <= 0 or flush_batches % self.write_every != 0:
                return
        atomic_write_json(
            self.path,
            self._payload(stats=stats, elapsed_seconds=elapsed_seconds, status=status, error=error, extra=extra),
        )


def dedupe_db_default_path(out_path: Path) -> Path:
    if out_path.suffix:
        return out_path.with_suffix(".dedupe.sqlite")
    return out_path / "news_dedupe.sqlite"


def init_dedupe_db(path: Path) -> sqlite3.Connection:
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path), timeout=60.0)
    cur = conn.cursor()
    cur.execute("PRAGMA journal_mode=WAL")
    cur.execute("PRAGMA synchronous=NORMAL")
    cur.execute("PRAGMA temp_store=MEMORY")
    cur.execute("PRAGMA busy_timeout=60000")
    cur.execute("CREATE TABLE IF NOT EXISTS seen_url (url_hash TEXT PRIMARY KEY)")
    cur.execute("CREATE TABLE IF NOT EXISTS seen_exact (exact_hash TEXT PRIMARY KEY)")
    cur.execute("CREATE TABLE IF NOT EXISTS seen_near (near_hash TEXT PRIMARY KEY)")
    conn.commit()
    return conn


def execute_with_retry(
    cur: sqlite3.Cursor,
    sql: str,
    params: Tuple[Any, ...],
    retries: int = 8,
    base_delay_sec: float = 0.15,
) -> None:
    for attempt in range(retries + 1):
        try:
            cur.execute(sql, params)
            return
        except sqlite3.OperationalError as exc:
            if "locked" not in str(exc).lower():
                raise
            if attempt >= retries:
                raise
            time.sleep(base_delay_sec * (attempt + 1))


def near_duplicate_hash(rec: NormalizedNewsRecord) -> str:
    title_key = normalize_text_for_dedupe(rec.title)[:220]
    body_key = normalize_text_for_dedupe(rec.body)
    prefix = body_key[:320]
    token_sig = " ".join(body_key.split()[:80])
    payload = f"{title_key}|{prefix}|{token_sig}".strip("|")
    if not payload:
        return ""
    return hashlib.sha1(payload.encode("utf-8")).hexdigest()


def dedupe_keep_record(
    rec: NormalizedNewsRecord,
    conn: sqlite3.Connection,
    skip_near_dedupe: bool,
) -> Optional[str]:
    cur = conn.cursor()
    if rec.url:
        url_key = hashlib.sha1(rec.url.lower().encode("utf-8")).hexdigest()
        execute_with_retry(cur, "INSERT OR IGNORE INTO seen_url(url_hash) VALUES (?)", (url_key,))
        if cur.rowcount == 0:
            return "duplicate_url"

    exact_key = hashlib.sha1(
        normalize_text_for_dedupe(f"{rec.title}\n{rec.body}").encode("utf-8")
    ).hexdigest()
    execute_with_retry(cur, "INSERT OR IGNORE INTO seen_exact(exact_hash) VALUES (?)", (exact_key,))
    if cur.rowcount == 0:
        return "duplicate_exact"

    if not skip_near_dedupe:
        near_key = near_duplicate_hash(rec)
        if near_key:
            execute_with_retry(cur, "INSERT OR IGNORE INTO seen_near(near_hash) VALUES (?)", (near_key,))
            if cur.rowcount == 0:
                return "duplicate_near"
    return None


def append_embedding_jsonl(
    records: Sequence[ctx.ChunkRecord],
    vectors: Sequence[Sequence[float]],
    path: Path,
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        for rec, vec in zip(records, vectors):
            payload = {
                "chunk_id": rec.chunk_id,
                "company": rec.company,
                "file": rec.file,
                "section": rec.section,
                "corpus": rec.corpus,
                "doc_type": rec.doc_type,
                "doc_date": rec.doc_date,
                "source": rec.source,
                "ticker": rec.ticker,
                "topic": rec.topic,
                "url": rec.url,
                "title": rec.title,
                "published_at": rec.published_at,
                "ticker_relevance_json": rec.ticker_relevance_json,
                "text": rec.text,
                "embedding": list(vec),
            }
            fh.write(json.dumps(payload, ensure_ascii=False) + "\n")


def print_progress(stats: Dict[str, int], started_at: float) -> None:
    elapsed = max(1.0, time.time() - started_at)
    input_rate = stats["input_rows"] / elapsed
    keep_rate = stats["kept_rows"] / elapsed
    print(
        "[progress] "
        f"input={stats['input_rows']:,} kept={stats['kept_rows']:,} "
        f"chunks={stats['output_chunks']:,} batches={stats['flush_batches']:,} "
        f"elapsed_min={elapsed / 60.0:.1f} input_rows_per_sec={input_rate:.1f} "
        f"kept_rows_per_sec={keep_rate:.1f}"
    )


def flush_batch(
    normalized_batch: List[NormalizedNewsRecord],
    args: argparse.Namespace,
    out_path: Path,
    stats: Dict[str, int],
    faiss_records: List[ctx.ChunkRecord],
    faiss_vectors: List[List[float]],
    embedding_jsonl_path: Optional[Path],
) -> int:
    if not normalized_batch:
        return 0
    records = build_chunk_records(
        rows=normalized_batch,
        corpus=args.corpus,
        doc_type=args.doc_type,
        max_chars=max(200, args.max_chars),
        overlap_words=max(0, args.overlap_words),
    )
    normalized_batch.clear()
    if not records:
        return 0

    vectors = ctx.embed_texts(
        [r.text for r in records],
        backend=args.embed_backend,
        model_name=args.embed_model,
        ollama_endpoint=args.ollama_endpoint,
        hash_dim=args.hash_dim,
        st_device=args.st_device,
        st_batch_size=args.st_batch_size,
    )

    if args.db == "sqlite":
        ctx.store_sqlite(records, vectors, out_path)
    elif args.db == "chroma":
        ctx.store_chroma(records, vectors, out_path)
    elif args.db == "faiss":
        faiss_records.extend(records)
        faiss_vectors.extend([list(map(float, v)) for v in vectors])
    else:
        raise AssertionError("Unhandled db backend")

    if embedding_jsonl_path is not None:
        append_embedding_jsonl(records, vectors, embedding_jsonl_path)

    stats["output_chunks"] += len(records)
    stats["flush_batches"] += 1
    return len(records)


def stream_normalize_and_index(
    rows: Iterable[Dict[str, Any]],
    args: argparse.Namespace,
    out_path: Path,
    dedupe_conn: sqlite3.Connection,
    normalized_jsonl_path: Optional[Path],
    embedding_jsonl_path: Optional[Path],
    manifest_writer: Optional[ManifestWriter],
    stats: Optional[Dict[str, int]] = None,
) -> Tuple[Dict[str, int], List[ctx.ChunkRecord], List[List[float]]]:
    stats = stats if stats is not None else init_stats()
    started_at = time.time()
    asx_mode = bool(getattr(args, "asx_optimised_mode", False))
    rss_mode = bool(str(getattr(args, "input_rss_feeds_file", "") or "").strip())
    effective_min_text_chars = int(max(1, getattr(args, "_effective_min_text_chars", args.min_text_chars)))
    asx_ticker_allowlist = set(getattr(args, "_ticker_allowlist", set()) or set())
    asx_company_names = set(getattr(args, "_asx_company_names", set()) or set())
    ticker_name_linker = getattr(args, "_ticker_name_linker", None)
    normalized_batch: List[NormalizedNewsRecord] = []
    faiss_records: List[ctx.ChunkRecord] = []
    faiss_vectors: List[List[float]] = []
    ticker_seen: Set[str] = set()

    norm_fh = None
    if normalized_jsonl_path is not None:
        normalized_jsonl_path.parent.mkdir(parents=True, exist_ok=True)
        norm_fh = normalized_jsonl_path.open("w", encoding="utf-8")

    try:
        for row in rows:
            stats["input_rows"] += 1

            normalized, reason = normalize_news_row(
                row=row,
                min_text_chars=effective_min_text_chars,
                keep_non_english=args.keep_non_english,
                ticker_allowlist=getattr(args, "_ticker_allowlist", None),
                ticker_name_linker=ticker_name_linker,
                drop_ticker_nonmatching_rows=bool(getattr(args, "ticker_allowlist_drop_nonmatching", False)),
                skip_ticker_inference=rss_mode,
            )
            if not normalized:
                stats[f"dropped_{reason}"] = stats.get(f"dropped_{reason}", 0) + 1
                if args.progress_every > 0 and stats["input_rows"] % args.progress_every == 0:
                    dedupe_conn.commit()
                    if norm_fh is not None:
                        norm_fh.flush()
                    print_progress(stats, started_at)
                continue

            if args.min_doc_date or args.max_doc_date:
                if not normalized.doc_date:
                    stats["dropped_missing_doc_date"] += 1
                    if args.progress_every > 0 and stats["input_rows"] % args.progress_every == 0:
                        dedupe_conn.commit()
                        if norm_fh is not None:
                            norm_fh.flush()
                        print_progress(stats, started_at)
                    continue
                if args.min_doc_date and normalized.doc_date < args.min_doc_date:
                    stats["dropped_before_min_doc_date"] += 1
                    if args.progress_every > 0 and stats["input_rows"] % args.progress_every == 0:
                        dedupe_conn.commit()
                        if norm_fh is not None:
                            norm_fh.flush()
                        print_progress(stats, started_at)
                    continue
                if args.max_doc_date and normalized.doc_date > args.max_doc_date:
                    stats["dropped_after_max_doc_date"] += 1
                    if args.progress_every > 0 and stats["input_rows"] % args.progress_every == 0:
                        dedupe_conn.commit()
                        if norm_fh is not None:
                            norm_fh.flush()
                        print_progress(stats, started_at)
                    continue

            if asx_mode:
                if not row_matches_australia_country_or_au_domain(row=row, normalized=normalized):
                    stats["dropped_asx_country_or_domain"] += 1
                    if args.progress_every > 0 and stats["input_rows"] % args.progress_every == 0:
                        dedupe_conn.commit()
                        if norm_fh is not None:
                            norm_fh.flush()
                        print_progress(stats, started_at)
                    continue

                ticker_hits = match_asx_allowlisted_tickers(
                    normalized=normalized,
                    ticker_allowlist=asx_ticker_allowlist,
                )
                company_name_hit = match_asx_company_names(
                    normalized=normalized,
                    company_names=asx_company_names,
                )
                company_name_tickers = match_asx_company_name_tickers(
                    normalized=normalized,
                    ticker_name_linker=ticker_name_linker,
                )
                if not ticker_hits and not company_name_hit and not company_name_tickers:
                    stats["dropped_asx_missing_entity_match"] += 1
                    if args.progress_every > 0 and stats["input_rows"] % args.progress_every == 0:
                        dedupe_conn.commit()
                        if norm_fh is not None:
                            norm_fh.flush()
                        print_progress(stats, started_at)
                    continue
                merged_entity_tickers = set(ticker_hits) | set(company_name_tickers)
                if merged_entity_tickers:
                    merged_tickers = sorted(set(ctx.parse_ticker_blob(normalized.ticker)) | merged_entity_tickers)
                    merged_blob = serialize_ticker_blob(merged_tickers)
                    if merged_blob != normalized.ticker:
                        normalized = replace(normalized, ticker=merged_blob)

            dedupe_reason = dedupe_keep_record(
                rec=normalized,
                conn=dedupe_conn,
                skip_near_dedupe=args.skip_near_dedupe,
            )
            if dedupe_reason:
                stats[f"dropped_{dedupe_reason}"] = stats.get(f"dropped_{dedupe_reason}", 0) + 1
                if args.progress_every > 0 and stats["input_rows"] % args.progress_every == 0:
                    dedupe_conn.commit()
                    if norm_fh is not None:
                        norm_fh.flush()
                    print_progress(stats, started_at)
                continue

            stats["kept_rows"] += 1
            if normalized.doc_date:
                stats["kept_rows_with_doc_date"] += 1
            parsed_tickers = ctx.parse_ticker_blob(normalized.ticker)
            if parsed_tickers:
                stats["kept_rows_with_ticker"] += 1
                ticker_seen.update(parsed_tickers)
            if norm_fh is not None:
                norm_fh.write(json.dumps(asdict(normalized), ensure_ascii=False) + "\n")
            normalized_batch.append(normalized)

            reached_cap = args.max_rows > 0 and stats["kept_rows"] >= args.max_rows
            should_flush = len(normalized_batch) >= max(1, args.row_batch_size) or reached_cap
            if should_flush:
                flush_batch(
                    normalized_batch=normalized_batch,
                    args=args,
                    out_path=out_path,
                    stats=stats,
                    faiss_records=faiss_records,
                    faiss_vectors=faiss_vectors,
                    embedding_jsonl_path=embedding_jsonl_path,
                )
                dedupe_conn.commit()
                if norm_fh is not None:
                    norm_fh.flush()
                if manifest_writer is not None:
                    manifest_writer.write(
                        stats=stats,
                        elapsed_seconds=time.time() - started_at,
                        status="running",
                    )

            if args.progress_every > 0 and stats["input_rows"] % args.progress_every == 0:
                dedupe_conn.commit()
                if norm_fh is not None:
                    norm_fh.flush()
                print_progress(stats, started_at)
                if manifest_writer is not None:
                    manifest_writer.write(
                        stats=stats,
                        elapsed_seconds=time.time() - started_at,
                        status="running",
                    )

            if reached_cap:
                break

        if normalized_batch:
            flush_batch(
                normalized_batch=normalized_batch,
                args=args,
                out_path=out_path,
                stats=stats,
                faiss_records=faiss_records,
                faiss_vectors=faiss_vectors,
                embedding_jsonl_path=embedding_jsonl_path,
            )
        dedupe_conn.commit()
        stats["unique_tickers"] = len(ticker_seen)
        if manifest_writer is not None:
            manifest_writer.write(
                stats=stats,
                elapsed_seconds=time.time() - started_at,
                status="running",
                force=True,
            )
    finally:
        if norm_fh is not None:
            norm_fh.close()

    print_progress(stats, started_at)
    return stats, faiss_records, faiss_vectors


def build_chunk_records(
    rows: Sequence[NormalizedNewsRecord],
    corpus: str,
    doc_type: str,
    max_chars: int,
    overlap_words: int,
) -> List[ctx.ChunkRecord]:
    out: List[ctx.ChunkRecord] = []
    for rec in rows:
        payload = (f"{rec.title}\n\n{rec.body}" if rec.title else rec.body).strip()
        chunks = ctx.chunk_text(payload, max_chars=max_chars, overlap_words=overlap_words)
        tickers = ctx.parse_ticker_blob(rec.ticker)
        relevance_rows = infer_ticker_relevance_from_text(title=rec.title, body=rec.body, tickers=tickers)
        primary_ticker = choose_primary_ticker(relevance_rows, tickers)
        company = primary_ticker or "NEWS"
        ticker_relevance_json = serialize_ticker_relevance(relevance_rows)
        file_ref = rec.url or f"news://{rec.record_id}"
        for idx, chunk in enumerate(chunks):
            digest = hashlib.sha1(chunk.encode("utf-8")).hexdigest()[:12]
            chunk_id = f"{corpus}:{rec.record_id}:{idx}:{digest}"
            out.append(
                ctx.ChunkRecord(
                    chunk_id=chunk_id,
                    company=company,
                    file=file_ref,
                    section="fulltext_context",
                    text=chunk,
                    corpus=corpus,
                    doc_type=doc_type,
                    doc_date=rec.doc_date,
                    source=rec.source,
                    ticker=rec.ticker,
                    topic=rec.topic,
                    url=rec.url,
                    title=rec.title,
                    published_at=rec.published_at,
                    ticker_relevance_json=ticker_relevance_json,
                )
            )
    return out


def query_after_build(args, out_path: Path, corpus: str) -> None:
    if not args.query:
        return
    if args.db == "sqlite":
        rows = ctx.query_sqlite(
            db_path=out_path,
            query=args.query,
            backend=args.embed_backend,
            model_name=args.embed_model,
            ollama_endpoint=args.ollama_endpoint,
            hash_dim=args.hash_dim,
            st_device=args.st_device,
            st_batch_size=args.st_batch_size,
            company=args.company_filter,
            corpus_filter=args.corpus_filter or corpus,
            doc_type_filter=args.doc_type_filter,
            date_from=args.date_from,
            date_to=args.date_to,
            top_k=args.top_k,
            ticker_filter=args.ticker_filter,
            source_filter=args.source_filter,
        )
    elif args.db == "faiss":
        rows = ctx.query_faiss(
            index_dir=out_path,
            query=args.query,
            backend=args.embed_backend,
            model_name=args.embed_model,
            ollama_endpoint=args.ollama_endpoint,
            hash_dim=args.hash_dim,
            st_device=args.st_device,
            st_batch_size=args.st_batch_size,
            company=args.company_filter,
            corpus_filter=args.corpus_filter or corpus,
            doc_type_filter=args.doc_type_filter,
            date_from=args.date_from,
            date_to=args.date_to,
            top_k=args.top_k,
            ticker_filter=args.ticker_filter,
            source_filter=args.source_filter,
        )
    else:
        rows = ctx.query_chroma(
            chroma_dir=out_path,
            query=args.query,
            backend=args.embed_backend,
            model_name=args.embed_model,
            ollama_endpoint=args.ollama_endpoint,
            hash_dim=args.hash_dim,
            st_device=args.st_device,
            st_batch_size=args.st_batch_size,
            company=args.company_filter,
            corpus_filter=args.corpus_filter or corpus,
            doc_type_filter=args.doc_type_filter,
            date_from=args.date_from,
            date_to=args.date_to,
            top_k=args.top_k,
            ticker_filter=args.ticker_filter,
            source_filter=args.source_filter,
        )

    if not rows:
        print("No retrieval results for that query.")
        return
    for rank, (score, row) in enumerate(rows, start=1):
        print(
            f"\n[{rank}] score={score:.4f} corpus={row.get('corpus','')} "
            f"doc_type={row.get('doc_type','')} source={row.get('source','')} "
            f"ticker={row.get('ticker','')} date={row.get('doc_date','')} "
            f"title={row.get('title','')}"
        )
        print(str(row.get("text", ""))[:600].strip())


def main() -> int:
    ap = argparse.ArgumentParser(description="Build isolated news corpus vector DB (experimental research module)")
    ap.add_argument("--input-path", default="", help="Optional local JSONL file/dir (offline mode)")
    ap.add_argument(
        "--input-rss-feeds-file",
        default="",
        help="Optional newline-separated feed list (URLs or local XML paths); triggers RSS ingestion mode.",
    )
    ap.add_argument("--dataset-id", default=DEFAULT_DATASET_ID, help="Hugging Face dataset id")
    ap.add_argument("--dataset-config", default="", help="Optional Hugging Face dataset config name")
    ap.add_argument("--split", default="train", help="Dataset split")
    ap.add_argument("--dataset-cache-dir", default="", help="Hugging Face cache directory")
    ap.add_argument("--hf-token-env", default="HF_TOKEN", help="Env var containing HF token for gated access")
    ap.add_argument("--db", choices=["sqlite", "faiss", "chroma"], default="sqlite", help="Vector storage backend")
    ap.add_argument("--out", default=str(DEFAULT_NEWS_CONTEXT_DB), help="Output DB path")
    ap.add_argument("--normalized-jsonl", default="", help="Optional path to write normalized row JSONL")
    ap.add_argument("--corpus", default="news", help="Corpus label (default: news)")
    ap.add_argument("--doc-type", default="news_article", help="doc_type label (default: news_article)")
    ap.add_argument(
        "--embed-backend",
        choices=["sentence-transformers", "ollama", "hash"],
        default="sentence-transformers",
        help="Embedding runtime",
    )
    ap.add_argument("--embed-model", default="BAAI/bge-large-en-v1.5", help="Embedding model")
    ap.add_argument(
        "--st-device",
        choices=["auto", "cpu", "cuda", "cuda_strict"],
        default="cpu",
        help="Sentence-transformers device",
    )
    ap.add_argument("--st-batch-size", type=int, default=16, help="Sentence-transformers batch size")
    ap.add_argument("--ollama-endpoint", default="http://127.0.0.1:11434", help="Ollama base URL")
    ap.add_argument("--hash-dim", type=int, default=384, help="Vector size for hash embeddings")
    ap.add_argument("--max-chars", type=int, default=1200, help="Chunk size in characters")
    ap.add_argument("--overlap-words", type=int, default=60, help="Chunk overlap in words")
    ap.add_argument("--min-text-chars", type=int, default=200, help="Minimum body length gate")
    ap.add_argument("--rss-min-text-chars", type=int, default=40, help="Minimum body length gate for RSS mode")
    ap.add_argument("--min-doc-date", default="", help="Optional inclusive ingest date gate (YYYY-MM-DD)")
    ap.add_argument("--max-doc-date", default="", help="Optional inclusive ingest date gate (YYYY-MM-DD)")
    ap.add_argument("--keep-non-english", action="store_true", help="Disable simple English language gate")
    ap.add_argument("--ticker-allowlist-path", default="", help="Optional ticker allowlist path (txt/csv/json/jsonl)")
    ap.add_argument(
        "--use-default-asx-allowlist",
        action="store_true",
        help=f"Use default ASX ticker allowlist at ./{DEFAULT_ASX_ALLOWLIST_RELATIVE}",
    )
    ap.add_argument(
        "--ticker-allowlist-drop-nonmatching",
        action="store_true",
        help="When allowlist is active, drop rows that mention tickers but none are allowlisted",
    )
    ap.add_argument(
        "--asx-optimised-mode",
        action="store_true",
        help=(
            "Enable ASX-focused GDELT ingestion filters: Australia/.au source gate, "
            "headline prioritization, and ASX entity match requirement."
        ),
    )
    ap.add_argument("--max-rows", type=int, default=0, help="Optional cap on kept normalized rows")
    ap.add_argument("--row-batch-size", type=int, default=512, help="Normalized row batch size before embed/store flush")
    ap.add_argument("--progress-every", type=int, default=50000, help="Print progress every N input rows (0 disables)")
    ap.add_argument("--manifest-json", default="", help="Optional path to continuously write build manifest JSON")
    ap.add_argument("--manifest-write-every", type=int, default=1, help="Write manifest every N flush batches")
    ap.add_argument("--dedupe-db", default="", help="Path for persistent dedupe state SQLite")
    ap.add_argument("--reset-dedupe-db", action="store_true", help="Delete existing dedupe DB before run")
    ap.add_argument("--reset-output", action="store_true", help="Delete existing output artifact before run")
    ap.add_argument("--skip-near-dedupe", action="store_true", help="Disable approximate near-duplicate filtering")
    ap.add_argument("--write-embedding-jsonl", action="store_true", help="Also write chunk embeddings JSONL beside SQLite")
    ap.add_argument("--query", default="", help="Optional retrieval query after indexing")
    ap.add_argument("--company-filter", default="", help="Optional company filter for retrieval query")
    ap.add_argument("--corpus-filter", default="", help="Optional corpus filter for retrieval query")
    ap.add_argument("--doc-type-filter", default="news_article", help="Optional doc_type filter for retrieval query")
    ap.add_argument("--ticker-filter", default="", help="Optional ticker filter for retrieval query")
    ap.add_argument("--source-filter", default="", help="Optional source filter for retrieval query")
    ap.add_argument("--date-from", default="", help="Optional inclusive date filter (YYYY-MM-DD)")
    ap.add_argument("--date-to", default="", help="Optional inclusive date filter (YYYY-MM-DD)")
    ap.add_argument("--top-k", type=int, default=8, help="Top-k retrieval results")
    ap.add_argument(
        "--health-json",
        default="reports/research_engine_health.json",
        help="Health snapshot JSON path used for pre-run gating.",
    )
    ap.add_argument(
        "--allow-warning",
        action="store_true",
        help="Allow execution when health snapshot overall_status=warning.",
    )
    ap.add_argument(
        "--research-only-ack",
        action="store_true",
        help="Required flag acknowledging this module is research-only without legal approval",
    )
    ap.add_argument("--rss-out-jsonl", default="", help="Optional path to persist RSS intermediate JSONL")
    ap.add_argument(
        "--rss-identity-map-path",
        default="financial-engine_v2/config/ticker_identity_map.json",
        help="Ticker identity map path used by RSS ingester",
    )
    ap.add_argument("--rss-topic", default="asx_rss_headline", help="Topic label used for RSS rows")
    ap.add_argument("--rss-request-timeout", type=float, default=15.0, help="RSS HTTP timeout seconds")
    ap.add_argument("--rss-http-retries", type=int, default=2, help="RSS HTTP retries per feed")
    ap.add_argument("--rss-user-agent", default="tenn-asx-rss-ingest/1.0", help="RSS fetch User-Agent")
    ap.add_argument("--rss-keep-temp", action="store_true", help="Keep temporary RSS JSONL when auto-generated")
    ap.add_argument("--debug-rss-pipeline", action="store_true", help="Print RSS-mode stage counters for diagnosis")
    args = ap.parse_args()

    if not args.research_only_ack:
        print(COMPLIANCE_NOTICE, file=sys.stderr)
        print("Refusing to run without --research-only-ack.", file=sys.stderr)
        return 2

    print(COMPLIANCE_NOTICE)

    if args.date_from and not ctx.valid_iso_date(args.date_from):
        print(f"Invalid --date-from: {args.date_from}. Use YYYY-MM-DD.", file=sys.stderr)
        return 2
    if args.date_to and not ctx.valid_iso_date(args.date_to):
        print(f"Invalid --date-to: {args.date_to}. Use YYYY-MM-DD.", file=sys.stderr)
        return 2
    if args.date_from and args.date_to and args.date_from > args.date_to:
        print("--date-from cannot be after --date-to.", file=sys.stderr)
        return 2
    if args.min_doc_date and not ctx.valid_iso_date(args.min_doc_date):
        print(f"Invalid --min-doc-date: {args.min_doc_date}. Use YYYY-MM-DD.", file=sys.stderr)
        return 2
    if args.max_doc_date and not ctx.valid_iso_date(args.max_doc_date):
        print(f"Invalid --max-doc-date: {args.max_doc_date}. Use YYYY-MM-DD.", file=sys.stderr)
        return 2
    if args.min_doc_date and args.max_doc_date and args.min_doc_date > args.max_doc_date:
        print("--min-doc-date cannot be after --max-doc-date.", file=sys.stderr)
        return 2
    if int(args.manifest_write_every) <= 0:
        print("--manifest-write-every must be > 0", file=sys.stderr)
        return 2
    if args.input_path and args.input_rss_feeds_file:
        print("--input-path and --input-rss-feeds-file are mutually exclusive.", file=sys.stderr)
        return 2
    if args.input_rss_feeds_file and args.asx_optimised_mode:
        print("--input-rss-feeds-file cannot be combined with --asx-optimised-mode.", file=sys.stderr)
        return 2

    snapshot = load_health_snapshot(str(args.health_json))
    health_status = get_overall_status(snapshot)
    if bool(getattr(args, "debug_rss_pipeline", False)):
        print(f"[debug-rss] health gate status: {health_status}")
    assert_healthy(snapshot, allow_warning=bool(args.allow_warning))

    if args.input_rss_feeds_file:
        if str(args.corpus or "").strip() != "news_asx_rss":
            print("[rss-mode] forcing corpus=news_asx_rss")
        args.corpus = "news_asx_rss"
        args._effective_min_text_chars = int(max(1, args.rss_min_text_chars))
        print(f"[rss-mode] using rss_min_text_chars={int(args._effective_min_text_chars)}")
    else:
        args._effective_min_text_chars = int(max(1, args.min_text_chars))

    if args.asx_optimised_mode:
        if str(args.corpus or "").strip() != "news_asx_gdelt":
            print("[asx-optimised] forcing corpus=news_asx_gdelt")
        args.corpus = "news_asx_gdelt"

    allowlist_path = str(args.ticker_allowlist_path or "").strip()
    if args.use_default_asx_allowlist and not allowlist_path:
        allowlist_path = str(default_asx_allowlist_path())
    if args.input_rss_feeds_file and not allowlist_path:
        allowlist_path = str(default_asx_allowlist_path())
    if args.asx_optimised_mode and not allowlist_path:
        allowlist_path = str(default_asx_allowlist_path())
    ticker_allowlist: Optional[Set[str]] = None
    allowlist_resolved_path: Optional[Path] = None
    if allowlist_path:
        allowlist_resolved_path = Path(allowlist_path).expanduser().resolve()
        try:
            ticker_allowlist = load_ticker_allowlist(allowlist_resolved_path)
        except RuntimeError as exc:
            print(str(exc), file=sys.stderr)
            return 2
        if not ticker_allowlist:
            print(f"Ticker allowlist is empty after parsing: {allowlist_path}", file=sys.stderr)
            return 2
        print(f"ticker_allowlist={allowlist_path} size={len(ticker_allowlist)}")
    elif args.ticker_allowlist_drop_nonmatching:
        print(
            "--ticker-allowlist-drop-nonmatching requires --ticker-allowlist-path "
            "or --use-default-asx-allowlist",
            file=sys.stderr,
        )
        return 2

    if args.asx_optimised_mode and not ticker_allowlist:
        print("--asx-optimised-mode requires a non-empty ticker allowlist.", file=sys.stderr)
        return 2
    if args.input_rss_feeds_file and not ticker_allowlist:
        print("--input-rss-feeds-file requires a non-empty ticker allowlist.", file=sys.stderr)
        return 2

    asx_company_names: Set[str] = set()
    if args.asx_optimised_mode and allowlist_resolved_path is not None:
        try:
            asx_company_names = load_allowlist_company_names(allowlist_resolved_path)
        except RuntimeError as exc:
            print(str(exc), file=sys.stderr)
            return 2
        if asx_company_names:
            print(f"asx_company_names={len(asx_company_names)}")

    ticker_name_linker: Optional[EntityLinker] = None
    if allowlist_resolved_path is not None:
        identity_map_path = resolve_rss_identity_map_path(getattr(args, "rss_identity_map_path", ""))
        try:
            ticker_name_linker = build_ticker_name_linker(
                ticker_allowlist_path=allowlist_resolved_path,
                identity_map_path=identity_map_path,
            )
        except Exception as exc:
            print(f"[warn] unable to initialise ticker name linker: {exc}", file=sys.stderr)
        if ticker_name_linker is not None:
            print(f"ticker_name_linker=enabled identity_map={identity_map_path}")

    # Internal transport for stream worker path.
    args._ticker_allowlist = ticker_allowlist
    args._asx_company_names = asx_company_names
    args._ticker_name_linker = ticker_name_linker

    out_path = resolve_path(args.out)
    if args.db == "sqlite" and out_path.suffix != ".sqlite":
        out_path = out_path / "news.sqlite"

    dedupe_path = Path(args.dedupe_db).expanduser() if args.dedupe_db else dedupe_db_default_path(out_path)
    if args.reset_output:
        if args.db == "sqlite" and out_path.exists():
            out_path.unlink()
        elif args.db in {"faiss", "chroma"} and out_path.exists() and out_path.is_dir():
            shutil.rmtree(out_path)
    if args.reset_dedupe_db and dedupe_path.exists():
        dedupe_path.unlink()
    dedupe_conn = init_dedupe_db(dedupe_path)
    print(f"dedupe_db={dedupe_path}")
    debug_dedupe_before = read_dedupe_counts(dedupe_path) if bool(getattr(args, "debug_rss_pipeline", False)) else {}
    manifest_writer: Optional[ManifestWriter] = None
    if args.manifest_json:
        manifest_writer = ManifestWriter(
            path=Path(args.manifest_json).expanduser().resolve(),
            write_every=int(args.manifest_write_every),
            args=args,
            out_path=out_path,
            dedupe_path=dedupe_path,
            ticker_allowlist_size=len(ticker_allowlist or set()),
        )
        manifest_writer.write(
            stats=init_stats(),
            elapsed_seconds=0.0,
            status="running",
            force=True,
        )

    embedding_jsonl_path: Optional[Path] = None
    if args.write_embedding_jsonl:
        if args.db == "sqlite":
            embedding_jsonl_path = out_path.with_suffix(".jsonl")
        else:
            embedding_jsonl_path = out_path / "news_embeddings.jsonl"
        if embedding_jsonl_path.exists():
            embedding_jsonl_path.unlink()

    normalized_jsonl_path: Optional[Path] = None
    if args.normalized_jsonl:
        normalized_jsonl_path = Path(args.normalized_jsonl).expanduser()

    rss_temp_dir: Optional[Path] = None
    rss_jsonl_debug_count: Optional[int] = None
    stats: Dict[str, int] = init_stats()
    if args.input_rss_feeds_file:
        assert allowlist_resolved_path is not None
        rss_jsonl_path, rss_temp_dir, rss_report = prepare_rss_input_jsonl(
            args=args,
            ticker_allowlist_path=allowlist_resolved_path,
        )
        print(json.dumps({"rss_ingest": rss_report}, indent=2))
        if bool(getattr(args, "debug_rss_pipeline", False)):
            rss_exists = rss_jsonl_path.exists()
            rss_size_bytes = int(rss_jsonl_path.stat().st_size) if rss_exists else 0
            rss_jsonl_debug_count = count_jsonl_rows(rss_jsonl_path) if rss_exists else 0
            print(
                f"[debug-rss] rss_jsonl_path={rss_jsonl_path} exists={rss_exists} "
                f"size_bytes={rss_size_bytes} rows={rss_jsonl_debug_count}"
            )
            print(f"[debug-rss] target_corpus={args.corpus}")
            print(f"[debug-rss] min_text_chars={int(args._effective_min_text_chars)}")
        args.input_path = str(rss_jsonl_path)
        rows_iter = iter_local_rows(rss_jsonl_path, invalid_counter=stats)
    elif args.input_path:
        rows_iter = iter_local_rows(Path(args.input_path).expanduser().resolve(), invalid_counter=stats)
    else:
        rows_iter = iter_hf_rows(
            dataset_id=args.dataset_id,
            split=args.split,
            cache_dir=args.dataset_cache_dir,
            token_env=args.hf_token_env,
            dataset_config=args.dataset_config,
        )
    if args.asx_optimised_mode:
        rows_iter = iter_asx_prioritized_rows(rows_iter)

    main_started_at = time.time()

    faiss_records: List[ctx.ChunkRecord]
    faiss_vectors: List[List[float]]
    try:
        stats, faiss_records, faiss_vectors = stream_normalize_and_index(
            rows=rows_iter,
            args=args,
            out_path=out_path,
            dedupe_conn=dedupe_conn,
            normalized_jsonl_path=normalized_jsonl_path,
            embedding_jsonl_path=embedding_jsonl_path,
            manifest_writer=manifest_writer,
            stats=stats,
        )
    except Exception as exc:
        if manifest_writer is not None:
            manifest_writer.write(
                stats=stats,
                elapsed_seconds=time.time() - main_started_at,
                status="failed",
                force=True,
                error=str(exc),
            )
        dedupe_conn.close()
        raise
    finally:
        dedupe_conn.close()
        if rss_temp_dir is not None and rss_temp_dir.exists() and not bool(getattr(args, "rss_keep_temp", False)):
            shutil.rmtree(rss_temp_dir, ignore_errors=True)

    if bool(getattr(args, "debug_rss_pipeline", False)) and args.input_rss_feeds_file:
        dedupe_after = read_dedupe_counts(dedupe_path)
        input_rows = int(stats.get("input_rows", 0) or 0)
        dropped_short_text = int(stats.get("dropped_short_text", 0) or 0)
        dropped_non_english = int(stats.get("dropped_non_english", 0) or 0)
        rows_after_min_text = max(0, input_rows - dropped_short_text)
        dedupe_dropped_total = int(stats.get("dropped_duplicate_url", 0) or 0) + int(
            stats.get("dropped_duplicate_exact", 0) or 0
        ) + int(stats.get("dropped_duplicate_near", 0) or 0)
        print(
            json.dumps(
                {
                    "debug_rss_pipeline": {
                        "rows_read_from_jsonl": int(rss_jsonl_debug_count or 0),
                        "rows_seen_by_normalizer": input_rows,
                        "rows_surviving_min_text_chars": rows_after_min_text,
                        "rows_dropped_short_text": dropped_short_text,
                        "rows_dropped_non_english": dropped_non_english,
                        "rows_surviving_dedupe_db": int(stats.get("kept_rows", 0) or 0),
                        "rows_dropped_by_dedupe_db": dedupe_dropped_total,
                        "rows_inserted_chunks": int(stats.get("output_chunks", 0) or 0),
                        "corpus_to_write": str(args.corpus or ""),
                        "dedupe_db_before": debug_dedupe_before,
                        "dedupe_db_after": dedupe_after,
                    }
                },
                indent=2,
            )
        )

    if stats["kept_rows"] == 0:
        input_rows = int(stats.get("input_rows", 0) or 0)
        dropped_short_text = int(stats.get("dropped_short_text", 0) or 0)
        dropped_non_english = int(stats.get("dropped_non_english", 0) or 0)
        dropped_ticker_not_allowlisted = int(stats.get("dropped_ticker_not_allowlisted", 0) or 0)
        dropped_missing_doc_date = int(stats.get("dropped_missing_doc_date", 0) or 0)
        dropped_before_min_doc_date = int(stats.get("dropped_before_min_doc_date", 0) or 0)
        dropped_after_max_doc_date = int(stats.get("dropped_after_max_doc_date", 0) or 0)
        dropped_asx_country_or_domain = int(stats.get("dropped_asx_country_or_domain", 0) or 0)
        dropped_asx_missing_entity_match = int(stats.get("dropped_asx_missing_entity_match", 0) or 0)
        dedupe_dropped_total = int(stats.get("dropped_duplicate_url", 0) or 0) + int(
            stats.get("dropped_duplicate_exact", 0) or 0
        ) + int(stats.get("dropped_duplicate_near", 0) or 0)
        non_dedupe_drops = (
            dropped_short_text
            + dropped_non_english
            + dropped_ticker_not_allowlisted
            + dropped_missing_doc_date
            + dropped_before_min_doc_date
            + dropped_after_max_doc_date
            + dropped_asx_country_or_domain
            + dropped_asx_missing_entity_match
        )

        # Keep SQLite schema available even when all rows are filtered out.
        # This avoids downstream "no such table: context_chunks" failures
        # after --reset-output runs that intentionally produce zero records.
        if args.db == "sqlite":
            ctx.store_sqlite([], [], out_path)
        # If all kept_rows were filtered out solely due to duplicate detection,
        # treat this as an idempotent no-op rather than a hard failure.
        if input_rows > 0 and non_dedupe_drops == 0 and dedupe_dropped_total >= input_rows:
            if manifest_writer is not None:
                manifest_writer.write(
                    stats=stats,
                    elapsed_seconds=time.time() - main_started_at,
                    status="noop",
                    force=True,
                    error="All normalized news records were already present in the dedupe DB (idempotent run).",
                )
            print(
                "All normalized news records were already present in the dedupe DB; "
                "treating this build as an idempotent no-op.",
                file=sys.stderr,
            )
            return 0

        if manifest_writer is not None:
            manifest_writer.write(
                stats=stats,
                elapsed_seconds=time.time() - main_started_at,
                status="failed",
                force=True,
                error="No normalized news records remained after quality and dedupe gates.",
            )
        print("No normalized news records remained after quality and dedupe gates.", file=sys.stderr)
        print(json.dumps(stats, indent=2), file=sys.stderr)
        if bool(getattr(args, "debug_rss_pipeline", False)) and args.db == "sqlite":
            try:
                conn = sqlite3.connect(str(out_path))
                cur = conn.cursor()
                row = cur.execute(
                    "SELECT COUNT(*) FROM context_chunks WHERE corpus = ?",
                    (str(args.corpus or ""),),
                ).fetchone()
                conn.close()
                corpus_count = int((row or [0])[0] or 0)
            except Exception as exc:
                corpus_count = -1
                print(f"[debug-rss] sqlite corpus count query failed: {exc}", file=sys.stderr)
            print(f"[debug-rss] sqlite corpus chunk count after run: {corpus_count}", file=sys.stderr)
        return 1

    if args.db == "sqlite":
        print(f"Stored {stats['output_chunks']} chunks in SQLite: {out_path}")
    elif args.db == "chroma":
        print(f"Stored {stats['output_chunks']} chunks in Chroma dir: {out_path}")
    elif args.db == "faiss":
        if not faiss_records or not faiss_vectors:
            print("No FAISS vectors produced from normalized rows.", file=sys.stderr)
            return 1
        ctx.store_faiss(faiss_records, faiss_vectors, out_path)
        print(f"Stored {len(faiss_records)} chunks in FAISS dir: {out_path}")
    else:
        raise AssertionError("Unhandled db backend")
    if bool(getattr(args, "debug_rss_pipeline", False)) and args.db == "sqlite":
        try:
            conn = sqlite3.connect(str(out_path))
            cur = conn.cursor()
            row = cur.execute(
                "SELECT COUNT(*) FROM context_chunks WHERE corpus = ?",
                (str(args.corpus or ""),),
            ).fetchone()
            conn.close()
            corpus_count = int((row or [0])[0] or 0)
            print(f"[debug-rss] sqlite corpus chunk count after run: {corpus_count}")
        except Exception as exc:
            print(f"[debug-rss] sqlite corpus count query failed: {exc}")

    if manifest_writer is not None:
        manifest_writer.write(
            stats=stats,
            elapsed_seconds=time.time() - main_started_at,
            status="success",
            force=True,
        )
    print(json.dumps(stats, indent=2))
    query_after_build(args=args, out_path=out_path, corpus=args.corpus)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
