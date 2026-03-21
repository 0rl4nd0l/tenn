from __future__ import annotations

import json
from typing import Any, Callable

from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.screen import ModalScreen, Screen
from textual.widgets import Button, DataTable, Input, Label, RichLog, Select, Static


class ConfirmActionScreen(ModalScreen[bool]):
    BINDINGS = [
        ("enter", "confirm", "Run"),
        ("escape", "cancel", "Cancel"),
    ]

    def __init__(self, preview: dict[str, Any], on_decision: Callable[[bool], None] | None = None) -> None:
        super().__init__()
        self.preview = preview
        self.on_decision = on_decision

    def compose(self) -> ComposeResult:
        command = " ".join(self.preview.get("command", []))
        yield Vertical(
            Label("Confirm Action"),
            Static(f"Action: {self.preview.get('action_id')}"),
            Static(f"Impact: {self.preview.get('impact')}"),
            Static(f"Timeout: {self.preview.get('timeout_seconds')}s"),
            Static(f"Command: {command}"),
            Horizontal(
                Button("Cancel", id="confirm-cancel", variant="warning"),
                Button("Run", id="confirm-run", variant="success"),
            ),
            id="confirm-modal",
        )

    def on_button_pressed(self, event: Button.Pressed) -> None:
        event.stop()
        approved = event.button.id == "confirm-run"
        if self.on_decision:
            self.on_decision(approved)
        self.dismiss(approved)

    def action_confirm(self) -> None:
        if self.on_decision:
            self.on_decision(True)
        self.dismiss(True)

    def action_cancel(self) -> None:
        if self.on_decision:
            self.on_decision(False)
        self.dismiss(False)


class ChatScreen(Screen):
    BINDINGS = [("ctrl+l", "clear_log", "Clear")]

    def compose(self) -> ComposeResult:
        yield Label("Chat + Actions")
        yield Static("Model runtime: loading...", id="chat-model-status")
        yield RichLog(id="chat-log", wrap=True, markup=False)
        yield Static("", id="chat-status")
        yield Static("No pending action", id="chat-pending")
        yield Vertical(
            Horizontal(
                Button("Copy Chat/Output", id="chat-copy-output"),
                Button("Open Operations", id="chat-open-ops"),
            ),
            Horizontal(
                Button("Daily News Ingest", id="chat-run-daily-news", variant="success"),
                Button("Daily Announcement Ingest", id="chat-run-daily-announcements", variant="primary"),
            ),
            Horizontal(
                Button("Historical News Ingest", id="chat-run-historical-news", variant="warning"),
                Button("Single Ticker Backfill", id="chat-run-single-ticker-backfill", variant="primary"),
            ),
            Horizontal(
                Button("Universe Announcement Backfill", id="chat-run-universe-backfill", variant="error"),
                Button("Metric Extraction", id="chat-run-metric-extraction", variant="warning"),
            ),
            Horizontal(
                Button("Kill Running Action", id="chat-kill-action", variant="error"),
            ),
            id="chat-actions",
        )
        yield Input(
            placeholder="Ask questions or use /read <path> [max_chars=N], /confirm, /cancel",
            id="chat-input",
        )

    async def on_input_submitted(self, event: Input.Submitted) -> None:
        message = event.value.strip()
        event.input.value = ""
        if not message:
            return
        await self.app.handle_chat_message(message)

    def action_clear_log(self) -> None:
        self.query_one("#chat-log", RichLog).clear()

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "chat-open-ops":
            self.app.action_show_ops()
            return
        if event.button.id == "chat-run-daily-news":
            args = self.app.action_registry.parse_kv_args("")
            await self.app.execute_action("daily_news_ingest", args, log_target="chat-log")
            return
        if event.button.id == "chat-run-daily-announcements":
            args = self.app.action_registry.parse_kv_args("")
            await self.app.execute_action("daily_announcement_ingest", args, log_target="chat-log")
            return
        if event.button.id == "chat-run-historical-news":
            args = self.app.action_registry.parse_kv_args("")
            await self.app.execute_action("historical_news_ingest", args, log_target="chat-log")
            return
        if event.button.id == "chat-run-single-ticker-backfill":
            args = self.app.action_registry.parse_kv_args("")
            await self.app.execute_action("single_ticker_announcement_backfill", args, log_target="chat-log")
            return
        if event.button.id == "chat-run-universe-backfill":
            args = self.app.action_registry.parse_kv_args("")
            await self.app.execute_action("universe_announcement_enrichment_backfill", args, log_target="chat-log")
            return
        if event.button.id == "chat-run-metric-extraction":
            args = self.app.action_registry.parse_kv_args("")
            await self.app.execute_action("metric_extraction", args, log_target="chat-log")
            return
        if event.button.id == "chat-kill-action":
            await self.app.cancel_active_action(log_target="chat-log")
            return
        if event.button.id == "chat-copy-output":
            self.app.action_export_copy_bundle()


