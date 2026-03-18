from dataclasses import dataclass
from datetime import datetime, timezone
from typing import List, Optional, Tuple
import re
import httpx
from bs4 import BeautifulSoup
from dateutil import parser as dtparser
from urllib.parse import urljoin, urlparse, parse_qs

_ScraplingFetcher = None
try:
    from scrapling.fetchers import Fetcher as _ScraplingFetcher
except ImportError:
    pass

ASX_ANNOUNCEMENTS_URL="https://www.asx.com.au/asx/v2/statistics/announcements.do"
ASX_BASE_URL="https://www.asx.com.au"
ASX_TODAY_URL = "https://www.asx.com.au/asx/v2/statistics/todayAnns.do"
TICKER_RE = re.compile(r"\b[A-Z]{2,5}\b")
TICKER_STOPWORDS = {
    "ASX",
    "PDF",
    "THE",
    "AND",
    "FOR",
    "APPENDIX",
    "NOTICE",
    "ANNUAL",
    "HALF",
}

@dataclass
class DiscoveredDoc:
    ticker:str
    exchange:str
    doc_class:str
    doc_subtype:str
    title:str
    source_url:str
    published_at:Optional[datetime]=None
    period_end:Optional[datetime]=None

def _classify(title:str)->Tuple[str,str]:
    t=(title or "").lower()
    if "appendix 4c" in t: return "quarterly","4C"
    if "appendix 4d" in t: return "half_year","4D"
    if "appendix 4e" in t: return "annual","4E"
    if any(k in t for k in ["half year","half-year","interim"]): return "half_year","report"
    if any(k in t for k in ["annual","full year","year ended","annual report"]): return "annual","report"
    if any(k in t for k in ["quarterly","quarter","activities","cashflow","cash flow","production"]): return "quarterly","activities"
    return "quarterly","other"

def _try_period_end(title:str)->Optional[datetime]:
    m=re.search(r"(?:ended|year ended|half year ended|quarter ended)\s+(\d{1,2}\s+[A-Za-z]+\s+\d{4})", title or "", flags=re.I)
    if not m: return None
    try: return dtparser.parse(m.group(1), dayfirst=True).replace(tzinfo=timezone.utc)
    except Exception: return None


def _clean_title(raw:str)->str:
    title=(raw or "").strip()
    title=re.sub(r"\s+"," ",title)
    title=re.sub(r"\b\d+\s*pages?.*$","",title, flags=re.I).strip()
    return title or "ASX Announcement"


def _infer_ticker(href: str, row_text: str, fallback: str | None = None) -> str | None:
    if fallback:
        return fallback.upper()
    try:
        parsed = urlparse(href or "")
        qs = parse_qs(parsed.query)
        for key in ("asxCode", "asxcode", "ticker", "code"):
            values = qs.get(key) or qs.get(key.lower()) or []
            if values and values[0]:
                token = values[0].strip().upper()
                if 2 <= len(token) <= 5 and token.isalpha():
                    return token
    except Exception:
        pass

    text = (row_text or "").upper()
    for token in TICKER_RE.findall(text):
        if token in TICKER_STOPWORDS:
            continue
        return token
    return None

