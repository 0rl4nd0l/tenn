#!/usr/bin/env python3
from __future__ import annotations

import argparse
import datetime as dt
import email.utils
import html as html_lib
import hashlib
import json
import re
import sys
import time
import warnings
import xml.etree.ElementTree as ET
from dataclasses import dataclass, replace
from pathlib import Path
from typing import List, Sequence
from urllib.parse import parse_qsl, urlencode, urljoin, urlsplit, urlunsplit
from urllib.request import Request, urlopen

UTC = dt.timezone.utc
SOURCE_MODES = {"auto", "web", "rss", "url"}
TRACKING_PARAMS = {
    "fbclid",
    "gclid",
    "igshid",
    "mc_cid",
    "mc_eid",
    "ref",
    "ref_src",
    "ref_url",
    "utm_source",
    "utm_medium",
    "utm_campaign",
    "utm_term",
    "utm_content",
}
DEFAULT_KEYWORDS = (
    "asx",
    "earnings",
    "guidance",
    "dividend",
    "cash flow",
    "balance sheet",
    "income statement",
    "ebitda",
    "capital raising",
    "buyback",
    "acquisition",
    "merger",
    "inflation",
    "interest rate",
    "rba",
    "profit",
    "revenue",
    "share price",
    "stocks",
    "equities",
    "bond yields",
    "fiscal",
    "budget",
    "gdp",
)
DEFAULT_FINANCE_URL_INCLUDE_TOKENS = (
    "/business",
    "/markets",
    "/market",
    "/companies",
    "/economy",
    "/finance",
    "/invest",
    "/stocks",
    "/shares",
    "/wealth",
    "/bank",
    "/briefing",
)
DEFAULT_FINANCE_URL_EXCLUDE_TOKENS = (
    "/sport",
    "/sports",
    "/weather",
    "/travel",
    "/entertainment",
    "/culture",
    "/lifestyle",
    "/food",
    "/video",
)
SECTION_PATH_TAILS = {
    "business",
    "markets",
    "market",
    "companies",
    "economy",
    "finance",
    "invest",
    "stocks",
    "shares",
    "wealth",
    "bank",
    "banks",
    "topic",
    "news",
    "opinion",
    "analysis",
    "live",
}
NON_ARTICLE_PATH_SEGMENTS = {
    "author",
    "authors",
    "topic",
    "topics",
    "tag",
    "tags",
    "profile",
    "profiles",
    "newsletter",
    "newsletters",
    "about",
    "contact",
    "events",
    "login",
    "account",
    "subscribe",
    "membership",
}
HTTP_USER_AGENT = (
    "Mozilla/5.0 (X11; Linux x86_64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0.0.0 Safari/537.36"
)
AFR_FEED_PATHS = (
    "/rss",
    "/markets/rss",
    "/companies/rss",
    "/policy/economy/rss",
    "/wealth/rss",
)
CAPITALBRIEF_FEED_PATHS = (
    "/rss",
    "/feed",
    "/feed.xml",
    "/news/rss",
    "/briefing/rss",
)
KALKINE_FEED_PATHS = (
    "/rss",
    "/feed",
    "/feed.xml",
    "/au/feed",
    "/au/rss",
    "/au/news/feed",
)
BENZINGA_FEED_PATHS = (
    "/feed",
    "/rss/news",
    "/news/feed",
    "/markets/feed",
    "/feeds/news",
)
MARKETINDEX_FEED_PATHS = (
    "/news/rss",
    "/news/feed",
    "/feed",
    "/rss",
)
SKYNEWS_FEED_PATHS = (
    "/business/feed",
    "/business/rss",
    "/feed",
    "/rss",
)
STOCKHEAD_FEED_PATHS = (
    "/feed",
    "/rss",
    "/news/feed",
    "/markets/feed",
)
LIVEWIRE_FEED_PATHS = (
    "/feed",
    "/rss",
    "/latest-news/feed",
    "/news/feed",
)
YAHOO_FINANCE_FEED_PATHS = (
    "/news/rssindex",
    "/news/rss",
    "/rss",
    "/feed",
)
AUSTRALIAN_FEED_PATHS = (
    "/rss",
    "/feed",
    "/feed.xml",
    "/business/feed",
    "/business/rss",
    "/markets/feed",
)
BODY_NOISE_PATTERNS = (
    r"\bLoading\.\.\.\b",
    r"\bFetching latest articles\b",
    r"\bMost Viewed In [A-Za-z &]+\b",
    r"\bLatest In [A-Za-z &]+\b",
)
BODY_SOURCE_RANK = {
    "jsonld_articleBody": 6,
    "newspaper_fulltext": 5,
    "newspaper_text": 4,
    "jsonld_description": 3,
    "meta_description_html": 2,
    "meta_description": 1,
}
DEFAULT_PLAYWRIGHT_DOMAINS = (
    "stockhead.com.au",
    "skynews.com.au",
    "capitalbrief.com",
    "finance.yahoo.com",
    "benzinga.com",
)


@dataclass(frozen=True)
class SourceSpec:
    mode: str
    url: str
    original: str


@dataclass(frozen=True)
class FeedEntry:
    url: str
    title: str
    published_at: dt.datetime | None


@dataclass(frozen=True)
class ExtractedArticle:
    source_url: str
    source_name: str
    article_url: str
    title: str
    body: str
    language: str
    authors: List[str]
    published_at: dt.datetime | None
    keyword_hits: List[str]
    body_source: str = "newspaper"
    body_lengths: dict[str, int] | None = None
    raw_html_path: str = ""


def now_utc() -> dt.datetime:
    return dt.datetime.now(tz=UTC)


