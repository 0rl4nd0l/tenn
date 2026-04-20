from __future__ import annotations

import asyncio
import os
import shutil
import threading
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, AsyncIterator


DEFAULT_PROFILE_ROOT = Path.home() / ".tenn" / "browser_profiles"
DEFAULT_BROWSER_KIND = "auto"
DIRECT_RUNTIME_ENV = "MARKETPLACE_BROWSER_RUNTIME"
PROFILE_DIR_ENV = "MARKETPLACE_BROWSER_PROFILE_DIR"
BROWSER_KIND_ENV = "MARKETPLACE_BROWSER_KIND"
XDG_RUNTIME_DIR_ENV = "MARKETPLACE_BROWSER_XDG_RUNTIME_DIR"
EXECUTABLE_PATH_ENV = "MARKETPLACE_BROWSER_EXECUTABLE_PATH"
DIRECT_RUNTIME_VALUE = "direct"
_DIRECT_RUNTIME_PROFILE_LOCK = threading.Lock()
_DIRECT_RUNTIME_PROFILE_LOCK_TIMEOUT_SECONDS = 45.0

_BROWSER_CANDIDATES: dict[str, tuple[str, ...]] = {
    "brave": ("brave-browser", "brave"),
    "chrome": (
        "google-chrome",
        "google-chrome-stable",
        "chromium-browser",
        "chromium",
    ),
}


def use_direct_marketplace_runtime() -> bool:
    return str(os.environ.get(DIRECT_RUNTIME_ENV) or "").strip().lower() == DIRECT_RUNTIME_VALUE


def resolve_marketplace_browser_kind() -> str:
    raw = str(os.environ.get(BROWSER_KIND_ENV) or DEFAULT_BROWSER_KIND).strip().lower()
    return raw if raw in {"auto", "brave", "chrome"} else DEFAULT_BROWSER_KIND


def _resolve_playwright_browser_path() -> str | None:
    try:
        from playwright.sync_api import sync_playwright
    except Exception:
        return None

    try:
        with sync_playwright() as playwright:
            executable = str(playwright.chromium.executable_path or "").strip()
    except Exception:
        return None

    return executable if executable and Path(executable).exists() else None


def resolve_marketplace_browser(binary_kind: str | None = None) -> tuple[str, str]:
    explicit_path = str(os.environ.get(EXECUTABLE_PATH_ENV) or "").strip()
    if explicit_path:
        resolved_path = str(Path(explicit_path).expanduser().resolve())
        if Path(resolved_path).exists():
            return "chrome", resolved_path
        raise RuntimeError(
            f"Configured Marketplace browser executable does not exist: {resolved_path}"
        )

    browser_kind = str(binary_kind or "").strip().lower() or resolve_marketplace_browser_kind()
    families = ("brave", "chrome") if browser_kind == "auto" else (browser_kind,)
    for family in families:
        for candidate in _BROWSER_CANDIDATES[family]:
            resolved = shutil.which(candidate)
            if resolved:
                return family, resolved
    playwright_path = _resolve_playwright_browser_path()
    if playwright_path:
        return "chrome", playwright_path
    searched = ", ".join(candidate for family in families for candidate in _BROWSER_CANDIDATES[family])
    raise RuntimeError(
        "No supported browser binary was found. "
        f"Searched PATH candidates: {searched}. "
        "Playwright Chromium was also unavailable."
    )


def resolve_marketplace_profile_dir(browser_family: str) -> Path:
    override = str(os.environ.get(PROFILE_DIR_ENV) or "").strip()
    if override:
        return Path(override).expanduser().resolve()
    return (DEFAULT_PROFILE_ROOT / f"facebook-marketplace-{browser_family}").resolve()


def ensure_marketplace_xdg_runtime_dir() -> str:
    runtime_dir = str(
        os.environ.get(XDG_RUNTIME_DIR_ENV)
        or os.environ.get("XDG_RUNTIME_DIR")
        or f"/tmp/tenn-marketplace-runtime-{os.getuid()}"
    ).strip()
    path = Path(runtime_dir).expanduser().resolve()
    path.mkdir(parents=True, exist_ok=True)
    path.chmod(0o700)
    return str(path)


def marketplace_direct_runtime_detail(profile_path: str) -> str:
    return (
        "Marketplace direct headless runtime is enabled. "
        f"Browser profile: {profile_path}"
    )


def _profile_in_use_message(profile_path: str) -> str:
    return (
        "Marketplace browser profile is already in use by another Chromium instance or "
        f"Marketplace operation. Profile: {profile_path}. Close the other browser or wait "
        "for the current Marketplace task to finish, then retry."
    )


def _normalize_runtime_launch_error(exc: Exception, profile_path: str) -> RuntimeError:
    message = str(exc)
    if "ProcessSingleton" in message or "SingletonLock" in message:
        return RuntimeError(_profile_in_use_message(profile_path))
    return RuntimeError(message)


@asynccontextmanager
async def open_direct_marketplace_context() -> AsyncIterator[tuple[Any, str, str]]:
    try:
        from playwright.async_api import async_playwright
    except Exception as exc:  # pragma: no cover - environment specific
        raise RuntimeError("Playwright is not installed in this environment.") from exc

    browser_family, browser_binary = resolve_marketplace_browser()
    profile_dir = resolve_marketplace_profile_dir(browser_family)
    profile_dir.mkdir(parents=True, exist_ok=True)
    profile_path = str(profile_dir)

    launch_env = os.environ.copy()
    launch_env["XDG_RUNTIME_DIR"] = ensure_marketplace_xdg_runtime_dir()

    acquired = await asyncio.to_thread(
        _DIRECT_RUNTIME_PROFILE_LOCK.acquire,
        True,
        _DIRECT_RUNTIME_PROFILE_LOCK_TIMEOUT_SECONDS,
    )
    if not acquired:
        raise RuntimeError(_profile_in_use_message(profile_path))

    async with async_playwright() as playwright:
        try:
            context = await playwright.chromium.launch_persistent_context(
                user_data_dir=profile_path,
                executable_path=browser_binary,
                headless=True,
                args=[
                    "--disable-gpu",
                    "--disable-dev-shm-usage",
                    "--no-sandbox",
                ],
                env=launch_env,
            )
        except Exception as exc:
            _DIRECT_RUNTIME_PROFILE_LOCK.release()
            raise _normalize_runtime_launch_error(exc, profile_path) from exc

        try:
            yield context, browser_family, profile_path
        finally:
            try:
                await context.close()
            finally:
                _DIRECT_RUNTIME_PROFILE_LOCK.release()
