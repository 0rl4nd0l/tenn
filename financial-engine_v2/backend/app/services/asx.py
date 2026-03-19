from __future__ import annotations

import logging
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

        def _html_extract_one_page(html: str, year: int) -> None:
            nonlocal raw_count, parsed, skipped, skip_missing_url, skip_outside_window, skip_missing_title, docs
            try:
                soup = BeautifulSoup(html, "lxml")
            except Exception:
                soup = BeautifulSoup(html, "html.parser")

            candidates: list[tuple[str, str, Optional[datetime], str]] = []
            for tag in soup.find_all(True):
                href = None
                if tag.has_attr("href"):
                    href = str(tag.get("href") or "").strip()
                if not href:
                    for attr in ("data-href", "data-url", "data-pdf", "data-link"):
                        if tag.has_attr(attr):
                            href = str(tag.get(attr) or "").strip()
                            break
                if not href:
                    continue

                lower = href.lower()
                if not (
                    ".pdf" in lower
                    or "displayannouncement.do" in lower
                    or "asxpdf" in lower
                ):
                    continue

                url = _normalize_url(href)
                if not url or url in seen_urls:
                    continue
                seen_urls.add(url)

                title = (tag.get_text(" ", strip=True) or "").strip() or str(tag.get("title") or "").strip()
                if not title:
                    title = "ASX Announcement"
                    skip_missing_title += 1

                row = tag.find_parent(["tr", "div", "li"])
                row_text = row.get_text(" ", strip=True) if row else ""
                published = None
                m = re.search(r"(\d{1,2}/\d{1,2}/\d{2,4})", row_text)
                if m:
                    try:
                        published = dtparser.parse(m.group(1), dayfirst=True).replace(tzinfo=timezone.utc)
                    except Exception:
                        published = None
                if published is None:
                    m2 = re.search(r"(\d{1,2}\s+[A-Za-z]+\s+\d{4})", row_text)
                    if m2:
                        try:
                            published = dtparser.parse(m2.group(1), dayfirst=True).replace(tzinfo=timezone.utc)
                        except Exception:
                            published = None

                candidates.append((url, title, published, row_text))

            raw_count += len(candidates)
            for url, title, published, _row_text in candidates:
                if not url:
                    skipped += 1
                    skip_missing_url += 1
                    logger.warning("Skipping announcement: missing source_url (html) year=%s", year)
                    continue
                if published and (published < start or published > end):
                    skipped += 1
                    skip_outside_window += 1
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
                    raw_prefix = (r.text or "")[:4000]

                    logger.info(
                        "asx_discovery_raw status=%s content_type=%s year=%s body_prefix=%s",
                        getattr(r, "status_code", None),
                        r.headers.get("content-type"),
                        year,
                        raw_prefix.replace("\n", "\\n"),
                    )

                    payload = None
                    try:
                        payload = r.json()
                    except Exception:
                        payload = None

                    if isinstance(payload, Mapping):
                        logger.info(
                            "asx_discovery_schema year=%s top_keys=%s",
                            year,
                            ",".join(sorted([str(k) for k in payload.keys()])[:64]),
                        )
                        items = _extract_announcement_items(payload)
                        raw_count += len(items)
                        if items:
                            sample_keys = sorted([str(k) for k in items[0].keys()])[:80]
                            logger.info(
                                "asx_discovery_schema year=%s raw=%d sample_keys=%s",
                                year,
                                len(items),
                                ",".join(sample_keys),
                            )
                        for item in items:
                            title = _first_str(item, ("headline", "title", "subject", "name")) or "ASX Announcement"
                            source_url = _first_str(
                                item,
                                ("url", "link", "pdfUrl", "pdf_url", "documentUrl", "document_url"),
                            )
                            source_url = _normalize_url(source_url)
                            if not source_url:
                                skipped += 1
                                skip_missing_url += 1
                                logger.warning(
                                    "Skipping announcement: missing source_url keys=%s",
                                    ",".join(sorted([str(k) for k in item.keys()])[:80]),
                                )
                                continue

                            published = _parse_dt(
                                _first_str(
                                    item,
                                    (
                                        "date",
                                        "publishDate",
                                        "publish_date",
                                        "releaseDate",
                                        "release_date",
                                        "announcementDate",
                                        "announcement_date",
                                    ),
                                )
                            )
                            if published and (published < start or published > end):
                                skipped += 1
                                skip_outside_window += 1
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
                        continue

                    _html_extract_one_page(r.text or "", year)

            logger.info(
                "ASX discovery stats raw=%d parsed=%d skipped=%d skipped_missing_url=%d skipped_outside_window=%d skipped_missing_title=%d",
                raw_count,
                parsed,
                skipped,
                skip_missing_url,
                skip_outside_window,
                skip_missing_title,
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

