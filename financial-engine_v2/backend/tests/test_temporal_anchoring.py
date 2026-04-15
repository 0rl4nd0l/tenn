from __future__ import annotations

from datetime import datetime, timedelta, timezone
import sys
from pathlib import Path
from unittest.mock import MagicMock

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from app.services.tenn_chat import _build_prompt
from cockpit.core.tool_executor import ToolExecutor


def _make_executor() -> ToolExecutor:
    mock_router = MagicMock()
    mock_registry = MagicMock()
    mock_registry.get.return_value = None
    return ToolExecutor(tool_router=mock_router, action_registry=mock_registry)


def test_tenn_chat_system_prompt_contains_today() -> None:
    prompt = _build_prompt(
        "What changed for BHP?",
        [
            {
                "text": "BHP reported updated production guidance.",
                "source_name": "Reuters",
                "published_at": "2026-04-10",
            }
        ],
    )

    today_iso = datetime.now(timezone.utc).date().isoformat()
    assert today_iso in prompt
    assert "historical context" in prompt.lower()


def test_search_news_freshness_warning_injected_into_agent_context() -> None:
    executor = _make_executor()
    stale_timestamp = (datetime.now(timezone.utc) - timedelta(days=4)).isoformat()
    executor._router.get_news_context.return_value = {
        "ok": True,
        "hits": [
            {
                "title": "Older BHP article",
                "published_at": stale_timestamp,
                "url": "https://example.com/bhp-old",
                "provider": "Example News",
            }
        ],
    }

    result = executor.execute("search_news", {"query": "BHP"})

    warning = str(result.get("freshness_warning") or "")
    today_iso = datetime.now(timezone.utc).date().isoformat()
    assert today_iso in warning
    assert "4 day(s) old" in warning
    assert "historical context" in warning.lower()
