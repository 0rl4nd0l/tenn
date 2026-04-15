from __future__ import annotations

import inspect
import json
import logging
import os
from collections import Counter
from pathlib import Path
from typing import Any, Callable

from app.services.llm import generate_json
from app.services.source_registry import RESEARCH_MEMORY_ROOT


DEFAULT_COMMENTARY_MEMOS_PATH = RESEARCH_MEMORY_ROOT / "commentary_memos.jsonl"
DEFAULT_LLAMACPP_URL = os.getenv("LLAMACPP_URL", "http://127.0.0.1:8001").rstrip("/")
DEFAULT_LLAMACPP_MODEL = os.getenv("LLAMACPP_MODEL", "model.gguf").strip()

logger = logging.getLogger(__name__)

MULTIPASS_WINDOW_SIZE = 12_000
MULTIPASS_OVERLAP = 3_000


def _write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")


def load_commentary_memos(path: str | Path | None = None) -> list[dict[str, Any]]:
    memo_path = Path(path or DEFAULT_COMMENTARY_MEMOS_PATH).expanduser().resolve()
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
                raise RuntimeError(f"commentary memo row {lineno} is not a JSON object")
            rows.append(payload)
    return rows


def _normalize_list(
    value: Any, *, uppercase: bool = False, field_name: str = ""
) -> list[str]:
    if value in (None, ""):
        return []
    if not isinstance(value, list):
        logger.warning(
            "commentary_memo_extractor: _normalize_list coerced non-list value for "
            "field %r (type=%s, value=%r) — LLM may have returned malformed JSON",
            field_name or "<unknown>",
            type(value).__name__,
            value,
        )
    items = value if isinstance(value, list) else [value]
    normalized: list[str] = []
    seen = set()
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


def _dedup_normalized(items: list[str]) -> list[str]:
    """Deduplicate strings by lowercase+strip, preserving first occurrence."""
    seen: set[str] = set()
    result: list[str] = []
    for item in items:
        key = item.strip().lower()
        if key and key not in seen:
            seen.add(key)
            result.append(item)
    return result


_TIME_HORIZON_RANK: dict[str, int] = {
    "short-term": 0,
    "short term": 0,
    "near-term": 1,
    "near term": 1,
    "medium-term": 2,
    "medium term": 2,
    "mid-term": 2,
    "mid term": 2,
    "long-term": 3,
    "long term": 3,
}


