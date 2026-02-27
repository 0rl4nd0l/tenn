from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Optional


@dataclass(frozen=True)
class ArticleCandidate:
    provider: str
    provider_item_id: str
    canonical_url: str
    title: str
    description: str
    body: str
    source_name: str
    language: str
    published_at_utc: str
    fetched_at_utc: str
    provider_published_at_raw: str = ""
    raw_payload: Dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class EntityLink:
    article_id: str
    ticker: str
    confidence: float
    lane: str
    method: str
    matched_alias: str
    matched_span_start: Optional[int]
    matched_span_end: Optional[int]
    published_at_utc: str


@dataclass(frozen=True)
class UpsertResult:
    article_id: str
    inserted: bool
    dedupe_reason: str
    provider_best: str

