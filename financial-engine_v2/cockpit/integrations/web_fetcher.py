from __future__ import annotations

import re
from urllib.parse import parse_qs, unquote, urlparse

import httpx


class WebFetcher:
    FINANCE_TERMS = (
        "revenue",
        "ebit",
        "ebitda",
        "npat",
        "profit",
        "loss",
        "cash",
        "cashflow",
        "cash flow",
        "liquidity",
        "debt",
        "refinanc",
        "maturity",
        "covenant",
        "dividend",
        "guidance",
        "margin",
        "capex",
        "facility",
        "borrow",
    )
    _TITLE_RE = re.compile(r"<title[^>]*>(.*?)</title>", flags=re.IGNORECASE | re.DOTALL)
    _SCRIPT_STYLE_RE = re.compile(r"<(script|style)[^>]*>.*?</\1>", flags=re.IGNORECASE | re.DOTALL)
    _TAG_RE = re.compile(r"<[^>]+>")
    _DATE_RE = re.compile(
        r"(?:\b20\d{2}-\d{2}-\d{2}\b|\b\d{1,2}\s+[A-Za-z]{3,9}\s+20\d{2}\b|\b[A-Za-z]{3,9}\s+\d{1,2},\s*20\d{2}\b)"
    )
    _NUMBER_RE = re.compile(
        r"(?:[$€£¥]\s?\d[\d,]*(?:\.\d+)?(?:\s?(?:bn|billion|m|million|k|%|bps|bp))?"
        r"|\b\d[\d,]*(?:\.\d+)?\s?(?:%|bps|bp|bn|billion|m|million|k)?\b)",
        flags=re.IGNORECASE,
    )

    @staticmethod
    def _normalize_domain(value: str | None) -> str:
        raw = str(value or "").strip().lower()
        if not raw:
            return ""
        parsed = urlparse(raw if "://" in raw else f"https://{raw}")
        domain = str(parsed.netloc or parsed.path or "").strip().lower()
        if ":" in domain:
            domain = domain.split(":", 1)[0]
        if domain.startswith("www."):
            domain = domain[4:]
        return domain

    @classmethod
    def _is_preferred_domain(cls, url: str, preferred_domains: list[str]) -> bool:
        domain = cls._normalize_domain(url)
        if not domain:
            return False
        for preferred in preferred_domains:
            pd = cls._normalize_domain(preferred)
            if not pd:
                continue
            if domain == pd or domain.endswith("." + pd):
                return True
        return False

    def fetch_text(self, url: str, timeout: float = 20.0, max_chars: int | None = 8000) -> str:
        with httpx.Client(timeout=timeout, follow_redirects=True) as client:
            response = client.get(url, headers={"User-Agent": "FinancialEngineCockpit/1.0"})
            response.raise_for_status()
            body = response.text
            if max_chars is None:
                return body
            return body[:max_chars]

    @staticmethod
    def _extract_urls_from_duckduckgo_html(html: str, max_results: int) -> list[str]:
        urls: list[str] = []
        seen: set[str] = set()
        for match in re.findall(r'href="([^"]+)"', html or "", flags=re.IGNORECASE):
            candidate = str(match or "").strip()
            if not candidate:
                continue
            if candidate.startswith("//"):
                candidate = "https:" + candidate
            if candidate.startswith("/l/?"):
                parsed = urlparse("https://duckduckgo.com" + candidate)
                q = parse_qs(parsed.query)
                raw = (q.get("uddg") or [""])[0]
                if raw:
                    candidate = unquote(raw)
            parsed = urlparse(candidate)
            if parsed.scheme not in {"http", "https"}:
                continue
            netloc = (parsed.netloc or "").lower()
            if not netloc:
                continue
            if "duckduckgo.com" in netloc:
                continue
            if candidate in seen:
                continue
            seen.add(candidate)
            urls.append(candidate)
            if len(urls) >= max(1, int(max_results)):
                break
        return urls

    @classmethod
    def _rank_urls_by_preferred(
        cls,
        urls: list[str],
        preferred_domains: list[str],
    ) -> list[str]:
        scored: list[tuple[int, int, str]] = []
        for idx, url in enumerate(urls):
            preferred = 1 if cls._is_preferred_domain(url, preferred_domains) else 0
            scored.append((preferred, -idx, url))
        scored.sort(key=lambda row: (row[0], row[1]), reverse=True)
        return [row[2] for row in scored]

    @classmethod
    def _extract_page_title(cls, html: str) -> str:
        match = cls._TITLE_RE.search(str(html or ""))
        if not match:
            return ""
        title = re.sub(r"\s+", " ", match.group(1)).strip()
        return title[:240]

    @classmethod
    def _strip_html_to_text(cls, html: str) -> str:
        cleaned = cls._SCRIPT_STYLE_RE.sub(" ", str(html or ""))
        cleaned = cls._TAG_RE.sub(" ", cleaned)
        cleaned = cleaned.replace("&nbsp;", " ")
        cleaned = cleaned.replace("&amp;", "&")
        cleaned = re.sub(r"\s+", " ", cleaned).strip()
        return cleaned

    @classmethod
    def _extract_fact_rows(cls, text: str, url: str, *, max_facts: int = 3) -> list[dict]:
        cleaned = re.sub(r"\s+", " ", str(text or "")).strip()
        if not cleaned:
            return []
        sentences = re.split(r"(?<=[.!?])\s+", cleaned)
        out: list[dict] = []
        for sentence in sentences:
            claim = re.sub(r"\s+", " ", sentence).strip()
            if len(claim) < 40:
                continue
            lower = claim.lower()
            term_hits = [term for term in cls.FINANCE_TERMS if term in lower]
            if not term_hits:
                continue
            number_hits = [match.group(0).strip() for match in cls._NUMBER_RE.finditer(claim)]
            date_hits = [match.group(0).strip() for match in cls._DATE_RE.finditer(claim)]
            if not number_hits and not date_hits:
                continue
            out.append(
                {
                    "url": url,
                    "claim": claim[:360],
                    "numbers": number_hits[:4],
                    "dates": date_hits[:3],
                    "terms": sorted(set(term_hits))[:4],
                }
            )
            if len(out) >= max(1, int(max_facts)):
                break
        return out

    def search_and_fetch(
        self,
        query: str,
        *,
        max_results: int = 3,
        timeout: float = 20.0,
        max_chars_per_page: int = 3000,
        preferred_domains: list[str] | None = None,
        strict_official: bool = False,
    ) -> dict:
        q = str(query or "").strip()
        if not q:
            return {"ok": False, "error": "query is required", "query": q, "urls": [], "pages": []}

        preferred = [self._normalize_domain(domain) for domain in (preferred_domains or [])]
        preferred = [domain for domain in preferred if domain]
        if "asx.com.au" not in preferred:
            preferred.insert(0, "asx.com.au")

        with httpx.Client(timeout=timeout, follow_redirects=True) as client:
            search_resp = client.get(
                "https://duckduckgo.com/html/",
                params={"q": q},
                headers={"User-Agent": "FinancialEngineCockpit/1.0"},
            )
            search_resp.raise_for_status()
            html = search_resp.text or ""

            candidate_limit = max(max(1, int(max_results)) * 6, max(6, int(max_results)))
            discovered_urls = self._extract_urls_from_duckduckgo_html(html, max_results=candidate_limit)
            ranked_urls = self._rank_urls_by_preferred(discovered_urls, preferred)
            urls = ranked_urls[: max(1, int(max_results))]
            official_candidates = [url for url in discovered_urls if self._is_preferred_domain(url, preferred)]
            pages: list[dict] = []
            facts: list[dict] = []
            official_source_found = False
            for url in urls:
                official_source = self._is_preferred_domain(url, preferred)
                official_source_found = official_source_found or official_source
                try:
                    page_resp = client.get(url, headers={"User-Agent": "FinancialEngineCockpit/1.0"})
                    page_resp.raise_for_status()
                    body_html = page_resp.text or ""
                    text = self._strip_html_to_text(body_html)
                    page_facts = self._extract_fact_rows(text, url, max_facts=3)
                    facts.extend(page_facts)
                    pages.append(
                        {
                            "url": url,
                            "title": self._extract_page_title(body_html),
                            "official_source": official_source,
                            "content": text[: max(500, int(max_chars_per_page))],
                            "facts_count": len(page_facts),
                        }
                    )
                except Exception as exc:
                    pages.append({"url": url, "official_source": official_source, "error": str(exc)})

        return {
            "ok": True,
            "query": q,
            "urls": urls,
            "pages": pages,
            "preferred_domains": preferred,
            "official_source_required": bool(strict_official),
            "official_source_found": bool(official_source_found),
            "official_candidates_found": bool(official_candidates),
            "facts": facts[:20],
            "facts_count": len(facts),
            "fetched_count": len([p for p in pages if isinstance(p, dict) and str(p.get("content") or "").strip()]),
        }
