from __future__ import annotations

import inspect
import html
import json
import logging
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from app.services.llm import generate_json
from app.services.source_registry import RESEARCH_MEMORY_ROOT


DEFAULT_NEWS_MEMOS_PATH = RESEARCH_MEMORY_ROOT / "news_memos.jsonl"
DEFAULT_LLAMACPP_URL = os.getenv("LLAMACPP_URL", "http://127.0.0.1:8001").rstrip("/")
DEFAULT_LLAMACPP_MODEL = os.getenv("LLAMACPP_MODEL", "model.gguf").strip()
DEFAULT_NEWS_MEMO_MAX_ARTICLE_CHARS = 5000

logger = logging.getLogger(__name__)

VALID_SENTIMENTS = frozenset({"bullish", "bearish", "neutral", "mixed"})
VALID_IMPACT_MAGNITUDES = frozenset({"material", "moderate", "minor"})
EXCHANGE_TICKER_PATTERN = re.compile(
    r"\b(?:ASX|NYSE|NASDAQ|TSX|TSXV|TSE|LSE|AIM|OTCMKTS|OTC)\s*:\s*"
    r"([A-Z][A-Z0-9.\-]{0,12})\b",
    re.IGNORECASE,
)


def _today_iso_utc() -> str:
    return datetime.now(timezone.utc).date().isoformat()


def resolve_news_memo_max_article_chars(value: int | str | None = None) -> int:
    raw_value = value
    if raw_value in (None, ""):
        raw_value = os.getenv("NEWS_MEMO_MAX_ARTICLE_CHARS", "")
    if raw_value in (None, ""):
        return DEFAULT_NEWS_MEMO_MAX_ARTICLE_CHARS
    try:
        return max(1, int(raw_value))
    except (TypeError, ValueError) as exc:
        raise ValueError("NEWS_MEMO_MAX_ARTICLE_CHARS must be a positive integer") from exc


def _clean_article_text_for_prompt(text: str) -> str:
    cleaned = html.unescape(str(text or ""))
    cleaned = re.sub(
        r"<script\b[^>]*>.*?</script>|<style\b[^>]*>.*?</style>",
        " ",
        cleaned,
        flags=re.IGNORECASE | re.DOTALL,
    )
    cleaned = re.sub(r"<[^>]+>", " ", cleaned)
    return re.sub(r"\s+", " ", cleaned).strip()


def _normalize_ticker_candidate(value: Any) -> str:
    raw = str(value or "").strip().upper()
    if ":" in raw:
        raw = raw.split(":", 1)[1]
    raw = re.sub(r"[^A-Z0-9.\-]", "", raw)
    return raw[:16]


def _exchange_ticker_candidates(text: str) -> list[str]:
    candidates: list[str] = []
    seen: set[str] = set()
    for match in EXCHANGE_TICKER_PATTERN.finditer(str(text or "")):
        candidate = _normalize_ticker_candidate(match.group(1))
        if not candidate or candidate in seen:
            continue
        seen.add(candidate)
        candidates.append(candidate)
    return candidates


def _normalize_candidate_tickers(value: Any) -> list[str]:
    if value in (None, ""):
        return []
    items = value if isinstance(value, list) else [value]
    normalized: list[str] = []
    seen: set[str] = set()
    for item in items:
        candidate = _normalize_ticker_candidate(item)
        if not candidate or candidate in seen:
            continue
        seen.add(candidate)
        normalized.append(candidate)
    return normalized


def _write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")


def load_news_memos(path: str | Path | None = None) -> list[dict[str, Any]]:
    memo_path = Path(path or DEFAULT_NEWS_MEMOS_PATH).expanduser().resolve()
    if not memo_path.exists():
        return []
    rows: list[dict[str, Any]] = []
    with memo_path.open("r", encoding="utf-8") as handle:
        for lineno, raw_line in enumerate(handle, start=1):
            text = raw_line.strip()
            if not text:
                continue
            payload = json.loads(text)
            if not isinstance(payload, dict):
                raise RuntimeError(f"news memo row {lineno} is not a JSON object")
            rows.append(payload)
    return rows


def _normalize_list(
    value: Any, *, uppercase: bool = False, field_name: str = ""
) -> list[str]:
    if value in (None, ""):
        return []
    if not isinstance(value, list):
        logger.warning(
            "news_memo_extractor: _normalize_list coerced non-list value for field %r "
            "(type=%s, value=%r) — LLM may have returned malformed JSON",
            field_name or "<unknown>",
            type(value).__name__,
            value,
        )
    items = value if isinstance(value, list) else [value]
    normalized: list[str] = []
    seen: set[str] = set()
    for item in items:
        if isinstance(item, (dict, list, tuple, set)):
            logger.warning(
                "news_memo_extractor: dropped non-scalar list item for field %r "
                "(type=%s, value=%r)",
                field_name or "<unknown>",
                type(item).__name__,
                item,
            )
            continue
        text = str(item or "").strip()
        if not text:
            continue
        if text.startswith("{") or text.startswith("["):
            logger.warning(
                "news_memo_extractor: dropped dictlike string item for field %r "
                "(value=%r)",
                field_name or "<unknown>",
                text,
            )
            continue
        candidate = text.upper() if uppercase else text
        if candidate in seen:
            continue
        seen.add(candidate)
        normalized.append(candidate)
    return normalized


