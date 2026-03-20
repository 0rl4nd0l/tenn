"""Zeroboot sandbox integration for isolated code execution."""

from zeroboot import Sandbox, Result

from app.core.config import settings

_sandbox: Sandbox | None = None


def get_sandbox() -> Sandbox:
    """Return a lazily-initialised Sandbox client."""
    global _sandbox
    if _sandbox is None:
        if not settings.zeroboot_api_key:
            raise RuntimeError(
                "ZEROBOOT_API_KEY is not set. "
                "Add it to .env or export it as an environment variable."
            )
        _sandbox = Sandbox(
            settings.zeroboot_api_key,
            base_url=settings.zeroboot_base_url,
        )
    return _sandbox


def run_code(
    code: str,
    *,
    language: str = "python",
    timeout_seconds: int = 30,
) -> Result:
    """Execute *code* in an isolated Zeroboot sandbox and return the result."""
    return get_sandbox().run(code, language=language, timeout_seconds=timeout_seconds)


def run_batch(
    snippets: list[str],
    *,
    language: str = "python",
    timeout_seconds: int = 30,
) -> list[Result]:
    """Execute multiple code snippets in parallel sandboxes."""
    return get_sandbox().run_batch(
        snippets, language=language, timeout_seconds=timeout_seconds
    )
