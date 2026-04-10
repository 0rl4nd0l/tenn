from __future__ import annotations

import asyncio
import json
import logging
import os
import re
import shutil
import subprocess
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit, urlunsplit

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.widgets import Footer, Header, RichLog, Static

from cockpit.core.actions import ActionRegistry
from cockpit.core.backend_restart import restart_backend
from cockpit.core.chat import ChatController
from cockpit.core.job_runner import JobRunner
from cockpit.core.plotly_html import (
    build_candlestick_dashboard_html,
    build_snapshot_dashboard_html,
)
from cockpit.core.snapshot import build_snapshot_payload
from cockpit.core.config import DEFAULT_LLAMACPP_URL, DEFAULT_OLLAMA_URL
from cockpit.core.export_utils import extract_ticker_from_payload
from cockpit.core.types import JobRun
from cockpit.core.verification import run_verification
from cockpit.integrations.backend_api import BackendApiClient
from cockpit.integrations.db_reader import DbReader
from cockpit.integrations.file_indexer import FileIndexer
from cockpit.integrations.llamacpp_client import LlamaCppClient
from cockpit.integrations.qual_context_bootstrap import (
    build_qual_context_reader,
    context_enabled,
)
from cockpit.integrations.web_fetcher import WebFetcher
from cockpit.core.conversation_commands import derive_conversational_command
from cockpit.core.tool_call_debug import (
    cockpit_tool_chat_debug_mode,
    format_failure_block,
)
from cockpit.core.access_resume import (
    build_pending_action_payload,
    resolve_pending_action_alias,
)
from cockpit.core.backend_proposals import build_backend_runtime_remediation_request
from cockpit.core.backend_proposals import build_backend_access_proposal_request
from cockpit.core.sources import SourcesFormatter
from cockpit.core.tools import ToolRouter
from cockpit.storage.artifacts import ArtifactStore
from cockpit.storage.state import StateStore
from cockpit.ui.screens import (
    ChatScreen,
    ConfirmActionScreen,
    HistoryScreen,
    NewsSearchScreen,
    OperationsScreen,
    SettingsScreen,
    UpdaterScreen,
    VerificationScreen,
)
from cockpit.ui.help_modal import HelpScreen

logger = logging.getLogger(__name__)