def _normalize_sentiment(value: Any) -> str:
    raw = str(value or "").strip().lower()
    return raw if raw in VALID_SENTIMENTS else ""


def _normalize_impact_magnitude(value: Any) -> str:
    raw = str(value or "").strip().lower()
    return raw if raw in VALID_IMPACT_MAGNITUDES else ""


class NewsMemoExtractor:
    def __init__(
        self,
        *,
        llm_fn: Callable[..., Any] | None = None,
        llm_url: str | None = None,
        llm_model: str | None = None,
        memos_path: str | Path | None = None,
        max_article_chars: int | str | None = None,
    ) -> None:
        self.llm_fn = llm_fn or generate_json
        self.llm_url = str(llm_url or DEFAULT_LLAMACPP_URL).rstrip("/")
        self.llm_model = str(llm_model or DEFAULT_LLAMACPP_MODEL).strip()
        self.memos_path = (
            Path(memos_path or DEFAULT_NEWS_MEMOS_PATH).expanduser().resolve()
        )
        self.max_article_chars = resolve_news_memo_max_article_chars(max_article_chars)

    def _call_llm(
        self,
        *,
        prompt: str,
        provider: str,
        published_at: str | None,
    ) -> Any:
        metadata = {
            "task_type": "reasoning",
            "component": "news_memo_extractor",
            "operation": "news_memo",
            "provider": provider,
            "published_at": str(published_at or "").strip(),
            "llm_url": self.llm_url,
            "llm_model": self.llm_model,
        }
        try:
            signature = inspect.signature(self.llm_fn)
        except (TypeError, ValueError):
            signature = None

        if signature and "metadata" in signature.parameters:
            return self.llm_fn(prompt=prompt, metadata=metadata)

        return self.llm_fn(
            base_url=self.llm_url,
            model=self.llm_model,
            prompt=prompt,
        )

    def _prompt(
        self,
        *,
        article_text: str,
        provider: str,
        published_at: str | None,
        candidate_tickers: list[str] | None = None,
    ) -> str:
        today_iso = _today_iso_utc()
        cleaned_article = _clean_article_text_for_prompt(article_text)[
            : self.max_article_chars
        ]
        candidates = _normalize_candidate_tickers(
            candidate_tickers
            if candidate_tickers is not None
            else _exchange_ticker_candidates(cleaned_article)
        )
        candidate_text = ", ".join(candidates) if candidates else "NONE"
        return (
            "You are a financial news memo extractor. Extract only information directly supported by the article text.\n"
            f"Today's date is {today_iso}. Treat the published date and any dates in the article as historical context.\n"
            "Return only valid JSON with this exact schema:\n"
            '{"key_events":[],"sentiment":"bullish|bearish|neutral|mixed",'
            '"impact_magnitude":"material|moderate|minor",'
            '"tickers":[],"claims":[],"risks":[]}\n'
            "Rules:\n"
            "- key_events, claims, and risks must be arrays of plain strings, not objects.\n"
            "- tickers must be chosen only from CANDIDATE_TICKERS. If CANDIDATE_TICKERS is NONE, return [].\n"
            "- Do not output company names, index names, or inferred symbols as tickers.\n"
            "- Claims and risks must be short and grounded in the article text; omit weak or generic claims.\n"
            "- Prefer neutral sentiment unless the article gives clear price, earnings, guidance, deal, recall, downgrade, or risk evidence.\n\n"
            f"Provider: {provider}\n"
            f"Published: {published_at or 'unknown'}\n"
            f"CANDIDATE_TICKERS: {candidate_text}\n\n"
            f"ARTICLE:\n{cleaned_article}"
        )

    def _normalize_memo(
        self,
        *,
        raw_memo: Any,
        source_id: str,
        provider: str,
        published_at: str | None,
        candidate_tickers: list[str] | None = None,
    ) -> dict[str, Any]:
        payload = dict(raw_memo or {})
        key_events = _normalize_list(payload.get("key_events"), field_name="key_events")
        raw_tickers = _normalize_list(
            payload.get("tickers"), uppercase=True, field_name="tickers"
        )
        allowed_tickers = (
            set(_normalize_candidate_tickers(candidate_tickers))
            if candidate_tickers is not None
            else None
        )
        tickers: list[str] = []
        for ticker in raw_tickers:
            normalized = _normalize_ticker_candidate(ticker)
            if not normalized:
                continue
            if allowed_tickers is not None and normalized not in allowed_tickers:
                logger.warning(
                    "news_memo_extractor: dropped ticker outside candidate allowlist "
                    "for source_id=%r ticker=%r candidates=%r",
                    str(source_id or "").strip(),
                    ticker,
                    sorted(allowed_tickers),
                )
                continue
            if normalized not in tickers:
                tickers.append(normalized)
        claims = _normalize_list(payload.get("claims"), field_name="claims")
        risks = _normalize_list(payload.get("risks"), field_name="risks")
        sentiment = _normalize_sentiment(payload.get("sentiment"))
        impact_magnitude = _normalize_impact_magnitude(payload.get("impact_magnitude"))
        if not any([key_events, tickers, claims, risks, sentiment, impact_magnitude]):
            logger.warning(
                "news_memo_extractor: all extracted fields are empty for source_id=%r "
                "provider=%r — LLM may have returned garbage or failed silently; "
                "document will be stored as an empty memo and will not be re-extracted",
                str(source_id or "").strip(),
                str(provider or "").strip(),
            )
        return {
            "source_id": str(source_id or "").strip(),
            "provider": str(provider or "").strip(),
            "key_events": key_events,
            "sentiment": sentiment,
            "impact_magnitude": impact_magnitude,
            "tickers": tickers,
            "claims": claims,
            "risks": risks,
            "published_at": str(published_at or "").strip(),
            "extraction_provenance": {
                "component": "news_memo_extractor",
                "llm_model": self.llm_model,
                "llm_url": self.llm_url,
                "max_article_chars": self.max_article_chars,
            },
        }

    def extract(
        self,
        *,
        source_id: str,
        article_text: str,
        provider: str,
        published_at: str | None = None,
        candidate_tickers: list[str] | None = None,
    ) -> dict[str, Any]:
        resolved_candidate_tickers = (
            _normalize_candidate_tickers(candidate_tickers)
            if candidate_tickers is not None
            else _exchange_ticker_candidates(_clean_article_text_for_prompt(article_text))
        )
        raw_memo = self._call_llm(
            prompt=self._prompt(
                article_text=article_text,
                provider=provider,
                published_at=published_at,
                candidate_tickers=resolved_candidate_tickers,
            ),
            provider=provider,
            published_at=published_at,
        )
        return self._normalize_memo(
            raw_memo=raw_memo,
            source_id=source_id,
            provider=provider,
            published_at=published_at,
            candidate_tickers=resolved_candidate_tickers,
        )

    def upsert(self, memo: dict[str, Any]) -> dict[str, Any]:
        source_id = str(memo.get("source_id") or "").strip()
        if not source_id:
            raise ValueError("memo source_id is required")
        rows = load_news_memos(self.memos_path)
        merged: list[dict[str, Any]] = []
        replaced = False
        for row in rows:
            if str(row.get("source_id") or "") == source_id:
                merged.append(dict(memo))
                replaced = True
            else:
                merged.append(row)
        if not replaced:
            merged.append(dict(memo))
        merged.sort(key=lambda row: str(row.get("source_id") or ""))
        _write_jsonl(self.memos_path, merged)
        return dict(memo)

    def extract_and_store(
        self,
        *,
        source_id: str,
        article_text: str,
        provider: str,
        published_at: str | None = None,
        candidate_tickers: list[str] | None = None,
        route_signals: bool = True,
        company_memory_store=None,
        market_memory_store=None,
    ) -> dict[str, Any]:
        memo = self.extract(
            source_id=source_id,
            article_text=article_text,
            provider=provider,
            published_at=published_at,
            candidate_tickers=candidate_tickers,
        )
        stored = self.upsert(memo)
        result = dict(stored)
        if route_signals:
            try:
                from app.services.memory_signal_router import (
                    route_signals,
                    signals_from_news_memo,
                )

                routing = route_signals(
                    signals_from_news_memo(stored),
                    company_memory_store=company_memory_store,
                    market_memory_store=market_memory_store,
                )
                result["signal_routing"] = {"status": "ok", **routing}
            except Exception as exc:
                logger.warning(
                    "news memo signal routing failed for %s: %s",
                    source_id,
                    exc,
                )
                result["signal_routing"] = {
                    "status": "error",
                    "error": str(exc),
                }
        return result

    def extract_store_and_route(
        self,
        *,
        source_id: str,
        article_text: str,
        provider: str,
        published_at: str | None = None,
        candidate_tickers: list[str] | None = None,
        company_memory_store=None,
        market_memory_store=None,
    ) -> dict[str, Any]:
        from app.services.memory_signal_router import (
            route_signals,
            signals_from_news_memo,
        )

        memo = self.extract_and_store(
            source_id=source_id,
            article_text=article_text,
            provider=provider,
            published_at=published_at,
            candidate_tickers=candidate_tickers,
            route_signals=False,
        )
        signals = signals_from_news_memo(memo)
        routing = route_signals(
            signals,
            company_memory_store=company_memory_store,
            market_memory_store=market_memory_store,
        )
        return {"memo": memo, "signals": signals, "routing": routing}