class OperationsScreen(Screen):
    BINDINGS = [("d", "run_daily_news_ingest", "Daily News")]

    def compose(self) -> ComposeResult:
        yield Label("Ingestion Control")
        yield Button("Back to Chat", id="ops-back", variant="warning")
        actions = [(spec.label, spec.id) for spec in self.app.action_registry.list_actions()]
        yield Select(actions, value="daily_news_ingest", id="ops-action")
        yield Input(value="ticker=BHP years=5", id="ops-args", placeholder="key=value pairs")
        yield Button("Daily News Ingest", id="ops-run-daily-news", variant="success")
        yield Button("Daily Announcement Ingest", id="ops-run-daily-announcements", variant="primary")
        yield Button("Historical News Ingest", id="ops-run-historical-news", variant="warning")
        yield Button("Single Ticker Backfill", id="ops-run-single-ticker-backfill", variant="primary")
        yield Button("Universe Announcement Backfill", id="ops-run-universe-backfill", variant="error")
        yield Button("Metric Extraction", id="ops-run-metric-extraction", variant="warning")
        yield Horizontal(
            Button("Preview + Run", id="ops-run", variant="primary"),
            Button("Kill Running Action", id="ops-kill-action", variant="error"),
            Button("Tail Last Logs", id="ops-tail"),
        )
        yield RichLog(id="ops-log", wrap=True, markup=False)

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        log = self.query_one("#ops-log", RichLog)
        if event.button.id == "ops-back":
            self.app.action_show_chat()
            return
        if event.button.id == "ops-tail":
            for job in self.app.state_store.list_jobs(limit=3):
                log.write(f"{job['job_id']} {job['status']} out={job.get('stdout_path')}")
            return
        if event.button.id == "ops-kill-action":
            await self.app.cancel_active_action(log_target="ops-log")
            return

        if event.button.id == "ops-run-daily-news":
            args = self.app.action_registry.parse_kv_args(self.query_one("#ops-args", Input).value)
            await self.app.execute_action("daily_news_ingest", args, log_target="ops-log")
            return
        if event.button.id == "ops-run-daily-announcements":
            args = self.app.action_registry.parse_kv_args(self.query_one("#ops-args", Input).value)
            await self.app.execute_action("daily_announcement_ingest", args, log_target="ops-log")
            return
        if event.button.id == "ops-run-historical-news":
            args = self.app.action_registry.parse_kv_args(self.query_one("#ops-args", Input).value)
            await self.app.execute_action("historical_news_ingest", args, log_target="ops-log")
            return
        if event.button.id == "ops-run-single-ticker-backfill":
            args = self.app.action_registry.parse_kv_args(self.query_one("#ops-args", Input).value)
            await self.app.execute_action("single_ticker_announcement_backfill", args, log_target="ops-log")
            return
        if event.button.id == "ops-run-universe-backfill":
            args = self.app.action_registry.parse_kv_args(self.query_one("#ops-args", Input).value)
            await self.app.execute_action("universe_announcement_enrichment_backfill", args, log_target="ops-log")
            return
        if event.button.id == "ops-run-metric-extraction":
            args = self.app.action_registry.parse_kv_args(self.query_one("#ops-args", Input).value)
            await self.app.execute_action("metric_extraction", args, log_target="ops-log")
            return

        action_id = self.query_one("#ops-action", Select).value
        args_text = self.query_one("#ops-args", Input).value
        if not action_id:
            log.write("No action selected")
            return
        args = self.app.action_registry.parse_kv_args(args_text)
        await self.app.execute_action(action_id, args, log_target="ops-log")

    async def action_run_daily_news_ingest(self) -> None:
        args = self.app.action_registry.parse_kv_args(self.query_one("#ops-args", Input).value)
        await self.app.execute_action("daily_news_ingest", args, log_target="ops-log")


