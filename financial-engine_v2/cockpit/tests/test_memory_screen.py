from __future__ import annotations

import copy
import tempfile
import unittest
from pathlib import Path
from typing import Any

try:
    from textual.widgets import DataTable, Input, Static

    from cockpit.ui.app import CockpitApp
except ModuleNotFoundError:
    CockpitApp = None
    DataTable = Input = Static = object  # type: ignore[assignment]


REPO_ROOT = Path(__file__).resolve().parents[2]


def _build_config(tmpdir: Path) -> dict[str, object]:
    return {
        "exports": {"dir": str(tmpdir / "exports")},
        "reports": {"dir": str(tmpdir / "reports")},
        "memory": {"state_db": str(tmpdir / "state.db")},
        "db": {"database_url": f"sqlite:///{tmpdir / 'cockpit.sqlite'}"},
        "paths": {"allow_roots": [str(REPO_ROOT)]},
        "llm": {
            "provider": "llamacpp",
            "llamacpp_url": "http://localhost:8001",
            "model": "test-model",
            "timeout_seconds": 5,
        },
        "actions": {"confirm_required": False},
        "backend": {"api_base_url": ""},
        "rag": {},
        "web": {"enabled_default": False},
        "runtime": {},
    }


def _widget_text(widget: Static) -> str:
    renderable = widget.renderable
    if hasattr(renderable, "plain"):
        return str(renderable.plain)
    return str(renderable)


def _sample_memory_payload() -> dict[str, Any]:
    return {
        "ticker": "BHP",
        "company_memory": {
            "status": "ok",
            "entries_total": 1,
            "change_log_total": 1,
            "entries": [
                {
                    "entry_id": 11,
                    "company_id": "BHP",
                    "type": "risk",
                    "statement": "Rail outage is constraining exports.",
                    "status": "active",
                    "last_seen_at": "2026-04-18T01:02:03Z",
                }
            ],
            "change_log": [
                {
                    "change_id": 31,
                    "entry_id": 11,
                    "event_type": "insert",
                    "details": {"source_id": "manual:BHP:11"},
                    "created_at": "2026-04-18T01:02:03Z",
                }
            ],
        },
        "market_memory": {
            "status": "ok",
            "sector": "Materials",
            "items_total": 2,
            "sector_items_total": 1,
            "macro_items_total": 1,
            "sector_items": [
                {
                    "entry_id": 21,
                    "sector": "Materials",
                    "type": "sector_trend",
                    "statement": "Bulk commodity sentiment is improving.",
                    "status": "active",
                    "last_seen_at": "2026-04-18T01:03:03Z",
                }
            ],
            "macro_items": [
                {
                    "entry_id": 22,
                    "macro_topic": "macro",
                    "type": "macro_theme",
                    "statement": "China stimulus expectations are firming.",
                    "status": "active",
                    "last_seen_at": "2026-04-18T01:04:03Z",
                }
            ],
            "items": [],
        },
        "errors": [],
    }


class _FakeBackendClient:
    def __init__(self, payload: dict[str, Any]) -> None:
        self._payload = copy.deepcopy(payload)
        self.calls: list[tuple[str, dict[str, Any]]] = []

    def _record(self, name: str, **payload: Any) -> None:
        self.calls.append((name, payload))

    def get_memory_dump(self, ticker: str, **kwargs: Any) -> dict[str, Any]:
        self._record("get_memory_dump", ticker=ticker, kwargs=kwargs)
        return copy.deepcopy(self._payload)

    def add_company_memory_note(
        self,
        ticker: str,
        statement: str,
        *,
        type_: str = "observed_fact",
        **_: Any,
    ) -> dict[str, Any]:
        entries = self._payload["company_memory"]["entries"]
        change_log = self._payload["company_memory"]["change_log"]
        entry_id = max((int(item["entry_id"]) for item in entries), default=0) + 1
        change_id = max((int(item["change_id"]) for item in change_log), default=0) + 1
        entry = {
            "entry_id": entry_id,
            "company_id": ticker,
            "type": type_,
            "statement": statement,
            "status": "active",
            "last_seen_at": "2026-04-18T05:00:00Z",
        }
        entries.append(entry)
        change_log.append(
            {
                "change_id": change_id,
                "entry_id": entry_id,
                "event_type": "insert",
                "details": {"source_id": f"manual:{ticker}:{entry_id}"},
                "created_at": "2026-04-18T05:00:00Z",
            }
        )
        self._payload["company_memory"]["entries_total"] = len(entries)
        self._payload["company_memory"]["change_log_total"] = len(change_log)
        self._record(
            "add_company_memory_note",
            ticker=ticker,
            statement=statement,
            type_=type_,
        )
        return {"ok": True, "entry": copy.deepcopy(entry)}

    def add_market_memory_note(
        self,
        ticker: str,
        statement: str,
        *,
        scope: str = "sector",
        type_: str | None = None,
        **_: Any,
    ) -> dict[str, Any]:
        target_key = "sector_items" if scope == "sector" else "macro_items"
        entries = self._payload["market_memory"][target_key]
        entry_id = max((int(item["entry_id"]) for item in entries), default=20) + 1
        entry = {
            "entry_id": entry_id,
            "type": type_ or ("sector_trend" if scope == "sector" else "macro_theme"),
            "statement": statement,
            "status": "active",
            "last_seen_at": "2026-04-18T05:10:00Z",
        }
        if scope == "sector":
            entry["sector"] = self._payload["market_memory"]["sector"]
        else:
            entry["macro_topic"] = "macro"
        entries.append(entry)
        self._payload["market_memory"]["items_total"] = (
            len(self._payload["market_memory"]["sector_items"])
            + len(self._payload["market_memory"]["macro_items"])
        )
        self._record(
            "add_market_memory_note",
            ticker=ticker,
            statement=statement,
            scope=scope,
            type_=type_,
        )
        return {"ok": True, "entry": copy.deepcopy(entry)}

    def expire_company_memory_entry(self, ticker: str, entry_id: int, **_: Any) -> dict[str, Any]:
        for item in self._payload["company_memory"]["entries"]:
            if int(item["entry_id"]) == int(entry_id):
                item["status"] = "expired"
        self._record("expire_company_memory_entry", ticker=ticker, entry_id=entry_id)
        return {"ok": True}

    def expire_market_memory_entry(self, entry_id: int, *, scope: str, **_: Any) -> dict[str, Any]:
        target_key = "sector_items" if scope == "sector" else "macro_items"
        for item in self._payload["market_memory"][target_key]:
            if int(item["entry_id"]) == int(entry_id):
                item["status"] = "expired"
        self._record("expire_market_memory_entry", entry_id=entry_id, scope=scope)
        return {"ok": True}


