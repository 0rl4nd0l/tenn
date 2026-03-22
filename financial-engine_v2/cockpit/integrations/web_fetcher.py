from __future__ import annotations

import re
from html.parser import HTMLParser
from typing import Any

import httpx

_SEARCH_URL = "https://html.duckduckgo.com/html/"
_USER_AGENT = "FinancialEngineCockpit/1.0"

# Matches currency amounts and plain numeric quantities with financial units.
_NUMBER_RE = re.compile(
    r"\$[\d,\.]+(?:\s*(?:billion|million|bn|m|k))?"
    r"|\d+(?:\.\d+)?%"
    r"|\d{1,3}(?:,\d{3})+(?:\.\d+)?"
    r"|\d+(?:\.\d+)?\s*(?:billion|million|bn)",
    re.IGNORECASE,
)


class _LinkExtractor(HTMLParser):
    """Collects absolute href values from anchor tags."""

    def __init__(self) -> None:
        super().__init__()
        self.links: list[str] = []

    def handle_starttag(self, tag: str, attrs: list) -> None:
        if tag == "a":
            href = dict(attrs).get("href", "")
            if href.startswith("http"):
                self.links.append(href)


class _TextExtractor(HTMLParser):
    """Strips HTML tags and collects visible text."""

    def __init__(self) -> None:
        super().__init__()
        self._chunks: list[str] = []
        self._skip = False

    def handle_starttag(self, tag: str, attrs: list) -> None:  # noqa: ARG002
        if tag in ("script", "style"):
            self._skip = True

    def handle_endtag(self, tag: str) -> None:
        if tag in ("script", "style"):
            self._skip = False

    def handle_data(self, data: str) -> None:
        if not self._skip:
            chunk = data.strip()
            if chunk:
                self._chunks.append(chunk)

    @property
    def text(self) -> str:
        return " ".join(self._chunks)


def _extract_links(html_text: str) -> list[str]:
    parser = _LinkExtractor()
    try:
        parser.feed(html_text)
    except Exception:
        pass
    return parser.links


def _extract_text(html_text: str) -> str:
    parser = _TextExtractor()
    try:
        parser.feed(html_text)
    except Exception:
        pass
    return parser.text


def _extract_facts(url: str, text: str) -> list[dict[str, Any]]:
    """Return one fact dict per sentence that contains a numerical claim."""
    sentences = re.split(r"(?<=[.!?])\s+", text)
    facts: list[dict[str, Any]] = []
    for sentence in sentences:
        sentence = sentence.strip()
        numbers = _NUMBER_RE.findall(sentence)
        if numbers:
            facts.append({"url": url, "claim": sentence, "numbers": numbers})
    return facts


class WebFetcher:
    def fetch_text(self, url: str, timeout: float = 20.0) -> str:
        with httpx.Client(timeout=timeout, follow_redirects=True) as client:
            response = client.get(url, headers={"User-Agent": _USER_AGENT})
            response.raise_for_status()
            return response.text[:8000]

    def search_and_fetch(
        self,
        query: str,
        *,
        max_results: int = 5,
        timeout: float = 20.0,
        preferred_domains: list[str] | None = None,
        strict_official: bool = False,
    ) -> dict[str, Any]:
        """
        Search DuckDuckGo for *query*, fetch up to *max_results* pages, and
        extract numerical facts.

        When *preferred_domains* and *strict_official* are given, preferred-domain
        URLs are sorted to the front and the result includes ``official_source_found``
        (bool) and, when not found, ``official_source_required`` (True).

        Returns a dict with keys: ok, urls, pages, facts, facts_count.
        """
        headers = {"User-Agent": _USER_AGENT}
        try:
            with httpx.Client(timeout=timeout, follow_redirects=True) as client:
                # --- search ---
                resp = client.get(_SEARCH_URL, params={"q": query}, headers=headers)
                resp.raise_for_status()

                all_links = _extract_links(resp.text)
                # Deduplicate while preserving order.
                seen: set[str] = set()
                links: list[str] = []
                for link in all_links:
                    if link not in seen:
                        seen.add(link)
                        links.append(link)

                # Partition by preferred domains.
                official: list[str] = []
                others: list[str] = []
                if preferred_domains:
                    for link in links:
                        if any(d in link for d in preferred_domains):
                            official.append(link)
                        else:
                            others.append(link)
                else:
                    others = links

                official_source_found = bool(official)
                fetch_urls = (official + others)[:max_results]

                # --- fetch pages ---
                pages: list[dict[str, Any]] = []
                all_facts: list[dict[str, Any]] = []
                for url in fetch_urls:
                    is_official = preferred_domains and any(d in url for d in preferred_domains)
                    try:
                        r = client.get(url, headers=headers)
                        r.raise_for_status()
                        text = _extract_text(r.text)
                        facts = _extract_facts(url, text)
                        all_facts.extend(facts)
                        pages.append({
                            "url": url,
                            "text": text[:4000],
                            "official_source": bool(is_official),
                        })
                    except Exception as exc:
                        pages.append({
                            "url": url,
                            "error": str(exc),
                            "official_source": bool(is_official),
                        })

            result: dict[str, Any] = {
                "ok": True,
                "urls": fetch_urls,
                "pages": pages,
                "facts": all_facts,
                "facts_count": len(all_facts),
            }
            if preferred_domains and strict_official:
                result["official_source_found"] = official_source_found
                if not official_source_found:
                    result["official_source_required"] = True
            return result

        except Exception as exc:
            return {
                "ok": False,
                "error": str(exc),
                "urls": [],
                "pages": [],
                "facts": [],
                "facts_count": 0,
            }
