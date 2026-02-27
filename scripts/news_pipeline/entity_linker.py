from __future__ import annotations

import json
import re
from dataclasses import asdict
from pathlib import Path
from typing import Any, Dict, List, Sequence, Set, Tuple

from .models import EntityLink
from .utils import load_ticker_universe, normalize_space

SYMBOL_TOKEN_RE = re.compile(r"^[A-Z][A-Z0-9]{1,11}$")


def _normalize_alias(value: str) -> str:
    txt = normalize_space(value).strip()
    txt = re.sub(r"\s+", " ", txt)
    return txt


def _phrase_regex(value: str) -> re.Pattern[str]:
    escaped = re.escape(value).replace(r"\ ", r"\s+")
    return re.compile(rf"(?<![A-Za-z0-9]){escaped}(?![A-Za-z0-9])", flags=re.IGNORECASE)


class EntityLinker:
    def __init__(self, *, ticker_universe_path: Path, identity_map_path: Path) -> None:
        self.tickers = load_ticker_universe(Path(ticker_universe_path).expanduser().resolve())
        self.identity_map = self._load_identity_map(Path(identity_map_path).expanduser().resolve())
        self.aliases_by_ticker: Dict[str, List[str]] = {}
        self.ambiguous_aliases: Set[str] = set()
        self._build_alias_index()

        self.asx_patterns = {sym: re.compile(rf"\bASX\s*[:\-]\s*{re.escape(sym)}\b", flags=re.IGNORECASE) for sym in self.tickers}
        self.ax_patterns = {
            sym: re.compile(rf"(?<![A-Za-z0-9]){re.escape(sym)}\.AX(?![A-Za-z0-9])", flags=re.IGNORECASE)
            for sym in self.tickers
        }
        self.token_patterns = {
            sym: re.compile(rf"(?<![A-Za-z0-9]){re.escape(sym)}(?![A-Za-z0-9])", flags=re.IGNORECASE)
            for sym in self.tickers
        }

    def _load_identity_map(self, path: Path) -> Dict[str, Any]:
        if not path.exists():
            return {}
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return {}
        if not isinstance(payload, dict):
            return {}
        return payload

    def _collect_aliases_for_ticker(self, ticker: str) -> List[str]:
        aliases = {ticker}
        entry = self.identity_map.get(ticker)
        if isinstance(entry, dict):
            for key in ("canonical_names", "aliases"):
                values = entry.get(key)
                if isinstance(values, list):
                    for value in values:
                        alias = _normalize_alias(str(value or ""))
                        if not alias:
                            continue
                        if len(alias) > 80:
                            continue
                        if len(alias.split()) > 10:
                            continue
                        aliases.add(alias)
        # Keep stable ordering by length desc then lexicographically.
        return sorted(aliases, key=lambda item: (-len(item), item))

    def _build_alias_index(self) -> None:
        alias_to_tickers: Dict[str, Set[str]] = {}
        for ticker in self.tickers:
            aliases = self._collect_aliases_for_ticker(ticker)
            self.aliases_by_ticker[ticker] = aliases
            for alias in aliases:
                low = alias.lower()
                alias_to_tickers.setdefault(low, set()).add(ticker)
        self.ambiguous_aliases = {alias for alias, tickers in alias_to_tickers.items() if len(tickers) > 1}

    def _add_link(
        self,
        out: Dict[Tuple[str, str, str, int, int], EntityLink],
        *,
        article_id: str,
        ticker: str,
        confidence: float,
        lane: str,
        method: str,
        matched_alias: str,
        span_start: int | None,
        span_end: int | None,
        published_at_utc: str,
    ) -> None:
        key = (
            ticker,
            lane,
            method,
            int(span_start if span_start is not None else -1),
            int(span_end if span_end is not None else -1),
        )
        existing = out.get(key)
        if existing is not None and float(existing.confidence) >= float(confidence):
            return
        out[key] = EntityLink(
            article_id=article_id,
            ticker=ticker,
            confidence=float(confidence),
            lane=lane,
            method=method,
            matched_alias=matched_alias,
            matched_span_start=span_start,
            matched_span_end=span_end,
            published_at_utc=published_at_utc,
        )

    def link_article(
        self,
        *,
        article_id: str,
        title: str,
        description: str,
        body: str,
        published_at_utc: str,
    ) -> List[EntityLink]:
        text = "\n\n".join(
            part
            for part in (
                str(title or "").strip(),
                str(description or "").strip(),
                str(body or "").strip(),
            )
            if part
        )
        if not text:
            return []

        out: Dict[Tuple[str, str, str, int, int], EntityLink] = {}

        for ticker in self.tickers:
            # High-precision explicit symbol cues.
            for pat in (self.asx_patterns[ticker], self.ax_patterns[ticker]):
                for match in pat.finditer(text):
                    self._add_link(
                        out,
                        article_id=article_id,
                        ticker=ticker,
                        confidence=0.99,
                        lane="high_precision",
                        method="explicit_symbol",
                        matched_alias=match.group(0),
                        span_start=match.start(),
                        span_end=match.end(),
                        published_at_utc=published_at_utc,
                    )
                    self._add_link(
                        out,
                        article_id=article_id,
                        ticker=ticker,
                        confidence=0.85,
                        lane="high_recall",
                        method="explicit_symbol",
                        matched_alias=match.group(0),
                        span_start=match.start(),
                        span_end=match.end(),
                        published_at_utc=published_at_utc,
                    )

            aliases = self.aliases_by_ticker.get(ticker, [])
            for alias in aliases:
                low_alias = alias.lower()
                alias_is_ambiguous = low_alias in self.ambiguous_aliases
                # Skip weak ambiguous aliases in high precision lane.
                if alias_is_ambiguous:
                    continue
                # Avoid using bare short acronyms as precision aliases.
                if len(alias) <= 3 and SYMBOL_TOKEN_RE.fullmatch(alias.upper()):
                    continue
                if len(alias) < 4:
                    continue
                pattern = _phrase_regex(alias)
                for match in pattern.finditer(text):
                    self._add_link(
                        out,
                        article_id=article_id,
                        ticker=ticker,
                        confidence=0.91,
                        lane="high_precision",
                        method="alias_strict",
                        matched_alias=alias,
                        span_start=match.start(),
                        span_end=match.end(),
                        published_at_utc=published_at_utc,
                    )
                    self._add_link(
                        out,
                        article_id=article_id,
                        ticker=ticker,
                        confidence=0.72,
                        lane="high_recall",
                        method="alias_strict",
                        matched_alias=alias,
                        span_start=match.start(),
                        span_end=match.end(),
                        published_at_utc=published_at_utc,
                    )

            # High-recall ticker token matching.
            for match in self.token_patterns[ticker].finditer(text):
                self._add_link(
                    out,
                    article_id=article_id,
                    ticker=ticker,
                    confidence=0.45,
                    lane="high_recall",
                    method="ticker_token",
                    matched_alias=match.group(0),
                    span_start=match.start(),
                    span_end=match.end(),
                    published_at_utc=published_at_utc,
                )

            # High-recall ambiguous aliases retained at low confidence.
            for alias in aliases:
                low_alias = alias.lower()
                if low_alias not in self.ambiguous_aliases:
                    continue
                pattern = _phrase_regex(alias)
                for match in pattern.finditer(text):
                    self._add_link(
                        out,
                        article_id=article_id,
                        ticker=ticker,
                        confidence=0.33,
                        lane="high_recall",
                        method="alias_ambiguous",
                        matched_alias=alias,
                        span_start=match.start(),
                        span_end=match.end(),
                        published_at_utc=published_at_utc,
                    )

        return sorted(
            out.values(),
            key=lambda item: (
                item.lane,
                item.ticker,
                -item.confidence,
                item.method,
                int(item.matched_span_start if item.matched_span_start is not None else -1),
            ),
        )

