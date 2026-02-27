from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Sequence

from ..models import ArticleCandidate


@dataclass(frozen=True)
class ParseResult:
    candidate: ArticleCandidate | None
    reject_reason: str = ""
    diagnostics: Dict[str, Any] = field(default_factory=dict)


class ProviderClient:
    name: str = "provider"

    def fetch_window(self, *, window_start_utc: str, window_end_utc: str, tickers: Sequence[str]) -> List[Dict[str, Any]]:
        raise NotImplementedError

    def parse_item(self, item: Dict[str, Any], fetched_at_utc: str) -> ParseResult:
        raise NotImplementedError

