from __future__ import annotations

import asyncio
import json
from typing import Any, Callable

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.screen import ModalScreen, Screen
from textual.widgets import (
    Button,
    Collapsible,
    DataTable,
    Input,
    Label,
    RichLog,
    Select,
    Static,
    Switch,
)

from cockpit.core.config import format_cockpit_llm_readonly
from cockpit.core.plotly_html import build_verification_dashboard_html
from cockpit.ui.help_modal import HelpScreen


def _backend_ops_scope(job: dict[str, Any]) -> str:
    ticker = str(job.get("ticker") or "").strip().upper()
    if ticker:
        return ticker
    entity_scope = str(job.get("entity_scope") or "").strip()
    if entity_scope:
        return entity_scope
    job_family = str(job.get("job_family") or "").strip()
    if job_family:
        return job_family
    return "-"


def _backend_ops_detail(job: dict[str, Any]) -> str:
    title = str(job.get("title") or "").strip()
    summary = str(job.get("summary") or "").strip()
    parts: list[str] = []
    if title:
        parts.append(title)
    if summary and summary != title:
        parts.append(summary)
    counts: list[str] = []
    succeeded = int(job.get("succeeded_items") or 0)
    total = int(job.get("total_items") or 0)
    if total:
        counts.append(f"{succeeded}/{total}")
    failed = int(job.get("failed_items") or 0)
    if failed:
        counts.append(f"failed={failed}")
    warnings = int(job.get("warning_count") or 0)
    if warnings:
        counts.append(f"warn={warnings}")
    errors = int(job.get("error_count") or 0)
    if errors:
        counts.append(f"err={errors}")
    elapsed_ms = int(job.get("elapsed_ms") or 0)
    if elapsed_ms:
        counts.append(f"{elapsed_ms}ms")
    if counts:
        parts.append(f"({' '.join(counts)})")
    return " ".join(parts) if parts else "-"


def _backend_ops_tail_line(job: dict[str, Any]) -> str:
    pieces = [
        str(job.get("job_id") or "-"),
        str(job.get("status") or "-"),
    ]
    phase = str(job.get("phase") or "").strip()
    if phase:
        pieces.append(f"phase={phase}")
    scope = _backend_ops_scope(job)
    if scope and scope != "-":
        pieces.append(f"scope={scope}")
    detail = _backend_ops_detail(job)
    if detail and detail != "-":
        pieces.append(detail)
    trigger_source = str(job.get("trigger_source") or "").strip()
    if trigger_source:
        pieces.append(f"src={trigger_source}")
    return " | ".join(pieces)


_MEMORY_SCOPE_OPTIONS: list[tuple[str, str]] = [
    ("Company", "company"),
    ("Sector", "sector"),
    ("Macro", "macro"),
]

_MEMORY_DEFAULT_TYPES: dict[str, str] = {
    "company": "observed_fact",
    "sector": "sector_trend",
    "macro": "macro_theme",
}


def _memory_timestamp(value: Any) -> str:
    text = str(value or "").strip()
    if not text:
        return "-"
    return text[:19].replace("T", " ")


def _memory_change_summary(details: Any) -> str:
    if not isinstance(details, dict) or not details:
        return "-"

    parts: list[str] = []
    for key, value in details.items():
        if isinstance(value, list):
            rendered = ", ".join(str(item) for item in value[:4])
            if len(value) > 4:
                rendered = f"{rendered}, ..."
            parts.append(f"{key}=[{rendered}]")
            continue
        parts.append(f"{key}={value}")
    return "; ".join(parts) if parts else "-"


class TickerInputScreen(ModalScreen[str]):
    """Modal that prompts the user for a ticker before running a ticker-specific action."""

    BINDINGS = [
        ("escape", "cancel", "Cancel"),
    ]

    def __init__(self, action_label: str) -> None:
        super().__init__()
        self.action_label = action_label

    def compose(self) -> ComposeResult:
        yield Vertical(
            Label(f"Enter ticker for: {self.action_label}"),
            Input(placeholder="e.g. CSL, BHP, RIO", id="ticker-input"),
            Horizontal(
                Button("Cancel", id="ticker-cancel", variant="warning"),
                Button("Go", id="ticker-go", variant="success"),
            ),
            id="ticker-modal",
        )

    def on_mount(self) -> None:
        self.query_one("#ticker-input", Input).focus()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        """Handle Enter key from the Input widget directly."""
        if event.input.id == "ticker-input":
            ticker = event.input.value.strip().upper()
            self.dismiss(ticker)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        event.stop()
        if event.button.id == "ticker-go":
            ticker = self.query_one("#ticker-input", Input).value.strip().upper()
            self.dismiss(ticker)
        else:
            self.dismiss("")

    def action_cancel(self) -> None:
        self.dismiss("")


