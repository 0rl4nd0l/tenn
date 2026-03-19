from __future__ import annotations

import datetime as dt
import json
import urllib.request
from pathlib import Path
from typing import Any, Dict, List, Sequence

from ..models import ArticleCandidate
from ..utils import canonicalize_url, normalize_space, parse_datetime_utc, sha1_hex
from .base import ParseResult, ProviderClient

DEFAULT_API_CACHE_URL = "https://raw.githubusercontent.com/koala73/worldmonitor/main/api-cache.json"
DEFAULT_SOURCE_URL = "https://github.com/koala73/worldmonitor/blob/main/api-cache.json"


def _first_non_empty(*values: Any) -> str:
    for value in values:
        txt = normalize_space(value)
        if txt:
            return txt
    return ""


def _as_utc_datetime(value: str) -> dt.datetime | None:
    parsed = parse_datetime_utc(value)
    if not parsed:
        return None
    return dt.datetime.fromisoformat(parsed.replace("Z", "+00:00")).astimezone(dt.timezone.utc)


def _cache_key_priority(cache_key: str) -> int:
    key = str(cache_key or "").strip().lower()
    if key.startswith("theater-posture:v"):
        return 0
    if "backup" in key:
        return 1
    if "stale" in key:
        return 2
    return 3


def _normalize_ticker(value: Any) -> str:
    txt = normalize_space(value).upper()
    if not txt:
        return ""
    txt = txt.replace("ASX:", "").replace("ASX-", "")
    if "." in txt:
        txt = txt.split(".", 1)[0]
    txt = "".join(ch for ch in txt if ch.isalnum())
    if len(txt) < 2:
        return ""
    return txt


def _normalize_theater_key(value: Any) -> str:
    return normalize_space(value).strip().lower()


