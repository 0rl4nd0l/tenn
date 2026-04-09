from __future__ import annotations

import json
import logging
import os
import re
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

# Import cockpit core logic
from cockpit.core.actions import ActionRegistry
from cockpit.core.chat import ChatController, ChatResponse
from cockpit.core.config import RuntimeFlags, apply_runtime_flags, load_config, load_env
from cockpit.core.tools import ToolRouter
from cockpit.integrations.backend_api import BackendApiClient
from cockpit.integrations.db_reader import DbReader
from cockpit.integrations.file_indexer import FileIndexer
from cockpit.integrations.llamacpp_client import LlamaCppClient
from cockpit.integrations.qual_context_bootstrap import (
    build_qual_context_reader,
    context_enabled,
)
from cockpit.integrations.web_fetcher import WebFetcher
from cockpit.storage.state import StateStore
from cockpit.storage.artifacts import ArtifactStore

logger = logging.getLogger(__name__)

_SENSITIVE_KEY_RE = re.compile(
    r"(api[_-]?key|auth|authorization|token|secret|cookie|password|private[_-]?key)",
    re.IGNORECASE,
)
_BEARER_TOKEN_RE = re.compile(r"Bearer\s+[A-Za-z0-9._\-+/=]+", re.IGNORECASE)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _clip_text(value: Any, limit: int = 4000) -> str:
    text = str(value or "")
    if len(text) <= limit:
        return text
    return text[: limit - 1] + "..."


def _sanitize_payload(value: Any, *, key: str | None = None) -> Any:
    if key and _SENSITIVE_KEY_RE.search(key):
        return "***REDACTED***"
    if isinstance(value, dict):
        return {
            str(item_key): _sanitize_payload(item_value, key=str(item_key))
            for item_key, item_value in value.items()
        }
    if isinstance(value, list):
        return [_sanitize_payload(item) for item in value]
    if isinstance(value, tuple):
        return [_sanitize_payload(item) for item in value]
    if isinstance(value, str):
        return _BEARER_TOKEN_RE.sub("Bearer ***REDACTED***", value)
    return value


def _json_object_or_none(raw: str) -> dict[str, Any] | None:
    text = str(raw or "").strip()
    if not text:
        return None
    if text.startswith("```"):
        lines = text.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].startswith("```"):
            lines = lines[:-1]
        text = "\n".join(lines).strip()
    start = text.find("{")
    end = text.rfind("}")
    if start < 0 or end <= start:
        return None
    try:
        parsed = json.loads(text[start : end + 1])
    except json.JSONDecodeError:
        return None
    return parsed if isinstance(parsed, dict) else None


def _extract_tool_calls(evidence: list[dict[str, Any]] | None) -> list[dict[str, Any]]:
    calls: list[dict[str, Any]] = []
    for item in evidence or []:
        if not isinstance(item, dict) or not item.get("tool"):
            continue
        calls.append(
            {
                "tool": str(item.get("tool") or ""),
                "arguments": item.get("arguments")
                if isinstance(item.get("arguments"), dict)
                else {},
                "result": item.get("result"),
            }
        )
    return calls


def _render_flagged_summary(
    bundle: dict[str, Any], analysis: dict[str, Any] | None
) -> str:
    flagged = bundle.get("flagged_message") or {}
    lines = ["# Flagged Cockpit Chat", ""]
    lines.append(f"- Report ID: `{bundle.get('report_id')}`")
    lines.append(f"- Session ID: `{bundle.get('session_id') or 'global-main'}`")
    lines.append(f"- Saved At: `{bundle.get('saved_at')}`")
    lines.extend(
        [
            "",
            "## Flagged Response",
            "",
            _clip_text(flagged.get("content"), 2400),
            "",
        ]
    )
    if analysis:
        summary = str(analysis.get("summary") or "").strip()
        if summary:
            lines.extend(["## Analysis", "", summary, ""])
    return "\n".join(lines).strip() + "\n"


def _env_flag(name: str, default: bool = False) -> bool:
    raw = str(os.getenv(name, "")).strip().lower()
    if not raw:
        return default
    return raw in {"1", "true", "yes", "on", "y"}


def _normalize_database_url(repo_root: Path, database_url: str) -> str:
    value = (database_url or "").strip()
    if not value:
        value = "sqlite:///./data/fe_local.db"

    if value.startswith("sqlite:///"):
        path_part = value[len("sqlite:///") :]
        if path_part.startswith("./") or not path_part.startswith("/"):
            resolved = (repo_root / path_part).resolve()
            resolved.parent.mkdir(parents=True, exist_ok=True)
            return f"sqlite:///{resolved}"

        abs_path = Path(path_part)
        abs_path.parent.mkdir(parents=True, exist_ok=True)
        return value

    return value