class CockpitApp(App):
    ASSISTANT_NAME = "Tenn"
    _REDACTED_EXPORT_VALUE = "***REDACTED***"
    _SENSITIVE_EXPORT_KEY_PARTS = (
        "api_key",
        "apikey",
        "auth",
        "authorization",
        "bearer",
        "cookie",
        "password",
        "secret",
        "token",
        "private_key",
    )

    CSS = """
    #confirm-modal {
        border: round $accent;
        padding: 1 2;
        width: 90%;
    }
    Button#chat-copy-output {
        background: $warning;
        color: $text;
        border: heavy $accent;
    }
    Button#chat-copy-output:hover {
        background: $accent;
        color: $text;
    }
    #chat-ticker-context {
        height: 1;
        color: $accent;
    }
    #chat-status {
        height: 1;
        margin: 0 0 1 0;
    }
    #chat-pending {
        height: 1;
        margin: 0 0 1 0;
    }
    #chat-model-status {
        height: 8;
        border: round $primary;
        padding: 0 1;
        margin: 0 0 1 0;
    }
    #chat-actions {
        margin: 0 0 1 0;
    }
    #chat-actions Horizontal {
        margin: 0;
    }
    #chat-actions Button {
        width: 1fr;
    }
    #chat-log {
        height: 1fr;
        min-height: 8;
        border: round $surface;
        padding: 0 1;
    }
    #chat-live-response {
        display: none;
        margin: 0 0 1 0;
        padding: 0 1;
        border: round $accent;
        max-height: 12;
        overflow-y: auto;
    }
    #chat-live-response.-visible {
        display: block;
    }
    """
    BINDINGS = [
        Binding("c", "show_chat", "Chat"),
        Binding("o", "show_ops", "Ops"),
        Binding("u", "show_updater", "Updater"),
        Binding("v", "show_verification", "Verify"),
        Binding("h", "show_history", "History"),
        Binding("s", "show_settings", "Settings"),
        Binding("?", "show_help", "Help"),
        Binding("ctrl+n", "show_news_search", "News Search"),
        Binding("x", "export_copy_bundle", "Export"),
        Binding("q", "quit", "Quit"),
    ]

    def __init__(
        self, repo_root: Path, config: dict[str, Any], read_only: bool
    ) -> None:
        super().__init__()
        self._init_services(repo_root, config, read_only)

    def _init_services(
        self, repo_root: Path, config: dict[str, Any], read_only: bool
    ) -> None:
        """Initialize all cockpit services. Called from __init__ and from CockpitWebApp after pre-boot."""
        self.repo_root = repo_root
        self.config = config
        self.read_only = read_only

        self.artifacts = ArtifactStore(
            repo_root=repo_root,
            exports_dir=config["exports"]["dir"],
            reports_dir=config["reports"]["dir"],
        )
        self.state_store = StateStore(config["memory"]["state_db"])
        db_url = self._normalize_database_url(str(config["db"]["database_url"]))
        self.config.setdefault("db", {})
        self.config["db"]["database_url"] = db_url
        self.db_reader = DbReader(db_url)
        self.file_indexer = FileIndexer(config["paths"]["allow_roots"])
        self.web_fetcher = WebFetcher()
        llm_cfg = config.get("llm", {})
        llm_provider = llm_cfg.get("provider", "llamacpp")
        llm_model = llm_cfg.get("model", "llama3:latest")
        if llm_provider == "llamacpp":
            llm_url = llm_cfg.get("llamacpp_url", DEFAULT_LLAMACPP_URL)
        else:
            # Ollama also exposes an OpenAI-compatible /v1 API.
            llm_url = llm_cfg.get("llamacpp_url") or llm_cfg.get(
                "ollama_url", DEFAULT_OLLAMA_URL
            )
        self.ollama_client = LlamaCppClient(
            llm_url,
            llm_model,
            api_key=llm_cfg.get("llamacpp_api_key", ""),
        )
        self.action_registry = ActionRegistry(
            repo_root=repo_root,
            confirm_required=config["actions"].get("confirm_required", True),
        )
        self.job_runner = JobRunner(
            repo_root=repo_root, logs_dir=self.artifacts.logs_dir
        )

        # Wire production pipeline: BackendApiClient → qual/news context readers.
        backend_cfg = config.get("backend") or {}
        backend_api_url = str(backend_cfg.get("api_base_url") or "").strip()
        self._backend_client: BackendApiClient | None = None
        self._startup_warnings: list[str] = []

        if backend_api_url:
            self._backend_client = BackendApiClient(
                backend_api_url,
                api_key=str(backend_cfg.get("api_key") or "").strip(),
            )

        rag_cfg = config.get("rag") or {}
        qual_company = None
        qual_news = None

        if self._backend_client is not None:
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
                        backend_api_client=self._backend_client,
                        context_name="qualitative_context",
                    )
                except Exception as exc:
                    self._startup_warnings.append(
                        f"qual_context (company) disabled: {exc}"
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
                        backend_api_client=self._backend_client,
                        context_name="news_context",
                    )
                except Exception as exc:
                    self._startup_warnings.append(
                        f"qual_context (news) disabled: {exc}"
                    )
        else:
            self._startup_warnings.append(
                "backend.api_base_url not set — price, RAG, and news context disabled"
            )

        self.tool_router = ToolRouter(
            db_reader=self.db_reader,
            file_indexer=self.file_indexer,
            web_fetcher=self.web_fetcher,
            repo_root=self.repo_root,
            web_default_enabled=config["web"].get("enabled_default", False),
            backend_api_client=self._backend_client,
            qual_context_company_reader=qual_company,
            qual_context_news_reader=qual_news,
            state_store=self.state_store,
        )
        self.chat_controller = ChatController(
            ollama_client=self.ollama_client,
            tool_router=self.tool_router,
            action_registry=self.action_registry,
            llm_timeout_seconds=float(
                config.get("llm", {}).get("timeout_seconds", 300)
            ),
            state_store=self.state_store,
            thread_id="global-main",
            cockpit_llm=config.get("cockpit_llm"),
        )

        self.thread_id = "global-main"
        self.pending_action: dict[str, Any] | None = None
        self.last_verification_payload: dict[str, Any] | None = None
        self.last_snapshot_payload: dict[str, Any] | None = None
        self.last_chart_path: str | None = None
        self.last_detected_ticker: str | None = None
        self.last_response_mode: str | None = None
        self._latest_sources_payloads: list[dict[str, Any]] = []
        self.chat_inflight = False
        self._input_history: list[str] = []
        self._history_idx: int = -1
        self.active_job_task: asyncio.Task[None] | None = None
        self.active_job_id: str | None = None
        self.active_log_target: str = "chat-log"
        self._model_status_timer = None
        self._last_chat_inference_line: str | None = None
        self._chat_tasks: set[asyncio.Task[None]] = set()

    def _normalize_database_url(self, database_url: str) -> str:
        value = (database_url or "").strip()
        if not value:
            value = "sqlite:///./data/fe_local.db"

        if value.startswith("sqlite:///"):
            path_part = value[len("sqlite:///") :]
            if path_part.startswith("./") or not path_part.startswith("/"):
                resolved = (self.repo_root / path_part).resolve()
                resolved.parent.mkdir(parents=True, exist_ok=True)
                return f"sqlite:///{resolved}"

            # Absolute sqlite path: ensure parent exists.
            abs_path = Path(path_part)
            abs_path.parent.mkdir(parents=True, exist_ok=True)
            return value

        return value

    def _access_state(self) -> dict[str, Any]:
        rag_available = bool(
            any(
                reader is not None
                for reader in (
                    getattr(self.tool_router, "qual_context_company_reader", None),
                    getattr(self.tool_router, "qual_context_news_reader", None),
                )
            )
            or getattr(self.tool_router, "news_context_db_path", "")
        )
        rag_enabled = (
            bool(getattr(self.tool_router, "qual_context_enabled", False))
            and rag_available
        )
        return {
            "web_enabled": bool(
                self.config.get("web", {}).get("enabled_default", False)
            ),
            "rag_enabled": rag_enabled,
            "db_diagnostic_query_enabled": bool(
                self.state_store.get_preference("db_diagnostic_query_enabled", "true")
                == "true"
            ),
        }

    def get_capabilities(self) -> dict[str, Any]:
        """Return current capability status for the settings UI."""
        chat_ctrl = getattr(self, "chat_controller", None)
        hybrid_router = (
            getattr(chat_ctrl, "_hybrid_router", None) if chat_ctrl else None
        )
        from cockpit.core.llm_profile import cockpit_llm_profile_label

        cm = self.config.get("cockpit_llm") or {}
        allow_env = bool(cm.get("allow_env_override", False))
        explicit = (os.environ.get("HYBRID_ROUTER_POLICY") or "").strip()
        return {
            "backend_api": self._backend_client is not None,
            "backend_url": self._backend_client.base_url
            if self._backend_client
            else None,
            "brave_search": getattr(self.tool_router, "brave_search_client", None)
            is not None,
            "hn_search": getattr(self.tool_router, "hn_search_client", None)
            is not None,
            "dossier": getattr(self.tool_router, "dossier_service", None) is not None,
            "deep_research": getattr(self.tool_router, "deep_research_runner", None)
            is not None,
            "anthropic_api": hybrid_router is not None
            and hybrid_router._api is not None,
            "routing_policy": hybrid_router._policy
            if hybrid_router
            else "not initialized",
            "llm_profile": cockpit_llm_profile_label(cm),
            "llm_profile_id": str(cm.get("llm_profile_label") or "ops").strip().lower(),
            "explicit_policy_override": (explicit or None) if allow_env else None,
            "session_cost_usd": hybrid_router.total_cost_usd()
            if hybrid_router
            else 0.0,
            "cockpit_llm_config_path": str(
                self.repo_root / "config" / "cockpit_llm.yaml"
            ),
        }

    def set_llm_profile(self, profile: str) -> str:
        """LLM profile is fixed in config/cockpit_llm.yaml (no runtime override)."""
        _ = profile
        return (
            "LLM profile is configured in config/cockpit_llm.yaml (llm_profile_label). "
            "Edit that file and restart Cockpit to apply."
        )

    def set_routing_policy(self, policy: str) -> str:
        """HybridRouter policy is fixed in config/cockpit_llm.yaml (no runtime override)."""
        _ = policy
        return (
            "Routing policy is configured in config/cockpit_llm.yaml (hybrid_router_policy). "
            "Edit that file and restart Cockpit to apply."
        )

    def _set_access_scope(self, scope: str, enable: bool) -> str:
        normalized = str(scope or "").strip().lower()
        enabled = bool(enable)
        if normalized == "web":
            self.config.setdefault("web", {})["enabled_default"] = enabled
            self.tool_router.web_default_enabled = enabled
            return f"Web search {'enabled' if enabled else 'disabled'}."
        if normalized == "rag":
            rag_available = bool(
                any(
                    reader is not None
                    for reader in (
                        getattr(self.tool_router, "qual_context_company_reader", None),
                        getattr(self.tool_router, "qual_context_news_reader", None),
                    )
                )
                or getattr(self.tool_router, "news_context_db_path", "")
            )
            self.config.setdefault("rag", {})["enabled"] = enabled
            self.tool_router.qual_context_enabled = enabled and rag_available
            if enabled and not rag_available:
                return "RAG was requested, but no configured RAG readers are available in this session."
            return f"RAG retrieval {'enabled' if enabled else 'disabled'}."
        if normalized == "dbdiag":
            self.state_store.set_preference(
                "db_diagnostic_query_enabled",
                "true" if enabled else "false",
            )
            return f"DB diagnostics {'enabled' if enabled else 'disabled'}."
        raise ValueError(f"Unknown access scope: {scope}")

    def _apply_access_state(self, access: dict[str, Any] | None) -> None:
        if not isinstance(access, dict):
            return
        self._set_access_scope("web", bool(access.get("web_enabled", False)))
        self._set_access_scope("rag", bool(access.get("rag_enabled", False)))
        self._set_access_scope(
            "dbdiag",
            bool(access.get("db_diagnostic_query_enabled", False)),
        )

    async def _sync_access_state_from_backend(self) -> None:
        if self._backend_client is None:
            return
        try:
            capabilities = await asyncio.to_thread(
                self._backend_client.capabilities, 5.0
            )
        except Exception:
            return
        if not capabilities.get("ok"):
            return
        payload = capabilities.get("payload") or {}
        self._apply_access_state(payload.get("access"))

    def _apply_backend_access_proposal(self, proposal_id: str) -> str:
        if self._backend_client is None:
            return "Backend API not configured."
        result = self._backend_client.apply_proposal(proposal_id, timeout=15.0)
        if not result.get("ok"):
            return f"Failed to apply backend access proposal: {result.get('error', 'unknown error')}"
        payload = result.get("payload") or {}
        self._apply_access_state(payload.get("access"))
        return str(
            payload.get("message") or f"Applied backend access proposal: {proposal_id}"
        )

    @staticmethod
    def _parse_positive_int(value: str) -> int | None:
        try:
            parsed = int(value)
        except Exception:
            return None
        return parsed if parsed > 0 else None

    async def _start_extraction_runtime(self, log_target: str) -> bool:
        command = ["bash", "scripts/run_llama_server.sh"]
        self._write_log(log_target, f"Starting extraction runtime: {' '.join(command)}")
        try:
            subprocess.Popen(
                command,
                cwd=str(self.repo_root),
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                start_new_session=True,
            )
        except Exception as exc:
            self._write_log(log_target, f"Failed to launch extraction runtime: {exc}")
            return False

        extraction_url = (
            os.getenv("EXTRACTION_LLAMACPP_URL", "").strip()
            or os.getenv("LLAMACPP_URL", "").strip()
            or DEFAULT_LLAMACPP_URL
        )
        probe_client = LlamaCppClient(
            extraction_url,
            str(
                os.getenv("EXTRACT_MODEL")
                or getattr(self.ollama_client, "model", "")
                or "unknown"
            ),
            api_key=str(os.getenv("LLM_API_KEY") or ""),
        )
        for _ in range(20):
            await asyncio.sleep(1.0)
            health = probe_client.health(timeout=2.0)
            if health.get("ok"):
                self._write_log(
                    log_target,
                    f"Extraction runtime is reachable at {health.get('url')}.",
                )
                return True
        self._write_log(log_target, "Extraction runtime did not become ready in time.")
        return False

    async def _execute_internal_action(
        self, action: dict[str, Any], log_target: str
    ) -> bool:
        action_id = str(action.get("action_id") or "").strip()
        args = dict(action.get("args") or {})

        if action_id == "__runtime_remediation__":
            scope = str(args.get("scope") or "").strip().lower()
            if scope != "extraction_runtime":
                self._write_log(
                    log_target, f"Unsupported runtime remediation scope: {scope}"
                )
                return False
            error = str(args.get("error") or "").strip()
            if error:
                self._write_log(log_target, f"Remediation requested: {error}")
            if not await self._start_extraction_runtime(log_target):
                return False
            resume_action_id = str(args.get("resume_action_id") or "").strip()
            resume_args = dict(args.get("resume_args") or {})
            if resume_action_id:
                self._write_log(log_target, f"Resuming action: {resume_action_id}")
                await self.execute_action(
                    resume_action_id,
                    resume_args,
                    log_target=log_target,
                    skip_confirm=True,
                )
            return True

        if action_id == "adjust_signal_weights":
            try:
                from cockpit.core.strategy import StrategyService

                svc = StrategyService(self.state_store)
                result = svc.set_signal_weights(args)
                self._write_log(
                    log_target,
                    f"Signal weights updated: {', '.join(f'{k}={v:.2f}' for k, v in result.items())}",
                )
            except (ValueError, Exception) as exc:
                self._write_log(log_target, f"Failed to update signal weights: {exc}")
            return True

        if action_id == "__backend_proposal__":
            proposal_id = str(args.get("proposal_id") or "").strip()
            if not proposal_id:
                self._write_log(log_target, "Backend proposal is missing proposal_id.")
                return False
            if self._backend_client is None:
                self._write_log(
                    log_target,
                    "Backend proposal requested but backend client is not configured.",
                )
                return False
            self._write_log(log_target, f"Applying backend proposal: {proposal_id}")
            result = self._backend_client.apply_proposal(proposal_id, timeout=45.0)
            if not result.get("ok"):
                self._write_log(
                    log_target,
                    f"Backend proposal failed: {result.get('error', 'unknown error')}",
                )
                return False
            payload = result.get("payload") or {}
            self._apply_access_state(payload.get("access"))
            self._write_log(
                log_target,
                str(
                    payload.get("message") or f"Backend proposal applied: {proposal_id}"
                ),
            )
            resume_message = str(args.get("resume_message") or "").strip()
            if resume_message:
                self._write_log(log_target, "Resuming request after backend approval.")
                await self.handle_chat_message(resume_message)
                return True
            resume_action_id = str(args.get("resume_action_id") or "").strip()
            resume_args = dict(args.get("resume_args") or {})
            if resume_action_id:
                self._write_log(log_target, f"Resuming action: {resume_action_id}")
                await self.execute_action(
                    resume_action_id,
                    resume_args,
                    log_target=log_target,
                    skip_confirm=True,
                )
            return True

        return False

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        yield Footer()

    def on_mount(self) -> None:
        # CockpitWebApp sets _services_ready=False to defer initialization until
        # after the pre-boot screen. Skip here; _finish_mount() is called directly.
        if not getattr(self, "_services_ready", True):
            return
        self._finish_mount()

    async def on_unmount(self) -> None:
        if self._model_status_timer is not None:
            self._model_status_timer.stop()
            self._model_status_timer = None
        for task in list(self._chat_tasks):
            task.cancel()
        self._chat_tasks.clear()
        try:
            await self._summarize_and_store_session()
        except Exception:
            pass  # never block shutdown

    async def _summarize_and_store_session(self) -> None:
        """Summarize the current session and store for future cross-session context."""
        if not getattr(self, "state_store", None):
            return

        msgs = self.state_store.get_chat_messages("global-main", limit=30)
        if len(msgs) < 4:  # skip trivial sessions
            return

        # Build a compact transcript
        transcript_lines = []
        tickers_seen: set[str] = set()
        for m in msgs[-20:]:  # last 20 messages max
            role = m.get("role", "user")
            content = str(m.get("content", ""))[:200]
            transcript_lines.append(f"{role}: {content}")
            # crude ticker extraction: uppercase 2-4 char words
            for t in re.findall(r"\b[A-Z]{2,4}\b", content):
                if t not in {"ASX", "LLM", "RAG", "FCF", "PDF", "EPS", "YOY"}:
                    tickers_seen.add(t)

        transcript = "\n".join(transcript_lines)

        summary_prompt = (
            "You are summarising a financial analysis session in 2-3 sentences for future reference. "
            "Focus on: what companies were analysed, key findings or conclusions, and any decisions or actions taken. "
            "Be concise and factual.\n\nSession transcript:\n"
            + transcript
            + "\n\nSummary (2-3 sentences):"
        )

        llm_client = getattr(self, "ollama_client", None)
        if llm_client is None:
            return

        def _run_summary() -> str:
            result: list[str] = []

            def _collect(chunk: str) -> None:
                result.append(chunk)

            try:
                llm_client.chat(summary_prompt, timeout=30.0, on_chunk=_collect)
            except TypeError:
                # on_chunk not supported — try without
                try:
                    text = llm_client.chat(summary_prompt, timeout=30.0)
                    return str(text or "").strip()
                except Exception:
                    return ""
            return "".join(result)

        summary_text = await asyncio.to_thread(_run_summary)
        summary_text = summary_text.strip()[:800]

        if summary_text and len(summary_text) > 20:
            self.state_store.add_session_summary(
                summary=summary_text,
                tickers=list(tickers_seen)[:10],
            )

    def _finish_mount(self) -> None:
        """Install screens and surface startup info. Called by on_mount (normal flow)
        and by CockpitWebApp._on_preboot_launch (deferred web flow)."""
        self.install_screen(ChatScreen(), name="chat")
        self.install_screen(OperationsScreen(), name="ops")
        self.install_screen(UpdaterScreen(), name="updater")
        self.install_screen(VerificationScreen(), name="verification")
        self.install_screen(HistoryScreen(), name="history")
        self.install_screen(SettingsScreen(), name="settings")
        self.install_screen(NewsSearchScreen(), name="news_search")
        # Defer initial screen activation one tick to avoid startup stack race.
        self.set_timer(0.01, self._activate_initial_screen)

        # Replay recent history into chat log for continuity.
        try:
            screen = self.get_screen("chat")
            log = screen.query_one("#chat-log", RichLog)
            for message in self.state_store.get_chat_messages(self.thread_id, limit=50):
                log.write(f"{message['role']}: {message['content']}")
        except Exception:
            pass

        # Surface any startup wiring warnings (backend/RAG/news context).
        for warning in self._startup_warnings:
            self._screen_log("chat", f"startup warning: {warning}")

        # Health checks are blocking HTTP — run off the event loop.
        asyncio.create_task(self._run_startup_health_checks())
        asyncio.create_task(self._sync_access_state_from_backend())

        self._schedule_model_status_refresh()
        self._model_status_timer = self.set_interval(
            15.0, self._schedule_model_status_refresh
        )

    def action_show_help(self) -> None:
        self.push_screen(HelpScreen(repo_root=self.repo_root))

    async def _run_startup_health_checks(self) -> None:
        """Offload blocking health checks so the event loop stays responsive at startup."""
        if self._backend_client is not None:
            try:
                health = await asyncio.to_thread(self._backend_client.health, 4.0)
                if health.get("ok"):
                    self._screen_log(
                        "chat",
                        f"startup: backend API reachable at {self._backend_client.base_url}",
                    )
                else:
                    self._screen_log(
                        "chat",
                        f"startup: backend API unreachable at {self._backend_client.base_url}: {health.get('error')}",
                    )
            except Exception as exc:
                self._screen_log("chat", f"startup: backend health check failed: {exc}")

        try:
            health = await asyncio.to_thread(self.ollama_client.health, 4.0)
            if health.get("ok"):
                model = str(self.config.get("llm", {}).get("model", ""))
                names = (
                    health.get("models")
                    if isinstance(health.get("models"), list)
                    else []
                )
                if model and names and model not in names:
                    self._screen_log(
                        "chat",
                        f"startup: llama.cpp reachable at {health.get('url')} but model '{model}' is not pulled.",
                    )
                else:
                    self._screen_log(
                        "chat", f"startup: llama.cpp reachable at {health.get('url')}"
                    )
            else:
                self._screen_log(
                    "chat",
                    f"startup: llama.cpp unavailable at {health.get('url')}: {health.get('error')}",
                )
        except Exception as exc:
            self._screen_log("chat", f"startup: llama.cpp health check failed: {exc}")

    def timestamp(self) -> str:
        return datetime.now().strftime("%Y%m%d_%H%M%S")

    def _schedule_model_status_refresh(self) -> None:
        asyncio.create_task(self._refresh_model_status_widget())

    def _collect_system_metrics(self) -> dict[str, Any]:
        metrics: dict[str, Any] = {
            "gpus": [],
            "gpu_error": None,
        }

        try:
            proc = subprocess.run(
                [
                    "nvidia-smi",
                    "--query-gpu=name,utilization.gpu,memory.used,memory.total",
                    "--format=csv,noheader,nounits",
                ],
                check=False,
                capture_output=True,
                text=True,
                timeout=2.0,
            )
            if proc.returncode != 0:
                err = (proc.stderr or proc.stdout or "").strip()
                metrics["gpu_error"] = (
                    err.splitlines()[0] if err else "nvidia-smi failed"
                )
                return metrics

            rows = [
                line.strip()
                for line in (proc.stdout or "").splitlines()
                if line.strip()
            ]
            gpus: list[dict[str, Any]] = []
            for row in rows:
                parts = [part.strip() for part in row.split(",")]
                if len(parts) < 4:
                    continue
                try:
                    util = float(parts[1])
                except Exception:
                    util = None
                try:
                    mem_used = float(parts[2])
                except Exception:
                    mem_used = None
                try:
                    mem_total = float(parts[3])
                except Exception:
                    mem_total = None
                gpus.append(
                    {
                        "name": parts[0] or "GPU",
                        "util_percent": util,
                        "mem_used_mib": mem_used,
                        "mem_total_mib": mem_total,
                    }
                )
            metrics["gpus"] = gpus
        except FileNotFoundError:
            metrics["gpu_error"] = "nvidia-smi not installed"
        except Exception as exc:
            metrics["gpu_error"] = str(exc).splitlines()[0]

        return metrics

    def _collect_runtime_snapshot(
        self, endpoint: str
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        try:
            health = self.ollama_client.health(timeout=2.0)
        except Exception as exc:
            health = {"ok": False, "error": str(exc), "url": endpoint, "models": []}
        return health, self._collect_system_metrics()

    async def _refresh_model_status_widget(self) -> None:
        # Entire body is guarded: this runs in an asyncio.create_task which bypasses
        # Textual's run_worker error isolation. An unhandled exception here would
        # propagate through Textual's global exception handler and terminate the session.
        try:
            await self._refresh_model_status_widget_inner()
        except Exception:
            pass

    async def _refresh_model_status_widget_inner(self) -> None:
        llm_cfg = self.config.get("llm", {})
        provider = str(llm_cfg.get("provider") or "ollama")
        model = str(
            llm_cfg.get("model")
            or getattr(self.ollama_client, "model", "")
            or "unknown"
        )
        endpoint = str(
            getattr(self.ollama_client, "base_url", "") or llm_cfg.get("ollama_url", "")
        )
        provider_label = (
            "Local llama.cpp (chat client)"
            if provider == "llamacpp"
            else "Ollama (chat client)"
        )

        health, sys_metrics = await asyncio.to_thread(
            self._collect_runtime_snapshot, endpoint
        )

        # For llama.cpp, get the actually-loaded model from the API.
        if health.get("ok") and provider == "llamacpp":
            api_models = health.get("models") or []
            loaded = api_models[0] if api_models else model
        else:
            loaded = model

        agent_mode = os.environ.get("COCKPIT_AGENT_MODE", "keyword")
        inference = getattr(self, "_last_chat_inference_line", None)
        if inference is None:
            cm_llm = self.config.get("cockpit_llm") or {}
            pol = str(cm_llm.get("hybrid_router_policy") or "")
            api_ok = bool(os.environ.get("ANTHROPIC_API_KEY"))
            inference = (
                f"Last chat inference: (none yet) — policy {pol or '?'}; "
                f"Anthropic API key {'present' if api_ok else 'absent'}"
            )
        lines = [
            f"Chat client: {provider_label}  |  Model runtime: {loaded}",
            inference,
            f"Endpoint: {endpoint}",
            f"Last mode: {self.last_response_mode or 'none'}  |  Agent: {agent_mode}",
        ]

        if health.get("ok"):
            names = (
                health.get("models") if isinstance(health.get("models"), list) else []
            )
            if provider == "ollama" and model and names and model not in names:
                lines.append(
                    f"{provider_label}: reachable — configured model not pulled"
                )
            else:
                lines.append(f"{provider_label}: reachable")
        else:
            lines.append(
                f"{provider_label}: unavailable ({health.get('error') or 'unknown error'})"
            )

        gpus = (
            sys_metrics.get("gpus") if isinstance(sys_metrics.get("gpus"), list) else []
        )
        if gpus:
            preview_lines: list[str] = []
            for gpu in gpus[:2]:
                name = str(gpu.get("name") or "GPU")
                util = gpu.get("util_percent")
                used = gpu.get("mem_used_mib")
                total = gpu.get("mem_total_mib")
                util_txt = f"{float(util):.0f}%" if util is not None else "n/a"
                mem_txt = (
                    f"{float(used):.0f}/{float(total):.0f} MiB"
                    if used is not None and total is not None
                    else "n/a"
                )
                preview_lines.append(f"{name} {util_txt} {mem_txt}")
            if len(gpus) > 2:
                preview_lines.append(f"+{len(gpus) - 2} more GPU(s)")
            lines.append("GPU: " + " | ".join(preview_lines))
        else:
            gpu_error = str(sys_metrics.get("gpu_error") or "").strip()
            lines.append(f"GPU: unavailable ({gpu_error or 'no devices reported'})")

        try:
            screen = self.get_screen("chat")
            panel = screen.query_one("#chat-model-status", Static)
            panel.update("\n".join(lines))
        except Exception:
            pass

    def _screen_log(self, screen_name: str, text: str) -> None:
        try:
            screen = self.get_screen(screen_name)
            self._append_log(screen.query_one("#chat-log", RichLog), text)
        except Exception:
            pass

    @staticmethod
    def _append_log(widget: RichLog, text: str) -> None:
        widget.write(text, scroll_end=True)
        try:
            widget.scroll_end(animate=False)
        except Exception:
            pass

    def _set_chat_live_response(self, text: str) -> None:
        try:
            screen = self.get_screen("chat")
            widget = screen.query_one("#chat-live-response", Static)
        except Exception:
            return

        cleaned = text.rstrip()
        if cleaned:
            widget.update(f"{self.ASSISTANT_NAME}: {cleaned}")
            widget.add_class("-visible")
        else:
            widget.update("")
            widget.remove_class("-visible")

    def launch_chat_message(self, message: str) -> None:
        task = asyncio.create_task(self.handle_chat_message(message))
        self._chat_tasks.add(task)

        def _on_done(done_task: asyncio.Task[None]) -> None:
            self._chat_tasks.discard(done_task)
            try:
                done_task.result()
            except asyncio.CancelledError:
                return
            except Exception as exc:
                self._write_log("chat-log", f"assistant: chat task error: {exc}")

        task.add_done_callback(_on_done)

    def write_report_json(self, rel_path: str, payload: dict[str, Any]) -> str:
        return self.artifacts.write_json(rel_path, payload)

    def write_report_html(self, rel_path: str, content: str) -> str:
        return self.artifacts.write_text(rel_path, content)

    async def handle_chat_message(self, message: str) -> None:
        chat = self.get_screen("chat")
        log = chat.query_one("#chat-log", RichLog)
        status = chat.query_one("#chat-status", Static)
        pending = chat.query_one("#chat-pending")

        if (
            self.chat_inflight
            and message.strip() not in {"/cancel", "/confirm", "/restart backend"}
            and not message.startswith("/run ")
            and not message.startswith("/read ")
        ):
            self._append_log(
                log,
                f"{self.ASSISTANT_NAME}: still thinking about the previous message.",
            )
            return

        message = resolve_pending_action_alias(message, self.pending_action is not None)

        created = datetime.now(timezone.utc).isoformat()
        self.state_store.add_chat_message(self.thread_id, "user", message, created)
        try:
            from rich.text import Text as _Text

            _user_line = _Text()
            _user_line.append("You: ", style="bold cyan")
            _user_line.append(message)
            log.write(_user_line, scroll_end=True)
        except Exception:
            self._append_log(log, f"You: {message}")
        self._set_chat_live_response("")

        if message.strip():
            self._input_history.append(message.strip())
            self._history_idx = len(self._input_history)  # reset index to end

        # Resolve natural language to slash commands (e.g. "add BHP to watchlist" → "/watch add BHP")
        stripped = message.strip()
        derived_cmd = derive_conversational_command(stripped) if stripped else None
        if derived_cmd:
            import logging as _logging

            _logging.getLogger(__name__).debug(
                "conversational command resolved: %s", derived_cmd
            )
            stripped = derived_cmd

        if stripped.startswith("/request-access"):
            scope = stripped[len("/request-access") :].strip().lower()
            now_iso = datetime.now(timezone.utc).isoformat()
            if scope not in {"web", "rag", "dbdiag"}:
                reply = "Usage: /request-access <web|rag|dbdiag>"
                self._append_log(log, f"assistant: {reply}")
                self.state_store.add_chat_message(
                    self.thread_id, "assistant", reply, now_iso
                )
                return
            preview = build_backend_access_proposal_request(
                scope,
                enable=True,
                resume_message=message,
            )
            self.pending_action = build_pending_action_payload(preview, message)
            reply = (
                f"Approve enabling {scope} access with /confirm or cancel with /cancel."
            )
            pending.update(
                f"Pending: __backend_proposal__ args={self.pending_action['args']} (/confirm or /cancel)"
            )
            self._append_log(log, f"assistant: {reply}")
            self.state_store.add_chat_message(
                self.thread_id, "assistant", reply, now_iso
            )
            return

        # Handle /watch commands (from slash input or resolved conversational command)
        if stripped.startswith("/watch "):
            parts = stripped[len("/watch ") :].split(maxsplit=1)
            sub = parts[0].lower() if parts else ""
            arg = parts[1].strip().upper() if len(parts) > 1 else ""
            now_iso = datetime.now(timezone.utc).isoformat()
            if sub == "add" and arg:
                added = self.state_store.add_watch_ticker(arg, now_iso)
                reply = (
                    f"Added {arg} to watchlist."
                    if added
                    else f"{arg} is already on the watchlist."
                )
            elif sub == "remove" and arg:
                removed = self.state_store.remove_watch_ticker(arg)
                reply = (
                    f"Removed {arg} from watchlist."
                    if removed
                    else f"{arg} was not on the watchlist."
                )
            elif sub == "list":
                tickers = self.state_store.list_watch_tickers()
                if tickers:
                    items = ", ".join(t["ticker"] for t in tickers)
                    reply = f"Watchlist ({len(tickers)}): {items}"
                else:
                    reply = "Watchlist is empty."
            elif sub == "clear":
                count = self.state_store.clear_watch_tickers()
                reply = f"Cleared {count} ticker(s) from watchlist."
            elif sub == "scan":
                try:
                    from cockpit.core.watchlist_trigger import WatchlistTrigger
                    from cockpit.core.research.alerts import AlertReader
                    from cockpit.core.strategy import StrategyService

                    strategy_svc = StrategyService(self.state_store)
                    if self._backend_client is None:
                        reply = (
                            "Backend API not configured — cannot run watchlist scan."
                        )
                    else:
                        trigger = WatchlistTrigger(
                            state_store=self.state_store,
                            strategy_service=strategy_svc,
                            backend_api_client=self._backend_client,
                            alert_reader=AlertReader(),
                            dossier_service=getattr(
                                self.chat_controller, "_dossier_service", None
                            ),
                        )
                        ticker_list: list[str] | None = None
                        if arg:
                            ticker_list = [
                                t.strip() for t in arg.split(",") if t.strip()
                            ]
                        summary = trigger.run(tickers=ticker_list)
                        lines = [
                            f"Watchlist scan complete: {summary.tickers_scanned} ticker(s), "
                            f"{summary.total_alerts} alert(s), {summary.total_errors} error(s)."
                        ]
                        for r in summary.results:
                            status = "ok" if r.analysis_ok else "no analysis"
                            alerts_str = (
                                f"{r.alerts_generated} alert(s)"
                                if r.alerts_generated
                                else "clean"
                            )
                            err_str = f" [{', '.join(r.errors)}]" if r.errors else ""
                            lines.append(
                                f"  {r.ticker}: {status}, {alerts_str}{err_str}"
                            )
                        reply = "\n".join(lines)
                except Exception as exc:
                    reply = f"Watchlist scan failed: {exc}"
            else:
                reply = "Usage: /watch add|remove|list|clear|scan [TICKER]"
            self._append_log(log, f"assistant: {reply}")
            self.state_store.add_chat_message(
                self.thread_id, "assistant", reply, now_iso
            )
            return

        # Handle /review commands for transcript approval gate
        if stripped.startswith("/review"):
            parts = stripped[len("/review") :].strip().split(maxsplit=1)
            sub = parts[0].lower() if parts else "list"
            arg = parts[1].strip() if len(parts) > 1 else ""
            now_iso = datetime.now(timezone.utc).isoformat()
            reply = self._handle_review_command(sub, arg, log)
            self._append_log(log, f"assistant: {reply}")
            self.state_store.add_chat_message(
                self.thread_id, "assistant", reply, now_iso
            )
            return

        # Handle /strategy commands
        if stripped.startswith("/strategy"):
            from cockpit.core.strategy import StrategyService

            strategy_svc = StrategyService(self.state_store)
            parts = stripped[len("/strategy") :].strip().split(maxsplit=2)
            sub = parts[0].lower() if parts else "list"
            arg1 = parts[1] if len(parts) > 1 else ""
            arg2 = parts[2] if len(parts) > 2 else ""
            now_iso = datetime.now(timezone.utc).isoformat()

            if sub == "list":
                # /strategy list OR /strategy list <TICKER>
                if arg1 and arg1.upper().isalpha() and 2 <= len(arg1) <= 5:
                    tkr = arg1.upper()
                    gcriteria = strategy_svc.get_global()
                    tcriteria = strategy_svc.get_ticker(tkr)
                    decision = strategy_svc.get_decision(tkr)
                    lines = []
                    if gcriteria:
                        lines.append(f"Global criteria ({len(gcriteria)}):")
                        for c in gcriteria:
                            lines.append(
                                f"  [{c['id']}] {c['criterion']} ({c['category']}, P{c['priority']})"
                            )
                    if tcriteria:
                        lines.append(f"\n{tkr}-specific criteria ({len(tcriteria)}):")
                        for c in tcriteria:
                            dec = (
                                f" [decision: {c['decision']}]"
                                if c.get("decision")
                                else ""
                            )
                            lines.append(
                                f"  [{c['id']}] {c['criterion']} ({c['category']}, P{c['priority']}){dec}"
                            )
                    if decision and decision.get("decision_rationale"):
                        lines.append(
                            f"\nDecision: {decision['decision']} — {decision['decision_rationale']}"
                        )
                    reply = (
                        "\n".join(lines)
                        if lines
                        else f"No strategy criteria defined for {tkr}."
                    )
                else:
                    gcriteria = strategy_svc.get_global()
                    if gcriteria:
                        lines = [f"Global criteria ({len(gcriteria)}):"]
                        for c in gcriteria:
                            lines.append(
                                f"  [{c['id']}] {c['criterion']} ({c['category']}, P{c['priority']})"
                            )
                        reply = "\n".join(lines)
                    else:
                        reply = "No global strategy criteria defined. Use /strategy add <criterion> to add one."
            elif sub == "add":
                # /strategy add <TICKER> <criterion> OR /strategy add <criterion>
                if arg1 and arg1.upper().isalpha() and 2 <= len(arg1) <= 5 and arg2:
                    result = strategy_svc.add_ticker(arg1.upper(), arg2)
                    reply = f"Added {arg1.upper()} criterion [{result['id']}]: {arg2}"
                elif arg1:
                    full_criterion = (arg1 + " " + arg2).strip() if arg2 else arg1
                    result = strategy_svc.add_global(full_criterion)
                    reply = f"Added global criterion [{result['id']}]: {full_criterion}"
                else:
                    reply = "Usage: /strategy add [TICKER] <criterion>"
            elif sub == "decide":
                # /strategy decide <TICKER> <buy|watchlist|avoid> <rationale>
                if arg1 and arg2:
                    dec_parts = arg2.split(maxsplit=1)
                    decision_val = dec_parts[0].lower() if dec_parts else ""
                    rationale = dec_parts[1] if len(dec_parts) > 1 else ""
                    if decision_val in ("buy", "watchlist", "avoid"):
                        result = strategy_svc.record_decision(
                            arg1.upper(), decision_val, rationale
                        )
                        reply = (
                            f"Recorded decision for {arg1.upper()}: {decision_val}"
                            + (f" — {rationale}" if rationale else "")
                        )
                    else:
                        reply = "Decision must be one of: buy, watchlist, avoid"
                else:
                    reply = "Usage: /strategy decide <TICKER> <buy|watchlist|avoid> <rationale>"
            elif sub == "delete":
                if arg1 and arg1.isdigit():
                    deleted = strategy_svc.delete(int(arg1))
                    reply = (
                        f"Deleted criterion [{arg1}]."
                        if deleted
                        else f"Criterion [{arg1}] not found."
                    )
                else:
                    reply = "Usage: /strategy delete <id>"
            else:
                reply = "Usage: /strategy list|add|decide|delete [TICKER] [criterion]"
            self._append_log(log, f"assistant: {reply}")
            self.state_store.add_chat_message(
                self.thread_id, "assistant", reply, now_iso
            )
            return

        # Handle /sources commands
        if stripped.startswith("/sources"):
            parts = stripped[len("/sources") :].strip().split(maxsplit=1)
            sub = parts[0].lower() if parts else ""
            arg = parts[1].strip() if len(parts) > 1 else ""
            now_iso = datetime.now(timezone.utc).isoformat()
            if sub == "on":
                self.state_store.set_preference("show_sources", "true")
                reply = "Sources display enabled."
            elif sub == "off":
                self.state_store.set_preference("show_sources", "false")
                reply = "Sources display disabled."
            elif sub == "list":
                footer = SourcesFormatter.format_list(self._latest_sources_payloads)
                if footer:
                    reply = footer
                else:
                    reply = "No sources available for inspection. Ask a question first."
            elif sub == "show":
                index = self._parse_positive_int(arg)
                if index is None:
                    reply = "Usage: /sources show <n>"
                else:
                    reply = SourcesFormatter.format_show(
                        self._latest_sources_payloads, index=index
                    )
                    if not reply:
                        reply = (
                            "No sources available for inspection. Ask a question first."
                        )
            else:
                current = self.state_store.get_preference("show_sources", "true")
                reply = f"Sources display: {'ON' if current == 'true' else 'OFF'}. Use /sources on|off to toggle."
            self._append_log(log, f"assistant: {reply}")
            self.state_store.add_chat_message(
                self.thread_id, "assistant", reply, now_iso
            )
            return

        # Handle /rag on|off
        if stripped.startswith("/rag"):
            sub = stripped[len("/rag") :].strip().lower()
            now_iso = datetime.now(timezone.utc).isoformat()
            if sub == "on":
                reply = self._apply_backend_access_proposal("enable_rag_access")
            elif sub == "off":
                reply = self._apply_backend_access_proposal("disable_rag_access")
            else:
                enabled = self._access_state().get("rag_enabled", False)
                reply = f"RAG retrieval: {'ON' if enabled else 'OFF'}. Use /rag on|off to toggle."
            self._append_log(log, f"assistant: {reply}")
            self.state_store.add_chat_message(
                self.thread_id, "assistant", reply, now_iso
            )
            return

        # Handle /web on|off
        if stripped.startswith("/web"):
            sub = stripped[len("/web") :].strip().lower()
            now_iso = datetime.now(timezone.utc).isoformat()
            if sub == "on":
                reply = self._apply_backend_access_proposal("enable_web_access")
            elif sub == "off":
                reply = self._apply_backend_access_proposal("disable_web_access")
            else:
                enabled = self._access_state().get("web_enabled", False)
                reply = f"Web search: {'ON' if enabled else 'OFF'}. Use /web on|off to toggle."
            self._append_log(log, f"assistant: {reply}")
            self.state_store.add_chat_message(
                self.thread_id, "assistant", reply, now_iso
            )
            return

        if stripped.startswith("/dbdiag"):
            sub = stripped[len("/dbdiag") :].strip().lower()
            now_iso = datetime.now(timezone.utc).isoformat()
            if sub == "on":
                reply = self._apply_backend_access_proposal("enable_dbdiag_access")
            elif sub == "off":
                reply = self._apply_backend_access_proposal("disable_dbdiag_access")
            else:
                enabled = self._access_state().get("db_diagnostic_query_enabled", False)
                reply = f"DB diagnostics: {'ON' if enabled else 'OFF'}. Use /dbdiag on|off to toggle."
            self._append_log(log, f"assistant: {reply}")
            self.state_store.add_chat_message(
                self.thread_id, "assistant", reply, now_iso
            )
            return

        # Handle /health — check backend API health
        if stripped == "/health":
            now_iso = datetime.now(timezone.utc).isoformat()
            if self._backend_client is None:
                reply = "Backend API not configured (no api_base_url)."
            else:
                try:
                    health = self._backend_client.health(timeout=5.0)
                    capabilities = self._backend_client.capabilities(timeout=5.0)
                    payload = {"health": health, "capabilities": capabilities}
                    reply = f"Backend health: {json.dumps(payload, indent=2)}"
                except Exception as exc:
                    reply = f"Backend health check failed: {exc}"
            self._append_log(log, f"assistant: {reply}")
            self.state_store.add_chat_message(
                self.thread_id, "assistant", reply, now_iso
            )
            return

        # Handle /access — show current access/connection info
        if stripped == "/access":
            now_iso = datetime.now(timezone.utc).isoformat()
            lines = ["Access configuration:"]
            lines.append(
                f"  Backend API: {self._backend_client.base_url if self._backend_client else 'not configured'}"
            )
            lines.append(f"  LLM: {self.ollama_client.base_url}")
            lines.append(f"  State DB: {self.state_store.db_path}")
            access_state = self._access_state()
            lines.append(
                f"  Web: {'enabled' if access_state['web_enabled'] else 'disabled'}"
            )
            lines.append(
                f"  RAG: {'enabled' if access_state['rag_enabled'] else 'disabled'}"
            )
            lines.append(
                f"  DB diagnostics: {'enabled' if access_state['db_diagnostic_query_enabled'] else 'disabled'}"
            )
            if self._backend_client is not None:
                capabilities = self._backend_client.capabilities(timeout=5.0)
                if capabilities.get("ok"):
                    payload = capabilities.get("payload") or {}
                    features = payload.get("features") or {}
                    lines.append("  Backend capabilities:")
                    for key in ("ingestion", "extraction", "embeddings", "rag"):
                        item = features.get(key) or {}
                        status = str(item.get("status") or "unknown")
                        blockers = ", ".join(item.get("blockers") or [])
                        suffix = f" ({blockers})" if blockers else ""
                        lines.append(f"    {key}: {status}{suffix}")
                else:
                    lines.append(
                        f"  Backend capabilities: unavailable ({capabilities.get('error', 'unknown error')})"
                    )
            reply = "\n".join(lines)
            self._append_log(log, f"assistant: {reply}")
            self.state_store.add_chat_message(
                self.thread_id, "assistant", reply, now_iso
            )
            return

        # Handle /reconnect — re-probe all services and re-wire failed clients
        if stripped == "/reconnect":
            now_iso = datetime.now(timezone.utc).isoformat()
            self._append_log(log, "assistant: Reconnecting services...")
            results: list[str] = []

            # 1. Re-probe llama.cpp
            try:
                llm_health = self.ollama_client.health(timeout=5.0)
                if llm_health.get("ok"):
                    results.append(
                        f"  + llama.cpp: reachable at {llm_health.get('url')}"
                    )
                else:
                    results.append(f"  - llama.cpp: {llm_health.get('error')}")
            except Exception as exc:
                results.append(f"  - llama.cpp: {exc}")

            # 2. Re-probe / re-create backend client
            backend_cfg = self.config.get("backend") or {}
            backend_url = str(backend_cfg.get("api_base_url") or "").strip()
            if backend_url:
                if self._backend_client is None:
                    self._backend_client = BackendApiClient(
                        backend_url,
                        api_key=str(backend_cfg.get("api_key") or "").strip(),
                    )
                    self.tool_router.backend_api_client = self._backend_client
                    results.append(f"  + Backend API: created client for {backend_url}")
                try:
                    bh = self._backend_client.health(timeout=5.0)
                    if bh.get("ok"):
                        results.append(
                            f"  + Backend API: reachable at {self._backend_client.base_url}"
                        )
                    else:
                        results.append(f"  - Backend API: {bh.get('error')}")
                except Exception as exc:
                    results.append(f"  - Backend API: {exc}")
            else:
                results.append("  - Backend API: no api_base_url configured")

            # 3. Re-attempt Anthropic client if missing
            chat_ctrl = getattr(self, "chat_controller", None)
            hybrid_router = (
                getattr(chat_ctrl, "_hybrid_router", None) if chat_ctrl else None
            )
            if hybrid_router and hybrid_router._api is None:
                import os as _os

                if _os.environ.get("ANTHROPIC_API_KEY"):
                    try:
                        from cockpit.core.agent.anthropic_client import AnthropicClient

                        hybrid_router._api = AnthropicClient()
                        results.append(
                            "  + Claude API: connected (was missing, now initialized)"
                        )
                    except Exception as exc:
                        results.append(f"  - Claude API: init failed: {exc}")
                else:
                    results.append("  - Claude API: ANTHROPIC_API_KEY not set")
            elif hybrid_router and hybrid_router._api is not None:
                results.append("  + Claude API: already connected")
            else:
                results.append("  - Claude API: HybridRouter not initialized")

            reply = "Reconnect results:\n" + "\n".join(results)
            self._append_log(log, f"assistant: {reply}")
            self.state_store.add_chat_message(
                self.thread_id, "assistant", reply, now_iso
            )
            return

        # Handle /prompt — show the last assembled system instruction
        if stripped == "/prompt":
            now_iso = datetime.now(timezone.utc).isoformat()
            try:
                prompt = self.chat_controller._build_system_instruction(
                    mode=self.last_response_mode or "chat",
                    ticker=self.last_detected_ticker,
                    local_payload={},
                )
                reply = f"Current system prompt:\n{prompt}"
            except Exception as exc:
                reply = f"Could not build prompt: {exc}"
            self._append_log(log, f"assistant: {reply}")
            self.state_store.add_chat_message(
                self.thread_id, "assistant", reply, now_iso
            )
            return

        if message.strip() == "/cancel":
            self.pending_action = None
            pending.update("No pending action")
            self._append_log(log, "assistant: Pending action canceled.")
            self.state_store.add_chat_message(
                self.thread_id,
                "assistant",
                "Pending action canceled.",
                datetime.now(timezone.utc).isoformat(),
            )
            return

        if message.strip() == "/confirm":
            # Race-condition guard: if the user types /confirm while the
            # previous chat response is still being processed, pending_action
            # may not have been stored yet.  Wait for the inflight task to
            # populate it (pending_action is now set inside the try block,
            # before chat_inflight is cleared, so this loop exits quickly).
            if not self.pending_action and self.chat_inflight:
                for _ in range(100):  # up to ~10 s
                    await asyncio.sleep(0.1)
                    if self.pending_action or not self.chat_inflight:
                        break
            if not self.pending_action:
                self._append_log(log, "assistant: No pending action.")
                return
            action = self.pending_action
            self.pending_action = None
            pending.update("No pending action")
            if await self._execute_internal_action(action, "chat-log"):
                return
            await self.execute_action(
                action["action_id"],
                action["args"],
                log_target="chat-log",
                skip_confirm=True,
            )
            return

        if message.startswith("/run "):
            parts = message[5:].split(maxsplit=1)
            action_id = parts[0]
            args = self.action_registry.parse_kv_args(
                parts[1] if len(parts) > 1 else ""
            )
            await self.execute_action(action_id, args, log_target="chat-log")
            return

        if message.startswith("/read "):
            raw = message[len("/read ") :].strip()
            max_chars = 16000
            if " max_chars=" in raw:
                head, tail = raw.rsplit(" max_chars=", 1)
                raw = head.strip()
                try:
                    max_chars = max(1000, min(100000, int(tail.strip())))
                except Exception:
                    max_chars = 16000
            result = self.file_indexer.read_file(raw, max_chars=max_chars)
            if not result.get("ok"):
                text = f"assistant: /read failed: {result.get('error')}"
                self._append_log(log, text)
                self.state_store.add_chat_message(
                    self.thread_id,
                    "assistant",
                    text,
                    datetime.now(timezone.utc).isoformat(),
                )
                return

            snippet = (
                f"assistant: Loaded {result['path']} "
                f"(returned {result['chars_returned']} chars"
                f"{', truncated' if result['truncated'] else ''}).\n"
                f"{result['content']}"
            )
            self._append_log(log, snippet[:max_chars])
            self.state_store.add_chat_message(
                self.thread_id,
                "assistant",
                f"/read loaded {result['path']} ({result['chars_returned']} chars)",
                datetime.now(timezone.utc).isoformat(),
            )
            return

        if message.startswith("/prefer "):
            rest = message[len("/prefer ") :].strip()
            if "=" in rest:
                key, _, value = rest.partition("=")
                self.state_store.set_preference(key.strip(), value.strip())
                self._append_log(
                    log, f"assistant: Preference saved: {key.strip()} = {value.strip()}"
                )
            else:
                prefs = self.state_store.get_preferences()
                if prefs:
                    self._append_log(
                        log,
                        "assistant: Current preferences:\n"
                        + "\n".join(f"  {k} = {v}" for k, v in prefs.items()),
                    )
                else:
                    self._append_log(
                        log,
                        "assistant: No preferences set. Use /prefer key=value to set one.",
                    )
            return

        if message.strip() == "/restart backend":
            self._append_log(log, "Restarting backend…")
            try:
                await asyncio.to_thread(restart_backend, self.repo_root)
                self._append_log(log, "Backend restarted successfully.")
            except Exception as exc:
                self._append_log(log, f"Restart failed: {exc}")
            return

        spinner_frames = ["|", "/", "-", "\\"]
        stream_state = {"text": "", "last_flush": 0.0}
        action_id = self.chat_controller.detect_action_intent(message)
        if action_id:
            provisional_mode = "action"
        else:
            provisional_mode = self.chat_controller.classify_request(
                message,
                enable_web=self.config["web"].get("enabled_default", False),
            ).value
        thinking_prefix = f"{self.ASSISTANT_NAME} (thinking)"

        async def _spinner() -> None:
            idx = 0
            while self.chat_inflight:
                status.update(
                    f"{thinking_prefix} {spinner_frames[idx % len(spinner_frames)]}"
                )
                idx += 1
                await asyncio.sleep(0.12)

        def _on_chunk(chunk: str) -> None:
            if not chunk:
                return
            stream_state["text"] += chunk
            now = time.monotonic()
            if now - float(stream_state["last_flush"]) < 0.03 and "\n" not in chunk:
                return
            stream_state["last_flush"] = now
            try:
                self.call_from_thread(
                    self._set_chat_live_response, stream_state["text"]
                )
            except Exception:
                pass

        try:
            self.chat_inflight = True
            status.update(f"{thinking_prefix} |")
            spinner_task = asyncio.create_task(_spinner())
            _deep = provisional_mode == "deep_analysis"
            _analysis_mode_kw = {"analysis_mode": "deep"} if _deep else {}

            def _build_response():
                try:
                    return self.chat_controller.build_chat_response(
                        message,
                        self.config["web"].get("enabled_default", False),
                        self.last_detected_ticker,
                        on_chunk=_on_chunk,
                        **_analysis_mode_kw,
                    )
                except TypeError as exc:
                    exc_str = str(exc)
                    if "on_chunk" not in exc_str and "analysis_mode" not in exc_str:
                        raise
                    # analysis_mode not accepted — retry with on_chunk but no analysis_mode
                    if _analysis_mode_kw and "analysis_mode" in exc_str:
                        try:
                            return self.chat_controller.build_chat_response(
                                message,
                                self.config["web"].get("enabled_default", False),
                                self.last_detected_ticker,
                                on_chunk=_on_chunk,
                            )
                        except TypeError:
                            pass
                    # on_chunk not accepted — bare call (oldest signature)
                    return self.chat_controller.build_chat_response(
                        message,
                        self.config["web"].get("enabled_default", False),
                        self.last_detected_ticker,
                    )

            response = await asyncio.to_thread(_build_response)
            # Store pending_action immediately so /confirm can find it even
            # if it arrives before the finally block clears chat_inflight.
            if response.action_preview:
                self.pending_action = build_pending_action_payload(
                    response.action_preview, message
                )
        except Exception as exc:
            self.chat_inflight = False
            status.update("")
            partial = stream_state["text"].strip()
            if partial:
                self._append_log(log, f"assistant: {partial}")
                self.state_store.add_chat_message(
                    self.thread_id,
                    "assistant",
                    partial,
                    datetime.now(timezone.utc).isoformat(),
                )
            self._set_chat_live_response("")
            err_str = str(exc)
            # Provide user-friendly messages for common infrastructure errors
            # rather than showing raw exception text.
            if "ConnectError" in err_str or "connection refused" in err_str.lower():
                err = f"assistant: LLM server unreachable — connection refused. Check that llama-server is running."
            elif "unavailable" in err_str.lower() and "llama" in err_str.lower():
                err = f"assistant: LLM server unavailable. {err_str}"
            elif "TimeoutException" in err_str or "timed out" in err_str.lower():
                err = f"assistant: LLM request timed out. The model may be overloaded or unresponsive."
            else:
                err = f"assistant: chat error: {exc}"
            self._append_log(log, err)
            self.state_store.add_chat_message(
                self.thread_id, "assistant", err, datetime.now(timezone.utc).isoformat()
            )
            return
        finally:
            self.chat_inflight = False
            spinner_task = locals().get("spinner_task")
            if isinstance(spinner_task, asyncio.Task) and not spinner_task.done():
                spinner_task.cancel()
                try:
                    await spinner_task
                except asyncio.CancelledError:
                    pass
            status.update("")

        assistant_text = (response.text or stream_state["text"]).strip()
        self._set_chat_live_response("")
        self.last_response_mode = str(response.mode or provisional_mode)

        try:
            ticker = extract_ticker_from_payload(
                {
                    "evidence": response.evidence,
                    "actions_taken": [response.action_preview]
                    if response.action_preview
                    else [],
                    "action_preview": response.action_preview,
                }
            )
            if ticker:
                self.last_detected_ticker = ticker
        except Exception:
            pass

        try:
            self.query_one("#chat-ticker-context", Static).update(
                f"Context: {self.last_detected_ticker}"
                if self.last_detected_ticker
                else ""
            )
        except Exception:
            pass

        try:
            from rich.markdown import Markdown as _Markdown

            log.write(
                _Markdown(f"**{self.ASSISTANT_NAME}:** {assistant_text}"),
                scroll_end=True,
            )
        except Exception:
            self._append_log(log, f"assistant: {assistant_text}")

        # Append sources footer for analysis responses
        try:
            sources_data = SourcesFormatter.collect_sources_payloads(response.evidence)
            self._latest_sources_payloads = sources_data
            if sources_data:
                show = self.state_store.get_preference("show_sources", "true") == "true"
                footer = SourcesFormatter.format_footer(sources_data, show_sources=show)
                if footer:
                    self._append_log(log, footer)
        except Exception:
            pass  # sources footer is best-effort

        # Append routing metadata footer (which backend answered)
        try:
            if response.routing_metadata:
                meta = response.routing_metadata
                if meta.get("source") == "api":
                    src = "Anthropic Claude (cloud API)"
                    self._last_chat_inference_line = f"Last chat inference: Anthropic Claude (cloud) — model {meta.get('model', '?')}"
                else:
                    src = "Local llama.cpp"
                    self._last_chat_inference_line = f"Last chat inference: local llama.cpp — model {meta.get('model', '?')}"
                cost_raw = meta.get("cost_usd")
                cost_str = f"${float(cost_raw):.4f}" if cost_raw is not None else "free"
                self._append_log(
                    log,
                    f"  [Inference: {src} | {meta.get('model', '?')} | {meta.get('latency_ms', '?')}ms | {cost_str}]",
                )
                asyncio.create_task(self._refresh_model_status_widget())
        except Exception:
            pass  # routing footer is best-effort

        # Agent tool call trace (failures by default; full trace with COCKPIT_TOOL_DEBUG=1)
        try:
            traces = getattr(response, "tool_traces", None) or []
            if traces:
                show_failures, show_full = cockpit_tool_chat_debug_mode()
                if show_full:
                    block = format_failure_block(traces, include_success=True)
                elif show_failures and any(not t.get("ok") for t in traces):
                    block = format_failure_block(traces, include_success=False)
                else:
                    block = ""
                if block:
                    self._append_log(log, block)
        except Exception:
            pass

        self.state_store.add_chat_message(
            self.thread_id,
            "assistant",
            assistant_text,
            datetime.now(timezone.utc).isoformat(),
        )

        if response.action_preview:
            # pending_action was already set in the try block above (before
            # chat_inflight was cleared) so that a fast /confirm can find it
            # immediately.  If /confirm already consumed it, don't re-set.
            if self.pending_action is not None:
                ap = response.action_preview
                aid = ap.get("action_id") if isinstance(ap, dict) else None
                aargs = None
                if isinstance(ap, dict):
                    aargs = ap.get("args")
                    if aargs is None:
                        aargs = ap.get("arguments")
                pending.update(f"Pending: {aid} args={aargs} (/confirm or /cancel)")

            # Candlestick chart — generate HTML dashboard immediately.
            if response.action_preview.get("action_id") == "show_candlestick":
                try:
                    chart_args = response.action_preview.get("args") or {}
                    chart_ticker = str(
                        chart_args.get("ticker")
                        or self.last_detected_ticker
                        or "UNKNOWN"
                    )
                    bundle = self.tool_router.get_price_context_for_window(
                        chart_ticker,
                        range_="1y",
                        interval=str(chart_args.get("timeframe") or "1d"),
                        max_history_rows=260,
                    )
                    price = bundle.get("price") if isinstance(bundle, dict) else {}
                    price = price if isinstance(price, dict) else {}
                    dashboard_payload = {
                        "ticker": chart_ticker,
                        "window": "1y",
                        "price_state": bundle.get("price_state", {}),
                        "recent_history": price.get("recent_history", []),
                        "generated_at": datetime.now(timezone.utc).isoformat(),
                    }
                    html = build_candlestick_dashboard_html(dashboard_payload)
                    ts = self.timestamp()
                    chart_path = self.write_report_html(
                        f"reports/cockpit/{chart_ticker}_{ts}_candlestick_dashboard.html",
                        html,
                    )
                    self.last_chart_path = chart_path
                    self._append_log(
                        log, f"assistant: Chart dashboard written: {chart_path}"
                    )
                    self.pending_action = (
                        None  # chart already generated; no subprocess needed
                    )
                except Exception as exc:
                    self._append_log(log, f"assistant: chart generation error: {exc}")

        tool_traces = getattr(response, "tool_traces", None) or []
        failed_tool_traces = [
            trace
            for trace in tool_traces
            if isinstance(trace, dict) and not bool(trace.get("ok", True))
        ]

        export_payload = {
            "question": message,
            "answer": assistant_text,
            "response_mode": response.mode,
            "evidence": response.evidence,
            "actions_taken": [response.action_preview]
            if response.action_preview
            else [],
            "tool_traces": tool_traces,
            "tool_failures": failed_tool_traces,
            "sources": ["local_context"],
            "routing": response.routing_metadata,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        md_path, json_path = self.artifacts.write_analysis(
            self.thread_id, message, assistant_text, export_payload
        )
        self.state_store.add_export(
            self.thread_id,
            message,
            md_path,
            json_path,
            datetime.now(timezone.utc).isoformat(),
        )

    async def execute_action(
        self,
        action_id: str,
        args: dict[str, Any],
        log_target: str,
        skip_confirm: bool = False,
    ) -> None:
        if self.active_job_task and not self.active_job_task.done():
            self._write_log(
                log_target,
                f"Action already running (job_id={self.active_job_id or 'unknown'}). Kill it first.",
            )
            return

        try:
            spec = self.action_registry.get(action_id)
        except KeyError as exc:
            self._write_log(log_target, f"Unknown action: {action_id}")
            self._write_log(log_target, f"Error: {exc}")
            return
        if self.read_only and spec.is_mutating:
            self._write_log(log_target, "read-only mode: mutating action blocked")
            return

        try:
            preview = self.action_registry.preview(action_id, args)
        except ValueError as exc:
            remediation = build_backend_runtime_remediation_request(
                self._backend_client,
                action_id=action_id,
                args=args,
                error_message=str(exc),
            )
            if remediation is not None:
                self.pending_action = remediation
                self._write_log(log_target, f"⚠ {exc}")
                self._write_log(
                    log_target,
                    "Approve backend remediation with /confirm to recover and resume the requested action.",
                )
                return
            self._write_log(log_target, f"⚠ {exc}")
            return

        if spec.requires_confirmation and not skip_confirm:
            confirmed = await self._confirm_action(
                {
                    "action_id": action_id,
                    "command": preview.command,
                    "impact": preview.estimated_impact,
                    "timeout_seconds": preview.timeout_seconds,
                }
            )
            if not confirmed:
                self._write_log(log_target, "Action cancelled")
                return

        job = JobRun(
            job_id=uuid.uuid4().hex,
            action_id=action_id,
            args=args,
            started_at=datetime.now(timezone.utc),
            status="queued",
        )
        self.state_store.add_job(
            {
                "job_id": job.job_id,
                "action_id": job.action_id,
                "args": job.args,
                "started_at": job.started_at.isoformat(),
                "ended_at": None,
                "status": job.status,
                "exit_code": None,
                "stdout_path": None,
                "stderr_path": None,
                "artifacts": [],
            }
        )

        if preview.guard_message:
            self._write_log(log_target, f"Guard: {preview.guard_message}")
        self._write_log(log_target, f"Executing: {' '.join(preview.command)}")
        self._write_log(log_target, f"Job queued: {job.job_id}")
        self.active_job_id = job.job_id
        self.active_log_target = log_target
        last_ticker: str | None = None
        last_day: str | None = None
        last_critical_line: str | None = None

        def _emit(line: str) -> None:
            # _emit is always called from within the asyncio event loop (via _pump in
            # job_runner), so direct calls to _write_log are safe — no thread-hopping needed.
            nonlocal last_ticker, last_day, last_critical_line
            self._write_log(log_target, line)

            # Capture CRITICAL lines (e.g. circuit breaker) so the completion
            # summary can surface the failure reason without the user scrolling.
            if "CRITICAL" in line:
                last_critical_line = line

            ticker_match = re.search(
                r"\[(?:backfill|probe)\]\s+([A-Z0-9.]+)\s+attempt\s+\d+", line
            )
            if ticker_match:
                ticker = ticker_match.group(1)
                if ticker != last_ticker:
                    last_ticker = ticker
                    self._write_log(log_target, f"[progress] ingesting ticker={ticker}")

            day_match = re.search(
                r"\[asx_sweep\]\s+date=([0-9]{4}-[0-9]{2}-[0-9]{2})", line
            )
            if day_match:
                day = day_match.group(1)
                if day != last_day:
                    last_day = day
                    self._write_log(log_target, f"[progress] sweep_day={day}")

        async def _run_and_finalize() -> None:
            try:
                self._write_log(log_target, f"Job started: {job.job_id}")
                run_result = await self.job_runner.run(
                    job=job,
                    command=preview.command,
                    timeout_seconds=preview.timeout_seconds,
                    on_output=_emit,
                )

                self.state_store.add_job(
                    {
                        "job_id": run_result.job_id,
                        "action_id": run_result.action_id,
                        "args": run_result.args,
                        "started_at": run_result.started_at.isoformat(),
                        "ended_at": run_result.ended_at.isoformat()
                        if run_result.ended_at
                        else None,
                        "status": run_result.status,
                        "exit_code": run_result.exit_code,
                        "stdout_path": run_result.stdout_path,
                        "stderr_path": run_result.stderr_path,
                        "artifacts": run_result.artifacts,
                    }
                )
                self._write_log(
                    log_target,
                    f"Completed with status={run_result.status} exit={run_result.exit_code}",
                )
                if run_result.status == "failed":
                    # Surface the most important failure context so the user
                    # doesn't have to scroll through the full log.
                    if last_critical_line:
                        # Strip the [out]/[err] prefix that _pump adds.
                        clean = re.sub(r"^\[(out|err)\]\s*", "", last_critical_line)
                        self._write_log(log_target, f"⚠ {clean}")
                    elif run_result.stderr_path:
                        # Show last meaningful stderr lines as failure context.
                        try:
                            tail_lines = (
                                Path(run_result.stderr_path)
                                .read_text()
                                .strip()
                                .splitlines()[-5:]
                            )
                            if tail_lines:
                                self._write_log(log_target, "⚠ Last stderr output:")
                                for tl in tail_lines:
                                    self._write_log(log_target, f"  {tl}")
                        except Exception:
                            pass
            except Exception as exc:
                self._write_log(log_target, f"Action runner error: {exc}")
            finally:
                self.active_job_id = None
                self.active_job_task = None

        self.active_job_task = asyncio.create_task(_run_and_finalize())

    async def cancel_active_action(self, log_target: str) -> None:
        if not self.active_job_task or self.active_job_task.done():
            self._write_log(log_target, "No running action to cancel.")
            self.active_job_task = None
            self.active_job_id = None
            return

        status = await self.job_runner.cancel_active()
        self._write_log(
            log_target,
            f"Cancel request sent: {status} (job_id={self.active_job_id or 'unknown'})",
        )

    async def _confirm_action(self, preview: dict[str, Any]) -> bool:
        # Avoid push_screen_wait (requires worker context). Resolve a Future directly
        # from modal button handlers so confirm/cancel is deterministic in UI events.
        loop = asyncio.get_running_loop()
        future: asyncio.Future[bool] = loop.create_future()

        def _on_result(value: bool | None) -> None:
            if not future.done():
                future.set_result(bool(value))

        self.push_screen(ConfirmActionScreen(preview=preview, on_decision=_on_result))
        try:
            return await asyncio.wait_for(future, timeout=3600)
        except asyncio.TimeoutError:
            return False

    def _handle_review_command(self, sub: str, arg: str, log) -> str:
        """Handle /review subcommands — backend API when configured, local service otherwise."""
        if self._backend_client:
            return self._handle_review_via_backend(sub, arg, log)
        return self._handle_review_via_local(sub, arg, log)

    def _handle_review_via_backend(self, sub: str, arg: str, log) -> str:
        """Route /review commands through backend commentary API."""
        client = self._backend_client
        if sub == "list" or not sub:
            try:
                resp = client.get_pending_transcripts()
                pending_items = resp.get("pending", [])
            except Exception as exc:
                return f"Failed to list pending transcripts: {exc}"
            if pending_items:
                lines = [f"Pending review ({len(pending_items)} items):"]
                for i, item in enumerate(pending_items, 1):
                    sid = item.get("source_id", "?")
                    stype = item.get("source_type", "?")
                    title = item.get("title", "?")[:40]
                    chunks = item.get("chunk_count", 0)
                    staged = item.get("staged_at", "")[:10]
                    lines.append(
                        f"  [{i}] {sid} | {stype} | {title} | staged {staged} | {chunks} chunks"
                    )
                lines.append(
                    "Use: /review approve <source_id> or /review reject <source_id>"
                )
                return "\n".join(lines)
            return "No pending transcripts to review."
        if sub == "approve" and arg:
            self._append_log(log, f"assistant: Indexing chunks for {arg}...")
            try:
                result = client.approve_transcript(arg)
                n = result.get("points_upserted", 0)
                return f"Approved and indexed {n} chunks for {arg}."
            except Exception as exc:
                return f"Approve failed: {exc}"
        if sub == "reject" and arg:
            try:
                client.reject_transcript(arg)
                return f"Rejected and purged staged chunks for {arg}."
            except Exception as exc:
                return f"Reject failed: {exc}"
        if sub == "approve-all":
            try:
                resp = client.get_pending_transcripts()
                pending_items = resp.get("pending", [])
            except Exception as exc:
                return f"Failed to list pending transcripts: {exc}"
            if not pending_items:
                return "No pending transcripts to approve."
            total = 0
            for item in pending_items:
                try:
                    result = client.approve_transcript(item["source_id"])
                    total += result.get("points_upserted", 0)
                except Exception:
                    pass
            return f"Approved {len(pending_items)} source(s), indexed {total} chunks."
        if sub == "expired":
            try:
                result = client.purge_expired_transcripts()
                purged = result.get("purged", [])
                return (
                    f"Purged {len(purged)} expired staged source(s)."
                    if purged
                    else "No expired items."
                )
            except Exception as exc:
                return f"Purge failed: {exc}"
        return "Usage: /review list|approve|reject|approve-all|expired [source_id]"

    def _handle_review_via_local(self, sub: str, arg: str, log) -> str:
        """Route /review commands through local TranscriptReviewService (no backend)."""
        from cockpit.integrations.transcript_review import TranscriptReviewService

        review_svc = TranscriptReviewService()
        if sub == "list" or not sub:
            pending_items = review_svc.list_pending()
            if pending_items:
                lines = [f"Pending review ({len(pending_items)} items):"]
                for i, item in enumerate(pending_items, 1):
                    sid = item.get("source_id", "?")
                    stype = item.get("source_type", "?")
                    title = item.get("title", "?")[:40]
                    chunks = item.get("chunk_count", 0)
                    staged = item.get("staged_at", "")[:10]
                    lines.append(
                        f"  [{i}] {sid} | {stype} | {title} | staged {staged} | {chunks} chunks"
                    )
                lines.append(
                    "Use: /review approve <source_id> or /review reject <source_id>"
                )
                return "\n".join(lines)
            return "No pending transcripts to review."
        if sub == "approve" and arg:
            self._append_log(log, f"assistant: Indexing chunks for {arg}...")
            result = review_svc.approve(arg)
            if result.get("ok"):
                return f"Approved and indexed {result.get('chunks_indexed', 0)} chunks for {arg}."
            return f"Approve failed: {result.get('error', 'unknown')}"
        if sub == "reject" and arg:
            result = review_svc.reject(arg)
            if result.get("ok"):
                return f"Rejected and purged staged chunks for {arg}."
            return f"Reject failed: {result.get('error', 'unknown')}"
        if sub == "approve-all":
            pending_items = review_svc.list_pending()
            if not pending_items:
                return "No pending transcripts to approve."
            total = 0
            for item in pending_items:
                result = review_svc.approve(item["source_id"])
                total += result.get("chunks_indexed", 0)
            return f"Approved {len(pending_items)} source(s), indexed {total} chunks."
        if sub == "expired":
            purged = review_svc.purge_expired()
            return (
                f"Purged {len(purged)} expired staged source(s)."
                if purged
                else "No expired items."
            )
        return "Usage: /review list|approve|reject|approve-all|expired [source_id]"

    def _get_snapshot_data(self, ticker: str) -> tuple[dict | None, list]:
        """Get latest financial snapshot + docs via backend API."""
        if not self._backend_client:
            logger.warning(
                "Snapshot data requested but backend API client not configured"
            )
            return None, []
        try:
            ctx = self._backend_client.get_ticker_context(
                ticker, docs_limit=20, financials_limit=1
            )
            return ctx.get("latest_financial_snapshot"), ctx.get("docs", [])
        except Exception as exc:
            logger.warning("Snapshot data fetch failed for %s: %s", ticker, exc)
            return None, []

    async def run_updater_snapshot(
        self, ticker: str, years: int, process_documents: bool, log_target: str
    ) -> None:
        before, _ = self._get_snapshot_data(ticker)

        args = {
            "ticker": ticker,
            "years": years,
            "process_documents": process_documents,
            "report_path": f"reports/financial_update_{ticker}_{self.timestamp()}.json",
        }
        await self.execute_action(
            "update_ticker_financials", args, log_target=log_target
        )

        after, docs = self._get_snapshot_data(ticker)
        verification = self.run_verification(ticker=ticker)

        payload = build_snapshot_payload(
            ticker=ticker,
            run_context={"years": years, "process_documents": process_documents},
            docs=docs,
            before=before,
            after=after,
            verification_summary=verification,
        )
        self.last_snapshot_payload = payload
        out_path = self.write_report_json(
            f"reports/snapshots/{ticker}_{self.timestamp()}.json", payload
        )
        self._write_log(log_target, f"Snapshot written: {out_path}")
        html_path = self.write_report_html(
            f"reports/cockpit/{ticker}_{self.timestamp()}_snapshot_dashboard.html",
            build_snapshot_dashboard_html(payload),
        )
        self._write_log(log_target, f"Snapshot dashboard written: {html_path}")
        self._write_log(log_target, json.dumps(payload, default=str, indent=2)[:6000])

    def run_verification(self, ticker: str | None = None) -> dict[str, Any]:
        return run_verification(ticker=ticker, backend_api_client=self._backend_client)

    def run_document_extraction(self, document_id: str) -> dict[str, Any]:
        if not self._backend_client:
            raise RuntimeError("backend API client not configured")
        return self._backend_client.process_document(document_id)

    def create_extraction_review_session(
        self,
        document_ids: list[str] | None = None,
        *,
        run_ids: list[str] | None = None,
    ) -> dict[str, Any]:
        if not self._backend_client:
            raise RuntimeError("backend API client not configured")
        return self._backend_client.create_extraction_review_session(
            document_ids=document_ids,
            run_ids=run_ids,
        )

    def list_extraction_review_runs(
        self,
        *,
        ticker: str | None = None,
        limit: int = 50,
    ) -> dict[str, Any]:
        if not self._backend_client:
            raise RuntimeError("backend API client not configured")
        return self._backend_client.list_extraction_review_runs(
            ticker=ticker,
            limit=limit,
        )

    def get_extraction_review_session(self, session_id: str) -> dict[str, Any]:
        if not self._backend_client:
            raise RuntimeError("backend API client not configured")
        return self._backend_client.get_extraction_review_session(session_id)

    def submit_extraction_review_decision(
        self,
        session_id: str,
        *,
        item_id: str,
        status: str,
        expected_value: Any | None = None,
        reviewer_note: str | None = None,
    ) -> dict[str, Any]:
        if not self._backend_client:
            raise RuntimeError("backend API client not configured")
        return self._backend_client.submit_extraction_review_decision(
            session_id,
            item_id=item_id,
            status=status,
            expected_value=expected_value,
            reviewer_note=reviewer_note,
        )

    def get_extraction_review_errors(self, *, limit: int = 200) -> dict[str, Any]:
        if not self._backend_client:
            raise RuntimeError("backend API client not configured")
        return self._backend_client.get_extraction_review_errors(limit=limit)

    def _write_log(self, log_target: str, text: str) -> None:
        try:
            screen = self.screen
            widget = screen.query_one(f"#{log_target}", RichLog)
            self._append_log(widget, text)
            return
        except Exception:
            pass

        # Fallback by scanning known screens.
        for name in ["chat", "ops", "updater", "verification"]:
            try:
                screen = self.get_screen(name)
                widget = screen.query_one(f"#{log_target}", RichLog)
                self._append_log(widget, text)
                return
            except Exception:
                continue

    def action_show_chat(self) -> None:
        self.push_screen("chat")

    def action_show_ops(self) -> None:
        self.push_screen("ops")

    def action_show_updater(self) -> None:
        self.push_screen("updater")

    def action_show_verification(self) -> None:
        self.push_screen("verification")

    def action_show_history(self) -> None:
        self.push_screen("history")

    def action_show_settings(self) -> None:
        self.push_screen("settings")

    def action_show_news_search(self) -> None:
        self.push_screen("news_search")

    def _activate_initial_screen(self) -> None:
        # Only push if app is still on default screen.
        try:
            if getattr(self.screen, "id", "") == "_default":
                self.push_screen("chat")
        except Exception:
            self.push_screen("chat")

    def action_export_copy_bundle(self) -> None:
        ts = self.timestamp()

        screen_obj = self.screen
        raw_screen_name = getattr(screen_obj, "name", None) or type(screen_obj).__name__
        screen_name = str(raw_screen_name)
        screen_key = screen_name.lower()
        log_target = self._export_log_target(screen_key)

        payload: dict[str, Any] = {
            "exported_at": datetime.now(timezone.utc).isoformat(),
            "screen": screen_name,
            "thread_id": self.thread_id,
            "runtime": self.config.get("runtime", {}),
        }

        # Screen-specific snapshot for easier paste/share.
        if "chat" in screen_key:
            latest = self.state_store.get_latest_export(self.thread_id)
            latest_export_payload: dict[str, Any] | None = None
            effective_ticker = self.last_detected_ticker
            chat_export_limit = 80
            chat_messages = self.state_store.get_chat_messages(
                self.thread_id, limit=chat_export_limit
            )
            payload["chat_messages"] = chat_messages
            payload["chat_messages_export_limit"] = chat_export_limit
            try:
                total_messages = self.state_store.count_chat_messages(self.thread_id)
            except Exception:
                total_messages = len(chat_messages)
            payload["chat_messages_total_in_thread"] = total_messages
            payload["chat_messages_truncated"] = total_messages > len(chat_messages)
            payload["pending_action"] = self.pending_action
            payload["last_chart_path"] = self.last_chart_path
            payload["last_snapshot_payload"] = self.last_snapshot_payload
            payload["last_verification_payload"] = self.last_verification_payload
            if latest:
                payload["latest_analysis_export_meta"] = latest
                try:
                    json_path = Path(str(latest.get("json_path", ""))).expanduser()
                    if json_path.exists() and json_path.is_file():
                        latest_export_payload = json.loads(
                            json_path.read_text(encoding="utf-8")
                        )
                        payload["latest_analysis_export"] = latest_export_payload
                except (OSError, json.JSONDecodeError) as exc:
                    payload["latest_analysis_export_error"] = str(exc)
            if not effective_ticker:
                effective_ticker = extract_ticker_from_payload(latest_export_payload)
            payload["last_detected_ticker"] = effective_ticker
        elif "ops" in screen_key or "operation" in screen_key:
            payload["recent_jobs"] = self.state_store.list_jobs(limit=20)
        elif "updater" in screen_key:
            payload["recent_jobs"] = self.state_store.list_jobs(limit=20)
        elif "verification" in screen_key:
            payload["last_verification"] = self.last_verification_payload
        elif "history" in screen_key:
            payload["recent_jobs"] = self.state_store.list_jobs(limit=100)
            payload["recent_exports"] = self.state_store.list_exports(limit=100)
        elif "settings" in screen_key:
            payload["settings"] = self.config
        else:
            payload["recent_jobs"] = self.state_store.list_jobs(limit=20)

        sanitized_payload = self._sanitize_export_payload(payload)
        text_blob = json.dumps(sanitized_payload, indent=2, default=str)

        # Always write a fixed-path file so Claude can read it without hunting for
        # a timestamped filename.  Overwritten on every export — always fresh.
        out_dir = self.repo_root / "reports" / "cockpit" / "exports"
        out_dir.mkdir(parents=True, exist_ok=True)
        claude_path = out_dir / "claude_context.json"
        claude_path.write_text(text_blob, encoding="utf-8")

        copied = self._copy_to_clipboard(text_blob)
        if copied:
            notice = f"Copied to clipboard + saved: {claude_path}"
        else:
            # Also write a timestamped copy as a permanent record.
            txt_path = out_dir / f"copy_bundle_{ts}.txt"
            txt_path.write_text(text_blob, encoding="utf-8")
            notice = f"Saved for Claude: {claude_path}  (clipboard unavailable)"
        if log_target:
            self._write_log(log_target, notice)
        self.notify(notice)

    @classmethod
    def _is_sensitive_export_key(cls, key: str) -> bool:
        normalized = str(key or "").strip().lower().replace("-", "_")
        if not normalized:
            return False
        return any(part in normalized for part in cls._SENSITIVE_EXPORT_KEY_PARTS)

    @classmethod
    def _sanitize_export_string(cls, value: str) -> str:
        text = str(value or "")
        if not text:
            return text

        try:
            parsed = urlsplit(text)
        except Exception:
            parsed = None
        if (
            parsed
            and parsed.scheme
            and (parsed.username is not None or parsed.password is not None)
        ):
            host = parsed.hostname or ""
            if parsed.port is not None:
                host = f"{host}:{parsed.port}"
            return urlunsplit(
                (parsed.scheme, host, parsed.path, parsed.query, parsed.fragment)
            )

        if text.lower().startswith("bearer ") and len(text) > 7:
            return "Bearer " + cls._REDACTED_EXPORT_VALUE
        return text

    @classmethod
    def _sanitize_export_payload(cls, value: Any, *, key: str = "") -> Any:
        if cls._is_sensitive_export_key(key):
            return cls._REDACTED_EXPORT_VALUE

        if isinstance(value, dict):
            return {
                str(child_key): cls._sanitize_export_payload(
                    child_value, key=str(child_key)
                )
                for child_key, child_value in value.items()
            }
        if isinstance(value, list):
            return [cls._sanitize_export_payload(item, key=key) for item in value]
        if isinstance(value, tuple):
            return [cls._sanitize_export_payload(item, key=key) for item in value]
        if isinstance(value, str):
            return cls._sanitize_export_string(value)
        return value

    @staticmethod
    def _export_log_target(screen_key: str) -> str | None:
        if "chat" in screen_key:
            return "chat-log"
        if "ops" in screen_key or "operation" in screen_key:
            return "ops-log"
        if "updater" in screen_key:
            return "upd-log"
        if "verification" in screen_key:
            return "ver-log"
        return None

    def _copy_to_clipboard(self, text: str) -> bool:
        # OSC 52 — works over SSH; the terminal emulator on the far end sets the
        # clipboard.  iTerm2: Prefs → General → "Allow clipboard access to terminal apps".
        # kitty, WezTerm, and most modern terminals support it without configuration.
        import base64

        try:
            encoded = base64.b64encode(text.encode("utf-8")).decode("ascii")
            # Write directly to the controlling terminal, not stdout, so Textual's
            # rendering pipeline doesn't intercept the escape sequence.
            with open("/dev/tty", "w") as tty:
                tty.write(f"\033]52;c;{encoded}\a")
                tty.flush()
            return True
        except Exception:
            pass

        # Linux Wayland
        if shutil.which("wl-copy"):
            try:
                subprocess.run(["wl-copy"], input=text, text=True, check=True)
                return True
            except Exception:
                pass

        # Linux X11
        if shutil.which("xclip"):
            try:
                subprocess.run(
                    ["xclip", "-selection", "clipboard"],
                    input=text,
                    text=True,
                    check=True,
                )
                return True
            except Exception:
                pass
        if shutil.which("xsel"):
            try:
                subprocess.run(
                    ["xsel", "--clipboard", "--input"],
                    input=text,
                    text=True,
                    check=True,
                )
                return True
            except Exception:
                pass

        # macOS
        if shutil.which("pbcopy"):
            try:
                subprocess.run(["pbcopy"], input=text, text=True, check=True)
                return True
            except Exception:
                pass

        # Optional python module
        try:
            import pyperclip  # type: ignore

            pyperclip.copy(text)
            return True
        except Exception:
            return False
