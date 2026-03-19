#!/usr/bin/env python3
"""
Ingest ASX-focused RSS/Atom headlines into JSONL rows compatible with build_news_context_db.py.
"""

from __future__ import annotations

import argparse
import datetime
import hashlib
import importlib.util
import json
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from email.utils import parsedate_to_datetime
from pathlib import Path
from typing import Any, Iterable

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))
try:
    import build_qualitative_context_db as ctx
except Exception:
    ctx = None

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT_JSONL = REPO_ROOT / "reports" / "news_eval_input" / "asx_rss_headlines.jsonl"
DEFAULT_ASX_TICKERS = REPO_ROOT / "financial-engine_v2" / "data" / "raw" / "asx_ticker_universe.txt"
DEFAULT_IDENTITY_MAP = REPO_ROOT / "financial-engine_v2" / "config" / "ticker_identity_map.json"
DEFAULT_CORPUS = "news_asx_rss"
DEFAULT_TOPIC = "asx_rss_headline"

TAG_RE = re.compile(r"<[^>]+>")
WS_RE = re.compile(r"\s+")
BOUNDARY_TOKEN_RE = re.compile(r"(?<![A-Za-z0-9])([A-Z][A-Z0-9]{1,5})(?![A-Za-z0-9])")
ASX_PATTERN_RE = re.compile(r"\bASX\s*[:\-]\s*([A-Z][A-Z0-9]{1,5})\b", flags=re.IGNORECASE)
AX_SUFFIX_RE = re.compile(r"(?<![A-Za-z0-9])([A-Z][A-Z0-9]{1,5})\.AX(?![A-Za-z0-9])", flags=re.IGNORECASE)
DEFAULT_IDENTITY_CFG: dict[str, Any] = {
    "enable_identity_hardening": True,
    "canonical_name_required_for_acronym": True,
    "acronym_min_length": 4,
    "downgrade_ambiguous_acronym_boost": 0.02,
    "allow_headline_only_medium": True,
    "headline_only_body_chars": 120,
}
DEFAULT_HEADLINE_KEYWORDS: tuple[str, ...] = (
    "shares",
    "earnings",
    "dividend",
    "guidance",
    "profit",
    "results",
    "outlook",
)
DEFAULT_COLLISION_PHRASES: dict[str, list[str]] = {
    "CSL": [
        "communications sales",
        "communications sales leasing",
        "communications sales and leasing",
        "leasing portfolio",
        "landlord",
        "reit",
    ],
}
SHORT_ACRONYM_RE = re.compile(r"^[A-Z][A-Z0-9]{1,5}$")


def normalize_space(value: Any) -> str:
    return WS_RE.sub(" ", str(value or "").replace("\r", " ").replace("\n", " ")).strip()


def strip_html(value: Any) -> str:
    text = TAG_RE.sub(" ", str(value or ""))
    return normalize_space(text)


def normalize_phrase_text(value: Any) -> str:
    text = normalize_space(value).lower()
    if not text:
        return ""
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return normalize_space(text)


def normalize_url(value: Any) -> str:
    raw = str(value or "").strip()
    if not raw:
        return ""
    raw = raw.replace(" ", "")
    return raw.rstrip("/")


def parse_domain(value: Any) -> str:
    raw = normalize_space(value).lower()
    if not raw:
        return ""
    candidate = raw if "://" in raw else f"https://{raw}"
    try:
        host = str(urllib.parse.urlparse(candidate).netloc or "").strip().lower()
    except Exception:
        host = ""
    if not host:
        host = raw.split("/")[0].strip().lower()
    if host.startswith("www."):
        host = host[4:]
    return host


def parse_keyword_list(values: list[str] | tuple[str, ...] | None) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()
    raw_values = list(values or [])
    if not raw_values:
        raw_values = list(DEFAULT_HEADLINE_KEYWORDS)
    for raw in raw_values:
        token = normalize_phrase_text(raw)
        if not token or token in seen:
            continue
        seen.add(token)
        out.append(token)
    return out