class UpdaterScreen(Screen):
    def compose(self) -> ComposeResult:
        yield Label("Financial Data Updater")
        yield Horizontal(
            Input(value="BHP", id="upd-ticker", placeholder="Ticker"),
            Input(value="5", id="upd-years", placeholder="Years"),
            Input(value="true", id="upd-process", placeholder="process_documents true/false"),
        )
        yield Horizontal(
            Input(value="", id="upd-since", placeholder="since YYYY-MM-DD (optional)"),
            Input(value="0.40", id="upd-lowconf", placeholder="low confidence threshold"),
        )
        yield Horizontal(
            Button("Run Financial Refresh + Snapshot", id="upd-run", variant="primary"),
            Button("Rebuild Financials From Docs", id="upd-rebuild"),
            Button("Audit Financials QA", id="upd-audit"),
            Button("Show Latest Financial Row", id="upd-latest"),
        )
        yield RichLog(id="upd-log", wrap=True, markup=False)

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        log = self.query_one("#upd-log", RichLog)
        ticker = self.query_one("#upd-ticker", Input).value.strip().upper() or "BHP"
        if event.button.id == "upd-latest":
            row = self.app.db_reader.get_latest_financial_snapshot(ticker)
            log.write(json.dumps(row or {"ticker": ticker, "message": "no data"}, default=str, indent=2))
            return
        if event.button.id == "upd-rebuild":
            since = self.query_one("#upd-since", Input).value.strip()
            args = {"ticker": ticker}
            if since:
                args["since"] = since
            await self.app.execute_action("rebuild_ticker_financials", args, log_target="upd-log")
            return
        if event.button.id == "upd-audit":
            lowconf_raw = self.query_one("#upd-lowconf", Input).value.strip()
            args: dict[str, Any] = {"ticker": ticker}
            if lowconf_raw:
                args["low_confidence_threshold"] = lowconf_raw
            await self.app.execute_action("audit_ticker_financials", args, log_target="upd-log")
            return

        try:
            years = int(self.query_one("#upd-years", Input).value.strip() or "5")
        except (ValueError, TypeError):
            log.write("Invalid years value, defaulting to 5")
            years = 5
        process_documents = self.query_one("#upd-process", Input).value.strip().lower() in {"1", "true", "yes", "on"}
        await self.app.run_updater_snapshot(ticker=ticker, years=years, process_documents=process_documents, log_target="upd-log")


class VerificationScreen(Screen):
    def compose(self) -> ComposeResult:
        yield Label("Data Verification")
        yield Input(value="BHP", id="ver-ticker", placeholder="Ticker (blank for broad checks where available)")
        yield Horizontal(
            Button("Run Verification", id="ver-run", variant="primary"),
            Button("Export Verification", id="ver-export"),
        )
        yield RichLog(id="ver-log", wrap=True, markup=False)

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        ticker = self.query_one("#ver-ticker", Input).value.strip().upper()
        if event.button.id == "ver-run":
            payload = self.app.run_verification(ticker=ticker or None)
            self.app.last_verification_payload = payload
            self.query_one("#ver-log", RichLog).write(json.dumps(payload, default=str, indent=2))
            return

        if not self.app.last_verification_payload:
            self.query_one("#ver-log", RichLog).write("Run verification first")
            return
        out_path = self.app.write_report_json(
            f"reports/cockpit/verification_{self.app.timestamp()}.json",
            self.app.last_verification_payload,
        )
        self.query_one("#ver-log", RichLog).write(f"Exported: {out_path}")


class HistoryScreen(Screen):
    def compose(self) -> ComposeResult:
        yield Label("Run & Export History")
        yield Button("Refresh", id="hist-refresh")
        table = DataTable(id="hist-table")
        table.add_columns("Kind", "ID/Thread", "Status", "When", "Path")
        yield table

    def on_mount(self) -> None:
        self._refresh()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "hist-refresh":
            self._refresh()

    def _refresh(self) -> None:
        table = self.query_one("#hist-table", DataTable)
        table.clear()
        for job in self.app.state_store.list_jobs(limit=40):
            table.add_row("job", job["job_id"], job["status"], job["started_at"], job.get("stdout_path") or "")
        for export in self.app.state_store.list_exports(limit=40):
            table.add_row("analysis", export["thread_id"], "saved", export["created_at"], export["markdown_path"])


class SettingsScreen(Screen):
    def compose(self) -> ComposeResult:
        yield Label("Cockpit Settings")
        yield Static(id="settings-json")

    def on_mount(self) -> None:
        payload = {
            "runtime": self.app.config.get("runtime", {}),
            "llm": self.app.config.get("llm", {}),
            "paths": self.app.config.get("paths", {}),
            "memory": self.app.config.get("memory", {}),
            "web": self.app.config.get("web", {}),
        }
        self.query_one("#settings-json", Static).update(json.dumps(payload, indent=2))


_LOOKBACK_OPTIONS: list[tuple[str, str]] = [
    ("24h", "24h"),
    ("7d", "7d"),
    ("30d", "30d"),
    ("All", "all"),
]

