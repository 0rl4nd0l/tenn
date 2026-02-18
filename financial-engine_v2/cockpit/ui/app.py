from __future__ import annotations

import json
import shutil
import subprocess
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.widgets import Footer, Header, RichLog

from cockpit.core.actions import ActionRegistry
from cockpit.core.chat import ChatController
from cockpit.core.job_runner import JobRunner
from cockpit.core.snapshot import build_snapshot_payload
from cockpit.core.types import JobRun
from cockpit.core.verification import run_verification
from cockpit.integrations.db_reader import DbReader
from cockpit.integrations.file_indexer import FileIndexer
from cockpit.integrations.ollama_client import OllamaClient
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
        self.ollama_client = OllamaClient(config["llm"]["ollama_url"], config["llm"]["model"])
        self.action_registry = ActionRegistry(repo_root=repo_root, confirm_required=config["actions"].get("confirm_required", True))
        self.job_runner = JobRunner(repo_root=repo_root, logs_dir=self.artifacts.logs_dir)
        self.tool_router = ToolRouter(
            db_reader=self.db_reader,
            file_indexer=self.file_indexer,
            web_fetcher=self.web_fetcher,
            web_default_enabled=config["web"].get("enabled_default", False),
        )
        self.chat_controller = ChatController(
            ollama_client=self.ollama_client,
            tool_router=self.tool_router,
            action_registry=self.action_registry,
            llm_timeout_seconds=float(config.get("llm", {}).get("timeout_seconds", 300)),
        )

        self.thread_id = "global-main"
        self.pending_action: dict[str, Any] | None = None
        self.last_verification_payload: dict[str, Any] | None = None

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

        # Replay recent history into chat log for continuity.
        try:
            screen = self.get_screen("chat")
            log = screen.query_one("#chat-log", RichLog)
            for message in self.state_store.get_chat_messages(self.thread_id, limit=50):
                log.write(f"{message['role']}: {message['content']}")
        except Exception:
            pass

    def timestamp(self) -> str:
        return datetime.now().strftime("%Y%m%d_%H%M%S")

    def _screen_log(self, screen_name: str, text: str) -> None:
        try:
            screen = self.get_screen(screen_name)
            screen.query_one("#chat-log", RichLog).write(text)
        except Exception:
            pass

    def write_report_json(self, rel_path: str, payload: dict[str, Any]) -> str:
        return self.artifacts.write_json(rel_path, payload)

    async def handle_chat_message(self, message: str) -> None:
        chat = self.get_screen("chat")
        log = chat.query_one("#chat-log", RichLog)
        pending = chat.query_one("#chat-pending")

        created = datetime.now(timezone.utc).isoformat()
        self.state_store.add_chat_message(self.thread_id, "user", message, created)
        log.write(f"user: {message}")

        if message.strip() == "/cancel":
            self.pending_action = None
            pending.update("No pending action")
            log.write("assistant: Pending action canceled.")
            self.state_store.add_chat_message(self.thread_id, "assistant", "Pending action canceled.", datetime.now(timezone.utc).isoformat())
            return

        if message.strip() == "/confirm":
            if not self.pending_action:
                log.write("assistant: No pending action.")
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
                log.write(text)
                self.state_store.add_chat_message(self.thread_id, "assistant", text, datetime.now(timezone.utc).isoformat())
                return

            snippet = (
                f"assistant: Loaded {result['path']} "
                f"(returned {result['chars_returned']} chars"
                f"{', truncated' if result['truncated'] else ''}).\n"
                f"{result['content']}"
            )
            log.write(snippet[:14000])
            self.state_store.add_chat_message(
                self.thread_id,
                "assistant",
                f"/read loaded {result['path']} ({result['chars_returned']} chars)",
                datetime.now(timezone.utc).isoformat(),
            )
            return

        try:
            response = self.chat_controller.build_chat_response(
                message,
                enable_web=self.config["web"].get("enabled_default", False),
            )
        except Exception as exc:
            err = f"assistant: chat error: {exc}"
            log.write(err)
            self.state_store.add_chat_message(self.thread_id, "assistant", err, datetime.now(timezone.utc).isoformat())
            return

        log.write(f"assistant: {response.text}")
        self.state_store.add_chat_message(self.thread_id, "assistant", response.text, datetime.now(timezone.utc).isoformat())

        if response.action_preview:
            self.pending_action = {
                "action_id": response.action_preview["action_id"],
                "args": response.action_preview["args"],
            }
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
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        md_path, json_path = self.artifacts.write_analysis(self.thread_id, message, response.text, export_payload)
        self.state_store.add_export(self.thread_id, message, md_path, json_path, datetime.now(timezone.utc).isoformat())

    async def execute_action(
        self,
        action_id: str,
        args: dict[str, Any],
        log_target: str,
        skip_confirm: bool = False,
    ) -> None:
        spec = self.action_registry.get(action_id)
        if self.read_only and spec.is_mutating:
            self._write_log(log_target, "read-only mode: mutating action blocked")
            return

        preview = self.action_registry.preview(action_id, args)
        if spec.requires_confirmation and not skip_confirm:
            confirmed = await self.push_screen_wait(ConfirmActionScreen(preview={
                "action_id": action_id,
                "command": preview.command,
                "impact": preview.estimated_impact,
                "timeout_seconds": preview.timeout_seconds,
            }))
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

        def _emit(line: str) -> None:
            self.call_from_thread(lambda: self._write_log(log_target, line))

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

    async def run_updater_snapshot(self, ticker: str, years: int, process_documents: bool, log_target: str) -> None:
        before = self.db_reader.get_latest_financial_snapshot(ticker)

        args = {
            "ticker": ticker,
            "years": years,
            "process_documents": process_documents,
            "report_path": f"reports/cockpit/updater_{ticker}_{self.timestamp()}.json",
        }
        await self.execute_action("full_history", args, log_target=log_target)

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
            "runtime": self.config.get("runtime", {}),
        }

        # Screen-specific snapshot for easier paste/share.
        if "chat" in screen_key:
            payload["chat_messages"] = self.state_store.get_chat_messages(self.thread_id, limit=200)
            payload["pending_action"] = self.pending_action
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