def load_collision_phrase_map(path: Path | None) -> dict[str, list[str]]:
    merged: dict[str, list[str]] = {}

    def _add(ticker: str, phrases: list[str]) -> None:
        symbol = "".join(ch for ch in str(ticker or "").upper() if ch.isalnum())
        if not symbol:
            return
        for phrase in phrases:
            normalized = normalize_phrase_text(phrase)
            if not normalized:
                continue
            merged.setdefault(symbol, [])
            if normalized not in merged[symbol]:
                merged[symbol].append(normalized)

    for ticker, phrases in DEFAULT_COLLISION_PHRASES.items():
        if isinstance(phrases, list):
            _add(ticker, phrases)

    if path is None:
        return merged
    if not path.exists():
        raise RuntimeError(f"Collision phrase config not found: {path}")
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise RuntimeError(f"Failed parsing collision phrase config: {path} ({exc})") from exc
    if not isinstance(payload, dict):
        raise RuntimeError(f"Collision phrase config must be a JSON object: {path}")
    for raw_ticker, raw_phrases in payload.items():
        if isinstance(raw_phrases, str):
            _add(str(raw_ticker), [raw_phrases])
        elif isinstance(raw_phrases, list):
            _add(str(raw_ticker), [str(item) for item in raw_phrases])
    return merged


def atomic_write_jsonl(path: Path, rows: Iterable[dict[str, Any]]) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    count = 0
    with tmp.open("w", encoding="utf-8") as fh:
        for row in rows:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")
            count += 1
    tmp.replace(path)
    return count


def parse_datetime_best_effort(value: Any) -> str:
    raw = normalize_space(value)
    if not raw:
        return ""
    candidate = raw.replace("Z", "+00:00")
    try:
        dt = datetime.datetime.fromisoformat(candidate)
        if dt.tzinfo is not None and dt.utcoffset() == datetime.timedelta(0):
            return dt.isoformat().replace("+00:00", "Z")
        return dt.isoformat()
    except Exception:
        pass
    try:
        dt = parsedate_to_datetime(raw)
        if dt.tzinfo is not None and dt.utcoffset() == datetime.timedelta(0):
            return dt.isoformat().replace("+00:00", "Z")
        return dt.isoformat()
    except Exception:
        pass
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
        try:
            dt = datetime.datetime.strptime(raw, fmt)
            return dt.isoformat()
        except Exception:
            continue
    return ""


def iso_date(value: str) -> str:
    text = str(value or "").strip()
    if not text:
        return ""
    if "T" in text:
        try:
            dt = datetime.datetime.fromisoformat(text.replace("Z", "+00:00"))
            return dt.date().isoformat()
        except Exception:
            return ""
    try:
        return datetime.date.fromisoformat(text).isoformat()
    except Exception:
        return ""


def _resolve_feed_target(base_dir: Path, value: str) -> tuple[str, bool]:
    raw = str(value or "").strip()
    if not raw:
        return "", False
    parsed = urllib.parse.urlparse(raw)
    if parsed.scheme in {"http", "https"}:
        return raw, False
    if parsed.scheme == "file":
        return Path(urllib.request.url2pathname(parsed.path)).expanduser().resolve().as_posix(), True
    as_path = Path(raw).expanduser()
    if not as_path.is_absolute():
        as_path = (base_dir / as_path).resolve()
    return str(as_path), True


def load_feed_targets(feed_urls: list[str], feeds_file: Path | None) -> list[tuple[str, bool]]:
    out: list[tuple[str, bool]] = []
    seen: set[str] = set()

    for raw in feed_urls:
        target, is_local = _resolve_feed_target(Path.cwd(), raw)
        if not target or target in seen:
            continue
        seen.add(target)
        out.append((target, is_local))

    if feeds_file is not None:
        base_dir = feeds_file.parent
        for line in feeds_file.read_text(encoding="utf-8").splitlines():
            body = line.split("#", 1)[0].strip()
            if not body:
                continue
            target, is_local = _resolve_feed_target(base_dir, body)
            if not target or target in seen:
                continue
            seen.add(target)
            out.append((target, is_local))
    return out


def fetch_http(url: str, timeout: float, retries: int, user_agent: str) -> str:
    attempts = max(1, int(retries) + 1)
    for idx in range(attempts):
        req = urllib.request.Request(
            url,
            headers={"User-Agent": user_agent, "Accept": "application/rss+xml, application/atom+xml, application/xml, text/xml"},
            method="GET",
        )
        try:
            with urllib.request.urlopen(req, timeout=max(1.0, float(timeout))) as resp:
                data = resp.read()
                charset = resp.headers.get_content_charset() or "utf-8"
            return data.decode(charset, errors="replace")
        except Exception:
            if idx >= attempts - 1:
                raise
            time.sleep(0.2 * float(idx + 1))
    raise RuntimeError("unreachable")


