from __future__ import annotations

import asyncio
import json
import os
import threading
from collections.abc import Mapping
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from app.services.facebook_marketplace_inspector import (
    DEFAULT_MARKETPLACE_CDP_URL,
    DEFAULT_MARKETPLACE_TIMEOUT_MS,
    MarketplaceBrowserProbeTimeout,
    _await_marketplace_probe,
    _browser_unavailable_detail,
    _has_graphical_desktop_session,
    _is_local_cdp_url,
    _marketplace_probe_timeout_detail,
    _probe_timeout_seconds,
)
from app.services.marketplace_headless_runtime import (
    marketplace_direct_runtime_detail,
    open_direct_marketplace_context,
    use_direct_marketplace_runtime,
)


DEFAULT_MARKETPLACE_HOME_URL = "https://www.facebook.com/marketplace/"
DEFAULT_PROFILE_ROOT = Path.home() / ".tenn" / "browser_profiles"
DEFAULT_MARKETPLACE_HELPER_URL = "http://127.0.0.1:9233"
DEFAULT_MARKETPLACE_HEALTH_TIMEOUT_MS = 5_000
MARKETPLACE_SCAN_ALLOWED_HEALTH_STATUSES = frozenset(
    {"ready", "challenge_detected"}
)
_MARKETPLACE_HOME_EVALUATION_SCRIPT = """
() => {
  const text = document.body?.innerText || ''
  const normalized = text.toLowerCase()
  const challengeDetected =
    /confirm (it'?s )?you|challenge|checkpoint|security check|suspended/i.test(text) ||
    /checkpoint|challenge/i.test(window.location.href || '')
  return {
    challengeDetected,
    finalUrl: window.location.href || '',
  }
}
"""


def _is_profile_lock_busy_error(exc: Exception) -> bool:
    message = str(exc or "").lower()
    return "profile is already in use" in message and "marketplace" in message


def marketplace_scan_health_allows_execution(health: Mapping[str, object]) -> bool:
    status = str(health.get("status") or "").strip().lower()
    return status in MARKETPLACE_SCAN_ALLOWED_HEALTH_STATUSES


def _is_playwright_navigation_timeout(exc: Exception) -> bool:
    message = str(exc or "")
    normalized = message.lower()
    return "page.goto:" in normalized and "timeout" in normalized


async def _navigate_marketplace_home(page: object, *, timeout_ms: int) -> None:
    page.set_default_timeout(timeout_ms)
    try:
        await _await_marketplace_probe(
            page.goto(
                DEFAULT_MARKETPLACE_HOME_URL,
                wait_until="commit",
                timeout=timeout_ms,
            ),
            stage="Marketplace navigation",
            timeout_seconds=_probe_timeout_seconds(timeout_ms, extra_seconds=2.0),
        )
    except Exception as exc:
        if _is_playwright_navigation_timeout(exc):
            raise MarketplaceBrowserProbeTimeout("Marketplace navigation") from exc
        raise

    await _await_marketplace_probe(
        page.wait_for_timeout(1_000),
        stage="post-navigation wait",
        timeout_seconds=3.0,
    )


def _now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _browser_family(version_payload: dict[str, object]) -> str:
    browser_text = str(version_payload.get("Browser") or "").lower()
    if "brave" in browser_text:
        return "brave"
    return "chrome"


def _profile_path(browser_family: str) -> str:
    return str((DEFAULT_PROFILE_ROOT / f"facebook-marketplace-{browser_family}").resolve())


def _fetch_cdp_version(cdp_url: str, timeout_seconds: float = 1.5) -> dict[str, object] | None:
    version_url = f"{cdp_url.rstrip('/')}/json/version"
    try:
        with urlopen(version_url, timeout=timeout_seconds) as response:  # noqa: S310
            payload = json.loads(response.read().decode("utf-8"))
    except (OSError, URLError, ValueError, json.JSONDecodeError):
        return None
    return payload if isinstance(payload, dict) else None


def _helper_base_url() -> str:
    return (
        str(os.environ.get("MARKETPLACE_BROWSER_HELPER_URL") or DEFAULT_MARKETPLACE_HELPER_URL)
        .strip()
        .rstrip("/")
    )


def _helper_headers() -> dict[str, str]:
    headers: dict[str, str] = {}
    token = str(os.environ.get("MARKETPLACE_BROWSER_HELPER_TOKEN") or "").strip()
    if token:
        headers["X-Marketplace-Helper-Token"] = token
    return headers