class ASXProvider:
    def __init__(self, timeout:float=60.0):
        self.timeout=timeout

    def _discover_with_params(
        self,
        c: httpx.Client,
        *,
        start: datetime,
        end: datetime,
        params: dict[str, str],
        ticker_hint: str | None = None,
        seen: set[str] | None = None,
    ) -> list[DiscoveredDoc]:
        docs: list[DiscoveredDoc] = []
        seen_urls = seen if seen is not None else set()

        if _ScraplingFetcher is not None:
            try:
                page = _ScraplingFetcher.get(
                    ASX_ANNOUNCEMENTS_URL, params=params, timeout=self.timeout
                )
                links = page.css(
                    'a[href*=".pdf"], a[href*="displayannouncement.do"]',
                    auto_save=True,
                )
                for link in links:
                    href = link.css("::attr(href)").get()
                    if not href:
                        continue
                    url = urljoin(ASX_BASE_URL, href)
                    if url in seen_urls:
                        continue
                    seen_urls.add(url)
                    title = _clean_title(
                        " ".join(link.css("::text").getall()).strip()
                        or link.css("::attr(title)").get()
                        or "ASX Announcement"
                    )
                    row_text = " ".join(
                        link.xpath("./ancestor::tr[1]//text()").getall()
                    ).strip()
                    published = None
                    if row_text:
                        m = re.search(r"(\d{1,2}/\d{1,2}/\d{2,4})", row_text)
                        if m:
                            try:
                                published = dtparser.parse(
                                    m.group(1), dayfirst=True
                                ).replace(tzinfo=timezone.utc)
                            except Exception:
                                published = None
                        if published is None:
                            m2 = re.search(
                                r"(\d{1,2}\s+[A-Za-z]+\s+\d{4})", row_text
                            )
                            if m2:
                                try:
                                    published = dtparser.parse(
                                        m2.group(1), dayfirst=True
                                    ).replace(tzinfo=timezone.utc)
                                except Exception:
                                    published = None
                    if published and (published < start or published > end):
                        continue
                    ticker = _infer_ticker(href, row_text, fallback=ticker_hint)
                    if not ticker:
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
                return docs
            except Exception:
                pass

        r = c.get(ASX_ANNOUNCEMENTS_URL, params=params, headers={"User-Agent":"Mozilla/5.0"})
        r.raise_for_status()
        soup = BeautifulSoup(r.text, "lxml")
        anchors = soup.find_all("a", href=True)
        pdf = [
            a
            for a in anchors
            if (
                a["href"].lower().endswith(".pdf")
                or "displayannouncement.do" in a["href"].lower()
            )
        ]
        for a in pdf:
            url = urljoin(ASX_BASE_URL, a["href"])
            if url in seen_urls:
                continue
            seen_urls.add(url)
            title = _clean_title(a.get_text(" ", strip=True) or a.get("title") or "ASX Announcement")
            published = None
            row = a.find_parent(["tr", "div"])
            row_text = row.get_text(" ", strip=True) if row else ""
            if row:
                m = re.search(r"(\d{1,2}/\d{1,2}/\d{2,4})", row_text)
                if m:
                    try:
                        published = dtparser.parse(m.group(1), dayfirst=True).replace(tzinfo=timezone.utc)
                    except Exception:
                        published = None
                else:
                    m2 = re.search(r"(\d{1,2}\s+[A-Za-z]+\s+\d{4})", row_text)
                    if m2:
                        try:
                            published = dtparser.parse(m2.group(1), dayfirst=True).replace(tzinfo=timezone.utc)
                        except Exception:
                            published = None
            if published and (published < start or published > end):
                continue
            ticker = _infer_ticker(a["href"], row_text, fallback=ticker_hint)
            if not ticker:
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
        return docs

    def discover(self, ticker:str, start:datetime, end:datetime)->List[DiscoveredDoc]:
        ticker=ticker.upper()
        docs:List[DiscoveredDoc]=[]
        with httpx.Client(timeout=self.timeout, follow_redirects=True) as c:
            seen=set()
            years=range(start.year, end.year+1)
            for year in years:
                params={"asxCode":ticker,"by":"asxCode","timeframe":"Y","year":str(year)}
                batch = self._discover_with_params(
                    c,
                    start=start,
                    end=end,
                    params=params,
                    ticker_hint=ticker,
                    seen=seen,
                )
                if not batch:
                    continue
                docs.extend(batch)
        return docs

    def discover_marketwide(self, start: datetime, end: datetime) -> List[DiscoveredDoc]:
        docs: list[DiscoveredDoc] = []
        seen: set[str] = set()
        candidate_params = [
            {"timeframe": "D"},
            {"by": "timeframe", "timeframe": "D"},
            {"by": "asxCode", "timeframe": "D"},
            {},
        ]
        with httpx.Client(timeout=self.timeout, follow_redirects=True) as c:
            for params in candidate_params:
                try:
                    docs.extend(
                        self._discover_with_params(
                            c,
                            start=start,
                            end=end,
                            params=params,
                            ticker_hint=None,
                            seen=seen,
                        )
                    )
                except Exception:
                    continue
        return docs

    def discover_daily_all(self, day: datetime) -> List[DiscoveredDoc]:
        target_day = day.astimezone(timezone.utc).date()
        today_utc = datetime.now(timezone.utc).date()
        start = datetime.combine(target_day, datetime.min.time(), tzinfo=timezone.utc)
        end = datetime.combine(target_day, datetime.max.time(), tzinfo=timezone.utc)

        # Historical dates should avoid "broad" fallbacks that can return very large pages.
        urls = [ASX_ANNOUNCEMENTS_URL]
        if target_day == today_utc:
            urls.insert(0, ASX_TODAY_URL)
        day_tokens = {
            "iso": target_day.strftime("%Y-%m-%d"),
            "dmy_slash": target_day.strftime("%d/%m/%Y"),
            "dmy_dash": target_day.strftime("%d-%m-%Y"),
            "year": str(target_day.year),
        }
        param_sets = [
            {"date": day_tokens["dmy_slash"]},
            {"date": day_tokens["iso"]},
            {"date": day_tokens["dmy_dash"]},
            {"fromDate": day_tokens["dmy_slash"], "toDate": day_tokens["dmy_slash"]},
        ]
        if target_day == today_utc:
            param_sets = [
                {"timeframe": "D"},
                {"by": "timeframe", "timeframe": "D"},
                {"by": "asxCode", "timeframe": "D"},
            ] + param_sets + [{}]

        docs: list[DiscoveredDoc] = []
        seen_urls: set[str] = set()

        def _mentions_target_day(text: str) -> bool:
            t = (text or "").lower()
            return any(token.lower() in t for token in day_tokens.values())

        with httpx.Client(timeout=self.timeout, follow_redirects=True) as c:
            for base_url in urls:
                for params in param_sets:
                    try:
                        r = c.get(base_url, params=params, headers={"User-Agent": "Mozilla/5.0"})
                        r.raise_for_status()
                    except Exception:
                        continue

                    try:
                        soup = BeautifulSoup(r.text, "lxml")
                    except Exception:
                        # Some payloads can trigger heavy parser edge-cases; fallback parser is slower but robust.
                        soup = BeautifulSoup(r.text, "html.parser")
                    anchors = soup.find_all("a", href=True)
                    pdf_anchors = [
                        a
                        for a in anchors
                        if (
                            a["href"].lower().endswith(".pdf")
                            or "displayannouncement.do" in a["href"].lower()
                        )
                    ]
                    if not pdf_anchors:
                        continue

                    for a in pdf_anchors:
                        url = urljoin(ASX_BASE_URL, a["href"])
                        if url in seen_urls:
                            continue
                        row = a.find_parent(["tr", "div", "li"])
                        row_text = row.get_text(" ", strip=True) if row else ""

                        published = None
                        m = re.search(r"(\d{1,2}/\d{1,2}/\d{2,4})", row_text)
                        if m:
                            try:
                                published = dtparser.parse(m.group(1), dayfirst=True).replace(tzinfo=timezone.utc)
                            except Exception:
                                published = None
                        else:
                            m2 = re.search(r"(\d{1,2}\s+[A-Za-z]+\s+\d{4})", row_text)
                            if m2:
                                try:
                                    published = dtparser.parse(m2.group(1), dayfirst=True).replace(tzinfo=timezone.utc)
                                except Exception:
                                    published = None

                        if published and published.date() != target_day:
                            continue
                        if published is None and not _mentions_target_day(row_text):
                            # If we can't parse a row date, require day token hint to avoid over-ingestion.
                            continue

                        ticker = _infer_ticker(a["href"], row_text, fallback=None)
                        if not ticker:
                            continue

                        title = _clean_title(a.get_text(" ", strip=True) or a.get("title") or "ASX Announcement")
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
                        seen_urls.add(url)

        return docs
