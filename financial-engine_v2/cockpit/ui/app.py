from __future__ import annotations

import asyncio
import json
import os
import re
import shutil
import subprocess
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.widgets import Footer, Header, RichLog, Static

from cockpit.core.actions import ActionRegistry
from cockpit.core.backend_restart import restart_backend
from cockpit.core.chat import ChatController
from cockpit.core.job_runner import JobRunner
from cockpit.core.plotly_html import build_candlestick_dashboard_html, build_snapshot_dashboard_html
from cockpit.core.snapshot import build_snapshot_payload
from cockpit.core.config import DEFAULT_LLAMACPP_URL, DEFAULT_OLLAMA_URL
from cockpit.core.types import JobRun
from cockpit.core.verification import run_verification
from cockpit.integrations.backend_api import BackendApiClient
from cockpit.integrations.db_reader import DbReader
from cockpit.integrations.file_indexer import FileIndexer
from cockpit.integrations.llamacpp_client import LlamaCppClient
from cockpit.integrations.qual_context_bootstrap import build_qual_context_reader, context_enabled
from cockpit.integrations.web_fetcher import WebFetcher
from cockpit.core.conversation_commands import derive_conversational_command
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


class CockpitApp(App):
    ASSISTANT_NAME = "Tenn"

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
        height: 5;
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
        Binding("ctrl+n", "show_news_search", "News Search"),
        Binding("x", "export_copy_bundle", "Export"),
        Binding("q", "quit", "Quit"),
    ]

    def __init__(self, repo_root: Path, config: dict[str, Any], read_only: bool) -> None:
        super().__init__()
        self._init_services(repo_root, config, read_only)

    def _init_services(self, repo_root: Path, config: dict[str, Any], read_only: bool) -> None:
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
            llm_url = llm_cfg.get("llamacpp_url") or llm_cfg.get("ollama_url", DEFAULT_OLLAMA_URL)
        self.ollama_client = LlamaCppClient(
            llm_url,
            llm_model,
            api_key=llm_cfg.get("llamacpp_api_key", ""),
        )
        self.action_registry = ActionRegistry(repo_root=repo_root, confirm_required=config["actions"].get("confirm_required", True))
        self.job_runner = JobRunner(repo_root=repo_root, logs_dir=self.artifacts.logs_dir)

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
            qc_cfg = rag_cfg.get("qualitative_context") if isinstance(rag_cfg.get("qualitative_context"), dict) else None
            if context_enabled(qc_cfg, default=False):
                try:
                    qual_company = build_qual_context_reader(
                        repo_root=repo_root,
                        qc_cfg=qc_cfg,
                        backend_api_client=self._backend_client,
                        context_name="qualitative_context",
                    )
                except Exception as exc:
                    self._startup_warnings.append(f"qual_context (company) disabled: {exc}")

            news_cfg = rag_cfg.get("news_context") if isinstance(rag_cfg.get("news_context"), dict) else None
            if context_enabled(news_cfg, default=False):
                try:
                    qual_news = build_qual_context_reader(
                        repo_root=repo_root,
                        qc_cfg=news_cfg,
                        backend_api_client=self._backend_client,
                        context_name="news_context",
                    )
                except Exception as exc:
                    self._startup_warnings.append(f"qual_context (news) disabled: {exc}")
        else:
            self._startup_warnings.append("backend.api_base_url not set — price, RAG, and news context disabled")

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
            llm_timeout_seconds=float(config.get("llm", {}).get("timeout_seconds", 300)),
            state_store=self.state_store,
            thread_id="global-main",
        )

        self.thread_id = "global-main"
        self.pending_action: dict[str, Any] | None = None
        self.last_verification_payload: dict[str, Any] | None = None
        self.last_snapshot_payload: dict[str, Any] | None = None
        self.last_chart_path: str | None = None
        self.last_detected_ticker: str | None = None
        self.last_response_mode: str | None = None
        self.chat_inflight = False
        self._input_history: list[str] = []
        self._history_idx: int = -1
        self.active_job_task: asyncio.Task[None] | None = None
        self.active_job_id: str | None = None
        self.active_log_target: str = "chat-log"
        self._model_status_timer = None
        self._chat_tasks: set[asyncio.Task[None]] = set()

    def _normalize_database_url(self, database_url: str) -> str:
        value = (database_url or "").strip()
        if not value:
            value = "sqlite:///./data/fe_local.db"

        if value.startswith("sqlite:///"):
            path_part = value[len("sqlite:///"):]
            if path_part.startswith("./") or not path_part.startswith("/"):
                resolved = (self.repo_root / path_part).resolve()
                resolved.parent.mkdir(parents=True, exist_ok=True)
                return f"sqlite:///{resolved}"

            # Absolute sqlite path: ensure parent exists.
            abs_path = Path(path_part)
            abs_path.parent.mkdir(parents=True, exist_ok=True)
            return value

        return value

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

        self._schedule_model_status_refresh()
        self._model_status_timer = self.set_interval(15.0, self._schedule_model_status_refresh)

    async def _run_startup_health_checks(self) -> None:
        """Offload blocking health checks so the event loop stays responsive at startup."""
        if self._backend_client is not None:
            try:
                health = await asyncio.to_thread(self._backend_client.health, 4.0)
                if health.get("ok"):
                    self._screen_log("chat", f"startup: backend API reachable at {self._backend_client.base_url}")
                else:
                    self._screen_log("chat", f"startup: backend API unreachable at {self._backend_client.base_url}: {health.get('error')}")
            except Exception as exc:
                self._screen_log("chat", f"startup: backend health check failed: {exc}")

        try:
            health = await asyncio.to_thread(self.ollama_client.health, 4.0)
            if health.get("ok"):
                model = str(self.config.get("llm", {}).get("model", ""))
                names = health.get("models") if isinstance(health.get("models"), list) else []
                if model and names and model not in names:
                    self._screen_log(
                        "chat",
                        f"startup: llama.cpp reachable at {health.get('url')} but model '{model}' is not pulled.",
                    )
                else:
                    self._screen_log("chat", f"startup: llama.cpp reachable at {health.get('url')}")
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
                metrics["gpu_error"] = err.splitlines()[0] if err else "nvidia-smi failed"
                return metrics

            rows = [line.strip() for line in (proc.stdout or "").splitlines() if line.strip()]
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

    def _collect_runtime_snapshot(self, endpoint: str) -> tuple[dict[str, Any], dict[str, Any]]:
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
        model = str(llm_cfg.get("model") or getattr(self.ollama_client, "model", "") or "unknown")
        endpoint = str(getattr(self.ollama_client, "base_url", "") or llm_cfg.get("ollama_url", ""))
        provider_label = "llama.cpp"

        health, sys_metrics = await asyncio.to_thread(self._collect_runtime_snapshot, endpoint)

        # For llama.cpp, get the actually-loaded model from the API.
        if health.get("ok") and provider == "llamacpp":
            api_models = health.get("models") or []
            loaded = api_models[0] if api_models else model
        else:
            loaded = model

        agent_mode = os.environ.get("COCKPIT_AGENT_MODE", "keyword")
        lines = [
            f"Provider: {provider_label}  |  Model Runtime: {loaded}",
            f"Endpoint: {endpoint}",
            f"Last mode: {self.last_response_mode or 'none'}  |  Agent: {agent_mode}",
        ]

        if health.get("ok"):
            names = health.get("models") if isinstance(health.get("models"), list) else []
            if provider == "ollama" and model and names and model not in names:
                lines.append(f"{provider_label}: reachable — configured model not pulled")
            else:
                lines.append(f"{provider_label}: reachable")
        else:
            lines.append(f"{provider_label}: unavailable ({health.get('error') or 'unknown error'})")

        gpus = sys_metrics.get("gpus") if isinstance(sys_metrics.get("gpus"), list) else []
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
            self._append_log(log, f"{self.ASSISTANT_NAME}: still thinking about the previous message.")
            return

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
            _logging.getLogger(__name__).debug("conversational command resolved: %s", derived_cmd)
            stripped = derived_cmd

        # Handle /watch commands (from slash input or resolved conversational command)
        if stripped.startswith("/watch "):
            parts = stripped[len("/watch "):].split(maxsplit=1)
            sub = parts[0].lower() if parts else ""
            arg = parts[1].strip().upper() if len(parts) > 1 else ""
            now_iso = datetime.now(timezone.utc).isoformat()
            if sub == "add" and arg:
                added = self.state_store.add_watch_ticker(arg, now_iso)
                reply = f"Added {arg} to watchlist." if added else f"{arg} is already on the watchlist."
            elif sub == "remove" and arg:
                removed = self.state_store.remove_watch_ticker(arg)
                reply = f"Removed {arg} from watchlist." if removed else f"{arg} was not on the watchlist."
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
            else:
                reply = "Usage: /watch add|remove|list|clear [TICKER]"
            self._append_log(log, f"assistant: {reply}")
            self.state_store.add_chat_message(self.thread_id, "assistant", reply, now_iso)
            return

        # Handle /review commands for transcript approval gate
        if stripped.startswith("/review"):
            from cockpit.integrations.transcript_review import TranscriptReviewService
            review_svc = TranscriptReviewService()
            parts = stripped[len("/review"):].strip().split(maxsplit=1)
            sub = parts[0].lower() if parts else "list"
            arg = parts[1].strip() if len(parts) > 1 else ""
            now_iso = datetime.now(timezone.utc).isoformat()
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
                        lines.append(f"  [{i}] {sid} | {stype} | {title} | staged {staged} | {chunks} chunks")
                    lines.append("Use: /review approve <source_id> or /review reject <source_id>")
                    reply = "\n".join(lines)
                else:
                    reply = "No pending transcripts to review."
            elif sub == "approve" and arg:
                self._append_log(log, f"assistant: Indexing chunks for {arg}...")
                result = review_svc.approve(arg)
                if result.get("ok"):
                    reply = f"Approved and indexed {result.get('chunks_indexed', 0)} chunks for {arg}."
                else:
                    reply = f"Approve failed: {result.get('error', 'unknown')}"
            elif sub == "reject" and arg:
                result = review_svc.reject(arg)
                if result.get("ok"):
                    reply = f"Rejected and purged staged chunks for {arg}."
                else:
                    reply = f"Reject failed: {result.get('error', 'unknown')}"
            elif sub == "approve-all":
                pending_items = review_svc.list_pending()
                if not pending_items:
                    reply = "No pending transcripts to approve."
                else:
                    total = 0
                    for item in pending_items:
                        result = review_svc.approve(item["source_id"])
                        total += result.get("chunks_indexed", 0)
                    reply = f"Approved {len(pending_items)} source(s), indexed {total} chunks."
            elif sub == "expired":
                purged = review_svc.purge_expired()
                reply = f"Purged {len(purged)} expired staged source(s)." if purged else "No expired items."
            else:
                reply = "Usage: /review list|approve|reject|approve-all|expired [source_id]"
            self._append_log(log, f"assistant: {reply}")
            self.state_store.add_chat_message(self.thread_id, "assistant", reply, now_iso)
            return

        # Handle /strategy commands
        if stripped.startswith("/strategy"):
            from cockpit.core.strategy import StrategyService
            strategy_svc = StrategyService(self.state_store)
            parts = stripped[len("/strategy"):].strip().split(maxsplit=2)
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
                            lines.append(f"  [{c['id']}] {c['criterion']} ({c['category']}, P{c['priority']})")
                    if tcriteria:
                        lines.append(f"\n{tkr}-specific criteria ({len(tcriteria)}):")
                        for c in tcriteria:
                            dec = f" [decision: {c['decision']}]" if c.get("decision") else ""
                            lines.append(f"  [{c['id']}] {c['criterion']} ({c['category']}, P{c['priority']}){dec}")
                    if decision and decision.get("decision_rationale"):
                        lines.append(f"\nDecision: {decision['decision']} — {decision['decision_rationale']}")
                    reply = "\n".join(lines) if lines else f"No strategy criteria defined for {tkr}."
                else:
                    gcriteria = strategy_svc.get_global()
                    if gcriteria:
                        lines = [f"Global criteria ({len(gcriteria)}):"]
                        for c in gcriteria:
                            lines.append(f"  [{c['id']}] {c['criterion']} ({c['category']}, P{c['priority']})")
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
                        result = strategy_svc.record_decision(arg1.upper(), decision_val, rationale)
                        reply = f"Recorded decision for {arg1.upper()}: {decision_val}" + (f" — {rationale}" if rationale else "")
                    else:
                        reply = "Decision must be one of: buy, watchlist, avoid"
                else:
                    reply = "Usage: /strategy decide <TICKER> <buy|watchlist|avoid> <rationale>"
            elif sub == "delete":
                if arg1 and arg1.isdigit():
                    deleted = strategy_svc.delete(int(arg1))
                    reply = f"Deleted criterion [{arg1}]." if deleted else f"Criterion [{arg1}] not found."
                else:
                    reply = "Usage: /strategy delete <id>"
            else:
                reply = "Usage: /strategy list|add|decide|delete [TICKER] [criterion]"
            self._append_log(log, f"assistant: {reply}")
            self.state_store.add_chat_message(self.thread_id, "assistant", reply, now_iso)
            return

        # Handle /sources commands
        if stripped.startswith("/sources"):
            parts = stripped[len("/sources"):].strip().split(maxsplit=1)
            sub = parts[0].lower() if parts else ""
            now_iso = datetime.now(timezone.utc).isoformat()
            if sub == "on":
                self.state_store.set_preference("show_sources", "true")
                reply = "Sources display enabled."
            elif sub == "off":
                self.state_store.set_preference("show_sources", "false")
                reply = "Sources display disabled."
            else:
                current = self.state_store.get_preference("show_sources", "true")
                reply = f"Sources display: {'ON' if current == 'true' else 'OFF'}. Use /sources on|off to toggle."
            self._append_log(log, f"assistant: {reply}")
            self.state_store.add_chat_message(self.thread_id, "assistant", reply, now_iso)
            return

        if message.strip() == "/cancel":
            self.pending_action = None
            pending.update("No pending action")
            self._append_log(log, "assistant: Pending action canceled.")
            self.state_store.add_chat_message(self.thread_id, "assistant", "Pending action canceled.", datetime.now(timezone.utc).isoformat())
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
            await self.execute_action(action["action_id"], action["args"], log_target="chat-log", skip_confirm=True)
            return

        if message.startswith("/run "):
            parts = message[5:].split(maxsplit=1)
            action_id = parts[0]
            args = self.action_registry.parse_kv_args(parts[1] if len(parts) > 1 else "")
            await self.execute_action(action_id, args, log_target="chat-log")
            return

        if message.startswith("/read "):
            raw = message[len("/read "):].strip()
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
                self.state_store.add_chat_message(self.thread_id, "assistant", text, datetime.now(timezone.utc).isoformat())
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
            rest = message[len("/prefer "):].strip()
            if "=" in rest:
                key, _, value = rest.partition("=")
                self.state_store.set_preference(key.strip(), value.strip())
                self._append_log(log, f"assistant: Preference saved: {key.strip()} = {value.strip()}")
            else:
                prefs = self.state_store.get_preferences()
                if prefs:
                    self._append_log(log, "assistant: Current preferences:\n" + "\n".join(f"  {k} = {v}" for k, v in prefs.items()))
                else:
                    self._append_log(log, "assistant: No preferences set. Use /prefer key=value to set one.")
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
                status.update(f"{thinking_prefix} {spinner_frames[idx % len(spinner_frames)]}")
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
                self.call_from_thread(self._set_chat_live_response, stream_state["text"])
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
                self.pending_action = {
                    "action_id": response.action_preview["action_id"],
                    "args": response.action_preview["args"],
                }
        except Exception as exc:
            self.chat_inflight = False
            status.update("")
            partial = stream_state["text"].strip()
            if partial:
                self._append_log(log, f"assistant: {partial}")
                self.state_store.add_chat_message(self.thread_id, "assistant", partial, datetime.now(timezone.utc).isoformat())
            self._set_chat_live_response("")
            err = f"assistant: chat error: {exc}"
            self._append_log(log, err)
            self.state_store.add_chat_message(self.thread_id, "assistant", err, datetime.now(timezone.utc).isoformat())
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
            local_details = (response.evidence or [{}])[0].get("details", {})
            ticker = local_details.get("ticker")
            if isinstance(ticker, str) and ticker.strip():
                self.last_detected_ticker = ticker.strip().upper()
        except Exception:
            pass

        try:
            self.query_one("#chat-ticker-context", Static).update(
                f"Context: {self.last_detected_ticker}" if self.last_detected_ticker else ""
            )
        except Exception:
            pass

        try:
            from rich.markdown import Markdown as _Markdown
            log.write(_Markdown(f"**{self.ASSISTANT_NAME}:** {assistant_text}"), scroll_end=True)
        except Exception:
            self._append_log(log, f"assistant: {assistant_text}")

        # Append sources footer for analysis responses
        try:
            local_details = (response.evidence or [{}])[0].get("details", {})
            sources_data = local_details.get("sources", {})
            if sources_data:
                from cockpit.core.sources import SourcesFormatter
                show = self.state_store.get_preference("show_sources", "true") == "true"
                footer = SourcesFormatter.format_footer(sources_data, show_sources=show)
                if footer:
                    self._append_log(log, footer)
        except Exception:
            pass  # sources footer is best-effort

        self.state_store.add_chat_message(self.thread_id, "assistant", assistant_text, datetime.now(timezone.utc).isoformat())

        if response.action_preview:
            # pending_action was already set in the try block above (before
            # chat_inflight was cleared) so that a fast /confirm can find it
            # immediately.  If /confirm already consumed it, don't re-set.
            if self.pending_action is not None:
                pending.update(
                    "Pending: "
                    f"{response.action_preview['action_id']} "
                    f"args={response.action_preview['args']} "
                    "(/confirm or /cancel)"
                )

            # Candlestick chart — generate HTML dashboard immediately.
            if response.action_preview.get("action_id") == "show_candlestick":
                try:
                    chart_args = response.action_preview.get("args") or {}
                    chart_ticker = str(chart_args.get("ticker") or self.last_detected_ticker or "UNKNOWN")
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
                    self._append_log(log, f"assistant: Chart dashboard written: {chart_path}")
                    self.pending_action = None  # chart already generated; no subprocess needed
                except Exception as exc:
                    self._append_log(log, f"assistant: chart generation error: {exc}")

        export_payload = {
            "question": message,
            "answer": assistant_text,
            "response_mode": response.mode,
            "evidence": response.evidence,
            "actions_taken": [response.action_preview] if response.action_preview else [],
            "sources": ["local_context"],
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        md_path, json_path = self.artifacts.write_analysis(self.thread_id, message, assistant_text, export_payload)
        self.state_store.add_export(self.thread_id, message, md_path, json_path, datetime.now(timezone.utc).isoformat())

    async def execute_action(
        self,
        action_id: str,
        args: dict[str, Any],
        log_target: str,
        skip_confirm: bool = False,
    ) -> None:
        if self.active_job_task and not self.active_job_task.done():
            self._write_log(log_target, f"Action already running (job_id={self.active_job_id or 'unknown'}). Kill it first.")
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

        self._write_log(log_target, f"Executing: {' '.join(preview.command)}")
        self._write_log(log_target, f"Job queued: {job.job_id}")
        self.active_job_id = job.job_id
        self.active_log_target = log_target
        last_ticker: str | None = None
        last_day: str | None = None

        def _emit(line: str) -> None:
            # _emit is always called from within the asyncio event loop (via _pump in
            # job_runner), so direct calls to _write_log are safe — no thread-hopping needed.
            nonlocal last_ticker, last_day
            self._write_log(log_target, line)

            ticker_match = re.search(r"\[(?:backfill|probe)\]\s+([A-Z0-9.]+)\s+attempt\s+\d+", line)
            if ticker_match:
                ticker = ticker_match.group(1)
                if ticker != last_ticker:
                    last_ticker = ticker
                    self._write_log(log_target, f"[progress] ingesting ticker={ticker}")

            day_match = re.search(r"\[asx_sweep\]\s+date=([0-9]{4}-[0-9]{2}-[0-9]{2})", line)
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
                        "ended_at": run_result.ended_at.isoformat() if run_result.ended_at else None,
                        "status": run_result.status,
                        "exit_code": run_result.exit_code,
                        "stdout_path": run_result.stdout_path,
                        "stderr_path": run_result.stderr_path,
                        "artifacts": run_result.artifacts,
                    }
                )
                self._write_log(log_target, f"Completed with status={run_result.status} exit={run_result.exit_code}")
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
        self._write_log(log_target, f"Cancel request sent: {status} (job_id={self.active_job_id or 'unknown'})")

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

    async def run_updater_snapshot(self, ticker: str, years: int, process_documents: bool, log_target: str) -> None:
        before = self.db_reader.get_latest_financial_snapshot(ticker)

        args = {
            "ticker": ticker,
            "years": years,
            "process_documents": process_documents,
            "report_path": f"reports/financial_update_{ticker}_{self.timestamp()}.json",
        }
        await self.execute_action("update_ticker_financials", args, log_target=log_target)

        after = self.db_reader.get_latest_financial_snapshot(ticker)
        docs = self.db_reader.get_docs(ticker=ticker, limit=20)
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
        out_path = self.write_report_json(f"reports/snapshots/{ticker}_{self.timestamp()}.json", payload)
        self._write_log(log_target, f"Snapshot written: {out_path}")
        html_path = self.write_report_html(
            f"reports/cockpit/{ticker}_{self.timestamp()}_snapshot_dashboard.html",
            build_snapshot_dashboard_html(payload),
        )
        self._write_log(log_target, f"Snapshot dashboard written: {html_path}")
        self._write_log(log_target, json.dumps(payload, default=str, indent=2)[:6000])

    def run_verification(self, ticker: str | None = None) -> dict[str, Any]:
        return run_verification(self.db_reader, ticker=ticker)

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
            payload["chat_messages"] = self.state_store.get_chat_messages(self.thread_id, limit=200)
            payload["pending_action"] = self.pending_action
            payload["last_detected_ticker"] = self.last_detected_ticker
            latest = self.state_store.get_latest_export(self.thread_id)
            if latest:
                payload["latest_analysis_export_meta"] = latest
                try:
                    json_path = Path(str(latest.get("json_path", ""))).expanduser()
                    if json_path.exists() and json_path.is_file():
                        payload["latest_analysis_export"] = json.loads(json_path.read_text(encoding="utf-8"))
                except (OSError, json.JSONDecodeError) as exc:
                    payload["latest_analysis_export_error"] = str(exc)
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

        text_blob = json.dumps(payload, indent=2, default=str)

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
                subprocess.run(["xclip", "-selection", "clipboard"], input=text, text=True, check=True)
                return True
            except Exception:
                pass
        if shutil.which("xsel"):
            try:
                subprocess.run(["xsel", "--clipboard", "--input"], input=text, text=True, check=True)
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
