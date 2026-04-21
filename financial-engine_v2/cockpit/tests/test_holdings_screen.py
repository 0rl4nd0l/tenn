"""Textual UI tests for the cockpit Holdings screen (P6).

The HoldingsScreen renders cockpit-local holdings (P1 schema) and exposes
add/remove actions backed by the real `StateStore` SQLite store. No backend,
no LLM, no GPU — these tests stay safe to run alongside live extraction.
"""
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

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


@unittest.skipIf(CockpitApp is None, "textual/cockpit UI deps unavailable in this environment")
class HoldingsScreenTests(unittest.IsolatedAsyncioTestCase):
    def _build_app(self, tmpdir: Path) -> CockpitApp:
        app = CockpitApp(repo_root=REPO_ROOT, config=_build_config(tmpdir), read_only=False)

        async def _noop_async() -> None:
            return None

        app._run_startup_health_checks = _noop_async  # type: ignore[method-assign]
        app._sync_access_state_from_backend = _noop_async  # type: ignore[method-assign]
        app._refresh_model_status_widget = _noop_async  # type: ignore[method-assign]
        app._schedule_model_status_refresh = lambda: None  # type: ignore[method-assign]
        return app

    async def test_app_installs_holdings_screen_and_p_binding(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            app = self._build_app(Path(tmp))

            async with app.run_test() as pilot:
                await pilot.pause()

                bindings = {
                    getattr(binding, "key", ""): getattr(binding, "action", "")
                    for binding in app.BINDINGS
                }
                self.assertEqual(bindings.get("p"), "show_holdings")

                self.assertIsNotNone(app.get_screen("holdings"))

                chat_screen = app.get_screen("chat")
                self.assertIsNotNone(chat_screen.query_one("#chat-open-holdings"))

                app.action_show_holdings()
                await pilot.pause()
                self.assertEqual(app.screen, app.get_screen("holdings"))

    async def test_holdings_screen_loads_existing_rows_on_mount(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            app = self._build_app(Path(tmp))
            app.state_store.add_holding(
                "BHP", quantity=100.0, avg_cost=42.5, account_label="CommSec"
            )
            app.state_store.add_holding(
                "CSL", quantity=10.0, avg_cost=290.0, account_label="SMSF"
            )

            async with app.run_test() as pilot:
                await pilot.pause()
                app.action_show_holdings()
                await pilot.pause()

                screen = app.get_screen("holdings")
                table = screen.query_one("#holdings-table", DataTable)
                self.assertEqual(table.row_count, 2)

                status = screen.query_one("#holdings-status", Static)
                self.assertIn("Loaded 2 holding(s)", _widget_text(status))

    async def test_holdings_screen_add_persists_via_state_store(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            app = self._build_app(Path(tmp))

            async with app.run_test() as pilot:
                await pilot.pause()
                app.action_show_holdings()
                await pilot.pause()

                screen = app.get_screen("holdings")
                screen.query_one("#holdings-ticker", Input).value = "wbc"
                screen.query_one("#holdings-quantity", Input).value = "50"
                screen.query_one("#holdings-cost", Input).value = "27.40"
                screen.query_one("#holdings-account", Input).value = "CommSec"

                await screen._add_holding()
                await pilot.pause()

                rows = app.state_store.list_holdings()
                self.assertEqual(len(rows), 1)
                self.assertEqual(rows[0]["ticker"], "WBC")
                self.assertAlmostEqual(float(rows[0]["quantity"]), 50.0)
                self.assertAlmostEqual(float(rows[0]["avg_cost"]), 27.40)
                self.assertEqual(rows[0]["account_label"], "CommSec")

                table = screen.query_one("#holdings-table", DataTable)
                self.assertEqual(table.row_count, 1)

                status = screen.query_one("#holdings-status", Static)
                self.assertIn("Added WBC", _widget_text(status))

                # Inputs cleared after successful add.
                self.assertEqual(screen.query_one("#holdings-ticker", Input).value, "")
                self.assertEqual(screen.query_one("#holdings-quantity", Input).value, "")
                self.assertEqual(screen.query_one("#holdings-cost", Input).value, "")
                self.assertEqual(screen.query_one("#holdings-account", Input).value, "")

    async def test_holdings_screen_add_validation_missing_ticker(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            app = self._build_app(Path(tmp))

            async with app.run_test() as pilot:
                await pilot.pause()
                app.action_show_holdings()
                await pilot.pause()

                screen = app.get_screen("holdings")
                screen.query_one("#holdings-ticker", Input).value = "   "
                screen.query_one("#holdings-quantity", Input).value = "10"

                await screen._add_holding()
                await pilot.pause()

                self.assertEqual(app.state_store.list_holdings(), [])
                status = screen.query_one("#holdings-status", Static)
                self.assertIn("ticker is required", _widget_text(status).lower())

    async def test_holdings_screen_add_validation_non_numeric_quantity(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            app = self._build_app(Path(tmp))

            async with app.run_test() as pilot:
                await pilot.pause()
                app.action_show_holdings()
                await pilot.pause()

                screen = app.get_screen("holdings")
                screen.query_one("#holdings-ticker", Input).value = "BHP"
                screen.query_one("#holdings-quantity", Input).value = "not-a-number"

                await screen._add_holding()
                await pilot.pause()

                self.assertEqual(app.state_store.list_holdings(), [])
                status = screen.query_one("#holdings-status", Static)
                self.assertIn("quantity", _widget_text(status).lower())

    async def test_holdings_screen_remove_selected_calls_state_store(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            app = self._build_app(Path(tmp))
            holding_id = app.state_store.add_holding(
                "BHP", quantity=100.0, avg_cost=42.5
            )
            app.state_store.add_holding("CSL", quantity=10.0, avg_cost=290.0)

            async with app.run_test() as pilot:
                await pilot.pause()
                app.action_show_holdings()
                await pilot.pause()

                screen = app.get_screen("holdings")
                table = screen.query_one("#holdings-table", DataTable)
                self.assertEqual(table.row_count, 2)

                # Position cursor on the BHP row (alphabetical → row 0).
                bhp_index = next(
                    i for i, row in enumerate(screen._holdings_rows)
                    if row["ticker"] == "BHP"
                )
                table.move_cursor(row=bhp_index, column=0, animate=False, scroll=False)

                await screen._remove_selected()
                await pilot.pause()

                remaining = app.state_store.list_holdings()
                self.assertEqual(len(remaining), 1)
                self.assertEqual(remaining[0]["ticker"], "CSL")

                # Removed row gone, table shrunk.
                self.assertEqual(table.row_count, 1)

                status = screen.query_one("#holdings-status", Static)
                text = _widget_text(status)
                self.assertIn("Removed BHP", text)
                # Holding ID short prefix should appear so the operator sees the lineage.
                self.assertIn(holding_id[:8], text)

    async def test_holdings_screen_remove_with_no_selection_is_friendly(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            app = self._build_app(Path(tmp))
            # No holdings seeded.

            async with app.run_test() as pilot:
                await pilot.pause()
                app.action_show_holdings()
                await pilot.pause()

                screen = app.get_screen("holdings")
                await screen._remove_selected()
                await pilot.pause()

                status = screen.query_one("#holdings-status", Static)
                self.assertIn("no holding selected", _widget_text(status).lower())