_LOOKBACK_DATE_FROM: dict[str, str | None] = {
    "24h": None,  # computed at search time
    "7d": None,
    "30d": None,
    "all": None,
}


class NewsSearchScreen(Screen):
    BINDINGS = [("escape", "app.show_chat", "Back")]

    def compose(self) -> ComposeResult:
        from datetime import datetime, timedelta, timezone

        yield Label("News Search")
        yield Horizontal(
            Input(placeholder="Search query", id="news-query"),
            Input(placeholder="Ticker (optional)", id="news-ticker"),
            id="news-inputs-row1",
        )
        yield Horizontal(
            Input(placeholder="date_from YYYY-MM-DD (optional)", id="news-date-from"),
            Input(placeholder="date_to YYYY-MM-DD (optional)", id="news-date-to"),
            Select(
                [(label, value) for label, value in _LOOKBACK_OPTIONS],
                value="all",
                id="news-lookback",
                prompt="Lookback",
            ),
            id="news-inputs-row2",
        )
        yield Horizontal(
            Button("Search", id="news-search", variant="primary"),
            Button("Clear", id="news-clear"),
            id="news-controls",
        )
        yield Static("", id="news-source-status")
        yield RichLog(id="news-results", wrap=True, markup=False)

    def _compute_date_from(self, lookback: str) -> str | None:
        from datetime import datetime, timedelta, timezone

        now = datetime.now(timezone.utc)
        if lookback == "24h":
            return (now - timedelta(hours=24)).strftime("%Y-%m-%d")
        if lookback == "7d":
            return (now - timedelta(days=7)).strftime("%Y-%m-%d")
        if lookback == "30d":
            return (now - timedelta(days=30)).strftime("%Y-%m-%d")
        return None

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "news-clear":
            self.query_one("#news-query", Input).value = ""
            self.query_one("#news-ticker", Input).value = ""
            self.query_one("#news-date-from", Input).value = ""
            self.query_one("#news-date-to", Input).value = ""
            self.query_one("#news-results", RichLog).clear()
            self.query_one("#news-source-status", Static).update("")
            return

        if event.button.id == "news-search":
            await self._run_search()

    async def on_input_submitted(self, event: Input.Submitted) -> None:
        if event.input.id in ("news-query", "news-ticker", "news-date-from", "news-date-to"):
            await self._run_search()

    async def _run_search(self) -> None:
        query = self.query_one("#news-query", Input).value.strip()
        ticker_raw = self.query_one("#news-ticker", Input).value.strip().upper()
        date_from_raw = self.query_one("#news-date-from", Input).value.strip()
        date_to_raw = self.query_one("#news-date-to", Input).value.strip()
        lookback = str(self.query_one("#news-lookback", Select).value or "all")
        log = self.query_one("#news-results", RichLog)
        source_status = self.query_one("#news-source-status", Static)

        if not query:
            log.write("Enter a search query.")
            return

        log.clear()
        log.write("Searching...")

        # Date range: explicit inputs take priority over lookback selector.
        date_from = date_from_raw or self._compute_date_from(lookback)
        date_to = date_to_raw or None
        ticker = ticker_raw or None

        tool_router = self.app.tool_router
        try:
            result = tool_router.get_news_context(
                query=query,
                top_k=20,
                ticker=ticker,
                date_from=date_from,
                date_to=date_to,
            )
        except Exception as exc:
            log.clear()
            log.write(f"Error: {exc}")
            source_status.update("[ERROR] Search failed")
            return

        log.clear()
        source = result.get("_source", "unknown")
        hits = result.get("hits") or []

        if source == "qdrant":
            source_status.update("Source: Qdrant")
        else:
            source_status.update("Source: SQLite (fallback) [WARNING: Qdrant unavailable]")

        if not hits:
            log.write("No results found.")
            return

        for i, hit in enumerate(hits, 1):
            title = str(hit.get("title") or hit.get("headline") or "(no title)")
            provider = str(hit.get("provider") or hit.get("source") or hit.get("source_domain") or "")
            published = str(hit.get("published_at") or hit.get("doc_date") or "")
            hit_ticker = str(hit.get("ticker") or "")
            score = hit.get("score") or hit.get("final_score") or hit.get("semantic_score")
            score_str = f"{float(score):.4f}" if score is not None else "n/a"

            line_parts = [f"[{i}] {title}"]
            if provider:
                line_parts.append(f"  Source: {provider}")
            if published:
                line_parts.append(f"  Published: {published}")
            if hit_ticker:
                line_parts.append(f"  Ticker: {hit_ticker}")
            line_parts.append(f"  Score: {score_str}")
            log.write("\n".join(line_parts))
            log.write("")