class ConfirmActionScreen(ModalScreen[bool]):
    BINDINGS = [
        ("enter", "confirm", "Run"),
        ("escape", "cancel", "Cancel"),
    ]

    def __init__(
        self, preview: dict[str, Any], on_decision: Callable[[bool], None] | None = None
    ) -> None:
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
    BINDINGS = [
        ("ctrl+l", "clear_log", "Clear"),
        Binding("ctrl+up", "history_prev", "Previous input", show=False),
        Binding("ctrl+down", "history_next", "Next input", show=False),
    ]

    def compose(self) -> ComposeResult:
        yield Label("Chat + Actions")
        yield Static("Model runtime: loading...", id="chat-model-status")
        yield Static("", id="chat-ticker-context")
        yield RichLog(id="chat-log", wrap=True, markup=False, highlight=True)
        yield Static("", id="chat-live-response")
        yield Static("", id="chat-status")
        yield Static("No pending action", id="chat-pending")
        yield Vertical(
            Horizontal(
                Button("Copy Chat/Output", id="chat-copy-output"),
                Button("Open Memory", id="chat-open-memory"),
                Button("Open Operations", id="chat-open-ops"),
                Button("Help", id="chat-open-help"),
            ),
            Horizontal(
                Button(
                    "Daily News Ingest", id="chat-run-daily-news", variant="success"
                ),
                Button(
                    "Daily Announcement Ingest",
                    id="chat-run-daily-announcements",
                    variant="primary",
                ),
            ),
            Horizontal(
                Button(
                    "Historical News Ingest",
                    id="chat-run-historical-news",
                    variant="warning",
                ),
                Button(
                    "Single Ticker Backfill",
                    id="chat-run-single-ticker-backfill",
                    variant="primary",
                ),
            ),
            Horizontal(
                Button(
                    "Universe Announcement Backfill",
                    id="chat-run-universe-backfill",
                    variant="error",
                ),
                Button(
                    "Metric Extraction",
                    id="chat-run-metric-extraction",
                    variant="warning",
                ),
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
        self.app.launch_chat_message(message)

    async def _run_ticker_action(self, action_id: str, label: str) -> None:
        """Prompt user for a ticker via modal, then execute the action."""

        def _on_dismiss(ticker: str) -> None:
            if not ticker:
                return
            args = self.app.action_registry.parse_kv_args(f"ticker={ticker}")
            self.app.call_later(
                self.app.execute_action, action_id, args, log_target="chat-log"
            )

        self.app.push_screen(TickerInputScreen(label), callback=_on_dismiss)

    def action_clear_log(self) -> None:
        self.query_one("#chat-log", RichLog).clear()

    def action_history_prev(self) -> None:
        app = self.app  # type: ignore
        if not app._input_history or app._history_idx <= 0:
            return
        app._history_idx -= 1
        try:
            input_widget = self.query_one("#chat-input")
            input_widget.value = app._input_history[app._history_idx]
        except Exception:
            pass

    def action_history_next(self) -> None:
        app = self.app  # type: ignore
        if not app._input_history:
            return
        app._history_idx = min(app._history_idx + 1, len(app._input_history))
        try:
            input_widget = self.query_one("#chat-input")
            if app._history_idx < len(app._input_history):
                input_widget.value = app._input_history[app._history_idx]
            else:
                input_widget.value = ""
        except Exception:
            pass

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "chat-open-memory":
            self.app.action_show_memory()
            return
        if event.button.id == "chat-open-ops":
            self.app.action_show_ops()
            return
        if event.button.id == "chat-open-help":
            self.app.push_screen(HelpScreen(repo_root=self.app.repo_root))
            return
        if event.button.id == "chat-run-daily-news":
            args = self.app.action_registry.parse_kv_args("")
            await self.app.execute_action(
                "daily_news_ingest", args, log_target="chat-log"
            )
            return
        if event.button.id == "chat-run-daily-announcements":
            args = self.app.action_registry.parse_kv_args("")
            await self.app.execute_action(
                "daily_announcement_ingest", args, log_target="chat-log"
            )
            return
        if event.button.id == "chat-run-historical-news":
            args = self.app.action_registry.parse_kv_args("")
            await self.app.execute_action(
                "historical_news_ingest", args, log_target="chat-log"
            )
            return
        if event.button.id == "chat-run-single-ticker-backfill":
            await self._run_ticker_action(
                "single_ticker_announcement_backfill", "Single Ticker Backfill"
            )
            return
        if event.button.id == "chat-run-universe-backfill":
            args = self.app.action_registry.parse_kv_args("")
            await self.app.execute_action(
                "universe_announcement_enrichment_backfill", args, log_target="chat-log"
            )
            return
        if event.button.id == "chat-run-metric-extraction":
            await self._run_ticker_action("metric_extraction", "Metric Extraction")
            return
        if event.button.id == "chat-kill-action":
            await self.app.cancel_active_action(log_target="chat-log")
            return
        if event.button.id == "chat-copy-output":
            self.app.action_export_copy_bundle()


class OperationsScreen(Screen):
    BINDINGS = [("d", "run_daily_news_ingest", "Daily News")]

    def compose(self) -> ComposeResult:
        yield Label("Operations & Settings")
        yield Button("Back to Chat", id="ops-back", variant="warning")

        # ── Permissions & Config ──
        with Collapsible(title="Permissions & Config", collapsed=False):
            with Horizontal(id="perm-toggles"):
                with Vertical():
                    yield Label("Feature Toggles")
                    yield Horizontal(
                        Switch(id="perm-web", value=False), Label("Web Search")
                    )
                    yield Horizontal(
                        Switch(id="perm-rag", value=False), Label("RAG Context")
                    )
                    yield Horizontal(
                        Switch(id="perm-dbdiag", value=False), Label("DB Diagnostics")
                    )
                with Vertical():
                    yield Label(
                        "Cockpit LLM (read-only — edit config/cockpit_llm.yaml)"
                    )
                    yield Static(
                        format_cockpit_llm_readonly(self.app.repo_root),
                        id="perm-llm-readonly",
                    )
            yield Static(id="perm-capabilities")

        # ── Ingestion Control ──
        with Collapsible(title="Ingestion Control", collapsed=False):
            actions = [
                (spec.label, spec.id)
                for spec in self.app.action_registry.list_actions()
            ]
            yield Select(actions, value="daily_news_ingest", id="ops-action")
            yield Input(
                value="",
                id="ops-args",
                placeholder="ticker=CSL years=5 (required for ticker actions)",
            )
            yield Button(
                "Daily News Ingest", id="ops-run-daily-news", variant="success"
            )
            yield Button(
                "Daily Announcement Ingest",
                id="ops-run-daily-announcements",
                variant="primary",
            )
            yield Button(
                "Historical News Ingest",
                id="ops-run-historical-news",
                variant="warning",
            )
            yield Button(
                "Single Ticker Backfill",
                id="ops-run-single-ticker-backfill",
                variant="primary",
            )
            yield Button(
                "Universe Announcement Backfill",
                id="ops-run-universe-backfill",
                variant="error",
            )
            yield Button(
                "Metric Extraction", id="ops-run-metric-extraction", variant="warning"
            )
            yield Horizontal(
                Button("Preview + Run", id="ops-run", variant="primary"),
                Button("Kill Running Action", id="ops-kill-action", variant="error"),
                Button("Tail Last Logs", id="ops-tail"),
            )

        yield RichLog(id="ops-log", wrap=True, markup=False)

    def on_mount(self) -> None:
        self._refresh_permissions()

    def _refresh_permissions(self) -> None:
        """Sync toggle states and capability display with current runtime."""
        access = self.app._access_state()
        try:
            self.query_one("#perm-web", Switch).value = access.get("web_enabled", False)
        except Exception:
            pass
        try:
            self.query_one("#perm-rag", Switch).value = access.get("rag_enabled", False)
        except Exception:
            pass
        try:
            self.query_one("#perm-dbdiag", Switch).value = access.get(
                "db_diagnostic_query_enabled", False
            )
        except Exception:
            pass

        caps = self.app.get_capabilities()
        try:
            self.query_one("#perm-llm-readonly", Static).update(
                format_cockpit_llm_readonly(self.app.repo_root)
            )
        except Exception:
            pass

        ok = "+"
        no = "-"
        lines = []
        lines.append(
            f"  {ok if caps.get('backend_api') else no}  Backend API   {caps.get('backend_url') or 'not configured'}"
        )
        lines.append(f"  +  Effective routing  {caps.get('routing_policy')}")
        lines.append(f"  +  Profile label  {caps.get('llm_profile')}")
        lines.append(f"  +  Config  {caps.get('cockpit_llm_config_path')}")
        exo = caps.get("explicit_policy_override")
        if exo:
            lines.append(f"  !  HYBRID_ROUTER_POLICY (env override)  {exo}")
        lines.append(
            f"  {ok if caps.get('anthropic_api') else no}  Claude API    {'key loaded' if caps.get('anthropic_api') else 'no key'}"
        )
        lines.append(
            f"  {ok if caps.get('brave_search') else no}  Brave Search  {'active' if caps.get('brave_search') else 'no key'}"
        )
        lines.append(
            f"  {ok if caps.get('hn_search') else no}  HN Search     {'active' if caps.get('hn_search') else 'inactive'}"
        )
        lines.append(
            f"  {ok if caps.get('dossier') else no}  Dossier       {'active' if caps.get('dossier') else 'inactive'}"
        )
        lines.append(
            f"  {ok if caps.get('deep_research') else no}  Deep Research {'active' if caps.get('deep_research') else 'inactive'}"
        )
        lines.append(f"  +  Price Feeds   Yahoo Finance (no key needed)")
        cost = caps.get("session_cost_usd", 0.0)
        if cost > 0:
            lines.append(f"  Session API cost: ${cost:.4f}")
        try:
            self.query_one("#perm-capabilities", Static).update("\n".join(lines))
        except Exception:
            pass

    def on_switch_changed(self, event: Switch.Changed) -> None:
        log = self.query_one("#ops-log", RichLog)
        switch_id = event.switch.id
        if switch_id == "perm-web":
            msg = self.app._set_access_scope("web", event.value)
            log.write(msg)
        elif switch_id == "perm-rag":
            msg = self.app._set_access_scope("rag", event.value)
            log.write(msg)
        elif switch_id == "perm-dbdiag":
            msg = self.app._set_access_scope("dbdiag", event.value)
            log.write(msg)

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        log = self.query_one("#ops-log", RichLog)
        if event.button.id == "ops-back":
            self.app.action_show_chat()
            return
        if event.button.id == "ops-tail":
            try:
                jobs = await asyncio.to_thread(self.app.get_recent_observable_jobs, 3)
            except Exception as exc:
                log.write(f"Failed to load recent jobs: {exc}")
                return
            if not jobs:
                log.write("No recent jobs recorded.")
                return
            for job in jobs:
                if "title" in job or "job_family" in job:
                    log.write(_backend_ops_tail_line(job))
                else:
                    log.write(
                        f"{job['job_id']} {job['status']} out={job.get('stdout_path')}"
                    )
            return
        if event.button.id == "ops-kill-action":
            await self.app.cancel_active_action(log_target="ops-log")
            return

        if event.button.id == "ops-run-daily-news":
            args = self.app.action_registry.parse_kv_args(
                self.query_one("#ops-args", Input).value
            )
            await self.app.execute_action(
                "daily_news_ingest", args, log_target="ops-log"
            )
            return
        if event.button.id == "ops-run-daily-announcements":
            args = self.app.action_registry.parse_kv_args(
                self.query_one("#ops-args", Input).value
            )
            await self.app.execute_action(
                "daily_announcement_ingest", args, log_target="ops-log"
            )
            return
        if event.button.id == "ops-run-historical-news":
            args = self.app.action_registry.parse_kv_args(
                self.query_one("#ops-args", Input).value
            )
            await self.app.execute_action(
                "historical_news_ingest", args, log_target="ops-log"
            )
            return
        if event.button.id == "ops-run-single-ticker-backfill":
            args = self.app.action_registry.parse_kv_args(
                self.query_one("#ops-args", Input).value
            )
            await self.app.execute_action(
                "single_ticker_announcement_backfill", args, log_target="ops-log"
            )
            return
        if event.button.id == "ops-run-universe-backfill":
            args = self.app.action_registry.parse_kv_args(
                self.query_one("#ops-args", Input).value
            )
            await self.app.execute_action(
                "universe_announcement_enrichment_backfill", args, log_target="ops-log"
            )
            return
        if event.button.id == "ops-run-metric-extraction":
            args = self.app.action_registry.parse_kv_args(
                self.query_one("#ops-args", Input).value
            )
            await self.app.execute_action(
                "metric_extraction", args, log_target="ops-log"
            )
            return

        action_id = self.query_one("#ops-action", Select).value
        args_text = self.query_one("#ops-args", Input).value
        if not action_id:
            log.write("No action selected")
            return
        args = self.app.action_registry.parse_kv_args(args_text)
        await self.app.execute_action(action_id, args, log_target="ops-log")

    async def action_run_daily_news_ingest(self) -> None:
        args = self.app.action_registry.parse_kv_args(
            self.query_one("#ops-args", Input).value
        )
        await self.app.execute_action("daily_news_ingest", args, log_target="ops-log")


class UpdaterScreen(Screen):
    def compose(self) -> ComposeResult:
        yield Label("Financial Data Updater")
        yield Horizontal(
            Input(value="", id="upd-ticker", placeholder="Ticker (e.g. CSL, BHP)"),
            Input(value="5", id="upd-years", placeholder="Years"),
            Input(
                value="true",
                id="upd-process",
                placeholder="process_documents true/false",
            ),
        )
        yield Horizontal(
            Input(value="", id="upd-since", placeholder="since YYYY-MM-DD (optional)"),
            Input(
                value="0.40", id="upd-lowconf", placeholder="low confidence threshold"
            ),
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
        ticker = self.query_one("#upd-ticker", Input).value.strip().upper()
        if not ticker:
            log.write("⚠ Enter a ticker before running an action.")
            return
        if event.button.id == "upd-latest":
            if self.app._backend_client:
                try:
                    ctx = self.app._backend_client.get_ticker_context(
                        ticker, financials_limit=1
                    )
                    row = ctx.get("latest_financial_snapshot")
                except Exception as exc:
                    row = {"ticker": ticker, "error": f"Backend fetch failed: {exc}"}
            else:
                row = {"ticker": ticker, "error": "Backend API client not configured"}
            log.write(
                json.dumps(
                    row or {"ticker": ticker, "message": "no data"},
                    default=str,
                    indent=2,
                )
            )
            return
        if event.button.id == "upd-rebuild":
            since = self.query_one("#upd-since", Input).value.strip()
            args = {"ticker": ticker}
            if since:
                args["since"] = since
            await self.app.execute_action(
                "rebuild_ticker_financials", args, log_target="upd-log"
            )
            return
        if event.button.id == "upd-audit":
            lowconf_raw = self.query_one("#upd-lowconf", Input).value.strip()
            args: dict[str, Any] = {"ticker": ticker}
            if lowconf_raw:
                args["low_confidence_threshold"] = lowconf_raw
            await self.app.execute_action(
                "audit_ticker_financials", args, log_target="upd-log"
            )
            return

        try:
            years = int(self.query_one("#upd-years", Input).value.strip() or "5")
        except (ValueError, TypeError):
            log.write("Invalid years value, defaulting to 5")
            years = 5
        process_documents = self.query_one(
            "#upd-process", Input
        ).value.strip().lower() in {"1", "true", "yes", "on"}
        await self.app.run_updater_snapshot(
            ticker=ticker,
            years=years,
            process_documents=process_documents,
            log_target="upd-log",
        )


class VerificationScreen(Screen):
    BINDINGS = [
        Binding("a", "approve_metric", "Approve"),
        Binding("w", "mark_wrong", "Wrong"),
        Binding("u", "skip_metric", "Skip"),
        Binding("left", "prev_metric", "Prev", show=False),
        Binding("right", "next_metric", "Next", show=False),
    ]

    def __init__(self) -> None:
        super().__init__()
        self._verification_docs: list[dict[str, Any]] = []
        self._review_runs: list[dict[str, Any]] = []
        self._review_session: dict[str, Any] | None = None
        self._review_items: list[dict[str, Any]] = []
        self._review_index: int = 0

    def compose(self) -> ComposeResult:
        yield Label("Data Verification")
        yield Horizontal(
            Input(value="", id="ver-ticker", placeholder="Ticker (e.g. CSL)"),
            Input(value="10", id="ver-doc-limit", placeholder="Docs"),
        )
        yield Horizontal(
            Button("Run Verification", id="ver-run", variant="primary"),
            Button("Load Docs", id="ver-load-docs"),
            Button("Load Runs", id="ver-load-runs"),
            Button("Run Extraction", id="ver-run-extraction", variant="warning"),
            Button("Load Review", id="ver-load-review", variant="success"),
            Button("Show Wrong Queue", id="ver-show-errors"),
            Button("Export Verification", id="ver-export"),
        )
        yield Input(
            value="",
            id="ver-doc-ids",
            placeholder="Optional extra document_ids (comma separated) for a small review set",
        )
        yield Input(
            value="",
            id="ver-run-ids",
            placeholder="Optional run_ids (comma separated) for a prior extraction run review",
        )
        yield DataTable(id="ver-docs")
        yield DataTable(id="ver-runs")
        yield Static("No review session loaded.", id="ver-item-summary")
        yield Static("", id="ver-item-meta")
        yield Horizontal(
            Input(
                value="",
                id="ver-expected",
                placeholder="Correct / expected value (optional)",
            ),
            Input(value="", id="ver-note", placeholder="Reviewer note (optional)"),
        )
        yield Horizontal(
            Button("Prev", id="ver-prev"),
            Button("Approve", id="ver-approve", variant="success"),
            Button("Wrong", id="ver-wrong", variant="error"),
            Button("Skip / Unsure", id="ver-skip"),
            Button("Next", id="ver-next"),
        )
        yield RichLog(id="ver-log", wrap=False, markup=False)
        yield RichLog(id="ver-queue-log", wrap=True, markup=False)

    def on_mount(self) -> None:
        table = self.query_one("#ver-docs", DataTable)
        table.cursor_type = "row"
        table.add_columns("Published", "Document", "Class", "Title")
        runs_table = self.query_one("#ver-runs", DataTable)
        runs_table.cursor_type = "row"
        runs_table.add_columns(
            "Created", "Run", "Document", "Status", "Metrics", "Model"
        )

    def _parse_doc_limit(self) -> int:
        raw = self.query_one("#ver-doc-limit", Input).value.strip()
        try:
            return max(1, min(50, int(raw or "10")))
        except (TypeError, ValueError):
            return 10

    def _render_docs(self) -> None:
        table = self.query_one("#ver-docs", DataTable)
        table.clear()
        for doc in self._verification_docs:
            published_at = str(doc.get("published_at") or "")[:10]
            document_id = str(doc.get("document_id") or "")[:12]
            doc_class = str(doc.get("doc_class") or "")
            title = str(doc.get("title") or "")[:80]
            table.add_row(published_at, document_id, doc_class, title)

    def _render_runs(self) -> None:
        table = self.query_one("#ver-runs", DataTable)
        table.clear()
        for run in self._review_runs:
            created_at = str(run.get("created_at") or "")[:16].replace("T", " ")
            run_id = str(run.get("run_id") or "")[:12]
            document_id = str(run.get("document_id") or "")[:12]
            status = str(run.get("status") or "")
            metrics_count = str(run.get("metrics_count") or 0)
            model_name = str(run.get("model_name") or "")[:24]
            table.add_row(
                created_at, run_id, document_id, status, metrics_count, model_name
            )

    def _selected_document_ids(self) -> list[str]:
        selected: list[str] = []
        if self._verification_docs:
            table = self.query_one("#ver-docs", DataTable)
            try:
                row_index = int(getattr(table, "cursor_row", 0) or 0)
            except Exception:
                row_index = 0
            if 0 <= row_index < len(self._verification_docs):
                document_id = str(
                    self._verification_docs[row_index].get("document_id") or ""
                ).strip()
                if document_id:
                    selected.append(document_id)

        extra = self.query_one("#ver-doc-ids", Input).value
        for chunk in extra.replace("\n", ",").split(","):
            document_id = chunk.strip()
            if document_id and document_id not in selected:
                selected.append(document_id)
        return selected

    def _selected_run_ids(self) -> list[str]:
        selected: list[str] = []
        if self._review_runs:
            table = self.query_one("#ver-runs", DataTable)
            try:
                row_index = int(getattr(table, "cursor_row", 0) or 0)
            except Exception:
                row_index = 0
            if 0 <= row_index < len(self._review_runs):
                run_id = str(self._review_runs[row_index].get("run_id") or "").strip()
                if run_id:
                    selected.append(run_id)

        extra = self.query_one("#ver-run-ids", Input).value
        for chunk in extra.replace("\n", ",").split(","):
            run_id = chunk.strip()
            if run_id and run_id not in selected:
                selected.append(run_id)
        return selected

    def _current_review_item(self) -> dict[str, Any] | None:
        if not self._review_items:
            return None
        self._review_index = max(
            0, min(self._review_index, len(self._review_items) - 1)
        )
        return self._review_items[self._review_index]

    def _render_review_item(self) -> None:
        summary = self.query_one("#ver-item-summary", Static)
        meta = self.query_one("#ver-item-meta", Static)
        log = self.query_one("#ver-log", RichLog)
        log.clear()

        item = self._current_review_item()
        if item is None:
            summary.update("No review items loaded.")
            meta.update("")
            return

        summary.update(
            "Review {current}/{total}: {metric} | {ticker} | {status}".format(
                current=self._review_index + 1,
                total=len(self._review_items),
                metric=item.get("metric_name", "metric"),
                ticker=item.get("ticker", "?"),
                status=item.get("review_status", "pending"),
            )
        )
        meta.update(
            "Run: {run_id} | Value: {value} | Period: {ptype} {pend} | Page: {page} | Provenance: {prov}\n"
            "Doc: {doc}\nFile: {file_path}\nEvidence: {summary}".format(
                run_id=item.get("run_id") or "?",
                value=item.get("extracted_value"),
                ptype=item.get("period_type") or "?",
                pend=item.get("period_end") or "?",
                page=item.get("page_number") or "?",
                prov=item.get("provenance_status") or "unknown",
                doc=item.get("document_id") or "?",
                file_path=item.get("file_path") or "?",
                summary=item.get("evidence_summary") or "none recorded",
            )
        )

        snippet = item.get("snippet") if isinstance(item.get("snippet"), dict) else {}
        log.write(f"Snippet kind: {snippet.get('kind', 'text_only')}")
        if snippet.get("image_path"):
            log.write(f"Image artifact: {snippet['image_path']}")
        if snippet.get("reason"):
            log.write(f"Snippet note: {snippet['reason']}")
        matched_text = snippet.get("matched_text") or item.get("evidence_text")
        if matched_text:
            log.write("Matched text:")
            for line in str(matched_text).splitlines():
                log.write(f"  {line}")
        ascii_preview = snippet.get("ascii_preview")
        if ascii_preview:
            log.write("ASCII preview:")
            for line in str(ascii_preview).splitlines():
                log.write(line)
        elif item.get("evidence_text"):
            log.write("Text evidence only:")
            for line in str(item.get("evidence_text") or "").splitlines():
                log.write(f"  {line}")

    def _render_error_queue(self, payload: dict[str, Any]) -> None:
        log = self.query_one("#ver-queue-log", RichLog)
        log.clear()
        items = payload.get("items") if isinstance(payload.get("items"), list) else []
        log.write(f"Wrong queue ({len(items)} item(s))")
        for item in items[:20]:
            log.write(
                "- {ticker} {metric} = {value} | expected={expected} | page={page} | note={note}".format(
                    ticker=item.get("ticker") or "?",
                    metric=item.get("metric_name") or "metric",
                    value=item.get("extracted_value"),
                    expected=item.get("expected_value") or "",
                    page=item.get("page_number") or "?",
                    note=item.get("reviewer_note") or "",
                )
            )

    async def _load_docs(self) -> None:
        ticker = self.query_one("#ver-ticker", Input).value.strip().upper()
        if not ticker:
            self.query_one("#ver-log", RichLog).write(
                "Ticker is required to load documents."
            )
            return
        if not getattr(self.app, "_backend_client", None):
            self.query_one("#ver-log", RichLog).write(
                "Backend API client not configured."
            )
            return
        payload = await asyncio.to_thread(
            self.app._backend_client.get_ticker_context,
            ticker,
            docs_limit=self._parse_doc_limit(),
            financials_limit=1,
            announcements_limit=1,
            failures_limit=5,
            low_confidence_limit=5,
        )
        docs = payload.get("docs") if isinstance(payload.get("docs"), list) else []
        self._verification_docs = [doc for doc in docs if isinstance(doc, dict)]
        self._render_docs()
        self.query_one("#ver-log", RichLog).write(
            f"Loaded {len(self._verification_docs)} document(s). Cursor row selects the primary document."
        )

    async def _load_runs(self) -> None:
        ticker = self.query_one("#ver-ticker", Input).value.strip().upper()
        log = self.query_one("#ver-log", RichLog)
        if not ticker:
            log.write("Ticker is required to load extraction runs.")
            return
        if not getattr(self.app, "_backend_client", None):
            log.write("Backend API client not configured.")
            return
        payload = await asyncio.to_thread(
            self.app.list_extraction_review_runs,
            ticker=ticker,
            limit=max(10, self._parse_doc_limit() * 3),
        )
        items = payload.get("items") if isinstance(payload.get("items"), list) else []
        self._review_runs = [item for item in items if isinstance(item, dict)]
        self._render_runs()
        log.write(
            f"Loaded {len(self._review_runs)} extraction run(s) for {ticker}. Cursor row selects the run to review."
        )

    async def _run_selected_extraction(self) -> None:
        document_ids = self._selected_document_ids()
        log = self.query_one("#ver-log", RichLog)
        if not document_ids:
            log.write("Select a document row or enter document_ids first.")
            return
        for document_id in document_ids:
            try:
                result = await asyncio.to_thread(
                    self.app.run_document_extraction, document_id
                )
                log.write(
                    f"Extraction run for {document_id}: {result.get('extraction_status', result.get('mode', 'ok'))}"
                )
            except Exception as exc:
                log.write(f"Extraction failed for {document_id}: {exc}")

    async def _load_review(self) -> None:
        log = self.query_one("#ver-log", RichLog)
        run_ids = self._selected_run_ids()
        document_ids: list[str] = []
        if not run_ids:
            document_ids = self._selected_document_ids()
            if not document_ids:
                log.write(
                    "Select a run row / enter run_ids, or select a document row / enter document_ids first."
                )
                return
        try:
            session = await asyncio.to_thread(
                self.app.create_extraction_review_session,
                document_ids,
                run_ids=run_ids or None,
            )
        except Exception as exc:
            log.write(f"Failed to create review session: {exc}")
            return
        self._review_session = session
        self._review_items = (
            session.get("items") if isinstance(session.get("items"), list) else []
        )
        self._review_index = 0
        log.write(
            f"Review session {session.get('session_id')} loaded with {len(self._review_items)} metric item(s)."
        )
        self._render_review_item()
        await self._show_error_queue()

    async def _show_error_queue(self) -> None:
        try:
            payload = await asyncio.to_thread(self.app.get_extraction_review_errors)
        except Exception as exc:
            self.query_one("#ver-queue-log", RichLog).write(
                f"Failed to load wrong queue: {exc}"
            )
            return
        self._render_error_queue(payload)

    async def _submit_review(self, status: str) -> None:
        item = self._current_review_item()
        log = self.query_one("#ver-log", RichLog)
        if item is None or not self._review_session:
            log.write("Load a review session first.")
            return
        expected_value = self.query_one("#ver-expected", Input).value.strip() or None
        reviewer_note = self.query_one("#ver-note", Input).value.strip()
        try:
            result = await asyncio.to_thread(
                self.app.submit_extraction_review_decision,
                str(self._review_session.get("session_id") or ""),
                item_id=str(item.get("item_id") or ""),
                status=status,
                expected_value=expected_value,
                reviewer_note=reviewer_note,
            )
        except Exception as exc:
            log.write(f"Failed to save review decision: {exc}")
            return

        updated_item = (
            result.get("item") if isinstance(result.get("item"), dict) else None
        )
        if updated_item is not None:
            self._review_items[self._review_index] = updated_item
        if isinstance(self._review_session, dict):
            self._review_session["items"] = list(self._review_items)
            if isinstance(result.get("summary"), dict):
                self._review_session["summary"] = result.get("summary")
        self.query_one("#ver-expected", Input).value = ""
        self.query_one("#ver-note", Input).value = ""
        log.write(
            f"Saved {status} for {item.get('metric_name')} ({item.get('document_id')})."
        )
        if self._review_index < len(self._review_items) - 1:
            self._review_index += 1
        self._render_review_item()
        await self._show_error_queue()

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        ticker = self.query_one("#ver-ticker", Input).value.strip().upper()
        if event.button.id == "ver-run":
            payload = self.app.run_verification(ticker=ticker or None)
            self.app.last_verification_payload = payload
            self.query_one("#ver-log", RichLog).write(
                json.dumps(payload, default=str, indent=2)
            )
            return
        if event.button.id == "ver-load-docs":
            await self._load_docs()
            return
        if event.button.id == "ver-load-runs":
            await self._load_runs()
            return
        if event.button.id == "ver-run-extraction":
            await self._run_selected_extraction()
            return
        if event.button.id == "ver-load-review":
            await self._load_review()
            return
        if event.button.id == "ver-show-errors":
            await self._show_error_queue()
            return
        if event.button.id == "ver-approve":
            await self._submit_review("approved")
            return
        if event.button.id == "ver-wrong":
            await self._submit_review("wrong")
            return
        if event.button.id == "ver-skip":
            await self._submit_review("abstain")
            return
        if event.button.id == "ver-prev":
            self.action_prev_metric()
            return
        if event.button.id == "ver-next":
            self.action_next_metric()
            return

        if self._review_session:
            out_path = self.app.write_report_json(
                f"reports/cockpit/extraction_review_{self.app.timestamp()}.json",
                self._review_session,
            )
            self.query_one("#ver-log", RichLog).write(
                f"Exported review session JSON: {out_path}"
            )
            try:
                queue_payload = await asyncio.to_thread(
                    self.app.get_extraction_review_errors
                )
            except Exception:
                queue_payload = None
            if queue_payload is not None:
                queue_path = self.app.write_report_json(
                    f"reports/cockpit/extraction_review_wrong_queue_{self.app.timestamp()}.json",
                    queue_payload,
                )
                self.query_one("#ver-log", RichLog).write(
                    f"Exported wrong queue JSON: {queue_path}"
                )
            return

        if not self.app.last_verification_payload:
            self.query_one("#ver-log", RichLog).write(
                "Run verification or load a review session first"
            )
            return
        out_path = self.app.write_report_json(
            f"reports/cockpit/verification_{self.app.timestamp()}.json",
            self.app.last_verification_payload,
        )
        html_path = self.app.write_report_html(
            f"reports/cockpit/verification_{self.app.timestamp()}_dashboard.html",
            build_verification_dashboard_html(self.app.last_verification_payload),
        )
        self.query_one("#ver-log", RichLog).write(f"Exported JSON: {out_path}")
        self.query_one("#ver-log", RichLog).write(
            f"Exported HTML dashboard: {html_path}"
        )

    async def action_approve_metric(self) -> None:
        await self._submit_review("approved")

    async def action_mark_wrong(self) -> None:
        await self._submit_review("wrong")

    async def action_skip_metric(self) -> None:
        await self._submit_review("abstain")

    def action_prev_metric(self) -> None:
        if self._review_items and self._review_index > 0:
            self._review_index -= 1
            self._render_review_item()

    def action_next_metric(self) -> None:
        if self._review_items and self._review_index < len(self._review_items) - 1:
            self._review_index += 1
            self._render_review_item()


class MemoryScreen(Screen):
    BINDINGS = [
        ("escape", "app.show_chat", "Back"),
        ("r", "refresh", "Refresh"),
        ("d", "expire_selected", "Expire"),
    ]

    def __init__(self) -> None:
        super().__init__()
        self._loaded_ticker: str = ""
        self._memory_rows: list[dict[str, Any]] = []
        self._memory_payload: dict[str, Any] = {}

    def compose(self) -> ComposeResult:
        yield Label("Backend Memory")
        yield Horizontal(
            Input(value="", id="memory-ticker", placeholder="Ticker (e.g. BHP)"),
            Button("Load", id="memory-load", variant="primary"),
            Button("Refresh", id="memory-refresh"),
            Button("Expire Selected", id="memory-expire", variant="warning"),
            id="memory-controls",
        )
        yield Horizontal(
            Select(
                [(label, value) for label, value in _MEMORY_SCOPE_OPTIONS],
                value="company",
                id="memory-note-scope",
                prompt="Scope",
            ),
            Input(
                value="",
                id="memory-note-type",
                placeholder="Type (blank uses scope default)",
            ),
            Input(value="", id="memory-note", placeholder="Manual note"),
            Button("Add Note", id="memory-add-note", variant="success"),
            id="memory-note-controls",
        )
        yield Static("No ticker loaded.", id="memory-summary")
        yield DataTable(id="memory-table")
        yield Static("", id="memory-status")

    def on_mount(self) -> None:
        table = self.query_one("#memory-table", DataTable)
        table.cursor_type = "row"
        table.add_columns("Source", "ID", "Entity", "Type", "Status", "Seen", "Statement")
        self.query_one("#memory-ticker", Input).focus()

    def _backend_client(self) -> Any | None:
        return getattr(self.app, "_backend_client", None)

    def _set_status(self, message: str) -> None:
        self.query_one("#memory-status", Static).update(str(message or ""))

    def _resolve_ticker(self) -> str:
        raw = self.query_one("#memory-ticker", Input).value.strip().upper()
        return raw or self._loaded_ticker

    def _selected_note_scope(self) -> str:
        value = self.query_one("#memory-note-scope", Select).value
        if isinstance(value, str) and value in _MEMORY_DEFAULT_TYPES:
            return value
        return "company"

    def _selected_row(self) -> dict[str, Any] | None:
        if not self._memory_rows:
            return None
        table = self.query_one("#memory-table", DataTable)
        try:
            row_index = int(getattr(table, "cursor_row", 0) or 0)
        except Exception:
            row_index = 0
        if 0 <= row_index < len(self._memory_rows):
            return self._memory_rows[row_index]
        return None

    def _build_memory_rows(self, payload: dict[str, Any], ticker: str) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        company_memory = (
            payload.get("company_memory")
            if isinstance(payload.get("company_memory"), dict)
            else {}
        )
        market_memory = (
            payload.get("market_memory")
            if isinstance(payload.get("market_memory"), dict)
            else {}
        )
        sector_name = str(market_memory.get("sector") or "").strip() or "sector"

        for item in company_memory.get("entries") or []:
            if not isinstance(item, dict):
                continue
            entry_id = int(item.get("entry_id") or 0)
            status = str(item.get("status") or "-")
            rows.append(
                {
                    "kind": "company",
                    "display_id": str(entry_id or "-"),
                    "entry_id": entry_id,
                    "ticker": ticker,
                    "scope": "company",
                    "entity": ticker,
                    "type": str(item.get("type") or "-"),
                    "status": status,
                    "seen_at": _memory_timestamp(
                        item.get("last_seen_at") or item.get("created_at")
                    ),
                    "statement": str(item.get("statement") or "-"),
                    "removable": status.lower() == "active" and entry_id > 0,
                }
            )

        for item in market_memory.get("sector_items") or []:
            if not isinstance(item, dict):
                continue
            entry_id = int(item.get("entry_id") or 0)
            status = str(item.get("status") or "-")
            rows.append(
                {
                    "kind": "sector",
                    "display_id": str(entry_id or "-"),
                    "entry_id": entry_id,
                    "ticker": ticker,
                    "scope": "sector",
                    "entity": str(item.get("sector") or sector_name),
                    "type": str(item.get("type") or "-"),
                    "status": status,
                    "seen_at": _memory_timestamp(
                        item.get("last_seen_at") or item.get("created_at")
                    ),
                    "statement": str(item.get("statement") or "-"),
                    "removable": status.lower() == "active" and entry_id > 0,
                }
            )

        for item in market_memory.get("macro_items") or []:
            if not isinstance(item, dict):
                continue
            entry_id = int(item.get("entry_id") or 0)
            status = str(item.get("status") or "-")
            rows.append(
                {
                    "kind": "macro",
                    "display_id": str(entry_id or "-"),
                    "entry_id": entry_id,
                    "ticker": ticker,
                    "scope": "macro",
                    "entity": str(item.get("macro_topic") or "macro"),
                    "type": str(item.get("type") or "-"),
                    "status": status,
                    "seen_at": _memory_timestamp(
                        item.get("last_seen_at") or item.get("created_at")
                    ),
                    "statement": str(item.get("statement") or "-"),
                    "removable": status.lower() == "active" and entry_id > 0,
                }
            )

        for item in company_memory.get("change_log") or []:
            if not isinstance(item, dict):
                continue
            change_id = int(item.get("change_id") or 0)
            rows.append(
                {
                    "kind": "company-log",
                    "display_id": f"log:{change_id}" if change_id else "log",
                    "entry_id": change_id,
                    "ticker": ticker,
                    "scope": "company-log",
                    "entity": ticker,
                    "type": str(item.get("event_type") or "change"),
                    "status": "log",
                    "seen_at": _memory_timestamp(item.get("created_at")),
                    "statement": _memory_change_summary(item.get("details")),
                    "removable": False,
                }
            )
        return rows

    def _render_memory_rows(self) -> None:
        table = self.query_one("#memory-table", DataTable)
        table.clear()
        for row in self._memory_rows:
            table.add_row(
                row["kind"],
                row["display_id"],
                row["entity"],
                row["type"],
                row["status"],
                row["seen_at"],
                row["statement"],
            )

    def _render_summary(self, payload: dict[str, Any], ticker: str) -> None:
        company_memory = (
            payload.get("company_memory")
            if isinstance(payload.get("company_memory"), dict)
            else {}
        )
        market_memory = (
            payload.get("market_memory")
            if isinstance(payload.get("market_memory"), dict)
            else {}
        )
        summary = (
            f"{ticker} | company entries: "
            f"{int(company_memory.get('entries_total', len(company_memory.get('entries') or [])) or 0)}"
            f" | company changes: "
            f"{int(company_memory.get('change_log_total', len(company_memory.get('change_log') or [])) or 0)}"
            f" | market items: "
            f"{int(market_memory.get('items_total', len(market_memory.get('items') or [])) or 0)}"
            f" | sector: {market_memory.get('sector') or '-'}"
        )
        self.query_one("#memory-summary", Static).update(summary)

    async def _load_memory(
        self,
        *,
        ticker: str | None = None,
        notice: str | None = None,
    ) -> None:
        client = self._backend_client()
        if client is None:
            self._set_status("Backend API client not configured.")
            return

        resolved_ticker = str(ticker or self._resolve_ticker()).strip().upper()
        if not resolved_ticker:
            self._set_status("Ticker is required.")
            return

        self.query_one("#memory-ticker", Input).value = resolved_ticker
        try:
            payload = await asyncio.to_thread(
                client.get_memory_dump,
                resolved_ticker,
                company_memory_entries_limit=300,
                company_memory_change_limit=150,
                market_memory_limit=150,
            )
        except Exception as exc:
            self._set_status(f"Failed to load memory for {resolved_ticker}: {exc}")
            return

        payload = payload if isinstance(payload, dict) else {}
        self._loaded_ticker = resolved_ticker
        self._memory_payload = payload
        self._memory_rows = self._build_memory_rows(payload, resolved_ticker)
        self._render_memory_rows()
        self._render_summary(payload, resolved_ticker)

        errors = payload.get("errors") if isinstance(payload.get("errors"), list) else []
        status_parts: list[str] = []
        if notice:
            status_parts.append(notice)
        if errors:
            status_parts.append("Errors: " + "; ".join(str(err) for err in errors))
        else:
            status_parts.append(
                f"Loaded {len(self._memory_rows)} row(s) for {resolved_ticker}."
            )
        self._set_status(" ".join(status_parts))

    async def _add_note(self) -> None:
        client = self._backend_client()
        if client is None:
            self._set_status("Backend API client not configured.")
            return

        ticker = self._resolve_ticker()
        if not ticker:
            self._set_status("Ticker is required before adding a note.")
            return

        note = self.query_one("#memory-note", Input).value.strip()
        if not note:
            self._set_status("Enter a note before submitting.")
            return

        scope = self._selected_note_scope()
        raw_type = self.query_one("#memory-note-type", Input).value.strip().lower()
        try:
            if scope == "company":
                result = await asyncio.to_thread(
                    client.add_company_memory_note,
                    ticker,
                    note,
                    type_=raw_type or _MEMORY_DEFAULT_TYPES["company"],
                )
            else:
                result = await asyncio.to_thread(
                    client.add_market_memory_note,
                    ticker,
                    note,
                    scope=scope,
                    type_=raw_type or None,
                )
        except Exception as exc:
            self._set_status(f"Failed to add {scope} note for {ticker}: {exc}")
            return

        self.query_one("#memory-note", Input).value = ""
        self.query_one("#memory-note-type", Input).value = ""
        entry = result.get("entry") if isinstance(result, dict) else {}
        entry_id = entry.get("entry_id") if isinstance(entry, dict) else None
        await self._load_memory(
            ticker=ticker,
            notice=f"Added {scope} note{f' {entry_id}' if entry_id else ''} for {ticker}.",
        )

    async def _expire_selected(self) -> None:
        client = self._backend_client()
        if client is None:
            self._set_status("Backend API client not configured.")
            return

        row = self._selected_row()
        if row is None:
            self._set_status("Select a memory row first.")
            return
        if not bool(row.get("removable")):
            self._set_status("Select an active company, sector, or macro memory row.")
            return

        entry_id = int(row.get("entry_id") or 0)
        if entry_id <= 0:
            self._set_status("Selected row does not have a valid entry id.")
            return

        try:
            if row.get("scope") == "company":
                await asyncio.to_thread(
                    client.expire_company_memory_entry,
                    str(row.get("ticker") or self._loaded_ticker),
                    entry_id,
                )
            else:
                await asyncio.to_thread(
                    client.expire_market_memory_entry,
                    entry_id,
                    scope=str(row.get("scope") or ""),
                )
        except Exception as exc:
            self._set_status(f"Failed to expire row {row.get('display_id')}: {exc}")
            return

        await self._load_memory(
            ticker=str(row.get("ticker") or self._loaded_ticker),
            notice=f"Expired {row.get('kind')} row {row.get('display_id')}.",
        )

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "memory-load":
            await self._load_memory()
            return
        if event.button.id == "memory-refresh":
            await self._load_memory()
            return
        if event.button.id == "memory-add-note":
            await self._add_note()
            return
        if event.button.id == "memory-expire":
            await self._expire_selected()

    async def on_input_submitted(self, event: Input.Submitted) -> None:
        if event.input.id == "memory-ticker":
            await self._load_memory()
            return
        if event.input.id in {"memory-note", "memory-note-type"}:
            await self._add_note()

    async def action_refresh(self) -> None:
        await self._load_memory()

    async def action_expire_selected(self) -> None:
        await self._expire_selected()


class HistoryScreen(Screen):
    def compose(self) -> ComposeResult:
        yield Label("Run & Export History")
        yield Button("Refresh", id="hist-refresh")
        table = DataTable(id="hist-table")
        table.add_columns(
            "Kind",
            "ID/Thread",
            "Status",
            "Phase",
            "Ticker/Scope",
            "When",
            "Summary / Artifact",
        )
        yield table

    async def on_mount(self) -> None:
        await self._refresh()

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "hist-refresh":
            await self._refresh()

    async def _refresh(self) -> None:
        table = self.query_one("#hist-table", DataTable)
        table.clear()
        jobs = await asyncio.to_thread(self.app.get_recent_observable_jobs, 40)
        for job in jobs:
            if "title" in job or "job_family" in job:
                table.add_row(
                    "ops",
                    str(job.get("job_id") or ""),
                    str(job.get("status") or ""),
                    str(job.get("phase") or ""),
                    _backend_ops_scope(job),
                    str(job.get("started_at") or job.get("queued_at") or ""),
                    _backend_ops_detail(job),
                )
            else:
                table.add_row(
                    "job",
                    job["job_id"],
                    job["status"],
                    "",
                    job.get("ticker") or job.get("entity_scope") or "",
                    job["started_at"],
                    job.get("stdout_path") or "",
                )
        for export in self.app.state_store.list_exports(limit=40):
            table.add_row(
                "analysis",
                export["thread_id"],
                "saved",
                "",
                "",
                export["created_at"],
                export["markdown_path"],
            )


class SettingsScreen(Screen):
    def compose(self) -> ComposeResult:
        yield Label("Cockpit Settings")
        yield Button("Open Help", id="settings-open-help", variant="primary")
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

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "settings-open-help":
            self.app.push_screen(HelpScreen(repo_root=self.app.repo_root))


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
        if event.input.id in (
            "news-query",
            "news-ticker",
            "news-date-from",
            "news-date-to",
        ):
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
            source_status.update(
                "Source: SQLite (fallback) [WARNING: Qdrant unavailable]"
            )

        if not hits:
            log.write("No results found.")
            return

        for i, hit in enumerate(hits, 1):
            title = str(hit.get("title") or hit.get("headline") or "(no title)")
            provider = str(
                hit.get("provider")
                or hit.get("source")
                or hit.get("source_domain")
                or ""
            )
            published = str(hit.get("published_at") or hit.get("doc_date") or "")
            hit_ticker = str(hit.get("ticker") or "")
            score = (
                hit.get("score") or hit.get("final_score") or hit.get("semantic_score")
            )
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