def _fetch_helper_health(timeout_seconds: float = 1.5) -> dict[str, object] | None:
    base_url = _helper_base_url()
    if not base_url:
        return None
    request = Request(
        f"{base_url}/health",
        headers=_helper_headers(),
        method="GET",
    )
    try:
        with urlopen(request, timeout=timeout_seconds) as response:  # noqa: S310
            payload = json.loads(response.read().decode("utf-8"))
    except HTTPError:
        return None
    except (OSError, URLError, ValueError, json.JSONDecodeError):
        return None
    return payload if isinstance(payload, dict) else None


async def _check_browser_health_async(
    *,
    cdp_url: str,
    timeout_ms: int,
) -> dict[str, object]:
    last_checked_at = _now_iso()
    if use_direct_marketplace_runtime():
        try:
            lock_timeout_seconds = max(min(timeout_ms / 1000.0, 2.0), 0.5)
            async with open_direct_marketplace_context(
                lock_timeout_seconds=lock_timeout_seconds
            ) as (
                context,
                browser_family,
                profile_path,
            ):
                page = context.pages[0] if context.pages else await context.new_page()
                await _navigate_marketplace_home(page, timeout_ms=timeout_ms)
                evaluated = await _await_marketplace_probe(
                    page.evaluate(_MARKETPLACE_HOME_EVALUATION_SCRIPT),
                    stage="Marketplace evaluation",
                    timeout_seconds=_probe_timeout_seconds(timeout_ms),
                )
        except MarketplaceBrowserProbeTimeout as exc:
            return {
                "status": "browser_unavailable",
                "cdp_url": cdp_url,
                "browser_family": "chrome",
                "profile_path": profile_path if "profile_path" in locals() else _profile_path("chrome"),
                "challenge_detected": False,
                "last_checked_at": last_checked_at,
                "detail": (
                    f"{marketplace_direct_runtime_detail(profile_path) if 'profile_path' in locals() else 'Marketplace direct headless runtime is enabled.'} "
                    f"Probe timed out during {exc.stage}."
                ),
            }
        except Exception as exc:
            if _is_profile_lock_busy_error(exc):
                return {
                    "status": "ready",
                    "cdp_url": cdp_url,
                    "browser_family": "chrome",
                    "profile_path": profile_path if "profile_path" in locals() else _profile_path("chrome"),
                    "challenge_detected": False,
                    "last_checked_at": last_checked_at,
                    "detail": "Marketplace browser profile is currently in use by another Marketplace task.",
                    "final_url": DEFAULT_MARKETPLACE_HOME_URL,
                }
            return {
                "status": "browser_unavailable",
                "cdp_url": cdp_url,
                "browser_family": "chrome",
                "profile_path": profile_path if "profile_path" in locals() else _profile_path("chrome"),
                "challenge_detected": False,
                "last_checked_at": last_checked_at,
                "detail": (
                    f"{marketplace_direct_runtime_detail(profile_path) if 'profile_path' in locals() else 'Marketplace direct headless runtime is enabled.'} "
                    f"Launch failed: {exc}"
                ),
            }

        challenge_detected = bool(evaluated.get("challengeDetected"))
        if challenge_detected:
            status = "challenge_detected"
            detail = "The browser session hit a Facebook checkpoint or challenge page."
        else:
            status = "ready"
            detail = marketplace_direct_runtime_detail(profile_path)

        return {
            "status": status,
            "cdp_url": cdp_url,
            "browser_family": browser_family,
            "profile_path": profile_path,
            "challenge_detected": challenge_detected,
            "last_checked_at": last_checked_at,
            "detail": detail,
            "final_url": str(evaluated.get("finalUrl") or DEFAULT_MARKETPLACE_HOME_URL),
        }

    version_payload = _fetch_cdp_version(cdp_url, timeout_seconds=max(timeout_ms / 1000, 1.5))
    if version_payload is None:
        helper_health = None
        if _is_local_cdp_url(cdp_url):
            helper_health = _fetch_helper_health(
                timeout_seconds=max(min(timeout_ms / 1000, 2.0), 0.5)
            )
        if helper_health and bool(helper_health.get("display_available")):
            helper_family = str(helper_health.get("browser_family") or "chrome").strip() or "chrome"
            return {
                "status": "browser_not_running",
                "cdp_url": cdp_url,
                "browser_family": helper_family,
                "profile_path": str(helper_health.get("profile_path") or _profile_path(helper_family)),
                "challenge_detected": False,
                "last_checked_at": last_checked_at,
                "detail": str(
                    helper_health.get("detail")
                    or "Marketplace desktop helper is ready to launch the browser."
                ).strip(),
            }
        status = "browser_not_running"
        detail = "No browser is listening on the configured remote debugging port."
        if _is_local_cdp_url(cdp_url) and not _has_graphical_desktop_session():
            status = "desktop_session_missing"
            detail = (
                "No graphical desktop session is available for a local Marketplace browser "
                "profile in this shell."
            )
        return {
            "status": status,
            "cdp_url": cdp_url,
            "browser_family": "chrome",
            "profile_path": _profile_path("chrome"),
            "challenge_detected": False,
            "last_checked_at": last_checked_at,
            "detail": detail,
        }

    family = _browser_family(version_payload)

    try:
        from playwright.async_api import async_playwright
    except Exception:
        return {
            "status": "browser_unavailable",
            "cdp_url": cdp_url,
            "browser_family": family,
            "profile_path": _profile_path(family),
            "challenge_detected": False,
            "last_checked_at": last_checked_at,
            "detail": _browser_unavailable_detail(cdp_url),
        }

    async with async_playwright() as playwright:
        try:
            browser = await _await_marketplace_probe(
                playwright.chromium.connect_over_cdp(cdp_url),
                stage="CDP attach",
                timeout_seconds=_probe_timeout_seconds(timeout_ms),
            )
        except MarketplaceBrowserProbeTimeout as exc:
            return {
                "status": "browser_unavailable",
                "cdp_url": cdp_url,
                "browser_family": family,
                "profile_path": _profile_path(family),
                "challenge_detected": False,
                "last_checked_at": last_checked_at,
                "detail": _marketplace_probe_timeout_detail(
                    cdp_url=cdp_url,
                    timeout_ms=timeout_ms,
                    stage=exc.stage,
                    version_payload=version_payload,
                ),
            }
        except Exception:
            return {
                "status": "browser_unavailable",
                "cdp_url": cdp_url,
                "browser_family": family,
                "profile_path": _profile_path(family),
                "challenge_detected": False,
                "last_checked_at": last_checked_at,
                "detail": _browser_unavailable_detail(cdp_url),
            }

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
                created_page = page not in context.pages[:-1]

            await _navigate_marketplace_home(page, timeout_ms=timeout_ms)
            evaluated = await _await_marketplace_probe(
                page.evaluate(_MARKETPLACE_HOME_EVALUATION_SCRIPT),
                stage="Marketplace evaluation",
                timeout_seconds=_probe_timeout_seconds(timeout_ms),
            )
            challenge_detected = bool(evaluated.get("challengeDetected"))

            if challenge_detected:
                status = "challenge_detected"
                detail = "The browser session hit a Facebook checkpoint or challenge page."
            else:
                status = "ready"
                detail = "Marketplace browser profile is ready."

            return {
                "status": status,
                "cdp_url": cdp_url,
                "browser_family": family,
                "profile_path": _profile_path(family),
                "challenge_detected": challenge_detected,
                "last_checked_at": last_checked_at,
                "detail": detail,
                "final_url": str(evaluated.get("finalUrl") or DEFAULT_MARKETPLACE_HOME_URL),
            }
        except MarketplaceBrowserProbeTimeout as exc:
            return {
                "status": "browser_unavailable",
                "cdp_url": cdp_url,
                "browser_family": family,
                "profile_path": _profile_path(family),
                "challenge_detected": False,
                "last_checked_at": last_checked_at,
                "detail": _marketplace_probe_timeout_detail(
                    cdp_url=cdp_url,
                    timeout_ms=timeout_ms,
                    stage=exc.stage,
                    version_payload=version_payload,
                ),
            }
        finally:
            if created_page and page is not None:
                try:
                    await page.close()
                except Exception:
                    pass


