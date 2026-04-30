from __future__ import annotations

import asyncio
import os
import re
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

from app.core.config import settings
from app.services.marketplace_headless_runtime import (
    marketplace_direct_runtime_detail,
    open_direct_marketplace_context,
    use_direct_marketplace_runtime,
)


FACEBOOK_MARKETPLACE_URL_RE = re.compile(
    r"^https?://(?:www\.|m\.)?facebook\.com/marketplace/item/[^\s?#]+(?:[^\s#]*)?$",
    re.IGNORECASE,
)

DEFAULT_MARKETPLACE_CDP_URL = "http://127.0.0.1:9222"
DEFAULT_MARKETPLACE_TIMEOUT_MS = 20_000
MARKETPLACE_TOPIC_TAGS = ["facebook_marketplace", "marketplace_listing"]


def _default_marketplace_capture_root() -> Path:
    backend_root = Path(__file__).resolve().parents[2]
    candidates = [
        Path(getattr(settings, "data_root", "/data")).expanduser().resolve()
        / "reports"
        / "marketplace_captures",
        backend_root / "reports" / "marketplace_captures",
    ]
    for candidate in candidates:
        try:
            candidate.mkdir(parents=True, exist_ok=True)
            if os.access(candidate, os.W_OK | os.X_OK):
                return candidate
        except OSError:
            continue
    return candidates[0]


MARKETPLACE_CAPTURE_ROOT = _default_marketplace_capture_root()
_GENERIC_MARKETPLACE_HOME_TITLE_RE = re.compile(
    r"facebook marketplace: buy and sell items locally or shipped",
    re.IGNORECASE,
)
_MARKETPLACE_LISTING_EVALUATION_SCRIPT = """
() => {
  const clean = (value) => (value || '').replace(/\\s+/g, ' ').trim()
  const dedupe = (items) => {
    const out = []
    const seen = new Set()
    for (const item of items) {
      const cleaned = clean(item)
      if (!cleaned) continue
      const key = cleaned.toLowerCase()
      if (seen.has(key)) continue
      seen.add(key)
      out.push(cleaned)
    }
    return out
  }
  const collect = (selector) =>
    Array.from(document.querySelectorAll(selector)).map((el) =>
      clean(el.innerText || el.textContent || '')
    )
  const visible = dedupe(
    collect('h1,h2,h3,span,div,p,a,li').filter(
      (text) => text.length >= 2 && text.length <= 280
    )
  )
  const byHeading = (heading) => {
    const index = visible.findIndex(
      (text) => text.toLowerCase() === heading
    )
    if (index < 0) return null
    for (let i = index + 1; i < Math.min(visible.length, index + 6); i += 1) {
      const candidate = visible[i]
      if (candidate && candidate.toLowerCase() !== heading) {
        return candidate
      }
    }
    return null
  }
  const metaTitle =
    clean(document.querySelector('meta[property="og:title"]')?.content) ||
    clean(document.querySelector('h1')?.textContent) ||
    clean(document.title) ||
    ''
  const metaDescription =
    clean(document.querySelector('meta[property="og:description"]')?.content) ||
    clean(document.querySelector('meta[name="description"]')?.content) ||
    ''
  const priceMatch =
    visible.find((text) => /(?:A\\$|AU\\$|USD\\s*\\$|\\$)\\s?\\d[\\d,]*(?:\\.\\d{2})?/.test(text)) ||
    clean(document.querySelector('meta[property="product:price:amount"]')?.content) ||
    null
  let location =
    visible.find((text) => /^Location is approximate/i.test(text)) ||
    byHeading('location') ||
    null
  if (!location && metaDescription) {
    const match = metaDescription.match(/\\bin\\s+([A-Za-z0-9 ,.'-]{3,80})/i)
    if (match) {
      location = clean(match[1])
    }
  }
  const description =
    byHeading('description') ||
    metaDescription ||
    visible.find((text) => text.length >= 80) ||
    null
  const sellerName =
    byHeading('seller details') ||
    byHeading('seller information') ||
    byHeading('seller') ||
    null
  return {
    final_url: window.location.href || '',
    title: metaTitle,
    price: priceMatch,
    seller_name: sellerName,
    location,
    description,
    visible_text: visible.slice(0, 80),
  }
}
"""


