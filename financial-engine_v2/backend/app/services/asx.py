from __future__ import annotations

import logging
import json
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Mapping, Optional
from urllib.parse import urljoin

import httpx
from bs4 import BeautifulSoup
from dateutil import parser as dtparser

from app.providers.asx_provider import ASXProvider as _HtmlASXProvider

logger = logging.getLogger(__name__)

ASX_BASE_URL = "https://www.asx.com.au"
ASX_ANNOUNCEMENTS_URL = "https://www.asx.com.au/asx/v2/statistics/announcements.do"


@dataclass
class DiscoveredDoc:
    ticker: str
    exchange: str
    doc_class: str
    doc_subtype: str
    title: str
    source_url: str
    published_at: Optional[datetime] = None
    period_end: Optional[datetime] = None


def _first_str(mapping: Mapping[str, Any], keys: tuple[str, ...]) -> str | None:
    for key in keys:
        value = mapping.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None


def _parse_dt(value: Any) -> Optional[datetime]:
    if isinstance(value, datetime):
        return value.astimezone(timezone.utc)
    if isinstance(value, (int, float)) and value > 0:
        try:
            return datetime.fromtimestamp(float(value) / (1000.0 if value > 2_000_000_000 else 1.0), tz=timezone.utc)
        except Exception:
            return None
    if isinstance(value, str) and value.strip():
        try:
            return dtparser.parse(value.strip()).replace(tzinfo=timezone.utc) if "tzinfo" not in dir(dtparser.parse(value.strip())) else dtparser.parse(value.strip()).astimezone(timezone.utc)
        except Exception:
            try:
                return dtparser.parse(value.strip(), dayfirst=True).replace(tzinfo=timezone.utc)
            except Exception:
                return None
    return None


def _classify(title: str) -> tuple[str, str]:
    t = (title or "").lower()
    if "appendix 4c" in t:
        return "quarterly", "4C"
    if "appendix 4d" in t:
        return "half_year", "4D"
    if "appendix 4e" in t:
        return "annual", "4E"
    if any(k in t for k in ["half year", "half-year", "interim"]):
        return "half_year", "report"
    if any(k in t for k in ["annual", "full year", "year ended", "annual report"]):
        return "annual", "report"
    if any(k in t for k in ["quarterly", "quarter", "activities", "cashflow", "cash flow", "production"]):
        return "quarterly", "activities"
    return "quarterly", "other"


def _try_period_end(title: str) -> Optional[datetime]:
    m = re.search(
        r"(?:ended|year ended|half year ended|quarter ended)\s+(\d{1,2}\s+[A-Za-z]+\s+\d{4})",
        title or "",
        flags=re.I,
    )
    if not m:
        return None
    try:
        return dtparser.parse(m.group(1), dayfirst=True).replace(tzinfo=timezone.utc)
    except Exception:
        return None


def _extract_announcement_items(payload: Any) -> list[Mapping[str, Any]]:
    if isinstance(payload, list):
        return [x for x in payload if isinstance(x, Mapping)]
    if not isinstance(payload, Mapping):
        return []

    for key in ("announcements", "items", "data", "results", "result"):
        value = payload.get(key)
        if isinstance(value, list):
            return [x for x in value if isinstance(x, Mapping)]
        if isinstance(value, Mapping):
            nested = _extract_announcement_items(value)
            if nested:
                return nested

    for value in payload.values():
        if isinstance(value, list) and value and all(isinstance(x, Mapping) for x in value):
            return list(value)

    return []


def _normalize_url(raw: str | None) -> str | None:
    if not raw:
        return None
    url = raw.strip()
    if not url:
        return None
    if url.startswith("//"):
        return "https:" + url
    if url.startswith("/"):
        return urljoin(ASX_BASE_URL, url)
    if url.startswith("http://") or url.startswith("https://"):
        return url
    return urljoin(ASX_BASE_URL, url)


def _detect_response_kind(*, content_type: str | None, text: str | None) -> str:
    ct = (content_type or "").lower()
    stripped = (text or "").lstrip()
    if "text/html" in ct or "application/xhtml" in ct:
        return "html"
    if stripped.startswith("<"):
        return "html"
    return "json"