def iso_utc(value: dt.datetime) -> str:
    return value.astimezone(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def normalize_space(value: object) -> str:
    return re.sub(r"\s+", " ", str(value or "").replace("\r", " ").replace("\n", " ")).strip()


def parse_keywords(path: Path | None, inline_keywords: str) -> List[str]:
    out: List[str] = []
    seen: set[str] = set()

    def _push(raw: str) -> None:
        token = normalize_space(raw).lower()
        if not token or token in seen:
            return
        seen.add(token)
        out.append(token)

    if path is not None:
        if not path.exists():
            raise RuntimeError(f"Keyword file not found: {path}")
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            _push(line)

    if inline_keywords.strip():
        for part in inline_keywords.split(","):
            _push(part)

    if not out:
        for token in DEFAULT_KEYWORDS:
            _push(token)
    return out


def parse_token_list(raw: str) -> List[str]:
    out: List[str] = []
    seen: set[str] = set()
    for part in str(raw or "").split(","):
        token = normalize_space(part).lower()
        if not token or token in seen:
            continue
        seen.add(token)
        out.append(token)
    return out


def parse_domain_list(raw: str) -> List[str]:
    out: List[str] = []
    seen: set[str] = set()
    for part in str(raw or "").split(","):
        token = normalize_space(part).lower()
        if not token:
            continue
        if "://" in token or "/" in token:
            token = domain_of(token)
        if token.startswith("www."):
            token = token[4:]
        if not token or token in seen:
            continue
        seen.add(token)
        out.append(token)
    return out


def _looks_like_article_path(path: str) -> bool:
    value = str(path or "").strip().lower()
    if not value or value == "/":
        return False
    if value.endswith((".jpg", ".jpeg", ".png", ".gif", ".svg", ".css", ".js", ".json", ".xml", ".pdf", ".ico")):
        return False
    segments = [seg for seg in value.split("/") if seg]
    return len(segments) >= 2


def canonicalize_url(value: object, strip_www: bool = True) -> str:
    raw = normalize_space(value)
    if not raw:
        return ""
    if "://" not in raw and not raw.startswith("//"):
        raw = "https://" + raw
    split = urlsplit(raw)
    scheme = (split.scheme or "https").lower()
    host = (split.hostname or "").lower()
    if strip_www and host.startswith("www."):
        host = host[4:]
    path = split.path or "/"
    if path != "/" and path.endswith("/"):
        path = path[:-1]
    kept_query = []
    for key, val in parse_qsl(split.query, keep_blank_values=True):
        low = key.strip().lower()
        if low in TRACKING_PARAMS or low.startswith("utm_"):
            continue
        kept_query.append((key, val))
    kept_query.sort(key=lambda item: (item[0].lower(), item[1]))
    query = urlencode(kept_query, doseq=True)
    return urlunsplit((scheme, host, path, query, ""))


def domain_of(value: str) -> str:
    canonical = canonicalize_url(value)
    if not canonical:
        return ""
    return (urlsplit(canonical).hostname or "").lower()


def parse_source_spec(raw: str) -> SourceSpec:
    text = normalize_space(raw)
    if not text:
        raise RuntimeError("Empty source line.")
    mode = "auto"
    url = text
    match = re.match(r"^(auto|web|rss|url)\s*:\s*(.+)$", text, flags=re.IGNORECASE)
    if match:
        mode = str(match.group(1)).strip().lower()
        url = str(match.group(2)).strip()
    if mode not in SOURCE_MODES:
        raise RuntimeError(f"Unsupported source mode '{mode}'. Expected one of: {sorted(SOURCE_MODES)}")
    canonical = canonicalize_url(url, strip_www=False)
    if not canonical:
        raise RuntimeError(f"Invalid source URL: {raw}")
    return SourceSpec(mode=mode, url=canonical, original=text)


def parse_sources(path: Path) -> List[SourceSpec]:
    if not path.exists():
        raise RuntimeError(f"Sources file not found: {path}")
    out: List[SourceSpec] = []
    seen: set[str] = set()
    for line in path.read_text(encoding="utf-8").splitlines():
        raw = line.strip()
        if not raw or raw.startswith("#"):
            continue
        spec = parse_source_spec(raw)
        dedupe_key = f"{spec.mode}:{spec.url}"
        if dedupe_key in seen:
            continue
        seen.add(dedupe_key)
        out.append(spec)
    return out


def domain_allowed(domain: str, allowed_domains: Sequence[str]) -> bool:
    if not domain:
        return False
    for allow in allowed_domains:
        token = str(allow or "").strip().lower()
        if not token:
            continue
        if domain == token or domain.endswith("." + token):
            return True
    return False


def keyword_hits(text: str, keywords: Sequence[str]) -> List[str]:
    haystack = normalize_space(text).lower()
    hits = [kw for kw in keywords if kw and kw in haystack]
    return sorted(set(hits))


def clean_article_text(value: object) -> str:
    text = normalize_space(value)
    if not text:
        return ""
    for pattern in BODY_NOISE_PATTERNS:
        text = re.sub(pattern, " ", text, flags=re.IGNORECASE)
    return normalize_space(text)


def finance_url_allowed(url: str, include_tokens: Sequence[str], exclude_tokens: Sequence[str]) -> bool:
    path = urlsplit(canonicalize_url(url)).path.lower()
    if not path:
        return False
    for token in exclude_tokens:
        if token and token in path:
            return False
    if not include_tokens:
        return True
    for token in include_tokens:
        if token and token in path:
            return True
    return False


def looks_like_article_url(url: str) -> bool:
    canonical = canonicalize_url(url)
    split = urlsplit(canonical)
    path = (split.path or "").lower().rstrip("/")
    if not path:
        return False

    segments = [seg for seg in path.split("/") if seg]
    if not segments:
        return False
    last = segments[-1]
    if last in SECTION_PATH_TAILS:
        return False

    host = (split.hostname or "").lower()
    if host == "afr.com" or host.endswith(".afr.com"):
        if re.search(r"-\d{8}-p[a-z0-9]+$", last):
            return True
        if re.search(r"/\d{4}/\d{2}/\d{2}/", path):
            return True
        return False

    if re.search(r"/\d{4}/\d{2}/\d{2}/", path):
        return True
    if re.search(r"\d{4}-\d{2}-\d{2}", path):
        return True
    if len(segments) >= 3 and re.search(r"\d", last):
        return True
    if len(segments) >= 4 and "-" in last and len(last) >= 24:
        return True
    return False


def is_explicitly_non_article_path(url: str) -> bool:
    canonical = canonicalize_url(url)
    path = (urlsplit(canonical).path or "").lower().strip("/")
    if not path:
        return True
    segments = [seg for seg in path.split("/") if seg]
    if not segments:
        return True
    return any(seg in NON_ARTICLE_PATH_SEGMENTS for seg in segments)


def is_domain_specific_non_article_path(url: str) -> bool:
    canonical = canonicalize_url(url)
    split = urlsplit(canonical)
    domain = (split.hostname or "").lower()
    path = (split.path or "").strip("/")
    segments = [seg for seg in path.split("/") if seg]
    if domain == "theaustralian.com.au":
        # Section landing pages are typically depth-1/2; article pages are deeper.
        return len(segments) < 3
    return False


def article_url_priority(url: str) -> tuple[int, int]:
    canonical = canonicalize_url(url)
    split = urlsplit(canonical)
    domain = (split.hostname or "").lower()
    path = (split.path or "").lower().strip("/")
    segments = [seg for seg in path.split("/") if seg]
    last = segments[-1] if segments else ""

    score = 0
    if is_explicitly_non_article_path(canonical):
        score -= 100
    if last in SECTION_PATH_TAILS:
        score -= 20

    if len(segments) >= 4:
        score += 4
    elif len(segments) >= 3:
        score += 2

    if re.search(r"/live-coverage/", path):
        score += 5
    if re.search(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$", last):
        score += 6
    if re.search(r"\d", last):
        score += 2
    if "-" in last and len(last) >= 24:
        score += 2

    if domain == "theaustralian.com.au":
        if len(segments) >= 3:
            score += 3
        else:
            score -= 12

    return score, len(path)


def coerce_datetime(value: object) -> dt.datetime | None:
    if value is None:
        return None
    if isinstance(value, dt.datetime):
        if value.tzinfo is None:
            return value.replace(tzinfo=UTC)
        return value.astimezone(UTC)
    if isinstance(value, dt.date):
        return dt.datetime(value.year, value.month, value.day, tzinfo=UTC)
    raw = normalize_space(value)
    if not raw:
        return None
    raw = raw.replace("/", "-")
    if raw.endswith("Z"):
        raw = raw[:-1] + "+00:00"
    candidates = [raw]
    if " " in raw and "T" not in raw:
        candidates.append(raw.replace(" ", "T"))
    for item in candidates:
        try:
            parsed = dt.datetime.fromisoformat(item)
            if parsed.tzinfo is None:
                return parsed.replace(tzinfo=UTC)
            return parsed.astimezone(UTC)
        except ValueError:
            continue
    try:
        parsed = email.utils.parsedate_to_datetime(raw)
        if parsed is None:
            return None
        if parsed.tzinfo is None:
            return parsed.replace(tzinfo=UTC)
        return parsed.astimezone(UTC)
    except Exception:
        return None


def _tag_local_name(tag: object) -> str:
    text = str(tag or "")
    if "}" in text:
        return text.split("}", 1)[1].lower()
    return text.lower()


def _entry_link(entry: ET.Element) -> str:
    preferred = ""
    for child in entry.iter():
        if _tag_local_name(child.tag) != "link":
            continue
        href = normalize_space(child.attrib.get("href", ""))
        rel = normalize_space(child.attrib.get("rel", "")).lower()
        text = normalize_space(child.text)
        if href and (not preferred or rel in {"", "alternate"}):
            preferred = href
        if text.startswith("http") and not preferred:
            preferred = text
    if preferred:
        return canonicalize_url(preferred)
    return ""


def _entry_text(entry: ET.Element, names: Sequence[str]) -> str:
    wanted = {name.lower() for name in names}
    for child in entry.iter():
        if _tag_local_name(child.tag) in wanted:
            value = normalize_space(child.text)
            if value:
                return value
    return ""


def parse_feed_entries_from_xml(xml_text: str) -> List[FeedEntry]:
    text = str(xml_text or "").strip()
    if not text:
        return []
    root = ET.fromstring(text)
    entries: list[FeedEntry] = []
    for node in root.iter():
        if _tag_local_name(node.tag) not in {"item", "entry"}:
            continue
        link = _entry_link(node)
        if not link:
            continue
        title = _entry_text(node, names=("title",))
        published_raw = _entry_text(node, names=("pubdate", "published", "updated", "date"))
        entries.append(
            FeedEntry(
                url=canonicalize_url(link),
                title=title,
                published_at=coerce_datetime(published_raw),
            )
        )
    return entries


def fetch_url_text(
    url: str,
    request_timeout_seconds: int,
    accept_header: str = "text/html,application/xhtml+xml,*/*;q=0.8",
    http_cookie: str = "",
) -> str:
    headers = {
        "User-Agent": HTTP_USER_AGENT,
        "Accept": accept_header,
    }
    cookie = normalize_space(http_cookie)
    if cookie:
        headers["Cookie"] = cookie
    req = Request(
        url,
        headers=headers,
    )
    with urlopen(req, timeout=float(max(1, request_timeout_seconds))) as resp:
        payload = resp.read()
        content_type = str(resp.headers.get("Content-Type", ""))
    charset_match = re.search(r"charset=([A-Za-z0-9._-]+)", content_type, flags=re.IGNORECASE)
    charset = charset_match.group(1) if charset_match else "utf-8"
    return payload.decode(charset, errors="replace")


def fetch_feed_entries(feed_url: str, request_timeout_seconds: int, http_cookie: str = "") -> List[FeedEntry]:
    xml_text = fetch_url_text(
        feed_url,
        request_timeout_seconds=request_timeout_seconds,
        accept_header="application/rss+xml, application/atom+xml, text/xml;q=0.9, */*;q=0.7",
        http_cookie=http_cookie,
    )
    return parse_feed_entries_from_xml(xml_text)


def extract_article_body_from_jsonld(html_text: str) -> str:
    text = str(html_text or "")
    if not text:
        return ""
    bodies: List[str] = []
    pattern = re.compile(r'"articleBody"\s*:\s*"((?:\\.|[^"\\])*)"', flags=re.IGNORECASE | re.DOTALL)
    for match in pattern.finditer(text):
        raw = match.group(1)
        try:
            decoded = json.loads(f'"{raw}"')
        except Exception:
            continue
        candidate = clean_article_text(decoded)
        if candidate:
            bodies.append(candidate)
    if not bodies:
        return ""
    return max(bodies, key=len)


def extract_description_from_jsonld(html_text: str) -> str:
    text = str(html_text or "")
    if not text:
        return ""
    descriptions: List[str] = []
    pattern = re.compile(r'"description"\s*:\s*"((?:\\.|[^"\\])*)"', flags=re.IGNORECASE | re.DOTALL)
    for match in pattern.finditer(text):
        raw = match.group(1)
        try:
            decoded = json.loads(f'"{raw}"')
        except Exception:
            continue
        candidate = clean_article_text(decoded)
        if candidate:
            descriptions.append(candidate)
    if not descriptions:
        return ""
    return max(descriptions, key=len)


def extract_meta_description_from_html(html_text: str) -> str:
    text = str(html_text or "")
    if not text:
        return ""
    preferred: list[str] = []
    fallback: list[str] = []
    for match in re.finditer(r"<meta\s+[^>]*>", text, flags=re.IGNORECASE):
        tag = match.group(0)
        attrs: dict[str, str] = {}
        for attr in re.finditer(r'([A-Za-z:_-]+)\s*=\s*["\']([^"\']*)["\']', tag):
            key = str(attr.group(1) or "").strip().lower()
            val = html_lib.unescape(str(attr.group(2) or "").strip())
            if key:
                attrs[key] = val
        name = str(attrs.get("name", "")).strip().lower()
        prop = str(attrs.get("property", "")).strip().lower()
        content = clean_article_text(attrs.get("content", ""))
        if not content:
            continue
        if name in {"description", "twitter:description"} or prop in {"og:description", "article:description"}:
            preferred.append(content)
        elif "description" in name or "description" in prop:
            fallback.append(content)
    candidates = preferred or fallback
    if not candidates:
        return ""
    return max(candidates, key=len)


def choose_best_article_body(
    *,
    newspaper_module: object,
    title: str,
    meta_description: str,
    item_text: str,
    item_html: str,
) -> tuple[str, str, dict[str, int]]:
    candidates: dict[str, str] = {}

    newspaper_text = clean_article_text(item_text)
    if newspaper_text:
        candidates["newspaper_text"] = newspaper_text

    meta_desc = clean_article_text(meta_description)
    if meta_desc:
        meta_payload = meta_desc if not title else clean_article_text(f"{title}. {meta_desc}")
        if meta_payload:
            candidates["meta_description"] = meta_payload

    html_payload = str(item_html or "")
    if html_payload:
        html_meta_desc = extract_meta_description_from_html(html_payload)
        if html_meta_desc:
            html_meta_payload = html_meta_desc if not title else clean_article_text(f"{title}. {html_meta_desc}")
            if html_meta_payload:
                candidates["meta_description_html"] = html_meta_payload

        jsonld_desc = extract_description_from_jsonld(html_payload)
        if jsonld_desc:
            jsonld_desc_payload = jsonld_desc if not title else clean_article_text(f"{title}. {jsonld_desc}")
            if jsonld_desc_payload:
                candidates["jsonld_description"] = jsonld_desc_payload

        jsonld_text = extract_article_body_from_jsonld(html_payload)
        if jsonld_text:
            candidates["jsonld_articleBody"] = jsonld_text
        fulltext_fn = getattr(newspaper_module, "fulltext", None)
        if callable(fulltext_fn):
            try:
                fulltext_value = clean_article_text(fulltext_fn(html_payload))
            except Exception:
                fulltext_value = ""
            if fulltext_value:
                candidates["newspaper_fulltext"] = fulltext_value

    if not candidates:
        return "", "none", {}

    source, body = max(candidates.items(), key=lambda item: (BODY_SOURCE_RANK.get(item[0], 0), len(item[1])))
    lengths = {key: len(value) for key, value in candidates.items()}
    return body, source, lengths


def extract_afr_article_urls_from_html(*, base_url: str, html_text: str, max_candidates: int) -> List[str]:
    base_domain = domain_of(base_url)
    if base_domain != "afr.com":
        return []

    text = html_lib.unescape(str(html_text or "")).replace("\\/", "/")
    patterns = (
        r"https?://(?:www\.)?afr\.com/[a-z0-9/_-]*-[0-9]{8}-p[0-9a-z]+",
        r"/[a-z0-9/_-]*-[0-9]{8}-p[0-9a-z]+",
    )
    out: List[str] = []
    seen: set[str] = set()

    for pattern in patterns:
        for match in re.finditer(pattern, text, flags=re.IGNORECASE):
            raw = match.group(0)
            abs_url = canonicalize_url(urljoin(base_url, raw))
            if not abs_url:
                continue
            dom = domain_of(abs_url)
            if dom != "afr.com":
                continue
            if abs_url in seen:
                continue
            seen.add(abs_url)
            out.append(abs_url)
            if len(out) >= int(max(1, max_candidates)):
                return out
    return out


def extract_candidate_urls_from_html(*, base_url: str, html_text: str, max_candidates: int) -> tuple[List[str], List[str]]:
    base_domain = domain_of(base_url)
    candidates: List[str] = []
    raw_candidates: List[str] = []
    feed_urls: List[str] = []
    seen: set[str] = set()
    feed_seen: set[str] = set()

    for url in extract_afr_article_urls_from_html(
        base_url=base_url,
        html_text=html_text,
        max_candidates=int(max(1, max_candidates)),
    ):
        if url in seen:
            continue
        seen.add(url)
        raw_candidates.append(url)

    for match in re.finditer(r"href\s*=\s*['\"]([^'\"]+)['\"]", str(html_text or ""), flags=re.IGNORECASE):
        href = html_lib.unescape(match.group(1).strip())
        if not href or href.startswith("javascript:") or href.startswith("mailto:") or href.startswith("#"):
            continue
        abs_url = canonicalize_url(urljoin(base_url, href))
        if not abs_url:
            continue
        abs_domain = domain_of(abs_url)
        if not abs_domain or (base_domain and not domain_allowed(abs_domain, [base_domain])):
            continue
        path = urlsplit(abs_url).path.lower()
        if "rss" in path or path.endswith(".xml") or "/feed" in path:
            if abs_url not in feed_seen:
                feed_seen.add(abs_url)
                feed_urls.append(abs_url)
            continue
        if not _looks_like_article_path(path):
            continue
        if abs_url in seen:
            continue
        seen.add(abs_url)
        raw_candidates.append(abs_url)

    ranked = sorted(raw_candidates, key=lambda value: article_url_priority(value), reverse=True)
    for url in ranked[: int(max(1, max_candidates))]:
        candidates.append(url)
    return candidates, feed_urls


def build_record(article: ExtractedArticle, fetched_at_utc: str) -> dict[str, object]:
    published = article.published_at or coerce_datetime(fetched_at_utc) or now_utc()
    published_iso = iso_utc(published)
    text = normalize_space(article.body)
    title = normalize_space(article.title)
    if title and not text.lower().startswith(title.lower()):
        text = f"{title}\n\n{text}"
    canonical_url = canonicalize_url(article.article_url)
    rec_id = hashlib.sha1(canonical_url.encode("utf-8")).hexdigest()
    extra_fields: dict[str, object] = {
        "source": article.source_name,
        "url": canonical_url,
        "category": "finance",
        "language": normalize_space(article.language).lower() or "en",
        "domain": domain_of(canonical_url),
        "stocks": [],
        "authors": [normalize_space(item) for item in article.authors if normalize_space(item)],
        "matched_keywords": article.keyword_hits,
        "source_url": canonicalize_url(article.source_url),
        "fetched_at_utc": fetched_at_utc,
    }
    if article.body_source:
        extra_fields["body_source"] = article.body_source
    if article.body_lengths:
        extra_fields["body_lengths"] = article.body_lengths
    if article.raw_html_path:
        extra_fields["raw_html_path"] = article.raw_html_path

    return {
        "id": rec_id,
        "date": published_iso,
        "title": title,
        "text": text,
        "extra_fields": extra_fields,
    }


def _import_newspaper():
    try:
        import newspaper  # type: ignore
    except Exception as exc:  # pragma: no cover - exercised by manual setup path
        raise RuntimeError(
            "newspaper4k is not installed in this environment. "
            "Create an isolated venv under integrations/newspaper4k_au and run "
            "'pip install -r integrations/newspaper4k_au/requirements.txt'."
        ) from exc
    return newspaper


def _newspaper_config(newspaper, request_timeout_seconds: int, http_cookie: str = ""):
    cfg = newspaper.Config()
    cfg.memoize_articles = False
    cfg.fetch_images = False
    cfg.request_timeout = int(max(1, request_timeout_seconds))
    cfg.browser_user_agent = HTTP_USER_AGENT
    headers = {"User-Agent": HTTP_USER_AGENT}
    cookie = normalize_space(http_cookie)
    if cookie:
        headers["Cookie"] = cookie
    cfg.headers = headers
    cfg.requests_params = {
        "timeout": int(max(1, request_timeout_seconds)),
        "headers": headers,
    }
    return cfg


def _source_feed_urls(source_obj: object) -> List[str]:
    out: list[str] = []
    for attr in ("feed_urls", "feeds"):
        value = getattr(source_obj, attr, None)
        if not isinstance(value, (list, tuple, set)):
            continue
        for item in value:
            url = canonicalize_url(item)
            if url and url not in out:
                out.append(url)
    return out


def _fallback_feed_urls_for_source(source_url: str) -> List[str]:
    dom = domain_of(source_url)
    if dom not in {
        "afr.com",
        "capitalbrief.com",
        "kalkinemedia.com",
        "kalkinemedia.com.au",
        "benzinga.com",
        "marketindex.com.au",
        "skynews.com.au",
        "stockhead.com.au",
        "stockhead.com",
        "livewiremarkets.com",
        "finance.yahoo.com",
        "theaustralian.com.au",
    }:
        return []
    split = urlsplit(source_url)
    if dom == "afr.com":
        default_host = "www.afr.com"
        feed_paths = AFR_FEED_PATHS
    elif dom == "capitalbrief.com":
        default_host = "www.capitalbrief.com"
        feed_paths = CAPITALBRIEF_FEED_PATHS
    elif dom == "kalkinemedia.com.au":
        default_host = "www.kalkinemedia.com.au"
        feed_paths = KALKINE_FEED_PATHS
    elif dom == "kalkinemedia.com":
        default_host = "www.kalkinemedia.com"
        feed_paths = KALKINE_FEED_PATHS
    elif dom == "theaustralian.com.au":
        default_host = "www.theaustralian.com.au"
        feed_paths = AUSTRALIAN_FEED_PATHS
    elif dom == "marketindex.com.au":
        default_host = "www.marketindex.com.au"
        feed_paths = MARKETINDEX_FEED_PATHS
    elif dom == "skynews.com.au":
        default_host = "www.skynews.com.au"
        feed_paths = SKYNEWS_FEED_PATHS
    elif dom == "stockhead.com.au":
        default_host = "stockhead.com.au"
        feed_paths = STOCKHEAD_FEED_PATHS
    elif dom == "stockhead.com":
        default_host = "www.stockhead.com"
        feed_paths = STOCKHEAD_FEED_PATHS
    elif dom == "livewiremarkets.com":
        default_host = "www.livewiremarkets.com"
        feed_paths = LIVEWIRE_FEED_PATHS
    elif dom == "finance.yahoo.com":
        default_host = "finance.yahoo.com"
        feed_paths = YAHOO_FINANCE_FEED_PATHS
    else:
        default_host = "www.benzinga.com"
        feed_paths = BENZINGA_FEED_PATHS
    host = split.hostname or default_host
    scheme = split.scheme or "https"
    out: List[str] = []
    for path in feed_paths:
        url = canonicalize_url(f"{scheme}://{host}{path}", strip_www=False)
        if url and url not in out:
            out.append(url)
    return out


def save_raw_html_snapshot(*, raw_html_dir: Path | None, article_url: str, html_text: str) -> str:
    if raw_html_dir is None:
        return ""
    payload = str(html_text or "")
    if not payload:
        return ""
    raw_html_dir.mkdir(parents=True, exist_ok=True)
    slug = hashlib.sha1(canonicalize_url(article_url).encode("utf-8")).hexdigest()
    path = raw_html_dir / f"{slug}.html"
    path.write_text(payload, encoding="utf-8")
    return str(path)


def _parse_article_object(
    *,
    item: object,
    item_url: str,
    min_text_chars: int,
    min_keyword_hits: int,
    keywords: Sequence[str],
    recent_cutoff: dt.datetime,
    newspaper_module: object,
) -> tuple[ExtractedArticle | None, str]:
    title = normalize_space(getattr(item, "title", ""))
    meta_description = clean_article_text(getattr(item, "meta_description", ""))
    body, body_source, body_lengths = choose_best_article_body(
        newspaper_module=newspaper_module,
        title=title,
        meta_description=meta_description,
        item_text=str(getattr(item, "text", "")),
        item_html=str(getattr(item, "html", "")),
    )
    if not body:
        return None, "missing_text"
    if len(body) < int(max(1, min_text_chars)):
        return None, "short_body"

    published = coerce_datetime(getattr(item, "publish_date", None))
    if published is not None and published < recent_cutoff:
        return None, "older_than_cutoff"

    hits = keyword_hits(f"{title}\n{body}", keywords)
    if not hits:
        return None, "not_finance_keyword"
    if len(hits) < int(max(1, min_keyword_hits)):
        return None, "insufficient_keyword_hits"

    resolved_item_url = canonicalize_url(getattr(item, "url", "")) or item_url
    source_url_raw = normalize_space(getattr(item, "source_url", ""))
    source_name = normalize_space(getattr(item, "brand", "") or domain_of(source_url_raw) or domain_of(resolved_item_url))
    authors_raw = getattr(item, "authors", [])
    authors = [normalize_space(value) for value in authors_raw if normalize_space(value)]
    article = ExtractedArticle(
        source_url=source_url_raw or resolved_item_url,
        source_name=source_name or domain_of(item_url),
        article_url=resolved_item_url,
        title=title,
        body=body,
        language=normalize_space(getattr(item, "meta_lang", "")),
        authors=authors,
        published_at=published,
        keyword_hits=hits,
        body_source=body_source,
        body_lengths=body_lengths,
    )
    return article, "ok"


def extract_from_source(
    *,
    source: SourceSpec,
    max_articles: int,
    min_text_chars: int,
    min_keyword_hits: int,
    request_timeout_seconds: int,
    finance_url_gate: bool,
    finance_url_include_tokens: Sequence[str],
    finance_url_exclude_tokens: Sequence[str],
    finance_url_gate_exempt_domains: Sequence[str],
    article_url_gate_exempt_domains: Sequence[str],
    keywords: Sequence[str],
    recent_cutoff: dt.datetime,
    raw_html_dir: Path | None,
    http_cookie: str,
    playwright_domains: Sequence[str] | None = None,
) -> tuple[list[ExtractedArticle], dict[str, int]]:
    newspaper = _import_newspaper()
    cfg = _newspaper_config(
        newspaper,
        request_timeout_seconds=request_timeout_seconds,
        http_cookie=http_cookie,
    )

    stats = {
        "source_articles_seen": 0,
        "feed_entries_seen": 0,
        "html_links_seen": 0,
        "download_errors": 0,
        "short_body": 0,
        "missing_url": 0,
        "missing_text": 0,
        "older_than_cutoff": 0,
        "not_finance_keyword": 0,
        "insufficient_keyword_hits": 0,
        "discovery_errors": 0,
        "url_filtered_non_finance_path": 0,
        "url_filtered_non_article_path": 0,
        "raw_html_saved": 0,
        "playwright_attempted": 0,
        "playwright_rescued": 0,
    }
    out: list[ExtractedArticle] = []

    candidates: list[tuple[str, object | None]] = []
    candidate_seen: set[str] = set()
    discovered_feed_urls: list[str] = []

    def _add_candidate(url: str, obj: object | None) -> None:
        canonical = canonicalize_url(url)
        if not canonical or canonical in candidate_seen:
            return
        candidate_seen.add(canonical)
        candidates.append((canonical, obj))

    if source.mode in {"url"}:
        _add_candidate(source.url, None)

    if source.mode in {"web", "auto"}:
        try:
            source_obj = newspaper.build(source.url, config=cfg)
            for article_obj in list(getattr(source_obj, "articles", []) or []):
                _add_candidate(getattr(article_obj, "url", ""), article_obj)
            discovered_feed_urls.extend(_source_feed_urls(source_obj))
        except Exception:
            if source.mode == "web":
                raise
            stats["discovery_errors"] += 1

    if source.mode in {"web", "auto"} and not candidates:
        try:
            html_text = fetch_url_text(
                source.url,
                request_timeout_seconds=request_timeout_seconds,
                http_cookie=http_cookie,
            )
            html_candidates, html_feed_urls = extract_candidate_urls_from_html(
                base_url=source.url,
                html_text=html_text,
                max_candidates=int(max(5, max_articles * 5)),
            )
            stats["html_links_seen"] += len(html_candidates)
            for url in html_candidates:
                _add_candidate(url, None)
            for feed_url in html_feed_urls:
                if feed_url not in discovered_feed_urls:
                    discovered_feed_urls.append(feed_url)
        except Exception:
            if source.mode == "web":
                raise
            stats["discovery_errors"] += 1

    # JS-rendering discovery: if static discovery found nothing and domain is
    # in the playwright_domains list, render the page with Scrapling/Playwright
    # and extract article URLs from the rendered HTML.
    if source.mode in {"web", "auto"} and not candidates and playwright_domains:
        source_domain = domain_of(source.url)
        _pw_domains = [str(d).lower().strip().removeprefix("www.") for d in (playwright_domains or [])]
        if source_domain in _pw_domains or any(source_domain.endswith("." + d) for d in _pw_domains):
            try:
                from playwright_fallback import fetch_article_html_playwright
                rendered_html = fetch_article_html_playwright(source.url, timeout_ms=30000)
                if rendered_html and len(rendered_html) > 1000:
                    js_candidates, js_feed_urls = extract_candidate_urls_from_html(
                        base_url=source.url,
                        html_text=rendered_html,
                        max_candidates=int(max(5, max_articles * 5)),
                    )
                    stats["html_links_seen"] += len(js_candidates)
                    for url in js_candidates:
                        _add_candidate(url, None)
                    for feed_url in js_feed_urls:
                        if feed_url not in discovered_feed_urls:
                            discovered_feed_urls.append(feed_url)
                    if js_candidates:
                        print(f"[newspaper4k] JS discovery for {source.url}: {len(js_candidates)} URLs from rendered HTML", flush=True)
            except Exception as exc:
                stats["discovery_errors"] += 1
                print(f"[newspaper4k] JS discovery failed for {source.url}: {exc}", flush=True)

    feed_urls: list[str] = []
    if source.mode == "rss":
        feed_urls = [source.url]
    elif source.mode == "auto" and not candidates:
        if discovered_feed_urls:
            feed_urls = discovered_feed_urls
        elif source.url.endswith(".xml") or "/rss" in source.url or "/feed" in source.url:
            feed_urls = [source.url]
        else:
            feed_urls = _fallback_feed_urls_for_source(source.url)

    for feed_url in feed_urls:
        try:
            entries = fetch_feed_entries(
                feed_url=feed_url,
                request_timeout_seconds=request_timeout_seconds,
                http_cookie=http_cookie,
            )
        except Exception:
            stats["discovery_errors"] += 1
            continue
        stats["feed_entries_seen"] += len(entries)
        for entry in entries:
            _add_candidate(entry.url, None)
            if len(candidates) >= int(max(1, max_articles)):
                break
        if len(candidates) >= int(max(1, max_articles)):
            break

    for item_url, article_obj in candidates[: int(max(1, max_articles))]:
        stats["source_articles_seen"] += 1
        if not item_url:
            stats["missing_url"] += 1
            continue
        if is_explicitly_non_article_path(item_url):
            stats["url_filtered_non_article_path"] += 1
            continue
        if is_domain_specific_non_article_path(item_url):
            stats["url_filtered_non_article_path"] += 1
            continue
        item_domain = domain_of(item_url)
        is_gate_exempt_domain = domain_allowed(item_domain, finance_url_gate_exempt_domains)
        if bool(finance_url_gate) and not is_gate_exempt_domain:
            if not finance_url_allowed(
                item_url,
                include_tokens=finance_url_include_tokens,
                exclude_tokens=finance_url_exclude_tokens,
            ):
                stats["url_filtered_non_finance_path"] += 1
                continue
        is_article_gate_exempt_domain = domain_allowed(item_domain, article_url_gate_exempt_domains)
        if not is_article_gate_exempt_domain:
            if not looks_like_article_url(item_url):
                stats["url_filtered_non_article_path"] += 1
                continue
        try:
            if article_obj is None:
                article_obj = newspaper.Article(item_url, config=cfg)
            article_obj.download()
            article_obj.parse()
        except Exception:
            # If download fails and domain needs JS rendering, try Scrapling
            _pw_rescue = False
            if playwright_domains is not None:
                try:
                    from playwright_fallback import domain_needs_playwright, fetch_article_html_playwright
                    if domain_needs_playwright(item_url, playwright_domains):
                        rendered_html = fetch_article_html_playwright(item_url, timeout_ms=30000)
                        if rendered_html and len(rendered_html) > 500:
                            body, body_source, body_lengths = choose_best_article_body(
                                newspaper_module=newspaper,
                                title="",
                                meta_description=extract_meta_description_from_html(rendered_html),
                                item_text="",
                                item_html=rendered_html,
                            )
                            if body and len(body) >= int(max(1, min_text_chars)):
                                title = normalize_space(extract_description_from_jsonld(rendered_html)) or ""
                                if not title:
                                    # Try <title> tag
                                    import re as _re
                                    _m = _re.search(r"<title[^>]*>([^<]+)</title>", rendered_html, _re.IGNORECASE)
                                    title = normalize_space(_m.group(1)) if _m else ""
                                published = coerce_datetime(None)
                                article = ExtractedArticle(
                                    source_url=source.url,
                                    source_name=domain_of(item_url),
                                    article_url=item_url,
                                    title=title,
                                    body=body,
                                    language="en",
                                    authors=[],
                                    published_at=published,
                                    keyword_hits=keyword_hits(f"{title}\n{body}", keywords),
                                    body_source=f"playwright+{body_source}",
                                    body_lengths=body_lengths,
                                )
                                out.append(article)
                                _pw_rescue = True
                except Exception:
                    pass
            if not _pw_rescue:
                stats["download_errors"] += 1
                continue

        article, reason = _parse_article_object(
            item=article_obj,
            item_url=item_url,
            min_text_chars=min_text_chars,
            min_keyword_hits=min_keyword_hits,
            keywords=keywords,
            recent_cutoff=recent_cutoff,
            newspaper_module=newspaper,
        )

        # --- Playwright fallback for JS-rendered sites ---
        if article is None and reason in ("short_body", "missing_text") and playwright_domains is not None:
            try:
                from playwright_fallback import domain_needs_playwright, fetch_article_html_playwright
            except ImportError:
                domain_needs_playwright = None  # type: ignore[assignment]
                fetch_article_html_playwright = None  # type: ignore[assignment]
            if domain_needs_playwright is not None and fetch_article_html_playwright is not None:
                if domain_needs_playwright(item_url, playwright_domains):
                    stats["playwright_attempted"] += 1
                    pw_html = fetch_article_html_playwright(item_url, timeout_ms=int(max(5000, request_timeout_seconds * 1000)))
                    if pw_html:
                        # Re-parse the rendered HTML through newspaper4k's fulltext extractor
                        fulltext_fn = getattr(newspaper, "fulltext", None)
                        pw_text = ""
                        if callable(fulltext_fn):
                            try:
                                pw_text = clean_article_text(fulltext_fn(pw_html))
                            except Exception:
                                pw_text = ""
                        if not pw_text:
                            # BeautifulSoup fallback for body text extraction
                            try:
                                from bs4 import BeautifulSoup
                                soup = BeautifulSoup(pw_html, "html.parser")
                                # Remove script/style tags
                                for tag in soup(["script", "style", "nav", "footer", "header"]):
                                    tag.decompose()
                                pw_text = clean_article_text(soup.get_text(separator=" "))
                            except Exception:
                                pw_text = ""
                        if pw_text and len(pw_text) >= int(max(1, min_text_chars)):
                            # Rebuild article_obj html attribute for re-parse
                            article_obj.html = pw_html  # type: ignore[attr-defined]
                            article_obj.text = pw_text  # type: ignore[attr-defined]
                            article, reason = _parse_article_object(
                                item=article_obj,
                                item_url=item_url,
                                min_text_chars=min_text_chars,
                                min_keyword_hits=min_keyword_hits,
                                keywords=keywords,
                                recent_cutoff=recent_cutoff,
                                newspaper_module=newspaper,
                            )
                            if article is not None:
                                stats["playwright_rescued"] += 1
                                article = replace(article, body_source=f"playwright+{article.body_source}")

        if article is None:
            stats[reason] += 1
            continue
        raw_html_path = save_raw_html_snapshot(
            raw_html_dir=raw_html_dir,
            article_url=item_url,
            html_text=str(getattr(article_obj, "html", "")),
        )
        if raw_html_path:
            stats["raw_html_saved"] += 1
            article = replace(article, raw_html_path=raw_html_path)
        out.append(article)

    return out, stats


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    script_dir = Path(__file__).resolve().parent
    ap = argparse.ArgumentParser(
        description="Isolated AU finance news collector using newspaper4k. Outputs JSONL compatible with build_news_context_db.py."
    )
    ap.add_argument(
        "--sources-file",
        default=str(script_dir / "sources_au_finance.txt"),
        help="Source list. Prefix optional per line: auto:, web:, rss:, url:",
    )
    ap.add_argument(
        "--output-jsonl",
        default=str(script_dir / "out" / "au_finance_news.jsonl"),
        help="Output JSONL path (research artifact only)",
    )
    ap.add_argument("--manifest-json", default="", help="Optional run-manifest JSON path")
    ap.add_argument(
        "--raw-html-dir",
        default="",
        help="Optional directory to persist raw fetched article HTML snapshots.",
    )
    ap.add_argument("--max-sources", type=int, default=0, help="Optional cap of sources from --sources-file")
    ap.add_argument("--max-articles-per-source", type=int, default=30, help="Cap per source")
    ap.add_argument("--max-total-articles", type=int, default=300, help="Global cap")
    ap.add_argument("--lookback-hours", type=int, default=96, help="Drop articles older than this window if publish date exists")
    ap.add_argument("--min-text-chars", type=int, default=350, help="Minimum article body chars")
    ap.add_argument("--min-keyword-hits", type=int, default=1, help="Minimum finance keyword hits required per article")
    ap.add_argument("--request-timeout-seconds", type=int, default=20, help="Timeout for source/feed/article requests")
    ap.add_argument("--sleep-seconds", type=float, default=0.5, help="Delay between source crawls")
    ap.add_argument("--keywords-file", default="", help="Optional newline keyword file")
    ap.add_argument("--keywords", default="", help="Optional extra comma-separated keywords")
    ap.add_argument("--http-cookie", default="", help="Optional Cookie header string for authenticated article fetches.")
    ap.add_argument(
        "--http-cookie-file",
        default="",
        help="Optional file containing a Cookie header value for authenticated article fetches.",
    )
    ap.add_argument(
        "--finance-url-include-tokens",
        default=",".join(DEFAULT_FINANCE_URL_INCLUDE_TOKENS),
        help="Comma-separated URL path tokens to include (finance gate).",
    )
    ap.add_argument(
        "--finance-url-exclude-tokens",
        default=",".join(DEFAULT_FINANCE_URL_EXCLUDE_TOKENS),
        help="Comma-separated URL path tokens to exclude (finance gate).",
    )
    ap.add_argument(
        "--finance-url-gate-exempt-domains",
        default="",
        help="Comma-separated domains exempt from finance URL-path gate (example: capitalbrief.com).",
    )
    ap.add_argument(
        "--article-url-gate-exempt-domains",
        default="",
        help="Comma-separated domains exempt from article URL-shape gate (example: capitalbrief.com).",
    )
    ap.add_argument("--disable-finance-url-gate", action="store_true", help="Disable finance URL-path gate.")
    ap.add_argument(
        "--playwright-domains",
        default=",".join(DEFAULT_PLAYWRIGHT_DOMAINS),
        help=(
            "Comma-separated domains that need Playwright JS rendering as fallback. "
            "Default: %(default)s"
        ),
    )
    ap.add_argument(
        "--no-playwright",
        action="store_true",
        help="Disable Playwright fallback entirely (pipeline runs without browser).",
    )
    ap.add_argument("--dry-run", action="store_true", help="Skip JSONL writes and print only manifest")
    ap.add_argument(
        "--allow-empty-overwrite",
        action="store_true",
        help="Allow zero-record runs to overwrite an existing non-empty output JSONL.",
    )
    ap.add_argument(
        "--keep-future-warnings",
        action="store_true",
        help="Show upstream newspaper4k FutureWarnings (suppressed by default).",
    )
    return ap.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    if not bool(args.keep_future_warnings):
        warnings.filterwarnings("ignore", category=FutureWarning, module=r"newspaper(\..*)?$")

    sources_file = Path(args.sources_file).expanduser().resolve()
    output_jsonl = Path(args.output_jsonl).expanduser().resolve()
    manifest_json = Path(args.manifest_json).expanduser().resolve() if str(args.manifest_json or "").strip() else None
    raw_html_dir = Path(args.raw_html_dir).expanduser().resolve() if str(args.raw_html_dir or "").strip() else None
    keywords_path = Path(args.keywords_file).expanduser().resolve() if str(args.keywords_file or "").strip() else None
    http_cookie = normalize_space(args.http_cookie)
    if str(args.http_cookie_file or "").strip():
        cookie_path = Path(args.http_cookie_file).expanduser().resolve()
        if not cookie_path.exists():
            print(f"Cookie file not found: {cookie_path}", file=sys.stderr)
            return 2
        http_cookie = normalize_space(cookie_path.read_text(encoding="utf-8"))

    try:
        sources = parse_sources(sources_file)
    except Exception as exc:
        print(str(exc), file=sys.stderr)
        return 2
    try:
        _import_newspaper()
    except Exception as exc:
        print(str(exc), file=sys.stderr)
        return 2

    if int(args.max_sources) > 0:
        sources = sources[: int(args.max_sources)]
    if not sources:
        print("No sources were resolved.", file=sys.stderr)
        return 2

    try:
        keywords = parse_keywords(keywords_path, str(args.keywords or ""))
    except Exception as exc:
        print(str(exc), file=sys.stderr)
        return 2
    allowed_domains = sorted({domain_of(spec.url) for spec in sources if domain_of(spec.url)})
    finance_url_include_tokens = parse_token_list(args.finance_url_include_tokens)
    finance_url_exclude_tokens = parse_token_list(args.finance_url_exclude_tokens)
    finance_url_gate_exempt_domains = parse_domain_list(args.finance_url_gate_exempt_domains)
    article_url_gate_exempt_domains = parse_domain_list(args.article_url_gate_exempt_domains)
    finance_url_gate = not bool(args.disable_finance_url_gate)
    playwright_domains: list[str] | None = None
    if not bool(args.no_playwright):
        pw_raw = parse_domain_list(getattr(args, "playwright_domains", ""))
        if pw_raw:
            playwright_domains = pw_raw
    fetched_at = iso_utc(now_utc())
    cutoff = now_utc() - dt.timedelta(hours=int(max(1, args.lookback_hours)))

    seen_urls: set[str] = set()
    all_records: list[dict[str, object]] = []
    source_breakdown: list[dict[str, object]] = []
    totals = {
        "source_articles_seen": 0,
        "feed_entries_seen": 0,
        "html_links_seen": 0,
        "download_errors": 0,
        "short_body": 0,
        "missing_url": 0,
        "missing_text": 0,
        "older_than_cutoff": 0,
        "not_finance_keyword": 0,
        "insufficient_keyword_hits": 0,
        "discovery_errors": 0,
        "url_filtered_non_finance_path": 0,
        "url_filtered_non_article_path": 0,
        "raw_html_saved": 0,
        "playwright_attempted": 0,
        "playwright_rescued": 0,
        "blocked_domain": 0,
        "duplicate_url": 0,
    }

    for index, spec in enumerate(sources, start=1):
        try:
            extracted, stats = extract_from_source(
                source=spec,
                max_articles=int(args.max_articles_per_source),
                min_text_chars=int(args.min_text_chars),
                min_keyword_hits=int(args.min_keyword_hits),
                request_timeout_seconds=int(args.request_timeout_seconds),
                finance_url_gate=finance_url_gate,
                finance_url_include_tokens=finance_url_include_tokens,
                finance_url_exclude_tokens=finance_url_exclude_tokens,
                finance_url_gate_exempt_domains=finance_url_gate_exempt_domains,
                article_url_gate_exempt_domains=article_url_gate_exempt_domains,
                keywords=keywords,
                recent_cutoff=cutoff,
                raw_html_dir=raw_html_dir,
                http_cookie=http_cookie,
                playwright_domains=playwright_domains,
            )
        except Exception as exc:
            source_breakdown.append(
                {
                    "source": spec.url,
                    "mode": spec.mode,
                    "error": str(exc),
                    "kept": 0,
                }
            )
            if index < len(sources) and float(args.sleep_seconds) > 0:
                time.sleep(float(args.sleep_seconds))
            continue

        for key in totals:
            if key in stats:
                totals[key] += int(stats[key])

        kept_for_source = 0
        for article in extracted:
            article_domain = domain_of(article.article_url)
            if not domain_allowed(article_domain, allowed_domains):
                totals["blocked_domain"] += 1
                continue
            canonical_url = canonicalize_url(article.article_url)
            if canonical_url in seen_urls:
                totals["duplicate_url"] += 1
                continue
            seen_urls.add(canonical_url)
            all_records.append(build_record(article, fetched_at_utc=fetched_at))
            kept_for_source += 1
            if 0 < int(args.max_total_articles) <= len(all_records):
                break

        source_breakdown.append(
            {
                "source": spec.url,
                "mode": spec.mode,
                "seen": int(stats.get("source_articles_seen", 0)),
                "feed_entries_seen": int(stats.get("feed_entries_seen", 0)),
                "html_links_seen": int(stats.get("html_links_seen", 0)),
                "kept": kept_for_source,
                "download_errors": int(stats.get("download_errors", 0)),
                "short_body": int(stats.get("short_body", 0)),
                "older_than_cutoff": int(stats.get("older_than_cutoff", 0)),
                "not_finance_keyword": int(stats.get("not_finance_keyword", 0)),
                "insufficient_keyword_hits": int(stats.get("insufficient_keyword_hits", 0)),
                "url_filtered_non_finance_path": int(stats.get("url_filtered_non_finance_path", 0)),
                "url_filtered_non_article_path": int(stats.get("url_filtered_non_article_path", 0)),
                "raw_html_saved": int(stats.get("raw_html_saved", 0)),
                "discovery_errors": int(stats.get("discovery_errors", 0)),
            }
        )
        if 0 < int(args.max_total_articles) <= len(all_records):
            break
        if index < len(sources) and float(args.sleep_seconds) > 0:
            time.sleep(float(args.sleep_seconds))

    output_write_skipped = False
    output_write_skip_reason = ""
    if not args.dry_run:
        output_jsonl.parent.mkdir(parents=True, exist_ok=True)
        existing_non_empty = output_jsonl.exists() and output_jsonl.stat().st_size > 0
        if len(all_records) == 0 and existing_non_empty and not bool(args.allow_empty_overwrite):
            output_write_skipped = True
            output_write_skip_reason = "empty_run_preserved_existing_non_empty_output"
            print(
                f"[safety] skipped overwriting non-empty output with zero-record run: {output_jsonl}",
                file=sys.stderr,
            )
        else:
            with output_jsonl.open("w", encoding="utf-8") as fh:
                for row in all_records:
                    fh.write(json.dumps(row, ensure_ascii=False) + "\n")

    manifest = {
        "status": "success",
        "fetched_at_utc": fetched_at,
        "source_count": len(sources),
        "keywords": keywords,
        "output_jsonl": "" if args.dry_run else str(output_jsonl),
        "dry_run": bool(args.dry_run),
        "records_kept": len(all_records),
        "output_write_skipped": output_write_skipped,
        "output_write_skip_reason": output_write_skip_reason,
        "totals": totals,
        "source_breakdown": source_breakdown,
    }
    if manifest_json is not None:
        manifest_json.parent.mkdir(parents=True, exist_ok=True)
        manifest_json.write_text(json.dumps(manifest, indent=2, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")

    print(json.dumps(manifest, indent=2, ensure_ascii=False, sort_keys=True))

    # Shut down shared Playwright browser if it was used.
    if playwright_domains is not None:
        try:
            from playwright_fallback import shutdown_playwright
            shutdown_playwright()
        except Exception:
            pass

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
