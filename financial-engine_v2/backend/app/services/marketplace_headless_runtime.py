from __future__ import annotations

import os
import shutil
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, AsyncIterator


DEFAULT_PROFILE_ROOT = Path.home() / ".tenn" / "browser_profiles"
DEFAULT_BROWSER_KIND = "auto"
DIRECT_RUNTIME_ENV = "MARKETPLACE_BROWSER_RUNTIME"
PROFILE_DIR_ENV = "MARKETPLACE_BROWSER_PROFILE_DIR"
BROWSER_KIND_ENV = "MARKETPLACE_BROWSER_KIND"
XDG_RUNTIME_DIR_ENV = "MARKETPLACE_BROWSER_XDG_RUNTIME_DIR"
DIRECT_RUNTIME_VALUE = "direct"

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


def resolve_marketplace_browser(binary_kind: str | None = None) -> tuple[str, str]:
    browser_kind = str(binary_kind or "").strip().lower() or resolve_marketplace_browser_kind()
    families = ("brave", "chrome") if browser_kind == "auto" else (browser_kind,)
    for family in families:
        for candidate in _BROWSER_CANDIDATES[family]:
            resolved = shutil.which(candidate)
            if resolved:
                return family, resolved
    searched = ", ".join(candidate for family in families for candidate in _BROWSER_CANDIDATES[family])
    raise RuntimeError(f"No supported browser binary was found. Searched: {searched}.")


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


@asynccontextmanager
async def open_direct_marketplace_context() -> AsyncIterator[tuple[Any, str, str]]:
    try:
        from playwright.async_api import async_playwright
    except Exception as exc:  # pragma: no cover - environment specific
        raise RuntimeError("Playwright is not installed in this environment.") from exc

    browser_family, browser_binary = resolve_marketplace_browser()
    profile_dir = resolve_marketplace_profile_dir(browser_family)
    profile_dir.mkdir(parents=True, exist_ok=True)

    launch_env = os.environ.copy()
    launch_env["XDG_RUNTIME_DIR"] = ensure_marketplace_xdg_runtime_dir()

    async with async_playwright() as playwright:
        context = await playwright.chromium.launch_persistent_context(
            user_data_dir=str(profile_dir),
            executable_path=browser_binary,
            headless=True,
            args=[
                "--disable-gpu",
                "--disable-dev-shm-usage",
                "--no-sandbox",
            ],
            env=launch_env,
        )
        try:
            yield context, browser_family, str(profile_dir)
        finally:
            await context.close()