@unittest.skipIf(CockpitApp is None, "textual/cockpit UI deps unavailable in this environment")
class MemoryScreenTests(unittest.IsolatedAsyncioTestCase):
    def _build_app(self, tmpdir: Path, backend_client: _FakeBackendClient | None = None) -> CockpitApp:
        app = CockpitApp(repo_root=REPO_ROOT, config=_build_config(tmpdir), read_only=True)

        async def _noop_async() -> None:
            return None

        app._run_startup_health_checks = _noop_async  # type: ignore[method-assign]
        app._sync_access_state_from_backend = _noop_async  # type: ignore[method-assign]
        app._refresh_model_status_widget = _noop_async  # type: ignore[method-assign]
        app._schedule_model_status_refresh = lambda: None  # type: ignore[method-assign]
        app._backend_client = backend_client
        return app

    async def test_app_installs_memory_screen_and_navigation(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            app = self._build_app(Path(tmp))

            async with app.run_test() as pilot:
                await pilot.pause()

                bindings = {
                    getattr(binding, "key", ""): getattr(binding, "action", "")
                    for binding in app.BINDINGS
                }
                self.assertEqual(bindings.get("m"), "show_memory")

                chat_screen = app.get_screen("chat")
                self.assertIsNotNone(chat_screen.query_one("#chat-open-memory"))
                self.assertIsNotNone(app.get_screen("memory"))

                app.action_show_memory()
                await pilot.pause()

                self.assertEqual(app.screen, app.get_screen("memory"))

    async def test_memory_screen_loads_rows_and_adds_company_note(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            backend = _FakeBackendClient(_sample_memory_payload())
            app = self._build_app(Path(tmp), backend)

            async with app.run_test() as pilot:
                await pilot.pause()
                app.action_show_memory()
                await pilot.pause()

                screen = app.get_screen("memory")
                screen.query_one("#memory-ticker", Input).value = "bhp"
                await screen._load_memory()
                await pilot.pause()

                table = screen.query_one("#memory-table", DataTable)
                summary = screen.query_one("#memory-summary", Static)
                status = screen.query_one("#memory-status", Static)

                self.assertEqual(table.row_count, 4)
                self.assertIn("BHP", _widget_text(summary))
                self.assertIn("company entries: 1", _widget_text(summary))
                self.assertIn("Loaded 4 row(s) for BHP.", _widget_text(status))

                screen.query_one("#memory-note", Input).value = "Manual note from cockpit."
                await screen._add_note()
                await pilot.pause()

                add_calls = [
                    payload for name, payload in backend.calls if name == "add_company_memory_note"
                ]
                self.assertEqual(len(add_calls), 1)
                self.assertEqual(add_calls[0]["ticker"], "BHP")
                self.assertEqual(add_calls[0]["type_"], "observed_fact")
                self.assertEqual(table.row_count, 6)
                self.assertIn("Added company note", _widget_text(status))

    async def test_memory_screen_expires_selected_market_row(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            backend = _FakeBackendClient(_sample_memory_payload())
            app = self._build_app(Path(tmp), backend)

            async with app.run_test() as pilot:
                await pilot.pause()
                app.action_show_memory()
                await pilot.pause()

                screen = app.get_screen("memory")
                screen.query_one("#memory-ticker", Input).value = "BHP"
                await screen._load_memory()
                await pilot.pause()

                table = screen.query_one("#memory-table", DataTable)
                sector_index = next(
                    index
                    for index, row in enumerate(screen._memory_rows)
                    if row["kind"] == "sector"
                )
                table.move_cursor(row=sector_index, column=0, animate=False, scroll=False)
                await screen._expire_selected()
                await pilot.pause()

                expire_calls = [
                    payload
                    for name, payload in backend.calls
                    if name == "expire_market_memory_entry"
                ]
                self.assertEqual(len(expire_calls), 1)
                self.assertEqual(expire_calls[0], {"entry_id": 21, "scope": "sector"})

                status = screen.query_one("#memory-status", Static)
                self.assertIn("Expired sector row 21.", _widget_text(status))

                sector_row = next(
                    row for row in screen._memory_rows if row["kind"] == "sector"
                )
                self.assertEqual(sector_row["status"], "expired")