def fetch_feed_xml(target: str, is_local: bool, timeout: float, retries: int, user_agent: str) -> str:
    if is_local:
        return Path(target).read_text(encoding="utf-8")
    try:
        return fetch_http(target, timeout=timeout, retries=retries, user_agent=user_agent)
    except urllib.error.URLError as exc:
        raise RuntimeError(f"failed fetching feed '{target}': {exc}") from exc
    except Exception as exc:
        raise RuntimeError(f"failed fetching feed '{target}': {exc}") from exc


def _local_tag(tag: str) -> str:
    return tag.split("}", 1)[1] if "}" in tag else tag


def _find_child_text(parent: ET.Element, candidates: tuple[str, ...]) -> str:
    candidate_set = {value.lower() for value in candidates}
    for child in list(parent):
        if _local_tag(child.tag).lower() in candidate_set:
            return normalize_space(child.text or "")
    return ""


def _find_link(parent: ET.Element) -> str:
    for child in list(parent):
        if _local_tag(child.tag).lower() != "link":
            continue
        href = normalize_space(child.attrib.get("href") or "")
        if href:
            return normalize_url(href)
        text = normalize_space(child.text or "")
        if text:
            return normalize_url(text)
    guid = _find_child_text(parent, ("guid", "id"))
    if guid.startswith("http://") or guid.startswith("https://"):
        return normalize_url(guid)
    return ""


def parse_feed_items(feed_xml: str, feed_url: str) -> list[dict[str, str]]:
    try:
        root = ET.fromstring(feed_xml)
    except Exception as exc:
        raise RuntimeError(f"invalid feed XML: {feed_url} ({exc})") from exc

    items: list[ET.Element] = []
    root_name = _local_tag(root.tag).lower()
    if root_name == "rss":
        for channel in list(root):
            if _local_tag(channel.tag).lower() == "channel":
                for child in list(channel):
                    if _local_tag(child.tag).lower() == "item":
                        items.append(child)
    elif root_name == "feed":
        for child in list(root):
            if _local_tag(child.tag).lower() == "entry":
                items.append(child)
    else:
        for child in root.iter():
            if _local_tag(child.tag).lower() in {"item", "entry"}:
                items.append(child)

    out: list[dict[str, str]] = []
    for item in items:
        title = _find_child_text(item, ("title",))
        link = _find_link(item)
        published_raw = _find_child_text(item, ("pubdate", "published", "updated", "date", "dc:date"))
        summary = _find_child_text(item, ("description", "summary", "content", "content:encoded"))
        summary = strip_html(summary)
        if not title and not link:
            continue
        out.append(
            {
                "title": title,
                "url": link,
                "published_at_raw": published_raw,
                "summary": summary,
                "feed_url": feed_url,
            }
        )
    return out


def load_asx_tickers(path: Path) -> set[str]:
    if not path.exists():
        raise RuntimeError(f"ASX ticker file not found: {path}")
    out: set[str] = set()
    for line in path.read_text(encoding="utf-8").splitlines():
        body = line.split("#", 1)[0].strip()
        if not body:
            continue
        token = "".join(ch for ch in body.upper() if ch.isalnum())
        if token:
            out.add(token)
    return out


def _load_identity_helpers() -> tuple[Any | None, dict[str, Any]]:
    module_path = (REPO_ROOT / "financial-engine_v2" / "cockpit" / "integrations" / "qual_context.py").resolve()
    if not module_path.exists():
        return None, {}
    try:
        spec = importlib.util.spec_from_file_location("cockpit_integrations_qual_context_rss", str(module_path))
        if spec is None or spec.loader is None:
            return None, {}
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
    except Exception:
        return None, {}

    evaluate = getattr(mod, "evaluate_ticker_identity_strength", None)
    load_map = getattr(mod, "load_ticker_identity_map", None)
    serialize = getattr(mod, "ctx", None)
    if not callable(evaluate) or not callable(load_map):
        return None, {}

    helpers = {
        "evaluate": evaluate,
        "load_map": load_map,
        "serialize_tickers": getattr(mod, "ctx", None),
    }
    if serialize is not None and hasattr(serialize, "serialize_tickers"):
        helpers["serialize_tickers"] = serialize.serialize_tickers  # type: ignore[attr-defined]
    return helpers, DEFAULT_IDENTITY_CFG.copy()


