from __future__ import annotations

import inspect
import json
import logging
import os
from pathlib import Path
from typing import Any, Callable

from app.services.llm import generate_json
from app.services.source_registry import RESEARCH_MEMORY_ROOT


DEFAULT_NEWS_MEMOS_PATH = RESEARCH_MEMORY_ROOT / "news_memos.jsonl"
DEFAULT_LLAMACPP_URL = os.getenv("LLAMACPP_URL", "http://127.0.0.1:8001").rstrip("/")
DEFAULT_LLAMACPP_MODEL = os.getenv("LLAMACPP_MODEL", "model.gguf").strip()

logger = logging.getLogger(__name__)

VALID_SENTIMENTS = frozenset({"bullish", "bearish", "neutral", "mixed"})
VALID_IMPACT_MAGNITUDES = frozenset({"material", "moderate", "minor"})


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


def _normalize_list(value: Any, *, uppercase: bool = False) -> list[str]:
    if value in (None, ""):
        return []
    items = value if isinstance(value, list) else [value]
    normalized: list[str] = []
    seen: set[str] = set()
    for item in items:
        text = str(item or "").strip()
        if not text:
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
    ) -> None:
        self.llm_fn = llm_fn or generate_json
        self.llm_url = str(llm_url or DEFAULT_LLAMACPP_URL).rstrip("/")
        self.llm_model = str(llm_model or DEFAULT_LLAMACPP_MODEL).strip()
        self.memos_path = (
            Path(memos_path or DEFAULT_NEWS_MEMOS_PATH).expanduser().resolve()
        )

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
    ) -> str:
        return (
            "You are a financial news analyst. Extract structured data from the following news article.\n"
            "Return only valid JSON with this schema:\n"
            '{"key_events":[],"sentiment":"bullish|bearish|neutral|mixed",'
            '"impact_magnitude":"material|moderate|minor",'
            '"tickers":[],"claims":[],"risks":[]}\n\n'
            f"Provider: {provider}\n"
            f"Published: {published_at or 'unknown'}\n\n"
            f"{article_text[:12000]}"
        )

    def _normalize_memo(
        self,
        *,
        raw_memo: Any,
        source_id: str,
        provider: str,
        published_at: str | None,
    ) -> dict[str, Any]:
        payload = dict(raw_memo or {})
        return {
            "source_id": str(source_id or "").strip(),
            "provider": str(provider or "").strip(),
            "key_events": _normalize_list(payload.get("key_events")),
            "sentiment": _normalize_sentiment(payload.get("sentiment")),
            "impact_magnitude": _normalize_impact_magnitude(
                payload.get("impact_magnitude")
            ),
            "tickers": _normalize_list(payload.get("tickers"), uppercase=True),
            "claims": _normalize_list(payload.get("claims")),
            "risks": _normalize_list(payload.get("risks")),
            "published_at": str(published_at or "").strip(),
        }

    def extract(
        self,
        *,
        source_id: str,
        article_text: str,
        provider: str,
        published_at: str | None = None,
    ) -> dict[str, Any]:
        raw_memo = self._call_llm(
            prompt=self._prompt(
                article_text=article_text,
                provider=provider,
                published_at=published_at,
            ),
            provider=provider,
            published_at=published_at,
        )
        return self._normalize_memo(
            raw_memo=raw_memo,
            source_id=source_id,
            provider=provider,
            published_at=published_at,
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
        route_signals: bool = True,
        company_memory_store=None,
        market_memory_store=None,
    ) -> dict[str, Any]:
        memo = self.extract(
            source_id=source_id,
            article_text=article_text,
            provider=provider,
            published_at=published_at,
        )
        stored = self.upsert(memo)
        if route_signals:
            try:
                from app.services.memory_signal_router import (
                    route_signals,
                    signals_from_news_memo,
                )

                route_signals(
                    signals_from_news_memo(stored),
                    company_memory_store=company_memory_store,
                    market_memory_store=market_memory_store,
                )
            except Exception as exc:
                logger.warning(
                    "news memo signal routing failed for %s: %s",
                    source_id,
                    exc,
                )
        return stored

    def extract_store_and_route(
        self,
        *,
        source_id: str,
        article_text: str,
        provider: str,
        published_at: str | None = None,
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
            route_signals=False,
        )
        signals = signals_from_news_memo(memo)
        routing = route_signals(
            signals,
            company_memory_store=company_memory_store,
            market_memory_store=market_memory_store,
        )
        return {"memo": memo, "signals": signals, "routing": routing}
