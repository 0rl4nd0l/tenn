# Scrapling integration note

[Scrapling](https://github.com/D4Vinci/Scrapling) is an adaptive web scraping framework (single request → full crawl) with fetchers (HTTP, stealth, dynamic), Scrapy-like spiders, and optional MCP for AI-assisted scraping.

## Where we could use it

| Current code | What we do now | Scrapling fit |
|-------------|----------------|---------------|
| **Cockpit `WebFetcher`** (`cockpit/integrations/web_fetcher.py`) | `httpx` for `fetch_text`; DuckDuckGo HTML + regex for search URLs; manual HTML strip | **Fetcher** or **StealthyFetcher** for fetch; built-in parser (`.css()`, `.xpath()`) for URL extraction and body text; optional **StealthyFetcher** when target sites block plain HTTP |
| **Pipeline** (`backend/app/services/pipeline.py`) | `httpx.get` in `_download_bytes`; BeautifulSoup for HTML | **Fetcher** for downloads; **Selector** (or Fetcher’s response) for parsing instead of BS4 when we parse HTML |
| **News pipeline (GDELT doc)** (`scripts/fetch_gdelt_doc_api.py`) | `urllib` for per-article URL fetch (enrichment) | **Fetcher** then **StealthyFetcher** for article body fetch; better TLS and retry on blocked news sites |
| **ASX provider** (`backend/app/providers/asx_provider.py`) | `httpx` + BeautifulSoup for ASX pages | **Fetcher** + `.css()` / `.xpath()`; **adaptive selectors** (`auto_save=True`, `adaptive=True`) to tolerate ASX layout changes |
| **Marketindex** (`scripts/marketindex_ingest.py`, `marketindex_headed_recovery.py`) | Raw **Playwright** (async, selectors, response interception) | **DynamicFetcher** or **StealthyFetcher** (Playwright under the hood) for “fetch page then `.css()`”; less custom Playwright code; built-in Cloudflare handling if needed |
| **Worker** (`worker_app/tasks.py`) | `httpx.get(doc.source_url)` | **Fetcher.get()** for consistent TLS/headers; optional **StealthyFetcher** for sources that block simple clients |
| **Future crawls** (e.g. multi-page ASX, sitemaps) | N/A | **Spider** API: `start_urls`, async `parse`, concurrency, pause/resume, optional proxy rotation |

## Benefits

- **One API** for HTTP vs browser: same `.css()` / `.xpath()` whether using Fetcher or Dynamic/Stealthy.
- **Resilience**: StealthyFetcher for Cloudflare/Turnstile; adaptive selectors when sites change layout.
- **Less custom code**: Replace ad-hoc regex + BeautifulSoup in `web_fetcher` and ASX with Scrapling’s parser.
- **Crawling**: Spiders for multi-page runs with checkpointing (e.g. Ctrl+C resume).
- **Optional MCP**: Use Scrapling’s MCP server from Cursor/agents for AI-assisted scraping experiments without changing app code.

## Constraints

- **Python 3.10+** (we already use this).
- **Optional deps**: Base install is parser only; `pip install "scrapling[fetchers]"` and `scrapling install` for browsers/Playwright.
- **Backward compatibility**: Any integration should be behind a small abstraction (e.g. keep `WebFetcher.fetch_text(url, max_chars)` contract) so we can switch implementation without touching callers.

## Suggested order of work

1. **Add dependency** in the relevant envs (e.g. `financial-engine_v2/backend/requirements.txt` or a dedicated script env):  
   `scrapling[fetchers]` (and run `scrapling install` where browser-based fetchers are used).
2. **Cockpit WebFetcher**: Implement a Scrapling-backed path (e.g. `Fetcher.get(url)` → `.css('body').getall()` or similar for `fetch_text`; use response `.css()` for DuckDuckGo URL extraction) behind the existing `fetch_text` / `search_and_fetch` interface; keep httpx fallback if Scrapling is optional.
3. **ASX provider**: Replace BeautifulSoup with Scrapling’s parser on the same httpx response (or use Fetcher), and add `auto_save=True` on critical selectors for future adaptability.
4. **Marketindex**: Evaluate replacing custom Playwright with DynamicFetcher/StealthyFetcher in one script (e.g. `marketindex_ingest.py`) as a PoC; if solid, consider `marketindex_headed_recovery`.
5. **Pipeline**: Optionally use Fetcher for `_download_bytes` and Scrapling Selector anywhere we currently parse HTML with BeautifulSoup.

## Minimal example (for trying locally)

```python
# Fetch + parse with Scrapling (parser-only or with fetchers)
from scrapling.fetchers import Fetcher

page = Fetcher.get("https://www.asx.com.au/asx/v2/statistics/announcements.do", params={"..."})
links = page.css("a[href*='.pdf']")
for a in links:
    href = a.attrib.get("href")
    text = a.css("::text").get()
```

```python
# Dynamic/JS-heavy or Cloudflare-protected (requires scrapling[fetchers] + scrapling install)
from scrapling.fetchers import StealthyFetcher
StealthyFetcher.adaptive = True
page = StealthyFetcher.fetch("https://example.com", headless=True, network_idle=True)
items = page.css(".product", auto_save=True)
```

---

**Summary**: Yes, we can utilise Scrapling. The highest leverage is Cockpit WebFetcher (unify fetch + parse, optional stealth), ASX provider (robust selectors + adaptive), and Marketindex (simplify Playwright usage).

---

## Implemented

- **Dependency**: `scrapling[fetchers]>=0.4.0` added to `financial-engine_v2/backend/requirements.txt`. Install with `pip install -r backend/requirements.txt`. For browser-based fetchers (Stealthy/Dynamic) run `scrapling install` separately.
- **Docker runtime**: `financial-engine_v2/backend/Dockerfile` now pre-installs the browser runtimes required by the canonical `newspaper4k` news path: `python -m playwright install --with-deps chromium` plus `camoufox fetch --browserforge`. That makes the backend and worker container images ready for Playwright and Scrapling StealthyFetcher without manual post-start setup.
- **Cockpit WebFetcher**: Scrapling-backed path behind the same `fetch_text` / `search_and_fetch` API. Enable with **`COCKPIT_USE_SCRAPLING=1`**. When Scrapling is enabled:
  - **fetch_text**: Tries `Fetcher.get` first; if that returns empty or raises, retries with **StealthyFetcher** (headless) when available. Then falls back to httpx.
  - **search_and_fetch**: Uses **CSS-based URL extraction** from the DuckDuckGo search page (`_extract_urls_from_scrapling_search_page` with `a[href]`) with regex fallback, so layout changes are easier to handle.
- **ASX provider** (`backend/app/providers/asx_provider.py`): When Scrapling is installed, **tries Fetcher first** for the announcements page and parses with **`.css('a[href*=".pdf"], a[href*="displayannouncement.do"]', auto_save=True)`** so selectors can be recovered if ASX change layout. Falls back to httpx + BeautifulSoup on any failure.
- **Pipeline** (`backend/app/services/pipeline.py`): **`_download_bytes`** retries on **403 / 407 / 503** using Scrapling **Fetcher.get** and returns a response-like object if the page has `.content`/`.body` (e.g. HTML redirect pages). PDF bytes may still require the first httpx success; the retry helps when the first request is blocked.
- **News pipeline (GDELT doc)** (`scripts/fetch_gdelt_doc_api.py`): **Article enrichment** uses Scrapling when installed: **`fetch_article_text`** tries **Fetcher.get** then **StealthyFetcher** (headless) for each GDELT result URL before falling back to urllib. Improves success on sites that block plain requests. Use **`--no-scrapling`** to force urllib-only (e.g. in minimal envs or CI).