class CommentaryMemoExtractor:
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
            Path(memos_path or DEFAULT_COMMENTARY_MEMOS_PATH).expanduser().resolve()
        )

    def _call_llm(
        self,
        *,
        prompt: str,
        source_type: str,
        speaker: str,
        published_at: str | None,
    ) -> Any:
        metadata = {
            "task_type": "reasoning",
            "component": "commentary_memo_extractor",
            "operation": "commentary_memo",
            "source_type": source_type,
            "speaker": speaker,
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
        transcript_text: str,
        speaker: str,
        source_type: str,
        published_at: str | None,
    ) -> str:
        return (
            "Return only valid JSON with this schema:\n"
            '{"speaker":"","claims":[],"catalysts":[],"risks":[],"sentiment":"","time_horizon":"","tickers":[]}\n'
            f"{transcript_text[:12000]}"
        )

    def _normalize_memo(
        self,
        *,
        raw_memo: Any,
        source_id: str,
        speaker: str,
        source_type: str,
        published_at: str | None,
    ) -> dict[str, Any]:
        payload = dict(raw_memo or {})
        normalized_speaker = str(payload.get("speaker") or speaker or "").strip()
        claims = _normalize_list(payload.get("claims"), field_name="claims")
        catalysts = _normalize_list(payload.get("catalysts"), field_name="catalysts")
        risks = _normalize_list(payload.get("risks"), field_name="risks")
        tickers = _normalize_list(
            payload.get("tickers"), uppercase=True, field_name="tickers"
        )
        sentiment = str(payload.get("sentiment") or "").strip().lower()
        time_horizon = str(payload.get("time_horizon") or "").strip()
        if not any([claims, catalysts, risks, tickers, sentiment, time_horizon]):
            logger.warning(
                "commentary_memo_extractor: all extracted fields are empty for "
                "source_id=%r speaker=%r — LLM may have returned garbage or failed "
                "silently; document will be stored as an empty memo and will not be "
                "re-extracted",
                str(source_id or "").strip(),
                normalized_speaker,
            )
        return {
            "source_id": str(source_id or "").strip(),
            "speaker": normalized_speaker,
            "claims": claims,
            "catalysts": catalysts,
            "risks": risks,
            "sentiment": sentiment,
            "time_horizon": time_horizon,
            "tickers": tickers,
            "source_type": str(source_type or "").strip(),
            "published_at": str(published_at or "").strip(),
        }

    def _extract_multipass(
        self,
        *,
        transcript_text: str,
        speaker: str,
        source_type: str,
        published_at: str | None,
    ) -> dict[str, Any]:
        """Split a long transcript into overlapping windows and merge LLM results."""
        step = MULTIPASS_WINDOW_SIZE - MULTIPASS_OVERLAP
        windows: list[str] = []
        offset = 0
        while offset < len(transcript_text):
            windows.append(transcript_text[offset : offset + MULTIPASS_WINDOW_SIZE])
            offset += step

        all_claims: list[str] = []
        all_catalysts: list[str] = []
        all_risks: list[str] = []
        all_tickers: list[str] = []
        sentiments: list[str] = []
        time_horizons: list[str] = []

        for window in windows:
            raw = self._call_llm(
                prompt=self._prompt(
                    transcript_text=window,
                    speaker=speaker,
                    source_type=source_type,
                    published_at=published_at,
                ),
                source_type=source_type,
                speaker=speaker,
                published_at=published_at,
            )
            payload = dict(raw or {})
            all_claims.extend(_normalize_list(payload.get("claims")))
            all_catalysts.extend(_normalize_list(payload.get("catalysts")))
            all_risks.extend(_normalize_list(payload.get("risks")))
            all_tickers.extend(_normalize_list(payload.get("tickers"), uppercase=True))

            sentiment = str(payload.get("sentiment") or "").strip().lower()
            if sentiment:
                sentiments.append(sentiment)

            horizon = str(payload.get("time_horizon") or "").strip()
            if horizon:
                time_horizons.append(horizon)

        # Pick most common sentiment; fall back to first if tie
        merged_sentiment = ""
        if sentiments:
            merged_sentiment = Counter(sentiments).most_common(1)[0][0]

        # Pick earliest (shortest-range) time horizon
        merged_horizon = ""
        if time_horizons:
            merged_horizon = min(
                time_horizons,
                key=lambda h: _TIME_HORIZON_RANK.get(h.lower(), 99),
            )

        return {
            "speaker": speaker,
            "claims": _dedup_normalized(all_claims),
            "catalysts": _dedup_normalized(all_catalysts),
            "risks": _dedup_normalized(all_risks),
            "sentiment": merged_sentiment,
            "time_horizon": merged_horizon,
            "tickers": _dedup_normalized(all_tickers),
        }

    def extract(
        self,
        *,
        source_id: str,
        transcript_text: str,
        speaker: str,
        source_type: str,
        published_at: str | None = None,
    ) -> dict[str, Any]:
        if len(transcript_text) > MULTIPASS_WINDOW_SIZE:
            raw_memo = self._extract_multipass(
                transcript_text=transcript_text,
                speaker=speaker,
                source_type=source_type,
                published_at=published_at,
            )
        else:
            raw_memo = self._call_llm(
                prompt=self._prompt(
                    transcript_text=transcript_text,
                    speaker=speaker,
                    source_type=source_type,
                    published_at=published_at,
                ),
                source_type=source_type,
                speaker=speaker,
                published_at=published_at,
            )
        return self._normalize_memo(
            raw_memo=raw_memo,
            source_id=source_id,
            speaker=speaker,
            source_type=source_type,
            published_at=published_at,
        )

    def upsert(self, memo: dict[str, Any]) -> dict[str, Any]:
        source_id = str(memo.get("source_id") or "").strip()
        if not source_id:
            raise ValueError("memo source_id is required")
        rows = load_commentary_memos(self.memos_path)
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
        transcript_text: str,
        speaker: str,
        source_type: str,
        published_at: str | None = None,
        route_signals: bool = True,
        company_memory_store=None,
        market_memory_store=None,
    ) -> dict[str, Any]:
        memo = self.extract(
            source_id=source_id,
            transcript_text=transcript_text,
            speaker=speaker,
            source_type=source_type,
            published_at=published_at,
        )
        stored = self.upsert(memo)
        if route_signals:
            try:
                from app.services.memory_signal_router import (
                    route_signals,
                    signals_from_commentary_memo,
                )

                route_signals(
                    signals_from_commentary_memo(stored),
                    company_memory_store=company_memory_store,
                    market_memory_store=market_memory_store,
                )
            except Exception as exc:
                logger.warning(
                    "commentary memo signal routing failed for %s: %s",
                    source_id,
                    exc,
                )
        return stored

    def extract_store_and_route(
        self,
        *,
        source_id: str,
        transcript_text: str,
        speaker: str,
        source_type: str,
        published_at: str | None = None,
        company_memory_store=None,
        market_memory_store=None,
    ) -> dict[str, Any]:
        from app.services.memory_signal_router import (
            route_signals,
            signals_from_commentary_memo,
        )

        memo = self.extract_and_store(
            source_id=source_id,
            transcript_text=transcript_text,
            speaker=speaker,
            source_type=source_type,
            published_at=published_at,
            route_signals=False,
        )
        signals = signals_from_commentary_memo(memo)
        routing = route_signals(
            signals,
            company_memory_store=company_memory_store,
            market_memory_store=market_memory_store,
        )
        return {"memo": memo, "signals": signals, "routing": routing}