@dataclass(frozen=True)
class MarketplaceListingCapture:
    url: str
    captured_at: str
    title: str
    price: str | None
    seller_name: str | None
    location: str | None
    description: str | None
    screenshot_path: str
    raw_text_lines: list[str]
    transcript_text: str


class MarketplaceBrowserProbeTimeout(RuntimeError):
    def __init__(self, stage: str) -> None:
        super().__init__(stage)
        self.stage = stage


def is_facebook_marketplace_url(url: str) -> bool:
    return bool(FACEBOOK_MARKETPLACE_URL_RE.match(str(url or "").strip()))


def _compact(value: str | None) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


def _slugify(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", str(value or "").strip().lower()).strip("-")


def _dedupe(items: list[str]) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()
    for item in items:
        cleaned = _compact(item)
        if not cleaned:
            continue
        key = cleaned.lower()
        if key in seen:
            continue
        seen.add(key)
        out.append(cleaned)
    return out


def _has_listing_content(
    extracted: dict[str, object],
    *,
    final_url: str,
) -> bool:
    normalized_url = str(final_url or "").strip().lower()
    if "/marketplace/item/" not in normalized_url:
        return False

    title = _compact(extracted.get("title"))
    price = _compact(extracted.get("price"))
    seller_name = _compact(extracted.get("seller_name"))
    location = _compact(extracted.get("location"))
    description = _compact(extracted.get("description"))
    generic_title = bool(_GENERIC_MARKETPLACE_HOME_TITLE_RE.search(title))

    return bool(
        price
        or seller_name
        or location
        or (description and len(description) >= 24)
        or (title and not generic_title)
    )


def _int_env(name: str, default: int) -> int:
    raw = str(os.environ.get(name, "") or "").strip()
    if not raw:
        return default
    try:
        parsed = int(raw)
    except ValueError:
        return default
    return parsed if parsed > 0 else default


def _has_graphical_desktop_session() -> bool:
    if not sys.platform.startswith("linux"):
        return True
    return bool(
        str(os.environ.get("DISPLAY") or "").strip()
        or str(os.environ.get("WAYLAND_DISPLAY") or "").strip()
    )


def _is_local_cdp_url(cdp_url: str) -> bool:
    parsed = urlparse(str(cdp_url or "").strip())
    host = str(parsed.hostname or "").strip().lower()
    return host in {"127.0.0.1", "localhost", "::1"}


def _browser_unavailable_detail(cdp_url: str) -> str:
    detail = (
        "marketplace_browser_unavailable: Could not connect to a local "
        "Brave/Chrome debugging session."
    )
    if _is_local_cdp_url(cdp_url) and not _has_graphical_desktop_session():
        detail += (
            " This backend shell has no X/Wayland desktop session, so Chrome/Brave "
            "must be started from a graphical desktop login on the same machine, or "
            "marketplace_browser_helper.py must be running there."
        )
    detail += " Start the browser with --remote-debugging-port=9222."
    return detail


def _probe_timeout_seconds(timeout_ms: int, *, extra_seconds: float = 0.0) -> float:
    return max((int(timeout_ms) / 1000.0) + extra_seconds, 5.0)


def _is_headless_browser_version(version_payload: dict[str, object] | None) -> bool:
    browser_text = str((version_payload or {}).get("Browser") or "")
    user_agent = str((version_payload or {}).get("User-Agent") or "")
    combined = f"{browser_text} {user_agent}"
    return "HeadlessChrome" in combined


def _marketplace_probe_timeout_detail(
    *,
    cdp_url: str,
    timeout_ms: int,
    stage: str,
    version_payload: dict[str, object] | None = None,
) -> str:
    timeout_seconds = _probe_timeout_seconds(timeout_ms)
    browser_name = str((version_payload or {}).get("Browser") or "Chrome/Brave").strip()
    detail = (
        "marketplace_browser_unavailable: Browser debugger is reachable, but the "
        f"Marketplace probe timed out during {stage} after about {timeout_seconds:.0f}s."
    )
    if _is_headless_browser_version(version_payload):
        detail += (
            " This Chrome session is running in headless mode, and the current "
            "Marketplace probe could not attach cleanly through Playwright CDP."
        )
    elif _is_local_cdp_url(cdp_url) and not _has_graphical_desktop_session():
        detail += (
            " This backend shell has no X/Wayland desktop session, so Chrome/Brave "
            "must be started from a graphical desktop login on the same machine, or "
            "marketplace_browser_helper.py must be running there."
        )
    detail += f" Browser: {browser_name}. Debugging URL: {cdp_url}"
    return detail


async def _await_marketplace_probe(
    awaitable,
    *,
    stage: str,
    timeout_seconds: float,
):
    try:
        return await asyncio.wait_for(awaitable, timeout=timeout_seconds)
    except asyncio.TimeoutError as exc:
        raise MarketplaceBrowserProbeTimeout(stage) from exc


def _compose_transcript(
    *,
    url: str,
    captured_at: str,
    title: str,
    price: str | None,
    seller_name: str | None,
    location: str | None,
    description: str | None,
    screenshot_path: str,
    raw_text_lines: list[str],
) -> str:
    lines = [
        "Facebook Marketplace listing snapshot",
        f"URL: {url}",
        f"Captured at: {captured_at}",
        f"Title: {title or 'Unknown listing'}",
    ]
    if price:
        lines.append(f"Price: {price}")
    if seller_name:
        lines.append(f"Seller: {seller_name}")
    if location:
        lines.append(f"Location: {location}")
    if description:
        lines.extend(["Description:", description])
    if screenshot_path:
        lines.append(f"Screenshot: {screenshot_path}")
    if raw_text_lines:
        lines.append("Visible listing text:")
        lines.extend(f"- {text}" for text in raw_text_lines[:30])
    return "\n".join(lines).strip()


def build_marketplace_listing_capture(
    *,
    url: str,
    captured_at: str | None = None,
    title: str | None = None,
    price: str | None = None,
    seller_name: str | None = None,
    location: str | None = None,
    description: str | None = None,
    screenshot_path: str | None = None,
    raw_text_lines: list[str] | None = None,
) -> MarketplaceListingCapture:
    normalized_url = str(url or "").strip()
    if not is_facebook_marketplace_url(normalized_url):
        raise ValueError("url must be a Facebook Marketplace item URL")

    normalized_captured_at = _compact(captured_at) or datetime.now(timezone.utc).replace(
        microsecond=0
    ).isoformat()
    normalized_title = _compact(title) or "Facebook Marketplace listing"
    normalized_price = _compact(price) or None
    normalized_seller_name = _compact(seller_name) or None
    normalized_location = _compact(location) or None
    normalized_description = _compact(description) or None
    normalized_screenshot_path = _compact(screenshot_path) or ""
    normalized_raw_text_lines = _dedupe(
        [str(item) for item in (raw_text_lines or [])]
    )

    transcript_text = _compose_transcript(
        url=normalized_url,
        captured_at=normalized_captured_at,
        title=normalized_title,
        price=normalized_price,
        seller_name=normalized_seller_name,
        location=normalized_location,
        description=normalized_description,
        screenshot_path=normalized_screenshot_path,
        raw_text_lines=normalized_raw_text_lines,
    )
    return MarketplaceListingCapture(
        url=normalized_url,
        captured_at=normalized_captured_at,
        title=normalized_title,
        price=normalized_price,
        seller_name=normalized_seller_name,
        location=normalized_location,
        description=normalized_description,
        screenshot_path=normalized_screenshot_path,
        raw_text_lines=normalized_raw_text_lines,
        transcript_text=transcript_text,
    )


async def _inspect_listing_async(
    *,
    url: str,
    cdp_url: str,
    timeout_ms: int,
) -> MarketplaceListingCapture:
    if not is_facebook_marketplace_url(url):
        raise ValueError("url must be a Facebook Marketplace item URL")

    try:
        from playwright.async_api import async_playwright
    except Exception as exc:  # pragma: no cover - environment-specific
        raise RuntimeError(
            "marketplace_browser_unavailable: Playwright is not installed in this environment."
        ) from exc

    MARKETPLACE_CAPTURE_ROOT.mkdir(parents=True, exist_ok=True)
    captured_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    ts = captured_at.replace(":", "").replace("-", "").replace("+00:00", "Z")
    screenshot_path = MARKETPLACE_CAPTURE_ROOT / f"{ts}_marketplace.png"

    if use_direct_marketplace_runtime():
        try:
            async with open_direct_marketplace_context() as (
                context,
                _browser_family,
                profile_path,
            ):
                page = context.pages[0] if context.pages else await context.new_page()
                page.set_default_timeout(timeout_ms)
                await _await_marketplace_probe(
                    page.goto(url, wait_until="domcontentloaded", timeout=timeout_ms),
                    stage="listing navigation",
                    timeout_seconds=_probe_timeout_seconds(timeout_ms, extra_seconds=2.0),
                )
                await _await_marketplace_probe(
                    page.wait_for_timeout(1_500),
                    stage="post-navigation wait",
                    timeout_seconds=3.0,
                )

                extracted = await _await_marketplace_probe(
                    page.evaluate(_MARKETPLACE_LISTING_EVALUATION_SCRIPT),
                    stage="listing evaluation",
                    timeout_seconds=_probe_timeout_seconds(timeout_ms),
                )

                final_url = str(extracted.get("final_url") or page.url or url).strip() or url
                if not _has_listing_content(extracted, final_url=final_url):
                    raise RuntimeError(
                        "marketplace_capture_failed: No listing content was detected after loading the page."
                    )

                title = _compact(extracted.get("title")) or "Facebook Marketplace listing"
                screenshot_path = screenshot_path.with_name(
                    f"{ts}_{_slugify(title) or 'marketplace'}.png"
                )
                await page.screenshot(path=str(screenshot_path), full_page=True)
                return build_marketplace_listing_capture(
                    url=final_url,
                    captured_at=captured_at,
                    title=title,
                    price=_compact(extracted.get("price")) or None,
                    seller_name=_compact(extracted.get("seller_name")) or None,
                    location=_compact(extracted.get("location")) or None,
                    description=_compact(extracted.get("description")) or None,
                    screenshot_path=str(screenshot_path),
                    raw_text_lines=[str(item) for item in (extracted.get("visible_text") or [])],
                )
        except MarketplaceBrowserProbeTimeout as exc:
            raise RuntimeError(
                f"{marketplace_direct_runtime_detail(profile_path if 'profile_path' in locals() else str((Path.home() / '.tenn' / 'browser_profiles' / 'facebook-marketplace-chrome').resolve()))} "
                f"Probe timed out during {exc.stage}."
            ) from exc
        except RuntimeError:
            raise
        except Exception as exc:
            raise RuntimeError(
                f"{marketplace_direct_runtime_detail(profile_path if 'profile_path' in locals() else str((Path.home() / '.tenn' / 'browser_profiles' / 'facebook-marketplace-chrome').resolve()))} "
                f"Launch failed: {exc}"
            ) from exc

    async with async_playwright() as playwright:
        try:
            browser = await _await_marketplace_probe(
                playwright.chromium.connect_over_cdp(cdp_url),
                stage="CDP attach",
                timeout_seconds=_probe_timeout_seconds(timeout_ms),
            )
        except MarketplaceBrowserProbeTimeout as exc:
            raise RuntimeError(
                _marketplace_probe_timeout_detail(
                    cdp_url=cdp_url,
                    timeout_ms=timeout_ms,
                    stage=exc.stage,
                )
            ) from exc
        except Exception as exc:
            raise RuntimeError(_browser_unavailable_detail(cdp_url)) from exc

        context = browser.contexts[0] if browser.contexts else await browser.new_context()
        page = None
        created_page = False
        try:
            try:
                page = await _await_marketplace_probe(
                    context.new_page(),
                    stage="page creation",
                    timeout_seconds=_probe_timeout_seconds(timeout_ms),
                )
                created_page = True
            except Exception:
                if context.pages:
                    page = context.pages[0]
                else:
                    page = await _await_marketplace_probe(
                        context.new_page(),
                        stage="page creation",
                        timeout_seconds=_probe_timeout_seconds(timeout_ms),
                    )
                    created_page = True

            page.set_default_timeout(timeout_ms)
            await _await_marketplace_probe(
                page.goto(url, wait_until="domcontentloaded", timeout=timeout_ms),
                stage="listing navigation",
                timeout_seconds=_probe_timeout_seconds(timeout_ms, extra_seconds=2.0),
            )
            await _await_marketplace_probe(
                page.wait_for_timeout(1_500),
                stage="post-navigation wait",
                timeout_seconds=3.0,
            )

            extracted = await _await_marketplace_probe(
                page.evaluate(_MARKETPLACE_LISTING_EVALUATION_SCRIPT),
                stage="listing evaluation",
                timeout_seconds=_probe_timeout_seconds(timeout_ms),
            )

            final_url = str(extracted.get("final_url") or page.url or url).strip() or url
            if not _has_listing_content(extracted, final_url=final_url):
                raise RuntimeError(
                    "marketplace_capture_failed: No listing content was detected after loading the page."
                )

            title = _compact(extracted.get("title")) or "Facebook Marketplace listing"
            screenshot_path = screenshot_path.with_name(
                f"{ts}_{_slugify(title) or 'marketplace'}.png"
            )
            await page.screenshot(path=str(screenshot_path), full_page=True)

            raw_text_lines = _dedupe(
                [str(item) for item in (extracted.get("visible_text") or [])]
            )
            if not title and not raw_text_lines:
                raise RuntimeError(
                    "marketplace_capture_failed: No listing content was detected after loading the page."
                )

            price = _compact(extracted.get("price")) or None
            seller_name = _compact(extracted.get("seller_name")) or None
            location = _compact(extracted.get("location")) or None
            description = _compact(extracted.get("description")) or None
        finally:
            if created_page and page is not None:
                try:
                    await page.close()
                except Exception:
                    pass

    return build_marketplace_listing_capture(
        url=final_url,
        captured_at=captured_at,
        title=title,
        price=price,
        seller_name=seller_name,
        location=location,
        description=description,
        screenshot_path=str(screenshot_path),
        raw_text_lines=raw_text_lines,
    )


def inspect_facebook_marketplace_listing(
    url: str,
    *,
    cdp_url: str | None = None,
    timeout_ms: int | None = None,
) -> MarketplaceListingCapture:
    resolved_cdp_url = (
        str(cdp_url or os.environ.get("FACEBOOK_MARKETPLACE_CDP_URL") or "").strip()
        or DEFAULT_MARKETPLACE_CDP_URL
    )
    resolved_timeout_ms = int(
        timeout_ms
        or _int_env(
            "FACEBOOK_MARKETPLACE_TIMEOUT_MS",
            DEFAULT_MARKETPLACE_TIMEOUT_MS,
        )
    )
    return asyncio.run(
        _inspect_listing_async(
            url=url,
            cdp_url=resolved_cdp_url,
            timeout_ms=resolved_timeout_ms,
        )
    )