class CockpitService:
    _instance = None
    _lock = threading.Lock()

    def __init__(self):
        repo_root = Path(__file__).resolve().parents[3]
        load_env(repo_root)

        config_path_value = str(
            os.getenv("COCKPIT_CONFIG") or "config/cockpit.yaml"
        ).strip()
        config_path = Path(config_path_value)
        if not config_path.is_absolute():
            config_path = (repo_root / config_path).resolve()

        cfg = load_config(str(config_path))
        cfg = apply_runtime_flags(
            cfg,
            RuntimeFlags(
                config_path=str(config_path),
                profile=str(os.getenv("COCKPIT_PROFILE") or "default").strip()
                or "default",
                read_only=_env_flag("COCKPIT_READ_ONLY", False),
                no_web=_env_flag("COCKPIT_NO_WEB", False),
                repo_root=repo_root,
            ),
        )

        db_cfg = cfg.get("db") if isinstance(cfg.get("db"), dict) else {}
        db_url = _normalize_database_url(
            repo_root, str(db_cfg.get("database_url") or "")
        )
        cfg.setdefault("db", {})
        cfg["db"]["database_url"] = db_url

        llm_cfg = cfg.get("llm") if isinstance(cfg.get("llm"), dict) else {}
        llm_provider = str(llm_cfg.get("provider") or "llamacpp").strip().lower()
        llm_model = str(llm_cfg.get("model") or "").strip()
        if llm_provider == "llamacpp":
            llm_url = str(llm_cfg.get("llamacpp_url") or "").strip()
        else:
            llm_url = str(
                llm_cfg.get("llamacpp_url") or llm_cfg.get("ollama_url") or ""
            ).strip()

        backend_cfg = cfg.get("backend") if isinstance(cfg.get("backend"), dict) else {}
        backend_api_url = str(backend_cfg.get("api_base_url") or "").strip()

        self.repo_root = repo_root
        self.config = cfg
        self.llm_timeout_seconds = float(llm_cfg.get("timeout_seconds", 300))
        self.artifact_store = ArtifactStore(
            repo_root=repo_root,
            exports_dir=cfg["exports"]["dir"],
            reports_dir=cfg["reports"]["dir"],
        )
        self.state_store = StateStore(cfg["memory"]["state_db"])
        self.db_reader = DbReader(db_url)
        self.file_indexer = FileIndexer(cfg["paths"]["allow_roots"])
        self.web_fetcher = WebFetcher()

        self.llm_client = LlamaCppClient(
            llm_url,
            llm_model,
            api_key=str(llm_cfg.get("llamacpp_api_key") or ""),
        )

        self.action_registry = ActionRegistry(
            repo_root=repo_root,
            confirm_required=cfg["actions"].get("confirm_required", True),
        )

        self.backend_api_client = None
        self.query_orchestrator = None
        if backend_api_url:
            self.backend_api_client = BackendApiClient(
                base_url=backend_api_url,
                api_key=str(backend_cfg.get("api_key") or "").strip(),
            )

        rag_cfg = cfg.get("rag") if isinstance(cfg.get("rag"), dict) else {}
        qual_company = None
        qual_news = None
        if self.backend_api_client is not None:
            qc_cfg = (
                rag_cfg.get("qualitative_context")
                if isinstance(rag_cfg.get("qualitative_context"), dict)
                else None
            )
            if context_enabled(qc_cfg, default=False):
                try:
                    qual_company = build_qual_context_reader(
                        repo_root=repo_root,
                        qc_cfg=qc_cfg,
                        backend_api_client=self.backend_api_client,
                        context_name="qualitative_context",
                    )
                except Exception as exc:
                    logger.warning(
                        "CockpitService: qual_context (company) disabled: %s", exc
                    )

            news_cfg = (
                rag_cfg.get("news_context")
                if isinstance(rag_cfg.get("news_context"), dict)
                else None
            )
            if context_enabled(news_cfg, default=False):
                try:
                    qual_news = build_qual_context_reader(
                        repo_root=repo_root,
                        qc_cfg=news_cfg,
                        backend_api_client=self.backend_api_client,
                        context_name="news_context",
                    )
                except Exception as exc:
                    logger.warning(
                        "CockpitService: qual_context (news) disabled: %s", exc
                    )

        self.tool_router = ToolRouter(
            db_reader=self.db_reader,
            file_indexer=self.file_indexer,
            web_fetcher=self.web_fetcher,
            repo_root=repo_root,
            web_default_enabled=cfg["web"].get("enabled_default", False),
            backend_api_client=self.backend_api_client,
            qual_context_company_reader=qual_company,
            qual_context_news_reader=qual_news,
            state_store=self.state_store,
        )
        self.chat_controller = ChatController(
            ollama_client=self.llm_client,
            tool_router=self.tool_router,
            action_registry=self.action_registry,
            llm_timeout_seconds=self.llm_timeout_seconds,
            state_store=self.state_store,
            thread_id="global-main",
            cockpit_llm=cfg.get("cockpit_llm"),
            repo_root=self.repo_root,
            query_orchestrator=self.query_orchestrator,
        )
        self._feedback_lock = threading.Lock()
        self._recent_turn_diagnostics: dict[str, list[dict[str, Any]]] = {}

        logger.info("CockpitService initialized successfully (config=%s)", config_path)

    @classmethod
    def get_instance(cls) -> CockpitService:
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    @staticmethod
    def _resolve_thread_id(session_id: str | None) -> str:
        candidate = str(session_id or "").strip()
        return candidate[:128] if candidate else "global-main"

    def _build_chat_controller(self, thread_id: str) -> ChatController:
        if thread_id == "global-main":
            return self.chat_controller
        return ChatController(
            ollama_client=self.llm_client,
            tool_router=self.tool_router,
            action_registry=self.action_registry,
            llm_timeout_seconds=self.llm_timeout_seconds,
            state_store=self.state_store,
            thread_id=thread_id,
            cockpit_llm=self.config.get("cockpit_llm"),
            repo_root=self.repo_root,
            query_orchestrator=self.query_orchestrator,
        )

    def _persist_chat_message(self, thread_id: str, role: str, content: str) -> None:
        text = str(content or "").strip()
        if not text:
            return
        self.state_store.add_chat_message(
            thread_id,
            role,
            text,
            datetime.now(timezone.utc).isoformat(),
        )

    def _remember_turn_diagnostics(
        self, thread_id: str, payload: dict[str, Any]
    ) -> None:
        with self._feedback_lock:
            items = self._recent_turn_diagnostics.setdefault(thread_id, [])
            items.append(payload)
            if len(items) > 20:
                del items[:-20]

    def _resolve_turn_diagnostics(
        self, thread_id: str, flagged_message: dict[str, Any] | None
    ) -> dict[str, Any] | None:
        flagged_text = str((flagged_message or {}).get("content") or "").strip()
        with self._feedback_lock:
            items = list(self._recent_turn_diagnostics.get(thread_id) or [])
        if not items:
            return None
        if flagged_text:
            for item in reversed(items):
                if str(item.get("response_text") or "").strip() == flagged_text:
                    return item
        return items[-1]

    def _analyze_flagged_bundle(self, bundle: dict[str, Any]) -> dict[str, Any] | None:
        review_input = _sanitize_payload(
            {
                "session_id": bundle.get("session_id"),
                "ticker": bundle.get("ticker"),
                "request": (
                    (bundle.get("backend_turn") or {}).get("request") or {}
                ).get("message"),
                "flagged_response": (
                    (bundle.get("flagged_message") or {}).get("content")
                ),
                "thinking": (
                    (bundle.get("backend_turn") or {}).get("thinking_events") or []
                )[:4],
                "status_events": (
                    (bundle.get("backend_turn") or {}).get("status_events") or []
                )[:12],
                "tool_traces": (
                    (bundle.get("backend_turn") or {}).get("tool_traces") or []
                )[:12],
                "tool_calls": (
                    (bundle.get("backend_turn") or {}).get("tool_calls") or []
                )[:6],
            }
        )
        prompt = (
            "You are reviewing a flagged cockpit chat turn. Return JSON only with keys "
            '"summary", "likely_failure_modes", "evidence", and "recommended_follow_up". '
            "Keep lists concise, factual, and grounded in the provided traces. If the cause is unclear, say so explicitly.\n\n"
            f"Context:\n{json.dumps(review_input, indent=2, default=str)}"
        )
        try:
            raw = self.llm_client.chat(
                prompt,
                timeout=min(max(self.llm_timeout_seconds, 10.0), 30.0),
            )
        except Exception as exc:
            logger.warning("Flagged chat analysis unavailable: %s", exc)
            return {"status": "llm_unavailable", "error": str(exc)}
        parsed = _json_object_or_none(raw)
        if parsed is not None:
            parsed.setdefault("status", "ok")
            return parsed
        return {"status": "unparsed", "raw": _clip_text(raw, 3000)}

    def flag_chat_feedback(
        self,
        *,
        session_id: str | None,
        ticker: str | None,
        flagged_message: dict[str, Any],
        transcript: list[dict[str, Any]] | None = None,
        frontend_context: dict[str, Any] | None = None,
        note: str | None = None,
    ) -> dict[str, Any]:
        thread_id = self._resolve_thread_id(session_id)
        matched_turn = self._resolve_turn_diagnostics(thread_id, flagged_message) or {}
        persisted_history = self.state_store.get_chat_messages(thread_id, limit=200)
        report_id = f"flag_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}"
        report_dir = (
            self.repo_root / f"reports/cockpit/flagged_sessions/{thread_id}/{report_id}"
        ).resolve()
        report_dir.mkdir(parents=True, exist_ok=True)
        bundle = {
            "report_id": report_id,
            "saved_at": _now_iso(),
            "session_id": thread_id,
            "ticker": str(ticker or "").strip().upper() or None,
            "note": str(note or "").strip() or None,
            "flagged_message": flagged_message
            if isinstance(flagged_message, dict)
            else {},
            "frontend_snapshot": {
                "transcript": [
                    item for item in (transcript or []) if isinstance(item, dict)
                ][-200:],
                "context": frontend_context
                if isinstance(frontend_context, dict)
                else {},
            },
            "persisted_history": persisted_history,
            "backend_turn": {
                **matched_turn,
                "tool_calls": _extract_tool_calls(matched_turn.get("evidence")),
            },
        }
        sanitized_bundle = _sanitize_payload(bundle)
        analysis = _sanitize_payload(self._analyze_flagged_bundle(bundle) or {})
        bundle_path = report_dir / "bundle.json"
        summary_path = report_dir / "summary.md"
        analysis_path = report_dir / "analysis.json"
        bundle_path.write_text(
            json.dumps(sanitized_bundle, indent=2, default=str), encoding="utf-8"
        )
        summary_path.write_text(
            _render_flagged_summary(sanitized_bundle, analysis), encoding="utf-8"
        )
        analysis_path.write_text(
            json.dumps(analysis, indent=2, default=str), encoding="utf-8"
        )
        return {
            "ok": True,
            "report_id": report_id,
            "report_dir": str(report_dir),
            "bundle_path": str(bundle_path),
            "summary_path": str(summary_path),
            "analysis_path": str(analysis_path),
            "analysis_summary": str(analysis.get("summary") or "").strip() or None,
        }

    def chat_stream(
        self,
        message: str,
        ticker: str | None = None,
        session_id: str | None = None,
        on_chunk: Callable[[str], None] | None = None,
        on_status: Callable[[str], None] | None = None,
        on_thinking: Callable[[str, str], None] | None = None,
        enable_web: bool | None = None,
        model: str | None = None,
        rag: bool | None = None,
        db_diagnostics: bool | None = None,
    ) -> ChatResponse:
        """Run a chat turn and return the full response, while optionally streaming chunks."""
        thread_id = self._resolve_thread_id(session_id)
        controller = self._build_chat_controller(thread_id)
        status_events: list[dict[str, Any]] = []
        thinking_events: list[dict[str, Any]] = []

        def _capture_chunk(chunk: str) -> None:
            if on_chunk is not None:
                on_chunk(chunk)

        def _capture_status(stage: str) -> None:
            status_events.append({"stage": str(stage or ""), "at": _now_iso()})
            if on_status is not None:
                on_status(stage)

        def _capture_thinking(assessment: str, plan: str) -> None:
            thinking_events.append(
                {
                    "assessment": str(assessment or ""),
                    "plan": str(plan or ""),
                    "at": _now_iso(),
                }
            )
            if on_thinking is not None:
                on_thinking(assessment, plan)

        self._persist_chat_message(thread_id, "user", message)
        response = controller.build_chat_response(
            message=message,
            enable_web=bool(enable_web) if enable_web is not None else False,
            enable_rag=bool(rag) if rag is not None else True,
            enable_db_diagnostics=bool(db_diagnostics)
            if db_diagnostics is not None
            else False,
            prior_ticker=ticker,
            on_chunk=_capture_chunk,
            on_status=_capture_status,
            on_thinking=_capture_thinking,
        )
        meta = dict(getattr(response, "routing_metadata", None) or {})
        meta.setdefault("source", "local")
        meta.setdefault("latency_ms", 0)
        meta.setdefault("cost_usd", 0.0)
        response.routing_metadata = meta
        self._persist_chat_message(thread_id, "assistant", response.text)
        self._remember_turn_diagnostics(
            thread_id,
            {
                "created_at": _now_iso(),
                "thread_id": thread_id,
                "session_id": thread_id,
                "ticker": str(ticker or "").strip().upper() or None,
                "request": {"message": message, "ticker": ticker},
                "status_events": status_events,
                "thinking_events": thinking_events,
                "response_text": response.text,
                "tool_traces": list(getattr(response, "tool_traces", None) or []),
                "evidence": list(response.evidence or []),
                "routing_metadata": meta,
            },
        )
        return response
