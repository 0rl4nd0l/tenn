from __future__ import annotations

from cockpit.core.chat_route_decision import build_chat_route_decision


def test_analysis_command_defers_to_orchestrator_when_available() -> None:
    decision = build_chat_route_decision(
        "analyse PPT",
        query_orchestrator_available=True,
    )

    assert decision.command_route.matched is True
    assert decision.command_route.tool == "run_analysis"
    assert decision.defer_command_to_orchestrator is True


def test_analysis_command_does_not_defer_without_orchestrator() -> None:
    decision = build_chat_route_decision(
        "analyse PPT",
        query_orchestrator_available=False,
    )

    assert decision.command_route.matched is True
    assert decision.command_route.tool == "run_analysis"
    assert decision.defer_command_to_orchestrator is False


def test_non_analysis_command_does_not_defer_to_orchestrator() -> None:
    decision = build_chat_route_decision(
        "ingest BHP news",
        query_orchestrator_available=True,
    )

    assert decision.command_route.matched is True
    assert decision.command_route.tool == "run_news_ingest"
    assert decision.defer_command_to_orchestrator is False


def test_recent_youtube_video_options_still_reach_command_router() -> None:
    decision = build_chat_route_decision(
        "ingest 1",
        recent_youtube_videos=[
            {
                "title": "Video",
                "webpage_url": "https://www.youtube.com/watch?v=abc12345678",
            }
        ],
        query_orchestrator_available=True,
    )

    assert decision.command_route.matched is True
    assert decision.command_route.tool == "ingest_youtube_videos"
    assert decision.command_route.arguments is not None
    assert decision.command_route.arguments["urls"] == [
        "https://www.youtube.com/watch?v=abc12345678"
    ]
    assert decision.command_route.arguments["selected_videos"] == [
        {
            "title": "Video",
            "webpage_url": "https://www.youtube.com/watch?v=abc12345678",
        }
    ]
    assert decision.defer_command_to_orchestrator is False
