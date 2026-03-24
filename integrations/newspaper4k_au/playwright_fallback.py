"""JS-rendering fallback for sites that newspaper4k cannot extract.

Uses Scrapling's StealthyFetcher (Camoufox — hardened Firefox with anti-bot
bypass) as the primary renderer, with Playwright Chromium as a secondary
fallback.  Falls back gracefully if neither is installed.

Future: Crawl4AI (https://github.com/unclecode/crawl4ai) is the intended
long-term replacement for both newspaper4k and this fallback module.  It
outputs clean Markdown from any page (JS or not) with async browser pooling,
which maps directly onto the RAG pipeline.  See docs/architecture/15_news_substrate.md.

Usage:
    from playwright_fallback import fetch_article_html, shutdown

    html = fetch_article_html("https://stockhead.com.au/some-article")
    # ... parse html with newspaper fulltext or BeautifulSoup ...

    shutdown()  # call once at end of batch
"""
from __future__ import annotations

import atexit
import logging
import threading
from urllib.parse import urlsplit

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Default domains known to require JS rendering
# ---------------------------------------------------------------------------
DEFAULT_PLAYWRIGHT_DOMAINS: tuple[str, ...] = (
    "stockhead.com.au",
    "skynews.com.au",
    "capitalbrief.com",
    "finance.yahoo.com",
    "benzinga.com",
    "marketindex.com.au",
    "livewiremarkets.com",
)

# ---------------------------------------------------------------------------
# Availability probes (cached)
# ---------------------------------------------------------------------------
_scrapling_available: bool | None = None
_playwright_available: bool | None = None


def _probe_scrapling() -> bool:
    global _scrapling_available
    if _scrapling_available is not None:
        return _scrapling_available
    try:
        from scrapling import StealthyFetcher  # noqa: F401
        _scrapling_available = True
    except Exception:
        logger.info("scrapling not installed — StealthyFetcher disabled")
        _scrapling_available = False
    return _scrapling_available


def _probe_playwright() -> bool:
    global _playwright_available
    if _playwright_available is not None:
        return _playwright_available
    try:
        from playwright.sync_api import sync_playwright  # noqa: F401
        _playwright_available = True
    except Exception:
        logger.info("playwright not installed — Playwright fallback disabled")
        _playwright_available = False
    return _playwright_available


# ---------------------------------------------------------------------------
# Playwright browser singleton (secondary fallback)
# ---------------------------------------------------------------------------
_pw_lock = threading.Lock()
_pw_browser = None
_pw_ctx = None


def _ensure_playwright_browser():
    global _pw_browser, _pw_ctx
    if _pw_browser is not None:
        return _pw_browser
    with _pw_lock:
        if _pw_browser is not None:
            return _pw_browser
        if not _probe_playwright():
            return None
        try:
            from playwright.sync_api import sync_playwright
            _pw_ctx = sync_playwright().start()
            _pw_browser = _pw_ctx.chromium.launch(headless=True)
            logger.info("Playwright browser launched (headless Chromium)")
        except Exception as exc:
            logger.warning("Failed to launch Playwright Chromium: %s", exc)
            _pw_browser = None
    return _pw_browser


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def _domain_of(url: str) -> str:
    host = (urlsplit(url).hostname or "").lower()
    if host.startswith("www."):
        host = host[4:]
    return host


def is_playwright_available() -> bool:
    """Return True if scrapling OR playwright is importable."""
    return _probe_scrapling() or _probe_playwright()


def domain_needs_playwright(url: str, playwright_domains: tuple[str, ...] | list[str] | None = None) -> bool:
    """Return True if the URL's domain is in the JS-rendering list."""
    domains = playwright_domains if playwright_domains is not None else DEFAULT_PLAYWRIGHT_DOMAINS
    url_domain = _domain_of(url)
    if not url_domain:
        return False
    for domain in domains:
        d = domain.lower().strip()
        if d.startswith("www."):
            d = d[4:]
        if url_domain == d or url_domain.endswith("." + d):
            return True
    return False


def _fetch_with_scrapling(url: str, timeout: int) -> str:
    """Fetch rendered HTML using Scrapling's StealthyFetcher (Camoufox)."""
    from scrapling import StealthyFetcher

    fetcher = StealthyFetcher()
    response = fetcher.fetch(
        url,
        headless=True,
        network_idle=True,
        timeout=timeout * 1000,  # scrapling uses ms
    )
    body = getattr(response, "body", None) or ""
    if isinstance(body, bytes):
        body = body.decode("utf-8", errors="replace")
    return str(body)


def _fetch_with_playwright(url: str, timeout_ms: int, js_settle_ms: int) -> str:
    """Fetch rendered HTML using Playwright headless Chromium."""
    browser = _ensure_playwright_browser()
    if browser is None:
        return ""
    context = None
    try:
        context = browser.new_context(
            user_agent=(
                "Mozilla/5.0 (X11; Linux x86_64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            ),
            java_script_enabled=True,
        )
        page = context.new_page()
        page.goto(url, timeout=timeout_ms, wait_until="domcontentloaded")
        if js_settle_ms > 0:
            page.wait_for_timeout(js_settle_ms)
        return page.content()
    except Exception as exc:
        logger.warning("Playwright fetch failed for %s: %s", url, exc)
        return ""
    finally:
        if context is not None:
            try:
                context.close()
            except Exception:
                pass


def fetch_article_html_playwright(
    url: str,
    timeout_ms: int = 30000,
    wait_until: str = "domcontentloaded",
    js_settle_ms: int = 3000,
) -> str:
    """Fetch a URL with JS rendering and return the rendered HTML.

    Tries Scrapling StealthyFetcher first (faster, anti-bot bypass),
    falls back to Playwright Chromium if scrapling is unavailable.

    Returns empty string on any failure or if neither renderer is installed.
    """
    timeout_s = max(1, timeout_ms // 1000)

    # Primary: Scrapling StealthyFetcher (Camoufox — anti-bot, faster)
    if _probe_scrapling():
        try:
            html = _fetch_with_scrapling(url, timeout=timeout_s)
            if html and len(html) > 500:
                return html
            logger.info("Scrapling returned short HTML for %s (%d chars), trying Playwright", url, len(html))
        except Exception as exc:
            logger.warning("Scrapling StealthyFetcher failed for %s: %s", url, exc)

    # Secondary: Playwright Chromium
    if _probe_playwright():
        try:
            return _fetch_with_playwright(url, timeout_ms=timeout_ms, js_settle_ms=js_settle_ms)
        except Exception as exc:
            logger.warning("Playwright fallback also failed for %s: %s", url, exc)

    return ""


def shutdown_playwright() -> None:
    """Tear down browser resources. Safe to call multiple times."""
    global _pw_browser, _pw_ctx
    with _pw_lock:
        if _pw_browser is not None:
            try:
                _pw_browser.close()
            except Exception:
                pass
            _pw_browser = None
        if _pw_ctx is not None:
            try:
                _pw_ctx.stop()
            except Exception:
                pass
            _pw_ctx = None


# Alias for backward compatibility
shutdown = shutdown_playwright

atexit.register(shutdown_playwright)