def _normalize_theater_ticker_map(raw: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    entries_obj = raw.get("theaters")
    entries = entries_obj if isinstance(entries_obj, dict) else raw
    if not isinstance(entries, dict):
        return {}

    normalized: Dict[str, Dict[str, Any]] = {}
    for raw_key, raw_value in entries.items():
        aliases: List[str] = [str(raw_key or "")]
        tickers: List[str] = []
        note = ""

        if isinstance(raw_value, dict):
            values = raw_value.get("tickers")
            if isinstance(values, list):
                tickers = [_normalize_ticker(item) for item in values]
            elif values is not None:
                tickers = [_normalize_ticker(values)]
            alias_values = raw_value.get("aliases")
            if isinstance(alias_values, list):
                aliases.extend([str(item or "") for item in alias_values])
            note = _first_non_empty(raw_value.get("note"), raw_value.get("reason"), raw_value.get("rationale"))
        elif isinstance(raw_value, list):
            tickers = [_normalize_ticker(item) for item in raw_value]
        elif raw_value is not None:
            tickers = [_normalize_ticker(raw_value)]

        ticker_values = sorted({ticker for ticker in tickers if ticker})
        if not ticker_values:
            continue

        for alias in aliases:
            alias_key = _normalize_theater_key(alias)
            if not alias_key:
                continue
            existing = normalized.get(alias_key)
            if existing is None:
                normalized[alias_key] = {"tickers": list(ticker_values), "note": note}
                continue
            merged = sorted(set(existing.get("tickers") or []) | set(ticker_values))
            existing["tickers"] = merged
            if not existing.get("note") and note:
                existing["note"] = note

    return normalized


class WorldMonitorProvider(ProviderClient):
    name = "worldmonitor"

    def __init__(
        self,
        *,
        api_cache_url: str = DEFAULT_API_CACHE_URL,
        request_timeout: float = 45.0,
        user_agent: str = "tenn-worldmonitor-ingest-v1/1.0",
        capture_path: Path | None = None,
        theater_map_path: Path | None = None,
    ) -> None:
        self.api_cache_url = str(api_cache_url or DEFAULT_API_CACHE_URL).strip()
        self.request_timeout = float(max(1.0, request_timeout))
        self.user_agent = str(user_agent or "tenn-worldmonitor-ingest-v1/1.0")
        self.capture_path = Path(capture_path).expanduser().resolve() if capture_path else None
        self.theater_map_path = Path(theater_map_path).expanduser().resolve() if theater_map_path else None
        self.theater_ticker_map = self._load_theater_ticker_map()

    def _load_json(self) -> Dict[str, Any]:
        if self.capture_path and self.capture_path.exists() and self.capture_path.is_file():
            payload = json.loads(self.capture_path.read_text(encoding="utf-8"))
            if isinstance(payload, dict):
                return payload
            return {}

        req = urllib.request.Request(
            self.api_cache_url,
            headers={"User-Agent": self.user_agent, "Accept": "application/json"},
            method="GET",
        )
        with urllib.request.urlopen(req, timeout=self.request_timeout) as resp:
            payload = json.loads(resp.read().decode("utf-8", errors="replace"))
        if isinstance(payload, dict):
            return payload
        return {}

    def _load_theater_ticker_map(self) -> Dict[str, Dict[str, Any]]:
        path = self.theater_map_path
        if path is None or (not path.exists()) or (not path.is_file()):
            return {}
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return {}
        if not isinstance(payload, dict):
            return {}
        return _normalize_theater_ticker_map(payload)

    def _resolve_mapped_tickers(self, posture: Dict[str, Any]) -> tuple[List[str], str]:
        mapping = self.theater_ticker_map
        if not mapping:
            return [], ""
        keys = [
            _normalize_theater_key(posture.get("theaterId")),
            _normalize_theater_key(posture.get("shortName")),
            _normalize_theater_key(posture.get("theaterName")),
        ]
        tickers: set[str] = set()
        notes: List[str] = []
        for key in keys:
            if not key:
                continue
            entry = mapping.get(key)
            if not isinstance(entry, dict):
                continue
            for item in entry.get("tickers") or []:
                symbol = _normalize_ticker(item)
                if symbol:
                    tickers.add(symbol)
            note = _first_non_empty(entry.get("note"))
            if note and note not in notes:
                notes.append(note)
        return sorted(tickers), "; ".join(notes)

    def fetch_window(self, *, window_start_utc: str, window_end_utc: str, tickers: Sequence[str]) -> List[Dict[str, Any]]:
        # `tickers` is intentionally unused in this provider.
        _ = tickers

        start_ts = _as_utc_datetime(window_start_utc)
        end_ts = _as_utc_datetime(window_end_utc)
        if start_ts is None or end_ts is None:
            raise ValueError("invalid worldmonitor fetch window")

        payload = self._load_json()
        rows: List[Dict[str, Any]] = []
        seen: set[tuple[str, str]] = set()
        cache_items = sorted(payload.items(), key=lambda kv: (_cache_key_priority(str(kv[0])), str(kv[0])))
        for cache_key, cache_entry in cache_items:
            if not str(cache_key).startswith("theater-posture"):
                continue
            if not isinstance(cache_entry, dict):
                continue
            value = cache_entry.get("value")
            if not isinstance(value, dict):
                continue
            postures = value.get("postures")
            if not isinstance(postures, list):
                continue

            snapshot_utc = parse_datetime_utc(value.get("timestamp"))
            if snapshot_utc:
                snapshot_ts = _as_utc_datetime(snapshot_utc)
                if snapshot_ts is not None and (snapshot_ts < start_ts or snapshot_ts > end_ts):
                    continue

            for posture in postures:
                if not isinstance(posture, dict):
                    continue
                theater_id = _first_non_empty(posture.get("theaterId"), posture.get("shortName"), "unknown")
                dedupe_key = (theater_id, str(snapshot_utc or ""))
                if dedupe_key in seen:
                    continue
                seen.add(dedupe_key)
                rows.append(
                    {
                        "cache_key": str(cache_key),
                        "snapshot_timestamp": str(snapshot_utc or ""),
                        "source": _first_non_empty(value.get("source"), "worldmonitor"),
                        "total_flights": value.get("totalFlights"),
                        "posture": posture,
                    }
                )
        return rows

    def parse_item(self, item: Dict[str, Any], fetched_at_utc: str) -> ParseResult:
        posture = item.get("posture")
        if not isinstance(posture, dict):
            return ParseResult(candidate=None, reject_reason="missing_posture_payload")

        theater_name = _first_non_empty(posture.get("theaterName"), posture.get("shortName"), posture.get("theaterId"))
        if not theater_name:
            return ParseResult(candidate=None, reject_reason="missing_identity")

        headline = _first_non_empty(posture.get("headline"), posture.get("summary"))
        title = f"WorldMonitor theater posture: {theater_name}"
        if headline:
            title = f"{title} - {headline}"

        published_at_utc = parse_datetime_utc(item.get("snapshot_timestamp"))
        if not published_at_utc:
            published_at_utc = parse_datetime_utc(fetched_at_utc)
        if not published_at_utc:
            return ParseResult(
                candidate=None,
                reject_reason="missing_published_at",
                diagnostics={"provider_published_at_raw": str(item.get("snapshot_timestamp") or "")},
            )

        cache_key = _first_non_empty(item.get("cache_key"), "theater-posture")
        theater_id = _first_non_empty(posture.get("theaterId"), posture.get("shortName"), "unknown")
        canonical_url = canonicalize_url(
            f"{DEFAULT_SOURCE_URL}?cache_key={cache_key}&theater_id={theater_id}&snapshot={published_at_utc}"
        )
        provider_item_id = _first_non_empty(
            posture.get("theaterId"),
            posture.get("shortName"),
            f"wm_{sha1_hex(canonical_url + published_at_utc)[:16]}",
        )

        source_name = _first_non_empty(item.get("source"), "worldmonitor")
        summary = _first_non_empty(posture.get("summary"), headline)
        mapped_tickers, mapping_note = self._resolve_mapped_tickers(posture)
        body_lines = [
            f"source={source_name}",
            f"cache_key={cache_key}",
            f"theater_id={_first_non_empty(posture.get('theaterId'), 'unknown')}",
            f"target_nation={_first_non_empty(posture.get('targetNation'), 'n/a')}",
            f"posture_level={_first_non_empty(posture.get('postureLevel'), 'unknown')}",
            f"trend={_first_non_empty(posture.get('trend'), 'unknown')}",
            f"change_percent={posture.get('changePercent')}",
            f"total_aircraft={posture.get('totalAircraft')}",
            f"total_vessels={posture.get('totalVessels')}",
            f"strike_capable={posture.get('strikeCapable')}",
            f"total_flights={item.get('total_flights')}",
        ]
        if mapped_tickers:
            mapped_symbols = [f"ASX:{ticker}" for ticker in mapped_tickers]
            body_lines.append(f"mapped_tickers={','.join(mapped_tickers)}")
            for symbol in mapped_symbols:
                body_lines.append(f"asx_exposure_hint={symbol}")
        if mapping_note:
            body_lines.append(f"mapping_note={mapping_note}")
        if summary:
            body_lines.append(f"summary={summary}")

        candidate = ArticleCandidate(
            provider=self.name,
            provider_item_id=str(provider_item_id),
            canonical_url=canonical_url,
            title=title,
            description=summary,
            body="\n".join(body_lines),
            source_name=source_name,
            language="en",
            published_at_utc=published_at_utc,
            fetched_at_utc=parse_datetime_utc(fetched_at_utc) or published_at_utc,
            provider_published_at_raw=str(item.get("snapshot_timestamp") or ""),
            raw_payload={
                "cache_key": cache_key,
                "source": source_name,
                "total_flights": item.get("total_flights"),
                "posture": posture,
                "mapped_tickers": mapped_tickers,
                "mapping_note": mapping_note,
            },
        )
        return ParseResult(candidate=candidate)
