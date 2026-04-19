from cockpit.core.tools import ToolRouter


def test_recent_update_query_requests_news_context() -> None:
    assert (
        ToolRouter._query_wants_news_context(
            "what happened with BHP this week",
            deep_mode=False,
        )
        is True
    )
