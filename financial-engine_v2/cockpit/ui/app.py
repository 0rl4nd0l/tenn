from __future__ import annotations

import atexit
import asyncio
import json
import os
import re
import shlex
import shutil
import subprocess
import threading
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.widgets import Button, Footer, Header, RichLog, Static

from cockpit.core.actions import ActionRegistry
from cockpit.core.action_runtime_guards import (
    extract_report_paths,
    evaluate_quality_gate,
    find_conflicting_job,
    load_json_reports,
)
from cockpit.core.access_resume import (
    access_scope_is_enabled as _access_scope_is_enabled_util,
    build_pending_action_payload as _build_pending_action_payload_util,
    resolve_confirm_resume_message as _resolve_confirm_resume_message_util,
    resolve_pending_action_alias as _resolve_pending_action_alias_util,
)
from cockpit.core.alerts import DEFAULT_ALERT_THRESHOLDS, evaluate_price_state_alerts
from cockpit.core.chat import ChatController
from cockpit.core.conversation_commands import derive_conversational_command
from cockpit.core.job_runner import JobRunner
from cockpit.core.snapshot import build_snapshot_payload
from cockpit.core.types import JobRun
from cockpit.core.update_status import (
    is_successful_update_status as _is_successful_update_status_util,
    normalize_update_status as _normalize_update_status_util,
)
from cockpit.core.update_delta import (
    build_announcement_update_delta_summary as _build_update_delta_summary,
    build_close_series as _build_close_series_util,
    compact_doc_row as _compact_doc_row_util,
    compute_reaction_for_time as _compute_reaction_for_time_util,
    doc_delta_key as _doc_delta_key_util,
    parse_timestamp_utc as _parse_timestamp_utc_util,
    sync_human as _sync_human_util,
)
from cockpit.core.verification import run_verification
from cockpit.integrations.backend_api import BackendApiClient
from cockpit.integrations.db_reader import DbReader
from cockpit.integrations.file_indexer import FileIndexer
from cockpit.integrations.ollama_client import OllamaClient
from cockpit.integrations.qual_context_bootstrap import (
    build_qual_context_reader,
    resolve_news_context_db_path,
    resolve_qual_context_db_path,
    resolve_rag_dependency_policy,
)
from cockpit.integrations.web_fetcher import WebFetcher
from cockpit.core.tools import ToolRouter
from cockpit.storage.artifacts import ArtifactStore
from cockpit.storage.state import StateStore
from cockpit.ui.screens import (
    ChatScreen,
    ConfirmActionScreen,
    HistoryScreen,
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
    #chat-mode-controls {
        margin: 0 0 1 0;
    }
    #chat-mode-controls Button {
        width: 1fr;
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
    #chat-top-actions {
        margin: 0 0 1 0;
    }
    #chat-top-actions Button {
        width: 1fr;
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
    #chat-log {
        height: 1fr;
        min-height: 8;
    }
    """
    BINDINGS = [
        Binding("c", "show_chat", "Chat"),
        Binding("o", "show_ops", "Ops"),
        Binding("u", "show_updater", "Updater"),
        Binding("v", "show_verification", "Verify"),
        Binding("h", "show_history", "History"),
        Binding("s", "show_settings", "Settings"),
        Binding("x", "export_copy_bundle", "Export"),
        Binding("q", "quit", "Quit"),
    ]

    def __init__(self, repo_root: Path, config: dict[str, Any], read_only: bool) -> None:
        super().__init__()
        self.repo_root = repo_root
        self.config = config
        self.read_only = read_only
        self._startup_notices: list[str] = []

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
        self.file_indexer = FileIndexer(config["paths"]["allow_roots"], default_root=repo_root)
        self.web_fetcher = WebFetcher()
        self.ollama_client = OllamaClient(config["llm"]["ollama_url"], config["llm"]["model"])
        self.backend_api_client = BackendApiClient(config.get("backend", {}).get("api_base_url", "http://localhost:8000"))
        self.action_registry = ActionRegistry(repo_root=repo_root, confirm_required=config["actions"].get("confirm_required", True))
        self.job_runner = JobRunner(repo_root=repo_root, logs_dir=self.artifacts.logs_dir)
        qual_context_reader = None
        qual_context_news_reader = None
        rag_cfg = config.get("rag", {})
        if isinstance(rag_cfg, dict) and rag_cfg.get("enabled"):
            qc_cfg = rag_cfg.get("qualitative_context", rag_cfg)
            if isinstance(qc_cfg, dict):
                raw_path = str(qc_cfg.get("db_path") or "").strip()
                profile = str(config.get("runtime", {}).get("profile") or "default").strip().lower()
                dependency_policy = resolve_rag_dependency_policy(
                    str(qc_cfg.get("dependency_policy") or "error"),
                    profile,
                )
                if raw_path:
                    db_path = resolve_qual_context_db_path(repo_root=self.repo_root, raw_path=raw_path)
                    qual_context_reader = build_qual_context_reader(
                        repo_root=self.repo_root,
                        qc_cfg=qc_cfg,
                        db_path=db_path,
                        dependency_policy=dependency_policy,
                        startup_notices=self._startup_notices,
                    )
                news_db_path = resolve_news_context_db_path(repo_root=self.repo_root, rag_cfg=rag_cfg)
                if news_db_path is not None:
                    news_cfg_raw = rag_cfg.get("news_context")
                    news_cfg_raw = news_cfg_raw if isinstance(news_cfg_raw, dict) else {}
                    news_cfg = dict(qc_cfg)
                    news_cfg.update(news_cfg_raw)
                    news_cfg["corpus_filter"] = str(news_cfg.get("corpus_filter") or "news")
                    news_cfg["exclude_corpus_filter"] = str(news_cfg.get("exclude_corpus_filter") or "")
                    news_cfg["top_k"] = int(news_cfg.get("top_k") or 4)
                    news_dependency_policy = resolve_rag_dependency_policy(
                        str(news_cfg.get("dependency_policy") or qc_cfg.get("dependency_policy") or "error"),
                        profile,
                    )
                    qual_context_news_reader = build_qual_context_reader(
                        repo_root=self.repo_root,
                        qc_cfg=news_cfg,
                        db_path=news_db_path,
                        dependency_policy=news_dependency_policy,
                        startup_notices=self._startup_notices,
                    )
                    self._startup_notices.append(
                        f"startup: optional news RAG enabled from {news_db_path}"
                    )
        self.tool_router = ToolRouter(
            db_reader=self.db_reader,
            file_indexer=self.file_indexer,
            web_fetcher=self.web_fetcher,
            repo_root=self.repo_root,
            web_default_enabled=config["web"].get("enabled_default", False),
            backend_api_client=self.backend_api_client,
            qual_context_reader=qual_context_reader,
            qual_context_company_reader=qual_context_reader,
            qual_context_news_reader=qual_context_news_reader,
        )
        self.chat_controller = ChatController(
            ollama_client=self.ollama_client,
            tool_router=self.tool_router,
            action_registry=self.action_registry,
            llm_timeout_seconds=float(config.get("llm", {}).get("timeout_seconds", 300)),
        )

        self.thread_id = "global-main"
        self.session_started_at = datetime.now(timezone.utc).isoformat()
        self.pending_action: dict[str, Any] | None = None
        self.last_verification_payload: dict[str, Any] | None = None
        self.last_detected_ticker: str | None = None
        self.last_prompt: str | None = None
        self.active_job_task: asyncio.Task[None] | None = None
        self.active_job_id: str | None = None
        self.active_log_target: str = "chat-log"
        self.active_chat_task: asyncio.Task[None] | None = None
        self.chat_inflight: bool = False
        self.chat_cancel_requested: bool = False
        self.chat_analysis_mode: str = "operational"
        self.auto_deep_detection_enabled: bool = True
        self.web_enabled: bool = bool(config.get("web", {}).get("enabled_default", False))
        self.rag_enabled: bool = bool(self.tool_router.qual_context_enabled)
        self.db_diagnostic_query_enabled: bool = bool(config.get("db", {}).get("diagnostic_query_enabled", False))
        self.chat_latency_window = int(config.get("llm", {}).get("latency_window", 120))
        self.chat_latency_samples: dict[str, list[float]] = {
            "total_ms": [],
            "context_ms": [],
            "llm_ms": [],
            "web_ms": [],
        }
        self._model_status_refresh_task: asyncio.Task[None] | None = None
        self._managed_backend_proc: subprocess.Popen[bytes] | None = None
        self._managed_backend_log_handle = None
        self._managed_backend_log_path = (self.artifacts.logs_dir / "backend_autostart.log").resolve()
        atexit.register(self._shutdown_managed_backend)

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
        self.install_screen(ChatScreen(), name="chat")
        self.install_screen(OperationsScreen(), name="ops")
        self.install_screen(UpdaterScreen(), name="updater")
        self.install_screen(VerificationScreen(), name="verification")
        self.install_screen(HistoryScreen(), name="history")
        self.install_screen(SettingsScreen(), name="settings")
        # Defer initial screen activation one tick to avoid startup stack race.
        self.set_timer(0.01, self._activate_initial_screen)
        self._update_chat_mode_widgets()
        for notice in self._startup_notices:
            self._screen_log("chat", notice)
        self._ensure_backend_api_started()
        self._schedule_model_status_refresh()
        self.set_interval(10.0, self._schedule_model_status_refresh)

        # Replay recent history into chat log for continuity.
        try:
            screen = self.get_screen("chat")
            log = screen.query_one("#chat-log", RichLog)
            for message in self.state_store.get_chat_messages_since(
                self.thread_id,
                self.session_started_at,
                limit=50,
            ):
                role = str(message.get("role") or "").strip().lower()
                role_label = self.ASSISTANT_NAME if role == "assistant" else role
                log.write(f"{role_label}: {message['content']}")
            self._smooth_scroll_to_end(log, animate=False)
        except Exception:
            pass

        # Early connectivity signal for the most common runtime failure path.
        try:
            health = self.ollama_client.health(timeout=4.0)
            if health.get("ok"):
                model = str(self.config.get("llm", {}).get("model", ""))
                names = health.get("models") if isinstance(health.get("models"), list) else []
                if model and names and model not in names:
                    self._screen_log(
                        "chat",
                        f"startup: Ollama reachable at {health.get('url')} but model '{model}' is not pulled.",
                    )
                else:
                    self._screen_log("chat", f"startup: Ollama reachable at {health.get('url')}")
            else:
                self._screen_log(
                    "chat",
                    f"startup: Ollama unavailable at {health.get('url')}: {health.get('error')}",
                )
        except Exception as exc:
            self._screen_log("chat", f"startup: Ollama health check failed: {exc}")

    def _ensure_backend_api_started(self) -> None:
        backend_cfg = self.config.get("backend", {}) if isinstance(self.config, dict) else {}
        health = self.backend_api_client.health(timeout=1.5)
        if health.get("ok"):
            self._screen_log("chat", f"startup: backend API reachable at {health.get('url')}")
            return

        self._screen_log(
            "chat",
            f"startup: backend API unavailable at {health.get('url')}: {health.get('error')}",
        )

        auto_start = bool(backend_cfg.get("auto_start", True))
        if not auto_start:
            return

        raw_command = backend_cfg.get("start_command") or ["./scripts/run_local_backend.sh"]
        if isinstance(raw_command, str):
            command = [token for token in shlex.split(raw_command) if token]
        elif isinstance(raw_command, list):
            command = [str(token).strip() for token in raw_command if str(token).strip()]
        else:
            command = ["./scripts/run_local_backend.sh"]
        if not command:
            command = ["./scripts/run_local_backend.sh"]

        try:
            self._managed_backend_log_path.parent.mkdir(parents=True, exist_ok=True)
            self._managed_backend_log_handle = self._managed_backend_log_path.open("ab")
            self._managed_backend_proc = subprocess.Popen(
                command,
                cwd=str(self.repo_root),
                env=os.environ.copy(),
                stdout=self._managed_backend_log_handle,
                stderr=subprocess.STDOUT,
            )
            self._screen_log("chat", f"startup: launching backend via `{' '.join(command)}`")
        except Exception as exc:
            self._screen_log("chat", f"startup: failed to launch backend API process: {exc}")
            self._shutdown_managed_backend()
            return

        timeout_seconds = float(backend_cfg.get("startup_timeout_seconds", 25) or 25)
        deadline = time.time() + max(1.0, timeout_seconds)
        while time.time() < deadline:
            proc = self._managed_backend_proc
            if proc is None:
                break
            if proc.poll() is not None:
                self._screen_log(
                    "chat",
                    (
                        "startup: backend process exited early "
                        f"(code={proc.returncode}). log={self._managed_backend_log_path}"
                    ),
                )
                return
            time.sleep(0.5)
            health = self.backend_api_client.health(timeout=1.2)
            if health.get("ok"):
                self._screen_log("chat", f"startup: backend API started at {health.get('url')}")
                return

        self._screen_log(
            "chat",
            (
                "startup: backend process launched but health check timed out. "
                f"Check log: {self._managed_backend_log_path}"
            ),
        )

    def _shutdown_managed_backend(self) -> None:
        proc = self._managed_backend_proc
        self._managed_backend_proc = None
        if proc is not None and proc.poll() is None:
            try:
                proc.terminate()
                proc.wait(timeout=5)
            except Exception:
                try:
                    proc.kill()
                    proc.wait(timeout=2)
                except Exception:
                    pass
        handle = self._managed_backend_log_handle
        self._managed_backend_log_handle = None
        if handle is not None:
            try:
                handle.close()
            except Exception:
                pass

    def action_quit(self) -> None:
        self._shutdown_managed_backend()
        self.exit()

    def timestamp(self) -> str:
        return datetime.now().strftime("%Y%m%d_%H%M%S")

    def assistant_line(self, text: str) -> str:
        return f"{self.ASSISTANT_NAME}: {text}"

    @staticmethod
    def _percentile(values: list[float], percentile: float) -> float:
        if not values:
            return 0.0
        ordered = sorted(values)
        if len(ordered) == 1:
            return ordered[0]
        rank = (percentile / 100.0) * (len(ordered) - 1)
        low = int(rank)
        high = min(low + 1, len(ordered) - 1)
        if low == high:
            return ordered[low]
        weight = rank - low
        return ordered[low] * (1.0 - weight) + ordered[high] * weight

    def _record_chat_latency(self, timings: dict[str, float] | None) -> str | None:
        if not timings:
            return None

        for key, bucket in self.chat_latency_samples.items():
            raw = timings.get(key)
            if raw is None:
                continue
            try:
                value = float(raw)
            except Exception:
                continue
            if value < 0:
                continue
            bucket.append(value)
            overflow = len(bucket) - self.chat_latency_window
            if overflow > 0:
                del bucket[:overflow]

        total_samples = self.chat_latency_samples.get("total_ms", [])
        if not total_samples:
            return None

        turn_total = float(timings.get("total_ms", 0.0))
        turn_context = float(timings.get("context_ms", 0.0))
        turn_llm = float(timings.get("llm_ms", 0.0))
        turn_web = float(timings.get("web_ms", 0.0))

        return (
            f"latency(ms): turn chat={turn_total:.1f} context={turn_context:.1f} "
            f"llm={turn_llm:.1f} web={turn_web:.1f} | rolling(n={len(total_samples)}) "
            f"chat p50={self._percentile(total_samples, 50):.1f} p95={self._percentile(total_samples, 95):.1f} "
            f"context p50={self._percentile(self.chat_latency_samples['context_ms'], 50):.1f} "
            f"p95={self._percentile(self.chat_latency_samples['context_ms'], 95):.1f} "
            f"llm p50={self._percentile(self.chat_latency_samples['llm_ms'], 50):.1f} "
            f"p95={self._percentile(self.chat_latency_samples['llm_ms'], 95):.1f}"
        )

    def _screen_log(self, screen_name: str, text: str) -> None:
        try:
            screen = self.get_screen(screen_name)
            screen.query_one("#chat-log", RichLog).write(text)
        except Exception:
            pass

    @staticmethod
    def _chat_log_near_bottom(log: RichLog, tolerance_lines: int = 2) -> bool:
        try:
            offset_obj = getattr(log, "scroll_offset", None)
            offset_y = int(getattr(offset_obj, "y", 0) if offset_obj is not None else 0)
            max_y = int(getattr(log, "max_scroll_y", 0))
            return (max_y - offset_y) <= max(0, tolerance_lines)
        except Exception:
            return True

    @staticmethod
    def _smooth_scroll_to_end(log: RichLog, animate: bool = True) -> None:
        try:
            # Textual versions differ on optional kwargs; try richer signature first.
            log.scroll_end(animate=animate, duration=0.12, easing="out_cubic")
            return
        except TypeError:
            pass
        except Exception:
            return
        try:
            log.scroll_end(animate=animate)
        except Exception:
            pass

    @staticmethod
    def _message_has_explicit_deep_intent(message: str) -> bool:
        text = message.lower()
        explicit_markers = [
            "deep analysis",
            "analyse in depth",
            "analyze in depth",
            "in-depth analysis",
            "full scale analysis",
            "full-scale analysis",
            "extreme analysis",
        ]
        return any(marker in text for marker in explicit_markers)

    def _message_requests_deep_mode(self, message: str) -> bool:
        if self._message_has_explicit_deep_intent(message):
            return True
        if not self.auto_deep_detection_enabled:
            return False
        text = message.lower()
        heuristic_markers = [
            "in depth",
            "detailed analysis",
            "comprehensive analysis",
            "thorough analysis",
            "full analysis",
            "full-scale",
        ]
        return any(marker in text for marker in heuristic_markers)

    @staticmethod
    def _is_source_attribution_request(message: str) -> bool:
        text = message.strip().lower()
        if not text:
            return False
        markers = [
            "where did you get this",
            "where did you get that",
            "where is this from",
            "where is that from",
            "what is this based on",
            "what is that based on",
            "based on what",
            "what are your sources",
            "what sources",
            "show sources",
            "show source",
            "sources?",
            "source?",
            "cite",
            "citation",
        ]
        return any(marker in text for marker in markers)

    def _build_source_attribution_reply(self) -> str:
        latest = self.state_store.get_latest_export(self.thread_id)
        if not latest:
            return "This cannot be verified based on available data. No prior analysis export was found."

        json_path = Path(str(latest.get("json_path", ""))).expanduser()
        if not json_path.exists() or not json_path.is_file():
            return "This cannot be verified based on available data. The latest analysis export file was not found."

        try:
            payload = json.loads(json_path.read_text(encoding="utf-8"))
        except Exception:
            return "This cannot be verified based on available data. The latest analysis export could not be parsed."

        question = str(payload.get("question") or "").strip()
        created_at = str(payload.get("created_at") or latest.get("created_at") or "").strip()
        evidence = payload.get("evidence") if isinstance(payload, dict) else []
        evidence = evidence if isinstance(evidence, list) else []

        sources: list[str] = []
        notes: list[str] = []
        seen: set[str] = set()

        def _add(item: str) -> None:
            key = item.strip()
            if not key or key in seen:
                return
            seen.add(key)
            sources.append(key)

        for ev in evidence:
            if not isinstance(ev, dict):
                continue
            ev_type = str(ev.get("type") or "").strip().lower()
            details = ev.get("details")
            details = details if isinstance(details, dict) else {}

            if ev_type == "web":
                url = str(details.get("url") or "").strip()
                if url:
                    _add(f"Web: {url}")

            docs = details.get("docs")
            if isinstance(docs, list):
                for doc in docs[:8]:
                    if not isinstance(doc, dict):
                        continue
                    title = str(doc.get("title") or doc.get("document_id") or "untitled").strip()
                    published = str(doc.get("published_at") or "").strip()
                    published = published.split(" ")[0] if published else ""
                    url = str(doc.get("source_url") or "").strip()
                    line = f"Doc: {title}"
                    if published:
                        line += f" ({published})"
                    if url:
                        line += f" - {url}"
                    _add(line)

            report_paths = details.get("reports")
            if isinstance(report_paths, list):
                for report in report_paths[:6]:
                    rp = str(report or "").strip()
                    if rp:
                        _add(f"Report: {rp}")

            note = str(details.get("note") or "").strip()
            if note:
                notes.append(note)

        if not sources:
            msg = (
                "This cannot be verified based on available data. "
                "The latest analysis export did not contain concrete source artifacts."
            )
            if notes:
                msg += f" Evidence note: {notes[0]}."
            msg += f" Export JSON: {json_path}"
            return msg

        header = "Latest source trail from the most recent analysis export:"
        if question:
            header += f" question='{question}'"
        if created_at:
            header += f" at {created_at}"
        lines = [header, f"Export JSON: {json_path}"]
        lines.extend(f"- {line}" for line in sources[:12])
        if len(sources) > 12:
            lines.append(f"- ... {len(sources) - 12} more source entries omitted.")
        return "\n".join(lines)

    def _update_chat_mode_widgets(self) -> None:
        try:
            screen = self.get_screen("chat")
            mode_btn = screen.query_one("#chat-toggle-mode", Button)
            auto_btn = screen.query_one("#chat-toggle-auto-deep", Button)
            deep_mode = self.chat_analysis_mode == "deep"
            mode_btn.label = f"Mode: {'Deep' if deep_mode else 'Operational'}"
            mode_btn.variant = "warning" if deep_mode else "primary"
            auto_btn.label = f"Auto-Deep: {'On' if self.auto_deep_detection_enabled else 'Off'}"
            auto_btn.variant = "success" if self.auto_deep_detection_enabled else "default"
        except Exception:
            pass

    def access_state(self) -> dict[str, Any]:
        runtime = self.config.get("runtime", {}) if isinstance(self.config, dict) else {}
        rag_available = any(
            reader is not None
            for reader in (
                getattr(self.tool_router, "qual_context_company_reader", None),
                getattr(self.tool_router, "qual_context_news_reader", None),
                getattr(self.tool_router, "qual_context_reader", None),
            )
        )
        return {
            "web_enabled": bool(self.web_enabled),
            "web_hard_disabled": bool(runtime.get("no_web")),
            "rag_enabled": bool(self.rag_enabled),
            "rag_available": rag_available,
            "db_diagnostic_query_enabled": bool(self.db_diagnostic_query_enabled),
            "read_only": bool(self.read_only),
        }

    def _format_access_status(self) -> str:
        state = self.access_state()
        return (
            "access status:\n"
            f"- web: {'on' if state['web_enabled'] else 'off'}"
            f"{' (locked off by --no-web)' if state['web_hard_disabled'] else ''}\n"
            f"- rag: {'on' if state['rag_enabled'] else 'off'}"
            f"{'' if state['rag_available'] else ' (unavailable: no qualitative context backend)'}\n"
            f"- db diagnostics (/sql): {'on' if state['db_diagnostic_query_enabled'] else 'off'}\n"
            f"- actions: {'read-only' if state['read_only'] else 'read/write with confirmation'}"
        )

    def _build_access_request_preview(self, scope: str, enable: bool = True) -> dict[str, Any] | None:
        key = str(scope or "").strip().lower()
        if key not in {"web", "rag", "dbdiag"}:
            return None
        if key == "web":
            command = ["/web", "on" if enable else "off"]
            impact = "enables external URL fetches for this session" if enable else "disables web fetch for this session"
        elif key == "rag":
            command = ["/rag", "on" if enable else "off"]
            impact = (
                "enables qualitative context retrieval in deep analysis for this session"
                if enable
                else "disables qualitative context retrieval in deep analysis for this session"
            )
        else:
            command = ["/dbdiag", "on" if enable else "off"]
            impact = (
                "enables read-only diagnostic SQL (/sql) for this session"
                if enable
                else "disables read-only diagnostic SQL (/sql) for this session"
            )
        return {
            "action_id": "__access_request__",
            "args": {"scope": key, "enable": bool(enable)},
            "command": command,
            "impact": impact,
            "timeout_seconds": 30,
        }

    def _apply_access_request(self, scope: str, enable: bool) -> str:
        key = str(scope or "").strip().lower()
        if key == "web":
            runtime = self.config.get("runtime", {}) if isinstance(self.config, dict) else {}
            if enable and bool(runtime.get("no_web")):
                return "web is hard-disabled by runtime flag (--no-web). Restart cockpit without --no-web to enable."
            self.web_enabled = bool(enable)
            return "web fetch enabled for this session." if enable else "web fetch disabled for this session."
        if key == "rag":
            rag_available = any(
                reader is not None
                for reader in (
                    getattr(self.tool_router, "qual_context_company_reader", None),
                    getattr(self.tool_router, "qual_context_news_reader", None),
                    getattr(self.tool_router, "qual_context_reader", None),
                )
            )
            if enable and not rag_available:
                return "rag is unavailable in this runtime (qualitative context backend not configured)."
            self.rag_enabled = bool(enable)
            self.tool_router.qual_context_enabled = bool(enable)
            return (
                "rag qualitative context enabled for this session."
                if enable
                else "rag qualitative context disabled for this session."
            )
        if key == "dbdiag":
            self.db_diagnostic_query_enabled = bool(enable)
            return (
                "db diagnostic query mode enabled. Use `/sql tables` or `/sql <select ...>`."
                if enable
                else "db diagnostic query mode disabled."
            )
        return "unsupported access scope request."

    @staticmethod
    def _access_scope_is_enabled(scope: str, state: dict[str, Any]) -> bool:
        return _access_scope_is_enabled_util(scope, state)

    @staticmethod
    def _build_pending_action_payload(action_preview: dict[str, Any], message: str) -> dict[str, Any]:
        return _build_pending_action_payload_util(action_preview, message)

    @classmethod
    def _resolve_confirm_resume_message(
        cls,
        action: dict[str, Any],
        state_after: dict[str, Any],
    ) -> str | None:
        return _resolve_confirm_resume_message_util(action, state_after)

    def _schedule_chat_resume(self, message: str) -> None:
        resume_message = str(message or "").strip()
        if not resume_message:
            return

        async def _resume() -> None:
            timeout_at = time.monotonic() + 3.0
            while self.chat_inflight and time.monotonic() < timeout_at:
                await asyncio.sleep(0.05)
            if self.chat_inflight:
                note = (
                    "Access was approved, but automatic resume timed out. "
                    "Please resend your previous request."
                )
                self._write_log("chat-log", self.assistant_line(note))
                self.state_store.add_chat_message(
                    self.thread_id,
                    "assistant",
                    note,
                    datetime.now(timezone.utc).isoformat(),
                )
                return
            self.submit_chat_message(resume_message)

        asyncio.create_task(_resume())

    def _sql_tables_query(self) -> str:
        db_url = str(self.config.get("db", {}).get("database_url") or self.db_reader.database_url).lower()
        if db_url.startswith("sqlite:"):
            return "select name as table_name from sqlite_master where type='table' order by name"
        return (
            "select table_schema, table_name "
            "from information_schema.tables "
            "where table_schema not in ('information_schema', 'pg_catalog') "
            "order by table_schema, table_name"
        )

    def _schedule_model_status_refresh(self) -> None:
        if self._model_status_refresh_task and not self._model_status_refresh_task.done():
            return
        self._model_status_refresh_task = asyncio.create_task(self._refresh_model_status_widget())

    @staticmethod
    def _collect_system_metrics() -> dict[str, Any]:
        metrics: dict[str, Any] = {
            "cpu_percent": None,
            "ram_percent": None,
            "ram_used_gb": None,
            "ram_total_gb": None,
            "gpus": [],
            "gpu_error": None,
        }

        # CPU/RAM: prefer psutil if available, fallback to /proc + load average.
        try:
            import psutil  # type: ignore

            metrics["cpu_percent"] = float(psutil.cpu_percent(interval=0.1))
            vm = psutil.virtual_memory()
            metrics["ram_percent"] = float(vm.percent)
            metrics["ram_used_gb"] = float(vm.used) / (1024 ** 3)
            metrics["ram_total_gb"] = float(vm.total) / (1024 ** 3)
        except Exception:
            try:
                load1, _, _ = os.getloadavg()
                cpu_count = max(1, int(os.cpu_count() or 1))
                metrics["cpu_percent"] = max(0.0, min(100.0, (float(load1) / float(cpu_count)) * 100.0))
            except Exception:
                pass
            try:
                mem_total_kb = 0.0
                mem_avail_kb = 0.0
                with open("/proc/meminfo", "r", encoding="utf-8") as handle:
                    for line in handle:
                        if line.startswith("MemTotal:"):
                            mem_total_kb = float(line.split()[1])
                        elif line.startswith("MemAvailable:"):
                            mem_avail_kb = float(line.split()[1])
                if mem_total_kb > 0:
                    used_kb = max(0.0, mem_total_kb - mem_avail_kb)
                    metrics["ram_total_gb"] = mem_total_kb / (1024 ** 2)
                    metrics["ram_used_gb"] = used_kb / (1024 ** 2)
                    metrics["ram_percent"] = (used_kb / mem_total_kb) * 100.0
            except Exception:
                pass

        # GPU via nvidia-smi if present.
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
            if proc.returncode == 0:
                rows = [line.strip() for line in (proc.stdout or "").splitlines() if line.strip()]
                gpus: list[dict[str, Any]] = []
                for row in rows:
                    parts = [part.strip() for part in row.split(",")]
                    if len(parts) < 4:
                        continue
                    name = parts[0]
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
                            "name": name,
                            "util_percent": util,
                            "mem_used_mib": mem_used,
                            "mem_total_mib": mem_total,
                        }
                    )
                metrics["gpus"] = gpus
            else:
                err = (proc.stderr or proc.stdout or "").strip()
                metrics["gpu_error"] = err.splitlines()[0] if err else "nvidia-smi failed"
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
        model = str(self.config.get("llm", {}).get("model") or self.ollama_client.model or "unknown")
        endpoint = str(getattr(self.ollama_client, "base_url", "") or self.config.get("llm", {}).get("ollama_url", ""))

        health, sys_metrics = await asyncio.to_thread(self._collect_runtime_snapshot, endpoint)

        lines = [f"Model Runtime  Configured: {model}", f"Endpoint: {endpoint}"]
        if health.get("ok"):
            names = health.get("models") if isinstance(health.get("models"), list) else []
            is_pulled = bool(model and model in names)
            pulled_state = "yes" if is_pulled else "no"
            if names:
                preview = ", ".join(str(name) for name in names[:3])
                if len(names) > 3:
                    preview += f", +{len(names) - 3} more"
            else:
                preview = "none reported"
            lines.append(f"Ollama: reachable | Pulled: {pulled_state}")
            lines.append(f"Installed models: {preview}")
        else:
            error = str(health.get("error") or "unknown error").splitlines()[0]
            if len(error) > 96:
                error = error[:93] + "..."
            lines.append("Ollama: unavailable")
            lines.append(f"Error: {error}")

        cpu = sys_metrics.get("cpu_percent")
        ram_percent = sys_metrics.get("ram_percent")
        ram_used = sys_metrics.get("ram_used_gb")
        ram_total = sys_metrics.get("ram_total_gb")
        if cpu is not None or ram_percent is not None:
            cpu_txt = f"{float(cpu):.1f}%" if cpu is not None else "n/a"
            if ram_used is not None and ram_total is not None and ram_percent is not None:
                ram_txt = f"{float(ram_used):.1f}/{float(ram_total):.1f} GB ({float(ram_percent):.1f}%)"
            elif ram_percent is not None:
                ram_txt = f"{float(ram_percent):.1f}%"
            else:
                ram_txt = "n/a"
            lines.append(f"System: CPU {cpu_txt} | RAM {ram_txt}")

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

    @staticmethod
    def _normalize_watch_ticker(raw: str) -> str | None:
        token = str(raw or "").strip().upper()
        if re.fullmatch(r"[A-Z]{2,5}", token):
            return token
        return None

    def _watch_usage_text(self) -> str:
        return (
            "watchlist commands:\n"
            "- /watch list\n"
            "- /watch add TICKER\n"
            "- /watch remove TICKER\n"
            "- /watch clear\n"
            "- /watch sync"
        )

    def _format_watchlist(self) -> str:
        rows = self.state_store.list_watch_tickers(limit=200)
        if not rows:
            return "watchlist is empty. Use `/watch add TICKER`."
        tickers = [str(row.get("ticker") or "").strip().upper() for row in rows]
        tickers = [t for t in tickers if t]
        return f"watchlist ({len(tickers)}): " + ", ".join(tickers)

    def _handle_watch_command(self, message_norm: str) -> str:
        tokens = [tok for tok in message_norm.strip().split() if tok]
        if len(tokens) <= 1:
            return self._format_watchlist() + "\n\n" + self._watch_usage_text()

        action = tokens[1].strip().lower()
        if action in {"list", "ls"}:
            return self._format_watchlist()

        if action in {"add", "+", "a"}:
            if len(tokens) < 3:
                return "watchlist add requires a ticker.\n" + self._watch_usage_text()
            ticker = self._normalize_watch_ticker(tokens[2])
            if not ticker:
                return f"invalid ticker `{tokens[2]}`. Expected 2-5 letters."
            created_at = datetime.now(timezone.utc).isoformat()
            added = self.state_store.add_watch_ticker(ticker, created_at)
            if added:
                return f"watchlist: added `{ticker}`.\n" + self._format_watchlist()
            return f"watchlist: `{ticker}` already present.\n" + self._format_watchlist()

        if action in {"remove", "rm", "del", "delete"}:
            if len(tokens) < 3:
                return "watchlist remove requires a ticker.\n" + self._watch_usage_text()
            ticker = self._normalize_watch_ticker(tokens[2])
            if not ticker:
                return f"invalid ticker `{tokens[2]}`. Expected 2-5 letters."
            removed = self.state_store.remove_watch_ticker(ticker)
            if removed:
                return f"watchlist: removed `{ticker}`.\n" + self._format_watchlist()
            return f"watchlist: `{ticker}` was not present.\n" + self._format_watchlist()

        if action in {"clear", "reset"}:
            removed = self.state_store.clear_watch_tickers()
            return f"watchlist cleared ({removed} removed)."

        fallback_ticker = self._normalize_watch_ticker(action)
        if fallback_ticker:
            created_at = datetime.now(timezone.utc).isoformat()
            added = self.state_store.add_watch_ticker(fallback_ticker, created_at)
            if added:
                return f"watchlist: added `{fallback_ticker}`.\n" + self._format_watchlist()
            return f"watchlist: `{fallback_ticker}` already present.\n" + self._format_watchlist()

        return "unknown /watch command.\n" + self._watch_usage_text()

    @staticmethod
    def _alerts_usage_text() -> str:
        return (
            "alerts commands:\n"
            "- /alerts                (evaluate watchlist)\n"
            "- /alerts TICKER         (evaluate one ticker)\n"
            "- /alerts thresholds"
        )

    @staticmethod
    def _alert_thresholds() -> dict[str, float]:
        return dict(DEFAULT_ALERT_THRESHOLDS)

    def _collect_alert_results(self, tickers: list[str]) -> list[dict[str, Any]]:
        out: list[dict[str, Any]] = []
        thresholds = self._alert_thresholds()
        for ticker in tickers:
            state = self.tool_router.get_price_state(ticker=ticker, deep_mode=False)
            evaluated = evaluate_price_state_alerts(state, thresholds=thresholds)
            out.append(
                {
                    "ticker": ticker,
                    "state": state,
                    "evaluated": evaluated,
                }
            )
        out.sort(key=lambda item: float((item.get("evaluated") or {}).get("score") or 0.0), reverse=True)
        return out

    def _format_alerts_thresholds(self) -> str:
        t = self._alert_thresholds()
        return (
            "alerts thresholds:\n"
            f"- abs(1D return) >= {t['ret_1d_abs']:.2f}%\n"
            f"- abs(20D return) >= {t['ret_20d_abs']:.2f}%\n"
            f"- 20D annualized volatility >= {t['vol_20d_ann']:.2f}%\n"
            f"- drawdown from 63D high <= {t['drawdown_63d']:.2f}%\n"
            "- stale_data = critical"
        )

    async def _handle_alerts_command(self, message_norm: str) -> str:
        tokens = [tok for tok in message_norm.strip().split() if tok]
        if len(tokens) <= 1:
            watch_rows = self.state_store.list_watch_tickers(limit=200)
            tickers = [str(row.get("ticker") or "").strip().upper() for row in watch_rows]
            tickers = [t for t in tickers if t]
        else:
            arg = tokens[1].strip().lower()
            if arg in {"thresholds", "config", "settings"}:
                return self._format_alerts_thresholds()
            if arg in {"help", "h", "?"}:
                return self._alerts_usage_text()
            ticker = self._normalize_watch_ticker(tokens[1])
            if ticker:
                tickers = [ticker]
            else:
                return "invalid /alerts target.\n" + self._alerts_usage_text()

        if not tickers:
            return "alerts: watchlist is empty. Add with `/watch add TICKER`."

        results = await asyncio.to_thread(self._collect_alert_results, tickers)
        triggered = [row for row in results if ((row.get("evaluated") or {}).get("alerts") or [])]
        lines = [f"alerts: checked {len(results)} ticker(s)."]
        if not triggered:
            lines.append("No alert triggers at current thresholds.")
        else:
            lines.append(f"Triggered: {len(triggered)} ticker(s).")
            for row in triggered[:25]:
                ticker = str(row.get("ticker") or "").strip().upper()
                evaluated = row.get("evaluated") if isinstance(row.get("evaluated"), dict) else {}
                alerts = evaluated.get("alerts") if isinstance(evaluated.get("alerts"), list) else []
                messages = [str(item.get("message") or "").strip() for item in alerts if isinstance(item, dict)]
                messages = [m for m in messages if m]
                lines.append(f"- {ticker}: " + "; ".join(messages))

        quiet = [row for row in results if not ((row.get("evaluated") or {}).get("alerts") or [])]
        if quiet:
            symbols = [str(row.get("ticker") or "").strip().upper() for row in quiet[:10]]
            symbols = [s for s in symbols if s]
            if symbols:
                lines.append("No triggers: " + ", ".join(symbols))
        lines.append(self._format_alerts_thresholds())
        return "\n".join(lines)

    @staticmethod
    def _changes_usage_text() -> str:
        return (
            "changes commands:\n"
            "- /changes TICKER\n"
            "- /changes                 (uses last detected ticker if available)"
        )

    @staticmethod
    def _parse_bool_like(value: Any, default: bool = False) -> bool:
        if isinstance(value, bool):
            return value
        if value is None:
            return default
        text = str(value).strip().lower()
        if text in {"1", "true", "yes", "on", "y", "ok"}:
            return True
        if text in {"0", "false", "no", "off", "n"}:
            return False
        return default

    def _format_actions_catalog(self) -> str:
        specs = self.action_registry.list_actions()
        lines = [f"actions ({len(specs)}):"]
        for spec in specs:
            mode = "mutating" if spec.is_mutating else "read-only"
            lines.append(f"- {spec.id}: {spec.label} [{mode}]")
        lines.append("usage: /run <action_id> key=value ... [dry_run=true]")
        lines.append("usage: /actions doctor [check_help=true|false] [action_id=<id>]")
        return "\n".join(lines)

    @staticmethod
    def _format_actions_doctor_report(report: dict[str, Any]) -> str:
        counts = report.get("counts") if isinstance(report.get("counts"), dict) else {}
        total = int(counts.get("total") or 0)
        ok_count = int(counts.get("ok") or 0)
        failed = int(counts.get("failed") or 0)
        check_help = bool(report.get("check_help"))
        lines = [
            f"actions doctor: ok={bool(report.get('ok'))} checked={total} passed={ok_count} failed={failed} check_help={check_help}"
        ]
        overlaps = report.get("overlaps") if isinstance(report.get("overlaps"), list) else []
        if overlaps:
            lines.append("overlaps:")
            for row in overlaps[:10]:
                if not isinstance(row, dict):
                    continue
                script = str(row.get("script") or "").strip()
                actions = row.get("actions") if isinstance(row.get("actions"), list) else []
                lines.append(f"- {script}: {', '.join(str(item) for item in actions)}")
        checks = report.get("checks") if isinstance(report.get("checks"), list) else []
        for row in checks[:30]:
            if not isinstance(row, dict):
                continue
            status = "ok" if bool(row.get("ok")) else "fail"
            aid = str(row.get("action_id") or "unknown")
            line = f"- {aid}: {status}"
            if row.get("help_returncode") is not None:
                line += f" help_rc={row.get('help_returncode')}"
            if row.get("error"):
                line += f" error={row.get('error')}"
            lines.append(line)
            no_effect = row.get("bool_args_no_effect") if isinstance(row.get("bool_args_no_effect"), list) else []
            if no_effect:
                lines.append(f"  no-effect bool args: {', '.join(str(arg) for arg in no_effect)}")
        if len(checks) > 30:
            lines.append(f"... {len(checks) - 30} more action check rows")
        return "\n".join(lines)

    @staticmethod
    def _normalize_update_status(status: str | None) -> str:
        return _normalize_update_status_util(status)

    @classmethod
    def _is_successful_update_status(cls, status: str | None) -> bool:
        return _is_successful_update_status_util(status)

    def _latest_update_job_status(self, action_id: str, ticker: str) -> str | None:
        ticker_norm = str(ticker or "").strip().upper()
        for row in self.state_store.list_jobs(limit=50):
            if not isinstance(row, dict):
                continue
            if str(row.get("action_id") or "") != str(action_id or ""):
                continue
            args = row.get("args") if isinstance(row.get("args"), dict) else {}
            job_ticker = str(args.get("ticker") or "").strip().upper()
            if ticker_norm and job_ticker != ticker_norm:
                continue
            return self._normalize_update_status(str(row.get("status") or ""))
        return None

    def _record_update_event(
        self,
        ticker: str,
        action_id: str,
        status: str,
        summary_text: str,
        delta_payload: dict[str, Any],
    ) -> None:
        self.state_store.add_update_event(
            thread_id=self.thread_id,
            ticker=ticker,
            action_id=action_id,
            status=status,
            summary={
                "text": summary_text,
                "delta": delta_payload,
                "action": {
                    "action_id": action_id,
                    "ticker": ticker,
                },
            },
            created_at=datetime.now(timezone.utc).isoformat(),
        )

    def _compute_reactions_for_docs(self, ticker: str, docs: list[dict[str, Any]]) -> dict[str, Any]:
        ticker_norm = str(ticker or "").strip().upper()
        if not ticker_norm:
            return {"ok": False, "error": "ticker is required", "rows": []}
        if not docs:
            return {"ok": True, "rows": []}

        result = self.backend_api_client.get_price(
            ticker=ticker_norm,
            exchange="ASX",
            range_="1y",
            interval="1d",
            timeout=15.0,
        )
        if not result.get("ok"):
            return {"ok": False, "error": str(result.get("error") or "price lookup failed"), "rows": []}

        payload = result.get("payload")
        payload = payload if isinstance(payload, dict) else {}
        close_series = _build_close_series_util(payload)
        if not close_series:
            return {"ok": False, "error": "no close history returned", "rows": []}

        rows: list[dict[str, Any]] = []
        for row in docs[:25]:
            if not isinstance(row, dict):
                continue
            published = _parse_timestamp_utc_util(row.get("published_at"))
            if published is None:
                continue
            reaction = _compute_reaction_for_time_util(close_series, published_at=published)
            if not isinstance(reaction, dict):
                continue
            rows.append(
                {
                    "document_id": row.get("document_id"),
                    "published_at": row.get("published_at"),
                    "title": row.get("title"),
                    "ret_1d": reaction.get("ret_1d"),
                    "ret_5d": reaction.get("ret_5d"),
                    "ret_20d": reaction.get("ret_20d"),
                }
            )
        rows.sort(key=lambda item: abs(float(item.get("ret_1d") or 0.0)), reverse=True)
        return {"ok": True, "rows": rows}

    async def _handle_changes_command(self, message_norm: str) -> str:
        tokens = [tok for tok in message_norm.strip().split() if tok]
        if len(tokens) <= 1:
            ticker = self.last_detected_ticker
        else:
            ticker = self._normalize_watch_ticker(tokens[1])
        if not ticker:
            return "changes requires a ticker.\n" + self._changes_usage_text()

        events = self.state_store.list_update_events(
            thread_id=self.thread_id,
            ticker=ticker,
            limit=20,
        )
        successful_events = [
            row
            for row in events
            if isinstance(row, dict) and self._is_successful_update_status(str(row.get("status") or ""))
        ]
        if not successful_events:
            return (
                f"No completed update history found for {ticker}. "
                f"Run `update {ticker} announcements now` then `/confirm` first."
            )

        event = successful_events[0]
        summary = event.get("summary") if isinstance(event.get("summary"), dict) else {}
        delta = summary.get("delta") if isinstance(summary.get("delta"), dict) else {}
        created_at = str(event.get("created_at") or "").strip()
        before_sync = delta.get("announcement_sync_before") if isinstance(delta.get("announcement_sync_before"), dict) else {}
        after_sync = delta.get("announcement_sync_after") if isinstance(delta.get("announcement_sync_after"), dict) else {}
        counts = delta.get("doc_counts") if isinstance(delta.get("doc_counts"), dict) else {}
        new_docs = delta.get("new_announcements") if isinstance(delta.get("new_announcements"), list) else []

        lines = [f"Latest changes for {ticker} (last completed update: {created_at or 'unknown time'}):"]
        lines.append(f"- Freshness: before {self._sync_human(before_sync)} -> after {self._sync_human(after_sync)}")
        if counts:
            lines.append(
                f"- Doc counts: before {counts.get('before')}, after {counts.get('after')}, new {counts.get('new')}"
            )
        else:
            lines.append("- Doc counts: unavailable")

        if new_docs:
            lines.append(f"- New announcements ({len(new_docs)}):")
            for row in new_docs[:8]:
                if not isinstance(row, dict):
                    continue
                date = str(row.get("published_at") or "").split(" ")[0]
                doc_class = str(row.get("doc_class") or "").strip().lower()
                title = str(row.get("title") or row.get("document_id") or "Untitled").strip()
                prefix = f"  - {date}: " if date else "  - "
                if doc_class:
                    prefix += f"[{doc_class}] "
                lines.append(prefix + title)
            if len(new_docs) > 8:
                lines.append(f"  - ... {len(new_docs) - 8} more")
        else:
            lines.append("- New announcements: none in the last completed update.")

        reactions = await asyncio.to_thread(self._compute_reactions_for_docs, ticker, new_docs)
        if reactions.get("ok"):
            rows = reactions.get("rows") if isinstance(reactions.get("rows"), list) else []
            if rows:
                lines.append("- Market reaction (top by |1D|):")
                for row in rows[:3]:
                    try:
                        ret_1d = f"{float(row.get('ret_1d')):+.2f}%"
                    except Exception:
                        ret_1d = "n/a"
                    try:
                        ret_5d = f"{float(row.get('ret_5d')):+.2f}%"
                    except Exception:
                        ret_5d = "n/a"
                    title = str(row.get("title") or row.get("document_id") or "Untitled").strip()
                    lines.append(f"  - {title}: 1D {ret_1d}, 5D {ret_5d}")
            else:
                lines.append("- Market reaction: no calculable reaction rows for the new announcements window.")
        else:
            lines.append(f"- Market reaction unavailable: {reactions.get('error')}")

        if len(successful_events) > 1:
            prev = successful_events[1]
            prev_time = str(prev.get("created_at") or "").strip()
            if prev_time:
                lines.append(f"- Previous completed update: {prev_time}")
        return "\n".join(lines)

    async def _handle_watch_sync_command(self, message_norm: str, log_target: str) -> str:
        _ = message_norm
        watch_rows = self.state_store.list_watch_tickers(limit=200)
        tickers = [str(row.get("ticker") or "").strip().upper() for row in watch_rows]
        tickers = [t for t in tickers if t]
        if not tickers:
            return "watch sync: watchlist is empty. Add tickers with `/watch add TICKER`."

        summary_lines = [f"watch sync starting for {len(tickers)} ticker(s): {', '.join(tickers)}"]
        completed = 0
        for ticker in tickers:
            before_snapshot = self._collect_announcement_sync_snapshot(ticker=ticker)
            args = {"ticker": ticker, "years": 1, "process_documents": True}
            started = await self.execute_action(
                "update_ticker_financials",
                args,
                log_target=log_target,
                skip_confirm=True,
                wait_for_completion=True,
            )
            if not started:
                summary_lines.append(f"- {ticker}: skipped (action did not start).")
                continue

            status = self._latest_update_job_status("update_ticker_financials", ticker=ticker) or "unknown"
            after_snapshot = self._collect_announcement_sync_snapshot(ticker=ticker)
            delta_text, delta_payload = self._build_announcement_update_delta_summary(
                ticker=ticker,
                before=before_snapshot,
                after=after_snapshot,
            )
            self._write_action_delta_export(
                question=f"/watch sync ticker={ticker}",
                answer=delta_text,
                action={"action_id": "update_ticker_financials", "args": args},
                delta_payload=delta_payload,
            )
            self._record_update_event(
                ticker=ticker,
                action_id="update_ticker_financials",
                status=status,
                summary_text=delta_text,
                delta_payload=delta_payload,
            )
            if self._is_successful_update_status(status):
                completed += 1
            new_count = int((delta_payload.get("doc_counts") or {}).get("new") or 0)
            summary_lines.append(f"- {ticker}: status={status}, new={new_count}, after={self._sync_human(after_snapshot.get('sync', {}))}")

        summary_lines.append(f"watch sync finished: {completed}/{len(tickers)} completed.")
        return "\n".join(summary_lines)

    @staticmethod
    def _doc_delta_key(row: dict[str, Any]) -> str:
        return _doc_delta_key_util(row)

    @staticmethod
    def _compact_doc_row(row: dict[str, Any]) -> dict[str, Any]:
        return _compact_doc_row_util(row)

    def _collect_announcement_sync_snapshot(self, ticker: str) -> dict[str, Any]:
        ticker_norm = str(ticker or "").strip().upper()
        docs = self.db_reader.get_docs(ticker=ticker_norm, limit=80)
        sync = self.chat_controller._compute_announcement_sync_status(
            ticker=ticker_norm,
            docs=docs if isinstance(docs, list) else [],
            message="latest announcements",
        )
        return {
            "ticker": ticker_norm,
            "docs": docs if isinstance(docs, list) else [],
            "sync": sync if isinstance(sync, dict) else {},
            "doc_count": len(docs) if isinstance(docs, list) else 0,
        }

    @staticmethod
    def _sync_human(sync: dict[str, Any]) -> str:
        return _sync_human_util(sync)

    def _build_announcement_update_delta_summary(
        self,
        ticker: str,
        before: dict[str, Any],
        after: dict[str, Any],
    ) -> tuple[str, dict[str, Any]]:
        return _build_update_delta_summary(ticker=ticker, before=before, after=after)

    def _write_action_delta_export(
        self,
        question: str,
        answer: str,
        action: dict[str, Any],
        delta_payload: dict[str, Any],
    ) -> None:
        export_payload = {
            "question": question,
            "answer": answer,
            "evidence": [{"type": "local_context", "details": delta_payload}],
            "actions_taken": [
                {
                    "action_id": action.get("action_id"),
                    "args": action.get("args"),
                    "executed": True,
                }
            ],
            "sources": ["local_context"],
            "timings": {},
            "analysis_mode": self.chat_analysis_mode,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        md_path, json_path = self.artifacts.write_analysis(self.thread_id, question, answer, export_payload)
        self.state_store.add_export(self.thread_id, question, md_path, json_path, datetime.now(timezone.utc).isoformat())

    def write_report_json(self, rel_path: str, payload: dict[str, Any]) -> str:
        return self.artifacts.write_json(rel_path, payload)

    def submit_chat_message(self, message: str) -> None:
        if self.chat_inflight:
            self._write_log("chat-log", self.assistant_line("Previous response is still running. Please wait."))
            return
        self.chat_cancel_requested = False
        self.active_chat_task = asyncio.create_task(self.handle_chat_message(message))

    async def handle_chat_message(self, message: str) -> None:
        if self.chat_inflight:
            self._write_log("chat-log", self.assistant_line("Previous response is still running. Please wait."))
            return
        self.chat_inflight = True
        self.chat_cancel_requested = False
        chat = self.get_screen("chat")
        log = chat.query_one("#chat-log", RichLog)
        status = chat.query_one("#chat-status", Static)
        pending = chat.query_one("#chat-pending")
        follow_stream = self._chat_log_near_bottom(log, tolerance_lines=3)

        created = datetime.now(timezone.utc).isoformat()
        self.state_store.add_chat_message(self.thread_id, "user", message, created)
        log.write(f"user: {message}")
        if follow_stream:
            self._smooth_scroll_to_end(log, animate=True)
        await asyncio.sleep(0)
        message_norm = message.strip()
        message_lower = message_norm.lower()
        conversational_command = derive_conversational_command(message_norm)
        if conversational_command:
            message_norm = conversational_command
            message_lower = message_norm.lower()
        message_norm = _resolve_pending_action_alias_util(message_norm, bool(self.pending_action))
        message_lower = message_norm.lower()

        try:
            if message_lower.startswith("/watch sync"):
                text = await self._handle_watch_sync_command(message_norm, log_target="chat-log")
                log.write(self.assistant_line(text))
                self.state_store.add_chat_message(self.thread_id, "assistant", text, datetime.now(timezone.utc).isoformat())
                return

            if message_lower.startswith("/watch"):
                text = self._handle_watch_command(message_norm)
                log.write(self.assistant_line(text))
                self.state_store.add_chat_message(self.thread_id, "assistant", text, datetime.now(timezone.utc).isoformat())
                return

            if message_lower.startswith("/changes"):
                text = await self._handle_changes_command(message_norm)
                log.write(self.assistant_line(text))
                self.state_store.add_chat_message(self.thread_id, "assistant", text, datetime.now(timezone.utc).isoformat())
                return

            if message_lower.startswith("/alerts"):
                text = await self._handle_alerts_command(message_norm)
                log.write(self.assistant_line(text))
                self.state_store.add_chat_message(self.thread_id, "assistant", text, datetime.now(timezone.utc).isoformat())
                return

            if message_lower in {"/access", "/access status"}:
                text = self._format_access_status()
                log.write(self.assistant_line(text))
                self.state_store.add_chat_message(self.thread_id, "assistant", text, datetime.now(timezone.utc).isoformat())
                return

            if message_lower.startswith("/request-access"):
                scope = message_norm[len("/request-access"):].strip().lower()
                preview = self._build_access_request_preview(scope, enable=True)
                if not preview:
                    text = "usage: `/request-access web|rag|dbdiag`"
                    log.write(self.assistant_line(text))
                    self.state_store.add_chat_message(self.thread_id, "assistant", text, datetime.now(timezone.utc).isoformat())
                    return
                self.pending_action = {
                    "action_id": preview["action_id"],
                    "args": preview["args"],
                }
                text = (
                    f"Access request prepared: {scope} enable. "
                    "Use /confirm to apply or /cancel to skip."
                )
                log.write(self.assistant_line(text))
                pending.update(
                    "Pending: "
                    f"{preview['action_id']} "
                    f"args={preview['args']} "
                    "(/confirm or /cancel)"
                )
                self.state_store.add_chat_message(self.thread_id, "assistant", text, datetime.now(timezone.utc).isoformat())
                return

            if message_lower in {"/web", "/web status"}:
                text = self._format_access_status()
                log.write(self.assistant_line(text))
                self.state_store.add_chat_message(self.thread_id, "assistant", text, datetime.now(timezone.utc).isoformat())
                return

            if message_lower == "/web on":
                text = self._apply_access_request("web", True)
                log.write(self.assistant_line(text))
                self.state_store.add_chat_message(self.thread_id, "assistant", text, datetime.now(timezone.utc).isoformat())
                return

            if message_lower == "/web off":
                text = self._apply_access_request("web", False)
                log.write(self.assistant_line(text))
                self.state_store.add_chat_message(self.thread_id, "assistant", text, datetime.now(timezone.utc).isoformat())
                return

            if message_lower in {"/rag", "/rag status"}:
                text = self._format_access_status()
                log.write(self.assistant_line(text))
                self.state_store.add_chat_message(self.thread_id, "assistant", text, datetime.now(timezone.utc).isoformat())
                return

            if message_lower == "/rag on":
                text = self._apply_access_request("rag", True)
                log.write(self.assistant_line(text))
                self.state_store.add_chat_message(self.thread_id, "assistant", text, datetime.now(timezone.utc).isoformat())
                return

            if message_lower == "/rag off":
                text = self._apply_access_request("rag", False)
                log.write(self.assistant_line(text))
                self.state_store.add_chat_message(self.thread_id, "assistant", text, datetime.now(timezone.utc).isoformat())
                return

            if message_lower in {"/dbdiag", "/dbdiag status"}:
                text = self._format_access_status()
                log.write(self.assistant_line(text))
                self.state_store.add_chat_message(self.thread_id, "assistant", text, datetime.now(timezone.utc).isoformat())
                return

            if message_lower == "/dbdiag on":
                text = self._apply_access_request("dbdiag", True)
                log.write(self.assistant_line(text))
                self.state_store.add_chat_message(self.thread_id, "assistant", text, datetime.now(timezone.utc).isoformat())
                return

            if message_lower == "/dbdiag off":
                text = self._apply_access_request("dbdiag", False)
                log.write(self.assistant_line(text))
                self.state_store.add_chat_message(self.thread_id, "assistant", text, datetime.now(timezone.utc).isoformat())
                return

            if message_lower.startswith("/sql"):
                if not self.db_diagnostic_query_enabled:
                    text = "db diagnostic query mode is off. Run `/dbdiag on` first."
                    log.write(self.assistant_line(text))
                    self.state_store.add_chat_message(self.thread_id, "assistant", text, datetime.now(timezone.utc).isoformat())
                    return

                raw = message_norm[len("/sql"):].strip()
                if not raw:
                    text = "usage: `/sql tables` or `/sql <SELECT ...> [max_rows=N]`"
                    log.write(self.assistant_line(text))
                    self.state_store.add_chat_message(self.thread_id, "assistant", text, datetime.now(timezone.utc).isoformat())
                    return

                max_rows = 50
                if " max_rows=" in raw:
                    head, tail = raw.rsplit(" max_rows=", 1)
                    raw = head.strip()
                    try:
                        max_rows = max(1, min(500, int(tail.strip())))
                    except Exception:
                        max_rows = 50
                query_text = self._sql_tables_query() if raw.strip().lower() == "tables" else raw
                result = self.db_reader.run_diagnostic_query(query_text, limit=max_rows)
                rendered = json.dumps(result, default=str, indent=2)
                if len(rendered) > 14000:
                    rendered = rendered[:14000] + "\n... (truncated)"
                log.write(self.assistant_line(rendered))
                self.state_store.add_chat_message(
                    self.thread_id,
                    "assistant",
                    f"/sql executed ok={bool(result.get('ok'))} rows={result.get('row_count')}",
                    datetime.now(timezone.utc).isoformat(),
                )
                return

            if message_lower in {"/mode", "/chat-mode"}:
                text = (
                    "chat mode is "
                    f"{self.chat_analysis_mode}. Use /mode deep for full analysis or /mode operational for normal chat."
                )
                log.write(self.assistant_line(text))
                self.state_store.add_chat_message(self.thread_id, "assistant", text, datetime.now(timezone.utc).isoformat())
                return

            if message_lower in {"/mode deep", "/mode full", "/deep on"}:
                self.chat_analysis_mode = "deep"
                self._update_chat_mode_widgets()
                text = "chat mode set to deep (full-scale analysis, minimal context truncation)."
                log.write(self.assistant_line(text))
                self.state_store.add_chat_message(self.thread_id, "assistant", text, datetime.now(timezone.utc).isoformat())
                return

            if message_lower in {"/mode operational", "/mode normal", "/deep off"}:
                self.chat_analysis_mode = "operational"
                self._update_chat_mode_widgets()
                text = "chat mode set to operational (conversational/ops optimized)."
                log.write(self.assistant_line(text))
                self.state_store.add_chat_message(self.thread_id, "assistant", text, datetime.now(timezone.utc).isoformat())
                return

            if message_lower in {"/auto-deep", "/autodeep"}:
                text = (
                    "auto-deep is "
                    f"{'enabled' if self.auto_deep_detection_enabled else 'disabled'}. "
                    "Use /auto-deep on or /auto-deep off."
                )
                log.write(self.assistant_line(text))
                self.state_store.add_chat_message(self.thread_id, "assistant", text, datetime.now(timezone.utc).isoformat())
                return

            if message_lower in {"/auto-deep on", "/autodeep on"}:
                self.auto_deep_detection_enabled = True
                self._update_chat_mode_widgets()
                text = "auto-deep enabled."
                log.write(self.assistant_line(text))
                self.state_store.add_chat_message(self.thread_id, "assistant", text, datetime.now(timezone.utc).isoformat())
                return

            if message_lower in {"/auto-deep off", "/autodeep off"}:
                self.auto_deep_detection_enabled = False
                self._update_chat_mode_widgets()
                text = "auto-deep disabled."
                log.write(self.assistant_line(text))
                self.state_store.add_chat_message(self.thread_id, "assistant", text, datetime.now(timezone.utc).isoformat())
                return

            if message_lower.startswith("/actions"):
                raw = message_norm[len("/actions"):].strip()
                if not raw or raw.lower() in {"list", "ls"}:
                    text = self._format_actions_catalog()
                    log.write(self.assistant_line(text))
                    self.state_store.add_chat_message(self.thread_id, "assistant", text, datetime.now(timezone.utc).isoformat())
                    return
                if raw.lower().startswith("doctor"):
                    doctor_raw = raw[len("doctor"):].strip()
                    doctor_args = self.action_registry.parse_kv_args(doctor_raw)
                    check_help = self._parse_bool_like(doctor_args.get("check_help"), default=True)
                    action_filter = str(doctor_args.get("action_id") or doctor_args.get("action") or "").strip() or None
                    start_line = "running actions doctor..."
                    log.write(self.assistant_line(start_line))
                    self.state_store.add_chat_message(
                        self.thread_id,
                        "assistant",
                        start_line,
                        datetime.now(timezone.utc).isoformat(),
                    )
                    try:
                        report = await asyncio.to_thread(self.action_registry.doctor, check_help, action_filter)
                    except Exception as exc:
                        text = f"actions doctor failed: {exc}"
                        log.write(self.assistant_line(text))
                        self.state_store.add_chat_message(
                            self.thread_id,
                            "assistant",
                            text,
                            datetime.now(timezone.utc).isoformat(),
                        )
                        return
                    text = self._format_actions_doctor_report(report)
                    log.write(self.assistant_line(text))
                    self.state_store.add_chat_message(self.thread_id, "assistant", text, datetime.now(timezone.utc).isoformat())
                    return
                text = "usage: /actions [list|doctor check_help=true|false action_id=<id>]"
                log.write(self.assistant_line(text))
                self.state_store.add_chat_message(self.thread_id, "assistant", text, datetime.now(timezone.utc).isoformat())
                return

            if message_norm == "/cancel":
                self.pending_action = None
                pending.update("No pending action")
                log.write(self.assistant_line("Pending action canceled."))
                self.state_store.add_chat_message(self.thread_id, "assistant", "Pending action canceled.", datetime.now(timezone.utc).isoformat())
                return

            if message_norm == "/confirm":
                if not self.pending_action:
                    log.write(self.assistant_line("No pending action."))
                    return
                action = self.pending_action
                self.pending_action = None
                pending.update("No pending action")
                action_id = str(action.get("action_id") or "").strip()
                action_args = action.get("args") if isinstance(action.get("args"), dict) else {}
                if action_id == "__access_request__":
                    scope = str(action_args.get("scope") or "").strip().lower()
                    enable = bool(action_args.get("enable", True))
                    text = self._apply_access_request(scope, enable)
                    log.write(self.assistant_line(text))
                    self.state_store.add_chat_message(self.thread_id, "assistant", text, datetime.now(timezone.utc).isoformat())
                    resume_message = self._resolve_confirm_resume_message(action, state_after=self.access_state())
                    if resume_message:
                        resume_note = "Access approved. Re-running your previous request automatically."
                        log.write(self.assistant_line(resume_note))
                        self.state_store.add_chat_message(
                            self.thread_id,
                            "assistant",
                            resume_note,
                            datetime.now(timezone.utc).isoformat(),
                        )
                        self._schedule_chat_resume(resume_message)
                    return
                ticker = str(action_args.get("ticker") or "").strip().upper()
                before_snapshot: dict[str, Any] | None = None
                wait_for_completion = False
                if action_id == "update_ticker_financials" and ticker:
                    before_snapshot = self._collect_announcement_sync_snapshot(ticker=ticker)
                    wait_for_completion = True
                started = await self.execute_action(
                    action_id,
                    action_args,
                    log_target="chat-log",
                    skip_confirm=True,
                    wait_for_completion=wait_for_completion,
                )
                if not started:
                    return
                if action_id == "update_ticker_financials" and ticker and before_snapshot is not None:
                    status = self._latest_update_job_status("update_ticker_financials", ticker=ticker) or "unknown"
                    if not self._is_successful_update_status(status):
                        summary_text = f"Update finished with status={status} for {ticker}. Delta summary skipped."
                        log.write(self.assistant_line(summary_text))
                        self.state_store.add_chat_message(
                            self.thread_id,
                            "assistant",
                            summary_text,
                            datetime.now(timezone.utc).isoformat(),
                        )
                        self._record_update_event(
                            ticker=ticker,
                            action_id="update_ticker_financials",
                            status=status,
                            summary_text=summary_text,
                            delta_payload={
                                "ticker": ticker,
                                "doc_counts": {},
                                "new_announcements": [],
                            },
                        )
                        return
                    after_snapshot = self._collect_announcement_sync_snapshot(ticker=ticker)
                    summary_text, delta_payload = self._build_announcement_update_delta_summary(
                        ticker=ticker,
                        before=before_snapshot,
                        after=after_snapshot,
                    )
                    log.write(self.assistant_line(summary_text))
                    self.state_store.add_chat_message(
                        self.thread_id,
                        "assistant",
                        summary_text,
                        datetime.now(timezone.utc).isoformat(),
                    )
                    self._write_action_delta_export(
                        question=f"/confirm {action_id} ticker={ticker}",
                        answer=summary_text,
                        action={"action_id": action_id, "args": action_args},
                        delta_payload=delta_payload,
                    )
                    self._record_update_event(
                        ticker=ticker,
                        action_id="update_ticker_financials",
                        status=status,
                        summary_text=summary_text,
                        delta_payload=delta_payload,
                    )
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
                    text = f"/read failed: {result.get('error')}"
                    log.write(self.assistant_line(text))
                    self.state_store.add_chat_message(self.thread_id, "assistant", text, datetime.now(timezone.utc).isoformat())
                    return

                snippet = (
                    f"Loaded {result['path']} "
                    f"(returned {result['chars_returned']} chars"
                    f"{', truncated' if result['truncated'] else ''}).\n"
                    f"{result['content']}"
                )
                log.write(self.assistant_line(snippet[:14000]))
                self.state_store.add_chat_message(
                    self.thread_id,
                    "assistant",
                    f"/read loaded {result['path']} ({result['chars_returned']} chars)",
                    datetime.now(timezone.utc).isoformat(),
                )
                return

            if message_norm.startswith("/prompt"):
                prompt = str(self.last_prompt or "").strip()
                if not prompt:
                    text = (
                        "No stored prompt yet. "
                        "Run a deep analysis first (for example: `deep analysis analyse BHP`) and then use `/prompt`."
                    )
                    log.write(self.assistant_line(text))
                    self.state_store.add_chat_message(self.thread_id, "assistant", text, datetime.now(timezone.utc).isoformat())
                    return

                ts = self.timestamp()
                out_dir = (self.repo_root / "reports" / "cockpit" / "prompts").resolve()
                out_dir.mkdir(parents=True, exist_ok=True)
                out_path = out_dir / f"prompt_{ts}.txt"
                out_path.write_text(prompt, encoding="utf-8")

                copied = self._copy_to_clipboard(prompt)
                if copied:
                    text = f"Copied last LLM prompt to clipboard. Also wrote: {out_path}"
                else:
                    text = f"Clipboard unavailable. Wrote last LLM prompt: {out_path}"
                log.write(self.assistant_line(text))
                self.state_store.add_chat_message(self.thread_id, "assistant", text, datetime.now(timezone.utc).isoformat())
                return

            if self._is_source_attribution_request(message_norm):
                text = self._build_source_attribution_reply()
                log.write(self.assistant_line(text))
                self.state_store.add_chat_message(self.thread_id, "assistant", text, datetime.now(timezone.utc).isoformat())
                return

            stream_buffer: list[str] = []
            stream_rendered_lines = 0
            last_render_at = 0.0
            first_chunk_seen = False
            spinner_active = True
            spinner_frames = ["|", "/", "-", "\\"]
            spinner_task: asyncio.Task[None] | None = None

            def _render_stream_to_log() -> None:
                nonlocal follow_stream, stream_rendered_lines
                if self.chat_cancel_requested:
                    return
                snapshot = self.assistant_line("".join(stream_buffer))

                if stream_rendered_lines > 0 and len(log.lines) >= stream_rendered_lines:
                    del log.lines[-stream_rendered_lines:]
                    log.refresh()

                before = len(log.lines)
                log.write(snapshot)
                stream_rendered_lines = max(0, len(log.lines) - before)
                if follow_stream and self._chat_log_near_bottom(log, tolerance_lines=4):
                    self._smooth_scroll_to_end(log, animate=True)
                elif follow_stream:
                    follow_stream = False

            def _on_chunk(chunk: str) -> None:
                nonlocal last_render_at, first_chunk_seen
                if not chunk:
                    return
                if self.chat_cancel_requested:
                    return
                first_chunk_seen = True
                stream_buffer.append(chunk)
                now = time.monotonic()
                if now - last_render_at < 0.08:
                    return
                last_render_at = now
                self.call_from_thread(_render_stream_to_log)

            async def _spinner() -> None:
                idx = 0
                while spinner_active and not first_chunk_seen:
                    frame = spinner_frames[idx % len(spinner_frames)]
                    status.update(f"{self.ASSISTANT_NAME} (thinking) {frame}")
                    idx += 1
                    await asyncio.sleep(0.12)

            status.update(f"{self.ASSISTANT_NAME} (thinking) |")
            spinner_task = asyncio.create_task(_spinner())
            effective_mode = self.chat_analysis_mode
            if self._message_requests_deep_mode(message):
                effective_mode = "deep"
                if self.chat_analysis_mode != "deep":
                    if self._message_has_explicit_deep_intent(message):
                        log.write(self.assistant_line("deep-analysis intent detected; using deep mode for this message."))
                    elif self.auto_deep_detection_enabled:
                        log.write(self.assistant_line("auto-deep detected in-depth intent; using deep mode for this message."))
            try:
                response = await asyncio.to_thread(
                    self.chat_controller.build_chat_response,
                    message,
                    self.web_enabled,
                    self.last_detected_ticker,
                    effective_mode,
                    _on_chunk,
                )
            except Exception as exc:
                spinner_active = False
                if spinner_task and not spinner_task.done():
                    spinner_task.cancel()
                status.update("")
                err = f"chat error: {exc}"
                log.write(self.assistant_line(err))
                self.state_store.add_chat_message(self.thread_id, "assistant", err, datetime.now(timezone.utc).isoformat())
                return
            finally:
                spinner_active = False
                if spinner_task and not spinner_task.done():
                    spinner_task.cancel()
                status.update("")

            if stream_buffer and stream_rendered_lines == 0:
                _render_stream_to_log()

            try:
                local_details = (response.evidence or [{}])[0].get("details", {})
                ticker = local_details.get("ticker")
                if isinstance(ticker, str) and ticker.strip():
                    self.last_detected_ticker = ticker.strip().upper()
            except Exception:
                pass
            try:
                prompt = getattr(response, "prompt", None)
                if isinstance(prompt, str) and prompt.strip():
                    self.last_prompt = prompt
            except Exception:
                pass

            if stream_buffer:
                streamed_text = "".join(stream_buffer).strip()
                final_text = response.text.strip()
                if final_text and final_text != streamed_text:
                    if stream_rendered_lines > 0 and len(log.lines) >= stream_rendered_lines:
                        del log.lines[-stream_rendered_lines:]
                        log.refresh()
                    log.write(self.assistant_line(response.text))
            else:
                log.write(self.assistant_line(response.text))
            if follow_stream:
                self._smooth_scroll_to_end(log, animate=True)
            self.state_store.add_chat_message(self.thread_id, "assistant", response.text, datetime.now(timezone.utc).isoformat())
            latency_line = self._record_chat_latency(response.timings)
            if latency_line:
                log.write(f"metrics: {latency_line}")

            if response.action_preview:
                self.pending_action = self._build_pending_action_payload(response.action_preview, message)
                pending.update(
                    "Pending: "
                    f"{response.action_preview['action_id']} "
                    f"args={response.action_preview['args']} "
                    "(/confirm or /cancel)"
                )

            export_payload = {
                "question": message,
                "answer": response.text,
                "evidence": response.evidence,
                "actions_taken": [response.action_preview] if response.action_preview else [],
                "sources": ["local_context"],
                "timings": response.timings or {},
                "analysis_mode": response.analysis_mode,
                "created_at": datetime.now(timezone.utc).isoformat(),
            }
            md_path, json_path = self.artifacts.write_analysis(self.thread_id, message, response.text, export_payload)
            self.state_store.add_export(self.thread_id, message, md_path, json_path, datetime.now(timezone.utc).isoformat())
        finally:
            self.chat_inflight = False
            self.active_chat_task = None
            self.chat_cancel_requested = False

    async def execute_action(
        self,
        action_id: str,
        args: dict[str, Any],
        log_target: str,
        skip_confirm: bool = False,
        wait_for_completion: bool = False,
    ) -> bool:
        if self.active_job_task and not self.active_job_task.done():
            self._write_log(log_target, f"Action already running (job_id={self.active_job_id or 'unknown'}). Kill it first.")
            return False

        command_args, control_args = self.action_registry.extract_control_args(args)
        dry_run = bool(control_args.get("dry_run"))

        try:
            spec = self.action_registry.get(action_id)
        except KeyError as exc:
            self._write_log(log_target, f"Unknown action: {action_id}")
            self._write_log(log_target, f"Error: {exc}")
            return False
        if self.read_only and spec.is_mutating and not dry_run:
            self._write_log(log_target, "read-only mode: mutating action blocked")
            return False

        if spec.is_mutating and not dry_run:
            conflict = find_conflicting_job(
                action_id=action_id,
                jobs=self.state_store.list_jobs(limit=200),
                current_job_id=self.active_job_id,
            )
            if conflict:
                self._write_log(
                    log_target,
                    "Action blocked by conflict guard: "
                    f"existing {conflict['action_id']} job_id={conflict['job_id']} status={conflict['status']}",
                )
                return False

        preview = self.action_registry.preview(action_id, command_args)
        if dry_run and spec.is_mutating and "--dry-run" not in preview.command:
            preview.command.append("--dry-run")
        if dry_run and not spec.is_mutating:
            self._write_log(log_target, f"Dry-run preview: {' '.join(preview.command)}")
            self._write_log(log_target, "Dry-run only. Command not executed for read-only action.")
            return True

        if spec.requires_confirmation and not skip_confirm and not dry_run:
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
                return False

        if dry_run:
            self._write_log(log_target, f"Dry-run execution: {' '.join(preview.command)}")

        job = JobRun(
            job_id=uuid.uuid4().hex,
            action_id=action_id,
            args=command_args,
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
            nonlocal last_ticker, last_day
            app_thread = getattr(self, "_thread_id", None)
            if app_thread is not None and threading.get_ident() == app_thread:
                self._write_log(log_target, line)
            else:
                self.call_from_thread(lambda: self._write_log(log_target, line))

            ticker_match = re.search(r"\[(?:backfill|probe)\]\s+([A-Z0-9.]+)\s+attempt\s+\d+", line)
            if ticker_match:
                ticker = ticker_match.group(1)
                if ticker != last_ticker:
                    last_ticker = ticker
                    msg = f"[progress] ingesting ticker={ticker}"
                    if app_thread is not None and threading.get_ident() == app_thread:
                        self._write_log(log_target, msg)
                    else:
                        self.call_from_thread(lambda m=msg: self._write_log(log_target, m))

            day_match = re.search(r"\[asx_sweep\]\s+date=([0-9]{4}-[0-9]{2}-[0-9]{2})", line)
            if day_match:
                day = day_match.group(1)
                if day != last_day:
                    last_day = day
                    msg = f"[progress] sweep_day={day}"
                    if app_thread is not None and threading.get_ident() == app_thread:
                        self._write_log(log_target, msg)
                    else:
                        self.call_from_thread(lambda m=msg: self._write_log(log_target, m))

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

                if run_result.status == "success" and spec.is_mutating and not dry_run:
                    report_paths = extract_report_paths(action_id, preview.command, self.repo_root)
                    if report_paths:
                        reports, missing_reports = load_json_reports(report_paths)
                        gate_ok, reasons = evaluate_quality_gate(action_id, reports)
                        if missing_reports:
                            self._write_log(
                                log_target,
                                "Quality gate warning: missing/unreadable reports: "
                                + ", ".join(missing_reports),
                            )
                        self._write_log(log_target, f"Quality gate: {'PASS' if gate_ok else 'FAIL'}")
                        for reason in reasons:
                            self._write_log(log_target, f"Quality gate detail: {reason}")
                    else:
                        self._write_log(log_target, "Quality gate: no report paths inferred; skipped.")

                self._write_log(log_target, f"Completed with status={run_result.status} exit={run_result.exit_code}")
            except Exception as exc:
                self._write_log(log_target, f"Action runner error: {exc}")
            finally:
                self.active_job_id = None
                self.active_job_task = None

        self.active_job_task = asyncio.create_task(_run_and_finalize())
        if wait_for_completion and self.active_job_task:
            await self.active_job_task
        return True

    async def cancel_active_action(self, log_target: str) -> None:
        canceled_any = False

        if self.active_job_task and not self.active_job_task.done():
            status = await self.job_runner.cancel_active()
            self._write_log(log_target, f"Cancel request sent: {status} (job_id={self.active_job_id or 'unknown'})")
            canceled_any = True
        else:
            self.active_job_task = None
            self.active_job_id = None

        if self.active_chat_task and not self.active_chat_task.done():
            self.chat_cancel_requested = True
            self.active_chat_task.cancel()
            try:
                await self.active_chat_task
            except asyncio.CancelledError:
                pass
            except Exception as exc:
                self._write_log(log_target, self.assistant_line(f"chat cancel error: {exc}"))
            self.chat_inflight = False
            self.active_chat_task = None
            try:
                chat = self.get_screen("chat")
                chat.query_one("#chat-status", Static).update("")
            except Exception:
                pass
            self._write_log(log_target, self.assistant_line("Active chat response canceled."))
            canceled_any = True

        if not canceled_any:
            self._write_log(log_target, "No running action or chat response to cancel.")

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
        started = await self.execute_action(
            "update_ticker_financials",
            args,
            log_target=log_target,
            wait_for_completion=True,
        )
        if not started:
            self._write_log(log_target, "Snapshot skipped: updater job did not start.")
            return

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
        out_path = self.write_report_json(f"reports/snapshots/{ticker}_{self.timestamp()}.json", payload)
        self._write_log(log_target, f"Snapshot written: {out_path}")
        self._write_log(log_target, json.dumps(payload, default=str, indent=2)[:6000])

    def run_verification(self, ticker: str | None = None) -> dict[str, Any]:
        return run_verification(self.db_reader, ticker=ticker)

    def _write_log(self, log_target: str, text: str) -> None:
        try:
            screen = self.screen
            widget = screen.query_one(f"#{log_target}", RichLog)
            widget.write(text)
            return
        except Exception:
            pass

        # Fallback by scanning known screens.
        for name in ["chat", "ops", "updater", "verification"]:
            try:
                screen = self.get_screen(name)
                widget = screen.query_one(f"#{log_target}", RichLog)
                widget.write(text)
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

        payload: dict[str, Any] = {
            "exported_at": datetime.now(timezone.utc).isoformat(),
            "screen": screen_name,
            "thread_id": self.thread_id,
            "assistant_name": self.ASSISTANT_NAME,
            "chat_scope": "session",
            "session_started_at": self.session_started_at,
            "chat_analysis_mode": self.chat_analysis_mode,
            "auto_deep_detection_enabled": self.auto_deep_detection_enabled,
            "runtime": self.config.get("runtime", {}),
        }

        # Screen-specific snapshot for easier paste/share.
        if "chat" in screen_key:
            chat_window = int(self.config.get("exports", {}).get("chat_window_messages", 40))
            chat_window = max(10, min(200, chat_window))
            payload["chat_messages_total_all"] = self.state_store.count_chat_messages(self.thread_id)
            payload["chat_messages_total"] = self.state_store.count_chat_messages_since(
                self.thread_id,
                self.session_started_at,
            )
            payload["chat_messages_window"] = chat_window
            payload["chat_messages"] = self.state_store.get_chat_messages_since(
                self.thread_id,
                self.session_started_at,
                limit=chat_window,
            )
            payload["pending_action"] = self.pending_action
            payload["last_detected_ticker"] = self.last_detected_ticker
            latest = self.state_store.get_latest_export_since(self.thread_id, self.session_started_at)
            if latest:
                payload["latest_analysis_export_meta"] = latest
                try:
                    json_path = Path(str(latest.get("json_path", ""))).expanduser()
                    if json_path.exists() and json_path.is_file():
                        payload["latest_analysis_export"] = json.loads(json_path.read_text(encoding="utf-8"))
                except Exception as exc:
                    payload["latest_analysis_export_error"] = str(exc)
        elif "ops" in screen_key or "operation" in screen_key:
            payload["recent_jobs"] = self.state_store.list_jobs(limit=20)
        elif "updater" in screen_key:
            payload["latest_financials_bhp"] = self.db_reader.get_financials("BHP", limit=5)
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
        copied = self._copy_to_clipboard(text_blob)
        if copied:
            notice = "Copied chat/output bundle to clipboard."
            self._write_log("chat-log", notice)
            self.notify(notice)
            return

        # Fallback only when clipboard command is unavailable/fails.
        out_dir = self.repo_root / "reports" / "cockpit" / "exports"
        out_dir.mkdir(parents=True, exist_ok=True)
        txt_path = out_dir / f"copy_bundle_{ts}.txt"
        txt_path.write_text(text_blob, encoding="utf-8")
        notice = f"Clipboard unavailable. Wrote fallback export: {txt_path}"
        self._write_log("chat-log", notice)
        self.notify(notice)

    def _copy_to_clipboard(self, text: str) -> bool:
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
