#!/usr/bin/env python3
"""
Quantify ASX news coverage using identity-aware ticker validation.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import re
import sqlite3
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from statistics import median
from typing import Any, Callable
from urllib.parse import urlparse


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from news_pipeline.cli_common import DEFAULT_NEWS_CONTEXT_DB, resolve_path  # noqa: E402

DEFAULT_NEWS_DB = DEFAULT_NEWS_CONTEXT_DB
DEFAULT_OUT_JSON = REPO_ROOT / "reports" / "analysis" / "asx_identity_coverage_baseline.json"
DEFAULT_CORPUS = "news"
DEFAULT_IDENTITY_MAP = "config/ticker_identity_map.json"
DEFAULT_IDENTITY_CFG: dict[str, Any] = {
    "enable_identity_hardening": True,
    "canonical_name_required_for_acronym": True,
    "acronym_min_length": 4,
    "downgrade_ambiguous_acronym_boost": 0.02,
}

BOUNDARY_TOKEN_RE = re.compile(r"(?<![A-Za-z0-9])([A-Z][A-Z0-9]{1,5})(?![A-Za-z0-9])")
ASX_PATTERN_RE = re.compile(r"\bASX\s*[:\-]\s*([A-Z][A-Z0-9]{1,5})\b", flags=re.IGNORECASE)
AX_SUFFIX_RE = re.compile(r"(?<![A-Za-z0-9])([A-Z][A-Z0-9]{1,5})\.AX(?![A-Za-z0-9])", flags=re.IGNORECASE)
DEFAULT_COLLISION_PHRASES: dict[str, tuple[str, ...]] = {
    "CSL": (
        "communications sales",
        "communications sales leasing",
        "communications sales and leasing",
        "leasing portfolio",
        "landlord",
        "reit",
    ),
}


def _iso_utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _safe_pct(part: int, total: int) -> float:
    if total <= 0:
        return 0.0
    return round((100.0 * float(part)) / float(total), 4)


def _atomic_write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True), encoding="utf-8")
    tmp.replace(path)


def _resolve_path(raw: str, *, prefer_repo_root: bool = False) -> Path:
    path = Path(str(raw or "").strip()).expanduser()
    if path.is_absolute():
        return path.resolve()
    if str(path).startswith("reports/qual_context/news"):
        return resolve_path(str(path))
    if prefer_repo_root:
        return (REPO_ROOT / path).resolve()
    cwd_candidate = (Path.cwd() / path).resolve()
    if cwd_candidate.exists():
        return cwd_candidate
    return (REPO_ROOT / path).resolve()


def _resolve_identity_map_path(raw: str) -> Path:
    base = _resolve_path(raw)
    if base.exists():
        return base
    rel = Path(str(raw or "").strip())
    if rel.is_absolute():
        return base
    alt = (REPO_ROOT / "financial-engine_v2" / rel).resolve()
    if alt.exists():
        return alt
    return alt


def _normalize_phrase(value: Any) -> str:
    return re.sub(r"[^a-z0-9]+", " ", str(value or "").lower()).strip()


def _fallback_load_ticker_identity_map(path: str) -> dict[str, Any]:
    target = _resolve_identity_map_path(path)
    if not target.exists() or not target.is_file():
        return {}
    try:
        payload = json.loads(target.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return payload if isinstance(payload, dict) else {}


def _fallback_evaluate_ticker_identity_strength(
    *,
    ticker: str,
    title: str,
    body: str,
    identity_map: dict[str, Any],
    config: dict[str, Any] | None = None,
) -> str:
    symbol = "".join(ch for ch in str(ticker or "").upper() if ch.isalnum())
    if not symbol:
        return "none"
    text = _normalize_phrase(f"{title}\n{body}")
    if not text:
        return "none"
    padded = f" {text} "
    entry = identity_map.get(symbol)
    if isinstance(entry, dict):
        for key in ("canonical_names", "aliases"):
            raw_values = entry.get(key)
            if not isinstance(raw_values, list):
                continue
            for raw in raw_values:
                token = _normalize_phrase(raw)
                if token and f" {token} " in padded:
                    return "strong"

    for phrase in DEFAULT_COLLISION_PHRASES.get(symbol, ()):
        normalized_phrase = _normalize_phrase(phrase)
        if normalized_phrase and f" {normalized_phrase} " in padded:
            return "ambiguous"

    cfg = dict(config or {})
    if bool(cfg.get("canonical_name_required_for_acronym", True)) and symbol in DEFAULT_COLLISION_PHRASES:
        return "ambiguous"
    return "medium"


def _load_identity_helpers() -> tuple[Callable[..., str], Callable[[str], dict[str, Any]]]:
    module_path = (REPO_ROOT / "financial-engine_v2" / "cockpit" / "integrations" / "qual_context.py").resolve()
    if not module_path.exists() or not module_path.is_file():
        return _fallback_evaluate_ticker_identity_strength, _fallback_load_ticker_identity_map

    spec = importlib.util.spec_from_file_location("cockpit_integrations_qual_context", str(module_path))
    if spec is None or spec.loader is None:
        return _fallback_evaluate_ticker_identity_strength, _fallback_load_ticker_identity_map
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)

    evaluate = getattr(module, "evaluate_ticker_identity_strength", None)
    load_map = getattr(module, "load_ticker_identity_map", None)
    if callable(evaluate) and callable(load_map):
        return evaluate, load_map
    return _fallback_evaluate_ticker_identity_strength, _fallback_load_ticker_identity_map


def _load_identity_config() -> dict[str, Any]:
    out = dict(DEFAULT_IDENTITY_CFG)
    cfg_path = REPO_ROOT / "financial-engine_v2" / "config" / "cockpit.yaml"
    if not cfg_path.exists() or not cfg_path.is_file():
        return out
    try:
        import yaml  # type: ignore
    except Exception:
        return out
    try:
        payload = yaml.safe_load(cfg_path.read_text(encoding="utf-8")) or {}
    except Exception:
        return out
    if not isinstance(payload, dict):
        return out
    rag = payload.get("rag")
    if not isinstance(rag, dict):
        return out
    news = rag.get("news_context")
    if not isinstance(news, dict):
        return out
    signal_weighting = news.get("signal_weighting")
    if not isinstance(signal_weighting, dict):
        return out
    identity_cfg = signal_weighting.get("ticker_identity")
    if not isinstance(identity_cfg, dict):
        return out
    for key, value in identity_cfg.items():
        out[key] = value
    return out


def _load_tickers(path: Path) -> list[str]:
    if not path.exists() or not path.is_file():
        raise FileNotFoundError(f"ASX ticker file not found: {path}")
    out: list[str] = []
    seen: set[str] = set()
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        body = raw_line.split("#", 1)[0].strip()
        if not body:
            continue
        token = "".join(ch for ch in body.upper() if ch.isalnum())
        if not token or token in seen:
            continue
        seen.add(token)
        out.append(token)
    out.sort()
    return out


def _extract_domain(row: sqlite3.Row, cols: set[str]) -> str:
    if "source_domain" in cols:
        direct = str(row["source_domain"] or "").strip().lower()
        if direct:
            return direct[4:] if direct.startswith("www.") else direct

    source = str(row["source"] or "").strip().lower() if "source" in cols else ""
    if source and "." in source and " " not in source:
        return source[4:] if source.startswith("www.") else source

    for key in ("url", "file"):
        if key not in cols:
            continue
        raw = str(row[key] or "").strip()
        if not raw:
            continue
        try:
            host = str(urlparse(raw).netloc or "").strip().lower()
        except Exception:
            host = ""
        if host:
            return host[4:] if host.startswith("www.") else host
    return ""


def _parse_ticker_blob(raw: str) -> set[str]:
    text = str(raw or "").strip()
    if not text:
        return set()
    parts = [part.strip().upper() for part in text.strip("|").split("|") if part.strip()]
    out: set[str] = set()
    for part in parts:
        sym = "".join(ch for ch in part if ch.isalnum())
        if sym:
            out.add(sym)
    return out


def _build_canonical_term_index(identity_map: dict[str, Any], asx_tickers: set[str]) -> list[tuple[str, set[str]]]:
    terms: dict[str, set[str]] = {}
    for ticker in sorted(asx_tickers):
        entry = identity_map.get(ticker)
        if not isinstance(entry, dict):
            continue
        values: list[str] = []
        for key in ("canonical_names", "aliases"):
            raw = entry.get(key)
            if isinstance(raw, list):
                values.extend(str(item).strip() for item in raw if str(item).strip())
        for value in values:
            token = value.lower()
            if not token:
                continue
            terms.setdefault(token, set()).add(ticker)
    return sorted(((term, tickers) for term, tickers in terms.items()), key=lambda item: item[0])


def _candidate_tickers(
    *,
    title: str,
    body: str,
    ticker_blob: str,
    asx_tickers: set[str],
    canonical_term_index: list[tuple[str, set[str]]],
) -> set[str]:
    payload = f"{title}\n{body[:4000]}"
    payload_upper = payload.upper()
    payload_lower = payload.lower()

    candidates: set[str] = set()
    candidates.update(sym for sym in _parse_ticker_blob(ticker_blob) if sym in asx_tickers)
    candidates.update(sym for sym in BOUNDARY_TOKEN_RE.findall(payload_upper) if sym in asx_tickers)
    candidates.update(sym.upper() for sym in ASX_PATTERN_RE.findall(payload_upper) if sym.upper() in asx_tickers)
    candidates.update(sym.upper() for sym in AX_SUFFIX_RE.findall(payload_upper) if sym.upper() in asx_tickers)

    for term, tickers in canonical_term_index:
        if term in payload_lower:
            candidates.update(tickers)
    return candidates


def quantify_asx_news_identity_coverage(
    *,
    news_db_path: Path,
    corpus: str,
    asx_tickers_file: Path,
    identity_map_path: Path,
) -> dict[str, Any]:
    generated_at_utc = _iso_utc_now()
    asx_tickers = _load_tickers(asx_tickers_file)
    asx_set = set(asx_tickers)
    evaluate_identity_strength, load_identity_map = _load_identity_helpers()
    identity_map = load_identity_map(str(identity_map_path))
    identity_cfg = _load_identity_config()
    canonical_term_index = _build_canonical_term_index(identity_map=identity_map, asx_tickers=asx_set)

    per_ticker_counts: dict[str, dict[str, int]] = {
        ticker: {"strong": 0, "medium": 0, "weak": 0, "ambiguous": 0} for ticker in asx_tickers
    }
    per_ticker_article_keys: dict[str, set[str]] = {ticker: set() for ticker in asx_tickers}

    total_chunks = 0
    unique_articles: set[str] = set()
    au_domain_counter: Counter[str] = Counter()
    asx_chunks_strong_or_medium = 0
    asx_chunks_ambiguous = 0
    asx_chunks_weak = 0

    if not news_db_path.exists() or not news_db_path.is_file():
        return {
            "generated_at_utc": generated_at_utc,
            "corpus": corpus,
            "total_chunks": 0,
            "unique_articles_estimated": 0,
            "error": f"news db not found: {news_db_path}",
            "asx_identity_summary": {
                "tickers_total": len(asx_tickers),
                "tickers_with_strong_or_medium_hits": 0,
                "tickers_zero_strong_hits": len(asx_tickers),
                "tickers_only_ambiguous": 0,
                "median_articles_per_ticker": 0.0,
                "asx_chunks_strong_or_medium": 0,
                "asx_chunks_ambiguous": 0,
                "asx_chunks_weak": 0,
                "pct_chunks_strong_or_medium": 0.0,
                "pct_chunks_ambiguous": 0.0,
            },
            "tickers_with_zero_strong_hits": list(asx_tickers),
            "tickers_with_only_ambiguous_hits": [],
            "top_au_domains": {},
            "per_ticker_identity_counts": per_ticker_counts,
        }

    conn = sqlite3.connect(str(news_db_path))
    conn.row_factory = sqlite3.Row
    try:
        cols = {
            str(row[1])
            for row in conn.execute("PRAGMA table_info(context_chunks)").fetchall()
        }
        if not cols:
            raise RuntimeError("context_chunks table not found")

        select_cols = [
            "title" if "title" in cols else "'' AS title",
            "text" if "text" in cols else "'' AS text",
            "url" if "url" in cols else "'' AS url",
            "file" if "file" in cols else "'' AS file",
            "source" if "source" in cols else "'' AS source",
            "source_domain" if "source_domain" in cols else "'' AS source_domain",
            "ticker" if "ticker" in cols else "'' AS ticker",
            "corpus" if "corpus" in cols else "'' AS corpus",
        ]
        sql = f"SELECT {', '.join(select_cols)} FROM context_chunks"
        args: list[Any] = []
        if corpus and "corpus" in cols:
            sql += " WHERE corpus = ?"
            args.append(corpus)

        for row in conn.execute(sql, tuple(args)):
            total_chunks += 1
            title = str(row["title"] or "")
            text = str(row["text"] or "")
            ticker_blob = str(row["ticker"] or "")
            article_key = str(row["url"] or "").strip() or str(row["title"] or "").strip().lower()
            if article_key:
                unique_articles.add(article_key)

            domain = _extract_domain(row=row, cols=cols)
            if domain.endswith(".au"):
                au_domain_counter[domain] += 1

            candidates = _candidate_tickers(
                title=title,
                body=text,
                ticker_blob=ticker_blob,
                asx_tickers=asx_set,
                canonical_term_index=canonical_term_index,
            )
            if not candidates:
                continue

            row_has_strong_or_medium = False
            row_has_ambiguous = False
            row_has_weak = False
            for ticker in sorted(candidates):
                strength = str(
                    evaluate_identity_strength(
                        ticker=ticker,
                        title=title,
                        body=text,
                        identity_map=identity_map,
                        config=identity_cfg,
                    )
                    or "none"
                ).lower()
                if strength in {"strong", "medium", "weak", "ambiguous"}:
                    per_ticker_counts[ticker][strength] += 1
                if strength in {"strong", "medium"}:
                    row_has_strong_or_medium = True
                    if article_key:
                        per_ticker_article_keys[ticker].add(article_key)
                elif strength == "ambiguous":
                    row_has_ambiguous = True
                elif strength == "weak":
                    row_has_weak = True

            if row_has_strong_or_medium:
                asx_chunks_strong_or_medium += 1
            elif row_has_ambiguous:
                asx_chunks_ambiguous += 1
            elif row_has_weak:
                asx_chunks_weak += 1
    finally:
        conn.close()

    tickers_with_strong_or_medium_hits = 0
    tickers_with_zero_strong_hits: list[str] = []
    tickers_with_only_ambiguous_hits: list[str] = []
    article_counts_for_median: list[int] = []
    for ticker in asx_tickers:
        counts = per_ticker_counts[ticker]
        valid_hits = int(counts["strong"]) + int(counts["medium"])
        if valid_hits > 0:
            tickers_with_strong_or_medium_hits += 1
        else:
            tickers_with_zero_strong_hits.append(ticker)
        if valid_hits == 0 and int(counts["ambiguous"]) > 0:
            tickers_with_only_ambiguous_hits.append(ticker)
        article_counts_for_median.append(len(per_ticker_article_keys[ticker]))

    top_au_domains = {
        domain: int(count)
        for domain, count in sorted(
            au_domain_counter.items(),
            key=lambda item: (-item[1], item[0]),
        )[:20]
    }

    return {
        "generated_at_utc": generated_at_utc,
        "corpus": corpus,
        "total_chunks": int(total_chunks),
        "unique_articles_estimated": int(len(unique_articles)),
        "asx_identity_summary": {
            "tickers_total": int(len(asx_tickers)),
            "tickers_with_strong_or_medium_hits": int(tickers_with_strong_or_medium_hits),
            "tickers_zero_strong_hits": int(len(tickers_with_zero_strong_hits)),
            "tickers_only_ambiguous": int(len(tickers_with_only_ambiguous_hits)),
            "median_articles_per_ticker": round(float(median(article_counts_for_median)), 4)
            if article_counts_for_median
            else 0.0,
            "asx_chunks_strong_or_medium": int(asx_chunks_strong_or_medium),
            "asx_chunks_ambiguous": int(asx_chunks_ambiguous),
            "asx_chunks_weak": int(asx_chunks_weak),
            "pct_chunks_strong_or_medium": _safe_pct(asx_chunks_strong_or_medium, total_chunks),
            "pct_chunks_ambiguous": _safe_pct(asx_chunks_ambiguous, total_chunks),
        },
        "tickers_with_zero_strong_hits": tickers_with_zero_strong_hits,
        "tickers_with_only_ambiguous_hits": tickers_with_only_ambiguous_hits,
        "top_au_domains": top_au_domains,
        "per_ticker_identity_counts": {ticker: per_ticker_counts[ticker] for ticker in asx_tickers},
    }


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description="Quantify ASX identity-aware news coverage from SQLite context chunks.")
    ap.add_argument("--news-db-path", default=str(DEFAULT_NEWS_DB), help="Path to news SQLite DB")
    ap.add_argument("--corpus", default=DEFAULT_CORPUS, help="Corpus filter to evaluate")
    ap.add_argument("--asx-tickers-file", required=True, help="Path to ASX tickers file (one ticker per line)")
    ap.add_argument("--identity-map-path", default=DEFAULT_IDENTITY_MAP, help="Ticker identity map JSON path")
    ap.add_argument("--out-json", default=str(DEFAULT_OUT_JSON), help="Output JSON path")
    return ap


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    news_db_path = _resolve_path(args.news_db_path)
    asx_tickers_file = _resolve_path(args.asx_tickers_file)
    identity_map_path = _resolve_identity_map_path(args.identity_map_path)
    out_json = _resolve_path(args.out_json)

    try:
        payload = quantify_asx_news_identity_coverage(
            news_db_path=news_db_path,
            corpus=str(args.corpus or "").strip(),
            asx_tickers_file=asx_tickers_file,
            identity_map_path=identity_map_path,
        )
    except Exception as exc:
        payload = {
            "generated_at_utc": _iso_utc_now(),
            "corpus": str(args.corpus or "").strip(),
            "total_chunks": 0,
            "unique_articles_estimated": 0,
            "error": str(exc),
            "asx_identity_summary": {
                "tickers_total": 0,
                "tickers_with_strong_or_medium_hits": 0,
                "tickers_zero_strong_hits": 0,
                "tickers_only_ambiguous": 0,
                "median_articles_per_ticker": 0.0,
                "asx_chunks_strong_or_medium": 0,
                "asx_chunks_ambiguous": 0,
                "asx_chunks_weak": 0,
                "pct_chunks_strong_or_medium": 0.0,
                "pct_chunks_ambiguous": 0.0,
            },
            "tickers_with_zero_strong_hits": [],
            "tickers_with_only_ambiguous_hits": [],
            "top_au_domains": {},
            "per_ticker_identity_counts": {},
        }
        print(f"[warn] coverage quantification failed: {exc}", file=sys.stderr)

    _atomic_write_json(out_json, payload)
    print(json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
