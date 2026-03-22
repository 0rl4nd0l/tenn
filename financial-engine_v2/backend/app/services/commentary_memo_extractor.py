from __future__ import annotations

import inspect
import json
import os
from pathlib import Path
from typing import Any, Callable

from app.services.llm import generate_json
from app.services.source_registry import RESEARCH_MEMORY_ROOT


DEFAULT_COMMENTARY_MEMOS_PATH = RESEARCH_MEMORY_ROOT / "commentary_memos.jsonl"
DEFAULT_LLAMACPP_URL = os.getenv("LLAMACPP_URL", "http://127.0.0.1:8001").rstrip("/")
DEFAULT_LLAMACPP_MODEL = os.getenv("LLAMACPP_MODEL", "model.gguf").strip()


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


def _normalize_list(value: Any, *, uppercase: bool = False) -> list[str]:
    if value in (None, ""):
        return []
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
        self.memos_path = Path(memos_path or DEFAULT_COMMENTARY_MEMOS_PATH).expanduser().resolve()

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
        return {
            "source_id": str(source_id or "").strip(),
            "speaker": normalized_speaker,
            "claims": _normalize_list(payload.get("claims")),
            "catalysts": _normalize_list(payload.get("catalysts")),
            "risks": _normalize_list(payload.get("risks")),
            "sentiment": str(payload.get("sentiment") or "").strip().lower(),
            "time_horizon": str(payload.get("time_horizon") or "").strip(),
            "tickers": _normalize_list(payload.get("tickers"), uppercase=True),
            "source_type": str(source_type or "").strip(),
            "published_at": str(published_at or "").strip(),
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
    ) -> dict[str, Any]:
        memo = self.extract(
            source_id=source_id,
            transcript_text=transcript_text,
            speaker=speaker,
            source_type=source_type,
            published_at=published_at,
        )
        return self.upsert(memo)
