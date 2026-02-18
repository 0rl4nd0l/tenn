from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any


@dataclass
class ChatResponse:
    text: str
    evidence: list[dict[str, Any]]
    action_preview: dict[str, Any] | None = None


ACTION_KEYWORDS = {
    "full_history": ["backfill", "full history", "history sync"],
    "daily_marketindex": ["daily marketindex", "daily ingest", "marketindex today"],
    "resume_pending": ["resume pending", "retry pending", "pending downloads"],
    "recover_headed": ["recover headed", "headed recovery", "recover marketindex"],
}


class ChatController:
    def __init__(self, ollama_client, tool_router, action_registry, llm_timeout_seconds: float = 300.0) -> None:
        self.ollama_client = ollama_client
        self.tool_router = tool_router
        self.action_registry = action_registry
        self.llm_timeout_seconds = float(llm_timeout_seconds)

    @staticmethod
    def _detect_ticker(message: str) -> str | None:
        # Accept lowercase ticker mentions and normalize to uppercase.
        hit = re.search(r"\b([A-Za-z]{2,5})\b", message)
        if not hit:
            return None
        token = hit.group(1).upper()
        # Avoid obvious non-ticker common short words.
        if token in {"ABOUT", "CHECK", "ANALYSE", "ANALYZE", "RECENT", "MOST"}:
            return None
        return token

    def detect_action_intent(self, message: str) -> str | None:
        text = message.lower()
        for action_id, words in ACTION_KEYWORDS.items():
            if any(w in text for w in words):
                return action_id
        return None

    def build_chat_response(self, message: str, enable_web: bool = False) -> ChatResponse:
        ticker = self._detect_ticker(message)
        local_context = self.tool_router.gather_local_context(ticker=ticker, query=message)

        evidence = [
            {"type": "local_context", "details": local_context.payload},
        ]

        action_id = self.detect_action_intent(message)
        if action_id:
            args = {"ticker": ticker or "BHP"}
            preview = self.action_registry.preview(action_id, args)
            return ChatResponse(
                text=(
                    f"Action candidate detected: {action_id}. "
                    f"Use /confirm to execute or /cancel to skip.\n"
                    f"Command: {' '.join(preview.command)}"
                ),
                evidence=evidence,
                action_preview={
                    "action_id": action_id,
                    "args": args,
                    "command": preview.command,
                    "impact": preview.estimated_impact,
                    "timeout_seconds": preview.timeout_seconds,
                },
            )

        prompt = (
            "You are the Financial Engine cockpit analyst.\n"
            "Use the local evidence below first. If confidence is weak, say so.\n"
            f"User question: {message}\n\n"
            "Local evidence JSON:\n"
            f"{json.dumps(local_context.payload)[:7000]}\n"
        )

        answer = self.ollama_client.chat(prompt, timeout=self.llm_timeout_seconds)
        if enable_web and "http" in message.lower():
            # Explicit user opt-in style: if they include URL and web enabled, we fetch.
            maybe_url = re.search(r"https?://\S+", message)
            if maybe_url:
                web = self.tool_router.fetch_web(maybe_url.group(0), enabled=True)
                evidence.append({"type": "web", "details": web.payload})

        return ChatResponse(text=answer.strip(), evidence=evidence)

    @staticmethod
    def now_iso() -> str:
        return datetime.now(timezone.utc).isoformat()