def _load_identity_map_fallback(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    if not isinstance(payload, dict):
        return {}

    normalized: dict[str, Any] = {}
    for raw_ticker, raw_entry in payload.items():
        ticker = "".join(ch for ch in str(raw_ticker or "").upper() if ch.isalnum())
        if not ticker:
            continue
        entry = raw_entry if isinstance(raw_entry, dict) else {}
        clean_entry: dict[str, list[str]] = {}
        for key in ("canonical_names", "aliases"):
            raw_values = entry.get(key)
            values: list[str] = []
            if isinstance(raw_values, list):
                for value in raw_values:
                    text = normalize_space(value)
                    if text:
                        values.append(text)
            clean_entry[key] = values
        normalized[ticker] = clean_entry
    return normalized


def _serialize_tickers(values: list[str]) -> str:
    uniq = sorted({str(val).upper() for val in values if str(val).strip()})
    if not uniq:
        return ""
    if ctx is not None and hasattr(ctx, "serialize_tickers"):
        try:
            return str(ctx.serialize_tickers(uniq))
        except Exception:
            pass
    return "|" + "|".join(uniq) + "|"


def _candidate_tickers(title: str, body: str, allowlist: set[str]) -> set[str]:
    payload = f"{title}\n{body[:3000]}"
    payload_upper = payload.upper()
    out: set[str] = set()
    out.update(sym for sym in BOUNDARY_TOKEN_RE.findall(payload_upper) if sym in allowlist)
    out.update(sym.upper() for sym in ASX_PATTERN_RE.findall(payload_upper) if sym.upper() in allowlist)
    out.update(sym.upper() for sym in AX_SUFFIX_RE.findall(payload_upper) if sym.upper() in allowlist)
    return out


def _compile_ticker_keyword_pattern(keywords: list[str]) -> re.Pattern[str] | None:
    if not keywords:
        return None
    alternates: list[str] = []
    for token in keywords:
        cleaned = normalize_phrase_text(token)
        if not cleaned:
            continue
        escaped = re.escape(cleaned).replace(r"\ ", r"\s+")
        alternates.append(escaped)
    if not alternates:
        return None
    return re.compile(
        rf"(?<![A-Za-z0-9])([A-Z][A-Z0-9]{{1,5}})(?![A-Za-z0-9])\s+(?:{'|'.join(alternates)})\b",
        flags=re.IGNORECASE,
    )


def _title_has_finance_keyword(title: str, keywords: list[str]) -> bool:
    title_text = normalize_phrase_text(title)
    if not title_text:
        return False
    padded = f" {title_text} "
    for token in keywords:
        phrase = normalize_phrase_text(token)
        if phrase and f" {phrase} " in padded:
            return True
    return False


def _headline_token_candidates(
    *,
    title: str,
    allowlist: set[str],
    ticker_keyword_pattern: re.Pattern[str] | None,
) -> set[str]:
    out: set[str] = set()
    title_upper = str(title or "").upper()
    out.update(sym.upper() for sym in ASX_PATTERN_RE.findall(title_upper) if sym.upper() in allowlist)
    out.update(sym.upper() for sym in AX_SUFFIX_RE.findall(title_upper) if sym.upper() in allowlist)
    if ticker_keyword_pattern is not None:
        out.update(sym.upper() for sym in ticker_keyword_pattern.findall(title_upper) if sym.upper() in allowlist)
    return out


def _headline_matches_collision_phrase(
    *,
    title: str,
    ticker: str,
    collision_phrase_map: dict[str, list[str]],
) -> bool:
    symbol = str(ticker or "").upper()
    phrases = collision_phrase_map.get(symbol) or []
    if not phrases:
        return False
    title_norm = normalize_phrase_text(title)
    if not title_norm:
        return False
    padded_title = f" {title_norm} "
    for phrase in phrases:
        phrase_norm = normalize_phrase_text(phrase)
        if phrase_norm and f" {phrase_norm} " in padded_title:
            return True
    return False


def _build_ambiguous_ticker_set(
    *,
    identity_map: dict[str, Any],
    collision_phrase_map: dict[str, list[str]],
) -> set[str]:
    out: set[str] = {symbol for symbol in collision_phrase_map.keys() if symbol}
    term_to_tickers: dict[str, set[str]] = {}
    for raw_ticker, raw_entry in identity_map.items():
        ticker = "".join(ch for ch in str(raw_ticker or "").upper() if ch.isalnum())
        if not ticker:
            continue
        entry = raw_entry if isinstance(raw_entry, dict) else {}
        values: list[str] = []
        for key in ("canonical_names", "aliases"):
            raw_values = entry.get(key)
            if isinstance(raw_values, list):
                values.extend(str(item or "") for item in raw_values)
        for value in values:
            token = "".join(ch for ch in normalize_space(value).upper() if ch.isalnum())
            if not SHORT_ACRONYM_RE.fullmatch(token):
                continue
            term_to_tickers.setdefault(token, set()).add(ticker)
    for symbols in term_to_tickers.values():
        if len(symbols) > 1:
            out.update(symbols)
    return out


def _ticker_has_identity_name_match(
    *,
    ticker: str,
    title: str,
    body: str,
    identity_map: dict[str, Any],
) -> bool:
    entry = identity_map.get(ticker)
    if not isinstance(entry, dict):
        return False
    haystack = normalize_phrase_text(f"{title}\n{body}")
    if not haystack:
        return False
    padded_haystack = f" {haystack} "
    values: list[str] = []
    for key in ("canonical_names", "aliases"):
        raw_values = entry.get(key)
        if isinstance(raw_values, list):
            values.extend(str(item or "") for item in raw_values)
    for value in values:
        token = normalize_phrase_text(value)
        if token and f" {token} " in padded_haystack:
            return True
    return False


def _score_candidates_with_identity(
    *,
    candidates: set[str],
    title: str,
    body: str,
    source_domain: str,
    feed_url: str,
    identity_helpers: Any | None,
    identity_map: dict[str, Any],
    identity_cfg: dict[str, Any],
) -> tuple[list[str], list[str], dict[str, int]]:
    strength_counts = {
        "strong": 0,
        "medium": 0,
        "ambiguous": 0,
        "weak": 0,
        "none": 0,
    }
    if not candidates:
        return [], [], strength_counts
    if identity_helpers is None:
        keep = sorted(candidates)
        strength_counts["strong"] = len(keep)
        return keep, [], strength_counts

    evaluate = identity_helpers.get("evaluate")
    if not callable(evaluate):
        keep = sorted(candidates)
        strength_counts["strong"] = len(keep)
        return keep, [], strength_counts

    keep: list[str] = []
    ambiguous: list[str] = []
    for ticker in sorted(candidates):
        eval_cfg = dict(identity_cfg)
        feed_domain = parse_domain(feed_url)
        eval_cfg["_source_domain"] = source_domain
        eval_cfg["_source_is_au"] = bool(str(source_domain or "").lower().endswith(".au"))
        eval_cfg["_feed_is_au"] = bool(str(feed_domain or "").lower().endswith(".au"))
        strength = str(
            evaluate(
                ticker=ticker,
                title=title,
                body=body,
                identity_map=identity_map,
                config=eval_cfg,
            )
            or "none"
        ).lower()
        if strength in strength_counts:
            strength_counts[strength] += 1
        else:
            strength_counts["none"] += 1
        if strength in {"strong", "medium"}:
            keep.append(ticker)
        elif strength == "ambiguous":
            ambiguous.append(ticker)
    return keep, ambiguous, strength_counts


def build_rss_rows(
    *,
    feed_targets: list[tuple[str, bool]],
    asx_tickers_file: Path,
    identity_map_path: Path,
    ticker_token_keywords: list[str] | None,
    collision_phrase_map: dict[str, list[str]],
    corpus: str,
    topic: str,
    request_timeout: float,
    http_retries: int,
    user_agent: str,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    allowlist = load_asx_tickers(asx_tickers_file)
    identity_helpers, identity_cfg = _load_identity_helpers()
    identity_map: dict[str, Any] = _load_identity_map_fallback(identity_map_path)
    if identity_helpers is not None:
        loader = identity_helpers.get("load_map")
        if callable(loader):
            loaded = loader(str(identity_map_path))
            if isinstance(loaded, dict):
                identity_map = loaded
    ambiguous_ticker_set = _build_ambiguous_ticker_set(
        identity_map=identity_map,
        collision_phrase_map=collision_phrase_map,
    )
    normalized_keywords = parse_keyword_list(ticker_token_keywords)
    ticker_keyword_pattern = _compile_ticker_keyword_pattern(normalized_keywords)

    dedupe: set[str] = set()
    rows: list[dict[str, Any]] = []
    stats = {
        "feeds_total": len(feed_targets),
        "feeds_ok": 0,
        "feeds_failed": 0,
        "feeds_with_zero_items": 0,
        "items_seen": 0,
        "items_parsed_total": 0,
        "items_parsed_by_feed": {},
        "rows_emitted": 0,
        "duplicates_dropped": 0,
        "items_with_ticker": 0,
        "rows_without_ticker_after_identity": 0,
        "identity_strong": 0,
        "identity_medium": 0,
        "identity_ambiguous": 0,
        "identity_weak": 0,
        "identity_none": 0,
        "ticker_token_hits": 0,
        "ticker_token_accepted": 0,
        "ticker_token_rejected_ambiguous": 0,
    }

    for target, is_local in feed_targets:
        feed_url = target if not is_local else Path(target).resolve().as_posix()
        try:
            xml_text = fetch_feed_xml(
                target=target,
                is_local=is_local,
                timeout=request_timeout,
                retries=http_retries,
                user_agent=user_agent,
            )
        except Exception as exc:
            stats["feeds_failed"] += 1
            print(f"[warn] {exc}", file=sys.stderr)
            continue

        try:
            items = parse_feed_items(xml_text, feed_url=feed_url)
        except RuntimeError as exc:
            stats["feeds_failed"] += 1
            print(f"[warn] {exc}", file=sys.stderr)
            continue
        stats["feeds_ok"] += 1
        items_len = len(items)
        stats["items_parsed_total"] += items_len
        stats["items_parsed_by_feed"][feed_url] = items_len
        if items_len == 0:
            stats["feeds_with_zero_items"] += 1

        for item in items:
            stats["items_seen"] += 1
            title = normalize_space(item.get("title"))
            url = normalize_url(item.get("url"))
            summary = normalize_space(item.get("summary"))
            published_at_raw = normalize_space(item.get("published_at_raw"))
            published_at = parse_datetime_best_effort(published_at_raw)
            doc_date = iso_date(published_at)
            source_domain = parse_domain(url or feed_url)
            source = source_domain or parse_domain(feed_url) or "rss"
            body = summary or title

            dedupe_key = f"{url.lower()}||{title.lower()}"
            if dedupe_key in dedupe:
                stats["duplicates_dropped"] += 1
                continue
            dedupe.add(dedupe_key)

            candidates = _candidate_tickers(title=title, body=body, allowlist=allowlist)
            selected, ambiguous, strength_counts = _score_candidates_with_identity(
                candidates=candidates,
                title=title,
                body=body,
                source_domain=source_domain,
                feed_url=feed_url,
                identity_helpers=identity_helpers,
                identity_map=identity_map,
                identity_cfg=identity_cfg,
            )
            stats["identity_strong"] += int(strength_counts.get("strong", 0) or 0)
            stats["identity_medium"] += int(strength_counts.get("medium", 0) or 0)
            stats["identity_ambiguous"] += int(strength_counts.get("ambiguous", 0) or 0)
            stats["identity_weak"] += int(strength_counts.get("weak", 0) or 0)
            stats["identity_none"] += int(strength_counts.get("none", 0) or 0)
            ambiguous_set = set(ambiguous)
            row_strength = "none"
            if strength_counts.get("strong", 0):
                row_strength = "strong"
            elif strength_counts.get("medium", 0):
                row_strength = "medium"
            source_au_eligible = bool(
                str(source_domain or "").lower().endswith(".au")
                or str(parse_domain(feed_url) or "").lower().endswith(".au")
            )
            title_has_finance_keyword = _title_has_finance_keyword(title, normalized_keywords)

            token_accepted: list[str] = []
            token_rejected_ambiguous: list[str] = []
            token_candidates = _headline_token_candidates(
                title=title,
                allowlist=allowlist,
                ticker_keyword_pattern=ticker_keyword_pattern,
            )
            if token_candidates:
                stats["ticker_token_hits"] += len(token_candidates)
                for ticker in sorted(token_candidates):
                    is_ambiguous = bool(ticker in ambiguous_ticker_set)
                    if is_ambiguous:
                        collision_hit = _headline_matches_collision_phrase(
                            title=title,
                            ticker=ticker,
                            collision_phrase_map=collision_phrase_map,
                        )
                        if not (source_au_eligible and title_has_finance_keyword and not collision_hit):
                            token_rejected_ambiguous.append(ticker)
                            continue
                    token_accepted.append(ticker)
                if token_accepted:
                    stats["ticker_token_accepted"] += len(set(token_accepted))
                if token_rejected_ambiguous:
                    ambiguous_set.update(token_rejected_ambiguous)
                    stats["ticker_token_rejected_ambiguous"] += len(token_rejected_ambiguous)

            # Harden acronym collisions for selected identity hits.
            if selected:
                hardened_selected: list[str] = []
                local_strengths: list[str] = []
                for ticker in selected:
                    collision_hit = _headline_matches_collision_phrase(
                        title=title,
                        ticker=ticker,
                        collision_phrase_map=collision_phrase_map,
                    )
                    canonical_identity_hit = _ticker_has_identity_name_match(
                        ticker=ticker,
                        title=title,
                        body=body,
                        identity_map=identity_map,
                    )
                    if canonical_identity_hit:
                        hardened_selected.append(ticker)
                        local_strengths.append("strong")
                        continue
                    if ticker in ambiguous_ticker_set:
                        if source_au_eligible and title_has_finance_keyword and not collision_hit:
                            hardened_selected.append(ticker)
                            local_strengths.append("medium")
                        else:
                            ambiguous_set.add(ticker)
                        continue
                    hardened_selected.append(ticker)
                    local_strengths.append("medium")
                selected = sorted(set(hardened_selected))
                if local_strengths:
                    row_strength = "strong" if "strong" in local_strengths else "medium"

            if not selected and token_accepted:
                selected = sorted(set(token_accepted))
                if row_strength == "none":
                    row_strength = "medium"

            if not selected and ambiguous_set:
                row_strength = "ambiguous"
            ticker_blob = _serialize_tickers(selected)
            if ticker_blob:
                stats["items_with_ticker"] += 1
            elif candidates:
                stats["rows_without_ticker_after_identity"] += 1

            seed = f"{feed_url}\n{url}\n{title}\n{published_at}\n{ticker_blob}"
            row_id = "rss_" + hashlib.sha1(seed.encode("utf-8")).hexdigest()[:24]
            extra_fields: dict[str, Any] = {
                "feed_url": feed_url,
                "source_domain": source_domain,
                "feed_is_au": bool(parse_domain(feed_url).endswith(".au")),
                "published_at_raw": published_at_raw,
                "ticker_identity_strength": row_strength,
            }
            if ambiguous_set:
                extra_fields["ambiguous_tickers"] = sorted(ambiguous_set)
            if token_accepted:
                extra_fields["ticker_token_matched"] = sorted(set(token_accepted))
            if token_rejected_ambiguous:
                extra_fields["ticker_token_rejected_ambiguous"] = sorted(set(token_rejected_ambiguous))

            rows.append(
                {
                    "id": row_id,
                    "published_at": published_at,
                    "date": doc_date,
                    "title": title,
                    "text": (f"{title}\n\n{body}" if body and body.lower() != title.lower() else title).strip(),
                    "source": source,
                    "topic": topic,
                    "url": url,
                    "ticker": ticker_blob,
                    "corpus": corpus,
                    "extra_fields": extra_fields,
                }
            )

    stats["rows_emitted"] = len(rows)
    return rows, stats


def ingest_asx_rss_headlines(
    *,
    feed_urls: list[str],
    feeds_file: Path | None,
    out_jsonl: Path,
    asx_tickers_file: Path,
    identity_map_path: Path,
    ticker_token_keywords: list[str] | None = None,
    collision_phrases_path: Path | None = None,
    corpus: str = DEFAULT_CORPUS,
    topic: str = DEFAULT_TOPIC,
    request_timeout: float = 15.0,
    http_retries: int = 2,
    user_agent: str = "tenn-asx-rss-ingest/1.0",
    debug_print_stats: bool = False,
) -> dict[str, Any]:
    targets = load_feed_targets(feed_urls=feed_urls, feeds_file=feeds_file)
    if not targets:
        raise RuntimeError("No feed targets were provided. Use --feed-url and/or --feeds-file.")
    collision_phrase_map = load_collision_phrase_map(collision_phrases_path)

    rows, stats = build_rss_rows(
        feed_targets=targets,
        asx_tickers_file=asx_tickers_file,
        identity_map_path=identity_map_path,
        ticker_token_keywords=ticker_token_keywords,
        collision_phrase_map=collision_phrase_map,
        corpus=corpus,
        topic=topic,
        request_timeout=request_timeout,
        http_retries=http_retries,
        user_agent=user_agent,
    )
    count = atomic_write_jsonl(out_jsonl, rows)
    report = {
        "out_jsonl": str(out_jsonl),
        "corpus": corpus,
        "rows_written": count,
        "stats": stats,
    }
    if debug_print_stats:
        debug_payload = {
            "feeds_processed": int(stats.get("feeds_ok", 0) or 0),
            "feeds_failed": int(stats.get("feeds_failed", 0) or 0),
            "items_parsed_per_feed": stats.get("items_parsed_by_feed", {}),
            "rss_parsed_rows": int(stats.get("items_parsed_total", 0) or 0),
            "rss_fetch_rows": int(stats.get("items_seen", 0) or 0),
            "rows_emitted": int(stats.get("rows_emitted", 0) or 0),
            "identity_strong": int(stats.get("identity_strong", 0) or 0),
            "identity_medium": int(stats.get("identity_medium", 0) or 0),
            "identity_ambiguous": int(stats.get("identity_ambiguous", 0) or 0),
            "identity_weak": int(stats.get("identity_weak", 0) or 0),
            "identity_none": int(stats.get("identity_none", 0) or 0),
            "ticker_token_hits": int(stats.get("ticker_token_hits", 0) or 0),
            "ticker_token_accepted": int(stats.get("ticker_token_accepted", 0) or 0),
            "ticker_token_rejected_ambiguous": int(stats.get("ticker_token_rejected_ambiguous", 0) or 0),
            "rows_without_ticker_after_identity": int(stats.get("rows_without_ticker_after_identity", 0) or 0),
            "deduped_rows_removed": int(stats.get("duplicates_dropped", 0) or 0),
            "rows_written": int(count),
            "out_jsonl": str(out_jsonl),
        }
        print(json.dumps({"debug_rss_stats": debug_payload}, indent=2), file=sys.stderr)
    return report


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Ingest ASX RSS/Atom headlines into JSONL for build_news_context_db.py")
    ap.add_argument("--feed-url", action="append", default=[], help="RSS/Atom URL or local XML path (repeatable)")
    ap.add_argument("--feeds-file", default="", help="Optional newline-separated list of RSS/Atom URLs or local XML paths")
    ap.add_argument("--out-jsonl", default=str(DEFAULT_OUT_JSONL), help="Output JSONL path")
    ap.add_argument("--asx-tickers-file", default=str(DEFAULT_ASX_TICKERS), help="ASX universe file path")
    ap.add_argument("--identity-map-path", default=str(DEFAULT_IDENTITY_MAP), help="Ticker identity map JSON path")
    ap.add_argument(
        "--ticker-token-keyword",
        action="append",
        default=[],
        help="Finance keyword used for 'XYZ <keyword>' headline token detection (repeatable)",
    )
    ap.add_argument(
        "--ticker-collision-phrases-json",
        default="",
        help="Optional JSON mapping ticker->collision phrases that should block ambiguous token fallback",
    )
    ap.add_argument("--corpus", default=DEFAULT_CORPUS, help="Corpus label to stamp in emitted rows")
    ap.add_argument("--topic", default=DEFAULT_TOPIC, help="Topic label for emitted rows")
    ap.add_argument("--request-timeout", type=float, default=15.0, help="Feed HTTP timeout in seconds")
    ap.add_argument("--http-retries", type=int, default=2, help="HTTP retries per feed")
    ap.add_argument("--user-agent", default="tenn-asx-rss-ingest/1.0", help="HTTP User-Agent")
    ap.add_argument("--debug-print-stats", action="store_true", help="Print RSS parse/filter/dedupe debug counters")
    args = ap.parse_args(argv)

    feeds_file = Path(args.feeds_file).expanduser().resolve() if str(args.feeds_file or "").strip() else None
    if feeds_file is not None and not feeds_file.exists():
        print(f"Feeds file not found: {feeds_file}", file=sys.stderr)
        return 2

    out_jsonl = Path(args.out_jsonl).expanduser().resolve()
    asx_tickers_file = Path(args.asx_tickers_file).expanduser().resolve()
    identity_map_path = Path(args.identity_map_path).expanduser()
    if not identity_map_path.is_absolute():
        identity_map_path = (Path.cwd() / identity_map_path).resolve()
    collision_phrases_path = (
        Path(args.ticker_collision_phrases_json).expanduser().resolve()
        if str(args.ticker_collision_phrases_json or "").strip()
        else None
    )

    try:
        report = ingest_asx_rss_headlines(
            feed_urls=list(args.feed_url),
            feeds_file=feeds_file,
            out_jsonl=out_jsonl,
            asx_tickers_file=asx_tickers_file,
            identity_map_path=identity_map_path,
            ticker_token_keywords=list(args.ticker_token_keyword or []),
            collision_phrases_path=collision_phrases_path,
            corpus=str(args.corpus or DEFAULT_CORPUS).strip() or DEFAULT_CORPUS,
            topic=str(args.topic or DEFAULT_TOPIC).strip() or DEFAULT_TOPIC,
            request_timeout=float(args.request_timeout),
            http_retries=int(args.http_retries),
            user_agent=str(args.user_agent or "").strip() or "tenn-asx-rss-ingest/1.0",
            debug_print_stats=bool(args.debug_print_stats),
        )
    except Exception as exc:
        print(str(exc), file=sys.stderr)
        return 1

    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