async def check_marketplace_browser_health_async(
    *,
    cdp_url: str | None = None,
    timeout_ms: int | None = None,
) -> dict[str, object]:
    resolved_cdp_url = str(cdp_url or "").strip() or DEFAULT_MARKETPLACE_CDP_URL
    resolved_timeout = int(timeout_ms or DEFAULT_MARKETPLACE_HEALTH_TIMEOUT_MS)
    return await _check_browser_health_async(
        cdp_url=resolved_cdp_url,
        timeout_ms=resolved_timeout,
    )


def check_marketplace_browser_health(
    *,
    cdp_url: str | None = None,
    timeout_ms: int | None = None,
) -> dict[str, object]:
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(
            check_marketplace_browser_health_async(
                cdp_url=cdp_url,
                timeout_ms=timeout_ms,
            )
        )

    result: dict[str, object] = {}
    failure: dict[str, BaseException] = {}

    def _runner() -> None:
        try:
            result["value"] = asyncio.run(
                check_marketplace_browser_health_async(
                    cdp_url=cdp_url,
                    timeout_ms=timeout_ms,
                )
            )
        except BaseException as exc:  # pragma: no cover - defensive thread handoff
            failure["error"] = exc

    thread = threading.Thread(target=_runner, daemon=True)
    thread.start()
    thread.join()

    if "error" in failure:
        raise failure["error"]
    return dict(result.get("value") or {})
