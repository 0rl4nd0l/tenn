"""Route-decision helpers for Cockpit chat turns.

This module starts the route-decision seam with the command pre-router and the
current rule that company-analysis commands defer to the query orchestrator
when the orchestrator is available.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from cockpit.core.command_router import CommandRoute, route_command

__all__ = ["ChatRouteDecision", "build_chat_route_decision"]


@dataclass(frozen=True)
class ChatRouteDecision:
    command_route: CommandRoute
    defer_command_to_orchestrator: bool


def build_chat_route_decision(
    message: str,
    *,
    active_ticker: str | None = None,
    recent_youtube_channel: str | None = None,
    recent_youtube_videos: list[dict[str, Any]] | None = None,
    query_orchestrator_available: bool = False,
) -> ChatRouteDecision:
    command_route = route_command(
        message,
        active_ticker=active_ticker,
        recent_youtube_channel=recent_youtube_channel,
        recent_youtube_videos=recent_youtube_videos,
    )
    return ChatRouteDecision(
        command_route=command_route,
        defer_command_to_orchestrator=(
            query_orchestrator_available and command_route.tool == "run_analysis"
        ),
    )