def _extract_date_from_text(text: str) -> Optional[datetime]:
    raw = (text or "").strip()
    if not raw:
        return None
    m = re.search(r"(\d{1,2}/\d{1,2}/\d{2,4})", raw)
    if m:
        try:
            return dtparser.parse(m.group(1), dayfirst=True).replace(tzinfo=timezone.utc)
        except Exception:
            pass
    m2 = re.search(r"(\d{1,2}\s+[A-Za-z]+\s+\d{4})", raw)
    if m2:
        try:
            return dtparser.parse(m2.group(1), dayfirst=True).replace(tzinfo=timezone.utc)
        except Exception:
            pass
    return None


class ASXProvider:
    def __init__(self, timeout: float = 60.0):
        self.timeout = timeout
        self._html = _HtmlASXProvider(timeout=timeout)

    def discover(self, ticker: str, start: datetime, end: datetime) -> list[DiscoveredDoc]:
        ticker = (ticker or "").strip().upper()
        headers = {
            "Accept": "application/json, text/javascript, */*; q=0.01",
            "X-Requested-With": "XMLHttpRequest",
            "User-Agent": "Mozilla/5.0",
        }

        raw_prefix = ""
        raw_count = 0
        parsed = 0
        skipped = 0
        skip_missing_url = 0
        skip_outside_window = 0
        skip_missing_title = 0
        docs: list[DiscoveredDoc] = []
        seen_urls: set[str] = set()

        def _log_skip(*, reason: str, parser: str, year: int, data: Any) -> None:
            nonlocal skipped
            skipped += 1
            logger.warning(
                "ASX skip",
                extra={
                    "reason": reason,
                    "parser": parser,
                    "ticker": ticker,
                    "year": year,
                    "data": data,
                },
            )

        def _json_items_from_payload(payload: Any) -> list[Mapping[str, Any]]:
            if isinstance(payload, list):
                return [x for x in payload if isinstance(x, Mapping)]
            if isinstance(payload, Mapping):
                data = payload.get("data") or payload.get("announcements") or payload.get("items") or []
                if isinstance(data, list):
                    return [x for x in data if isinstance(x, Mapping)]
                return []
            return []

        def _html_extract_one_page(html: str, year: int) -> None:
            nonlocal raw_count, parsed, skipped, skip_missing_url, skip_outside_window, skip_missing_title, docs
            try:
                soup = BeautifulSoup(html, "lxml")
            except Exception:
                soup = BeautifulSoup(html, "html.parser")

            candidates: list[tuple[str, str, Optional[datetime]]] = []
            for a in soup.find_all("a"):
                href = str(a.get("href") or "").strip()
                if not href:
                    continue
                lower = href.lower()
                if not (".pdf" in lower or "/asxpdf/" in lower):
                    continue
                url = _normalize_url(href)
                if not url:
                    skip_missing_url += 1
                    _log_skip(reason="missing_source_url", parser="html", year=year, data={"href": href[:512]})
                    continue
                if url in seen_urls:
                    continue
                seen_urls.add(url)

                title = (a.get_text(" ", strip=True) or "").strip()
                if not title:
                    title = "ASX Announcement"
                    skip_missing_title += 1

                candidates.append((url, title, None))

            raw_count += len(candidates)
            for url, title, published in candidates:
                if published and (published < start or published > end):
                    skip_outside_window += 1
                    _log_skip(
                        reason="outside_window",
                        parser="html",
                        year=year,
                        data={
                            "source_url": url,
                            "published_at": published.isoformat() if published else None,
                            "start": start.isoformat(),
                            "end": end.isoformat(),
                        },
                    )
                    continue

                doc_class, doc_subtype = _classify(title)
                docs.append(
                    DiscoveredDoc(
                        ticker=ticker,
                        exchange="ASX",
                        doc_class=doc_class,
                        doc_subtype=doc_subtype,
                        title=title,
                        source_url=url,
                        published_at=published,
                        period_end=_try_period_end(title),
                    )
                )
                parsed += 1

        try:
            with httpx.Client(timeout=self.timeout, follow_redirects=True) as c:
                for year in range(start.year, end.year + 1):
                    params = {
                        "asxCode": ticker,
                        "by": "asxCode",
                        "timeframe": "Y",
                        "year": str(year),
                    }
                    r = c.get(ASX_ANNOUNCEMENTS_URL, params=params, headers=headers)
                    r.raise_for_status()
                    content_type = r.headers.get("content-type")
                    body_text = r.text or ""
                    kind = _detect_response_kind(content_type=content_type, text=body_text)
                    logger.info(
                        "ASX response detected",
                        extra={
                            "kind": kind,
                            "content_type": content_type,
                            "ticker": ticker,
                            "year": year,
                        },
                    )
                    logger.info(
                        "ASX raw response preview",
                        extra={
                            "ticker": ticker,
                            "year": year,
                            "prefix": (body_text[:200] if body_text else ""),
                        },
                    )
                    raw_prefix = body_text[:4000]

                    payload = None
                    if kind == "html":
                        _html_extract_one_page(body_text, year)
                        continue

                    try:
                        payload = r.json()
                    except Exception as exc:
                        _log_skip(
                            reason="invalid_structure",
                            parser="json",
                            year=year,
                            data={"error": str(exc), "prefix": raw_prefix[:200]},
                        )
                        continue

                    items = _json_items_from_payload(payload)
                    if not isinstance(payload, (Mapping, list)):
                        _log_skip(reason="invalid_structure", parser="json", year=year, data={"type": str(type(payload))})
                        continue

                    if isinstance(payload, Mapping):
                        logger.info(
                            "asx_discovery_schema",
                            extra={
                                "ticker": ticker,
                                "year": year,
                                "top_keys": ",".join(sorted([str(k) for k in payload.keys()])[:64]),
                            },
                        )
                    raw_count += len(items)
                    if not items and isinstance(payload, Mapping):
                        _log_skip(
                            reason="invalid_structure",
                            parser="json",
                            year=year,
                            data={"top_keys": ",".join(sorted([str(k) for k in payload.keys()])[:64])},
                        )
                        continue
                    if not items and isinstance(payload, list):
                        _log_skip(reason="invalid_structure", parser="json", year=year, data={"list_len": len(payload)})
                        continue

                    for item in items:
                        title = (_first_str(item, ("headline", "title")) or "").strip()
                        source_url = _first_str(item, ("url", "link", "pdfUrl"))
                        published_raw = _first_str(item, ("date", "publishDate"))

                        if not title:
                            title = "ASX Announcement"
                            skip_missing_title += 1

                        source_url = _normalize_url(source_url)
                        if not source_url:
                            skip_missing_url += 1
                            _log_skip(
                                reason="missing_source_url",
                                parser="json",
                                year=year,
                                data={"item_keys": ",".join(sorted([str(k) for k in item.keys()])[:80])},
                            )
                            continue

                        published = _parse_dt(published_raw) if published_raw else None
                        if published and (published < start or published > end):
                            skip_outside_window += 1
                            _log_skip(
                                reason="outside_window",
                                parser="json",
                                year=year,
                                data={
                                    "source_url": source_url,
                                    "published_at": published.isoformat() if published else None,
                                    "start": start.isoformat(),
                                    "end": end.isoformat(),
                                },
                            )
                            continue

                        doc_class, doc_subtype = _classify(title)
                        docs.append(
                            DiscoveredDoc(
                                ticker=ticker,
                                exchange="ASX",
                                doc_class=doc_class,
                                doc_subtype=doc_subtype,
                                title=title,
                                source_url=source_url,
                                published_at=published,
                                period_end=_try_period_end(title),
                            )
                        )
                        parsed += 1

            logger.info(
                "ASX discovery stats",
                extra={
                    "raw": raw_count,
                    "parsed": parsed,
                    "skipped": skipped,
                    "skipped_missing_url": skip_missing_url,
                    "skipped_outside_window": skip_outside_window,
                    "skipped_missing_title": skip_missing_title,
                    "ticker": ticker,
                },
            )
            if raw_count > 0 and parsed == 0:
                logger.error(
                    "ASX parsing failed: raw>0 but parsed=0",
                    extra={
                        "ticker": ticker,
                        "raw": raw_count,
                        "parsed": parsed,
                        "skipped": skipped,
                    },
                )

            if docs:
                return docs
        except Exception as exc:
            logger.warning("ASX JSON discovery failed; falling back to HTML scrape: %s", exc)

        scraped = self._html.discover(ticker, start, end)
        logger.info("ASX discovery stats raw=%d parsed=%d skipped=%d (html_fallback)", len(scraped), len(scraped), 0)
        return [
            DiscoveredDoc(
                ticker=d.ticker,
                exchange=d.exchange,
                doc_class=d.doc_class,
                doc_subtype=d.doc_subtype,
                title=d.title,
                source_url=d.source_url,
                published_at=d.published_at,
                period_end=d.period_end,
            )
            for d in scraped
        ]

