"""Playwright-based fallback for JS-rendered sites that newspaper4k cannot extract.

This module provides a headless Chromium browser that renders JavaScript-heavy pages
and returns the full rendered HTML. It is designed to be used as a fallback when
newspaper4k's standard download+parse yields empty or too-short article bodies.

Usage:
    from playwright_fallback import fetch_article_html_playwright, shutdown_playwright

    html = fetch_article_html_playwright("https://stockhead.com.au/some-article")
    # ... parse html with newspaper fulltext or BeautifulSoup ...

    shutdown_playwright()  # call once at end of batch
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
)

# ---------------------------------------------------------------------------
# Browser singleton — kept alive across articles to avoid cold-start overhead
# ---------------------------------------------------------------------------
_lock = threading.Lock()
_browser = None  # playwright Browser instance
_playwright_ctx = None  # playwright context manager
_available: bool | None = None  # None = not yet probed


def _domain_of(url: str) -> str:
    """Extract bare domain (without www.) from a URL."""
    host = (urlsplit(url).hostname or "").lower()
    if host.startswith("www."):
        host = host[4:]
    return host


def _probe_playwright() -> bool:
    """Check whether playwright + chromium are usable. Cached after first call."""
    global _available
    if _available is not None:
        return _available
    try:
        from playwright.sync_api import sync_playwright  # noqa: F401
        _available = True
    except Exception:
        logger.info("playwright not installed — Playwright fallback disabled")
        _available = False
    return _available


def _ensure_browser():
    """Lazily launch a shared headless Chromium instance."""
    global _browser, _playwright_ctx
    if _browser is not None:
        return _browser
    with _lock:
        if _browser is not None:
            return _browser
        if not _probe_playwright():
            return None
        try:
            from playwright.sync_api import sync_playwright
            _playwright_ctx = sync_playwright().start()
            _browser = _playwright_ctx.chromium.launch(headless=True)
            atexit.register(shutdown_playwright)
            logger.info("Playwright browser launched (headless Chromium)")
        except Exception as exc:
            logger.warning("Failed to launch Playwright Chromium: %s", exc)
            _available = False
            _browser = None
    return _browser


def shutdown_playwright() -> None:
    """Tear down the shared browser and playwright context. Safe to call multiple times."""
    global _browser, _playwright_ctx
    with _lock:
        if _browser is not None:
            try:
                _browser.close()
            except Exception:
                pass
            _browser = None
        if _playwright_ctx is not None:
            try:
                _playwright_ctx.stop()
            except Exception:
                pass
            _playwright_ctx = None


def is_playwright_available() -> bool:
    """Return True if playwright is importable (does not launch browser)."""
    return _probe_playwright()


def domain_needs_playwright(url: str, playwright_domains: tuple[str, ...] | list[str] | None = None) -> bool:
    """Return True if the URL's domain is in the playwright-required list."""
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


def fetch_article_html_playwright(
    url: str,
    timeout_ms: int = 30000,
    wait_until: str = "domcontentloaded",
    js_settle_ms: int = 3000,
) -> str:
    """Fetch a URL with headless Chromium and return the rendered HTML.

    Parameters
    ----------
    url : str
        The article URL to render.
    timeout_ms : int
        Navigation timeout in milliseconds (default 30 000).
    wait_until : str
        Playwright load-state to wait for. One of "load", "domcontentloaded"
        (default), "networkidle". JS-heavy sites often never reach networkidle,
        so domcontentloaded + js_settle_ms is the safer default.
    js_settle_ms : int
        Extra milliseconds to wait after initial load for JS frameworks to
        render article content (default 3 000). Set to 0 to skip.

    Returns
    -------
    str
        Rendered page HTML, or empty string on any failure (including playwright
        not being installed).
    """
    if not _probe_playwright():
        return ""
    browser = _ensure_browser()
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
        page.goto(url, timeout=timeout_ms, wait_until=wait_until)
        if js_settle_ms > 0:
            page.wait_for_timeout(js_settle_ms)
        html = page.content()
        return html
    except Exception as exc:
        logger.warning("Playwright fetch failed for %s: %s", url, exc)
        return ""
    finally:
        if context is not None:
            try:
                context.close()
            except Exception:
                pass
