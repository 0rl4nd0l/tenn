from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace

from fastapi import FastAPI
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from app.routes.cockpit_api import router
from app.services.cockpit_service import CockpitService


def test_cockpit_execute_action_returns_renderable_chart_for_show_candlestick(
    tmp_path,
    monkeypatch,
) -> None:
    repo_root = tmp_path
    csv_path = repo_root / "reports" / "candles" / "BHP_candles_1d.csv"
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    csv_path.write_text(
        "timestamp,open,high,low,close,volume\n"
        "2026-04-07T00:00:00+00:00,40.1,40.9,39.8,40.5,123\n"
        "2026-04-08T00:00:00+00:00,40.5,41.2,40.2,41.0,456\n",
        encoding="utf-8",
    )

    class FakeArtifactStore:
        def __init__(self) -> None:
            self.writes: list[tuple[str, str]] = []

        def write_text(self, rel_path: str, content: str) -> str:
            self.writes.append((rel_path, content))
            return str(repo_root / rel_path)

    artifact_store = FakeArtifactStore()

    class FakeActionRegistry:
        @staticmethod
        def preview(action_id: str, args: dict[str, object]) -> SimpleNamespace:
            return SimpleNamespace(timeout_seconds=60, command=["noop"], args=args)

    class FakeToolRouter:
        @staticmethod
        def get_price_context_for_window(
            ticker: str,
            *,
            range_: str = "1y",
            interval: str = "1d",
            max_history_rows: int = 260,
        ) -> dict[str, object]:
            return {
                "price_state": {
                    "current": {"close": 41.0},
                    "metrics": {"sample_count": 2},
                },
                "price": {
                    "recent_history": [
                        {
                            "timestamp": "2026-04-07T00:00:00+00:00",
                            "open": 40.1,
                            "high": 40.9,
                            "low": 39.8,
                            "close": 40.5,
                            "volume": 123,
                        },
                        {
                            "timestamp": "2026-04-08T00:00:00+00:00",
                            "open": 40.5,
                            "high": 41.2,
                            "low": 40.2,
                            "close": 41.0,
                            "volume": 456,
                        },
                    ]
                },
            }

    fake_service = SimpleNamespace(
        repo_root=repo_root,
        action_registry=FakeActionRegistry(),
        artifact_store=artifact_store,
        tool_router=FakeToolRouter(),
    )

    monkeypatch.setattr(
        CockpitService, "get_instance", classmethod(lambda cls: fake_service)
    )

    app = FastAPI()
    app.include_router(router, prefix="/api/cockpit")
    client = TestClient(app)

    response = client.post(
        "/api/cockpit/action/execute",
        json={
            "action_id": "show_candlestick",
            "args": {
                "ticker": "BHP",
                "mode_flag": "-f",
                "mode_value": str(csv_path),
                "timeframe": "1d",
            },
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["action_id"] == "show_candlestick"
    assert payload["result"] == "Candlestick chart rendered for BHP (1d)."
    assert payload["chart"]["title"] == "BHP candlestick chart"
    assert "BHP Candlestick Dashboard" in payload["chart"]["html"]
    assert artifact_store.writes
    assert artifact_store.writes[0][0].startswith("reports/cockpit/BHP_")


def test_cockpit_execute_action_uses_backend_data_when_chart_csv_missing(
    tmp_path,
    monkeypatch,
) -> None:
    repo_root = tmp_path

    class FakeArtifactStore:
        def write_text(self, rel_path: str, content: str) -> str:
            return str(repo_root / rel_path)

    class FakeActionRegistry:
        @staticmethod
        def preview(action_id: str, args: dict[str, object]) -> SimpleNamespace:
            return SimpleNamespace(timeout_seconds=60, command=["noop"], args=args)

    class FakeToolRouter:
        @staticmethod
        def get_price_context_for_window(
            ticker: str,
            *,
            range_: str = "1y",
            interval: str = "1d",
            max_history_rows: int = 260,
        ) -> dict[str, object]:
            return {
                "price_state": {
                    "current": {"close": 42.0},
                    "metrics": {"sample_count": 1},
                },
                "price": {
                    "recent_history": [
                        {
                            "timestamp": "2026-04-08T00:00:00+00:00",
                            "open": 41.5,
                            "high": 42.3,
                            "low": 41.1,
                            "close": 42.0,
                            "volume": 999,
                        }
                    ]
                },
            }

    fake_service = SimpleNamespace(
        repo_root=repo_root,
        action_registry=FakeActionRegistry(),
        artifact_store=FakeArtifactStore(),
        tool_router=FakeToolRouter(),
    )

    monkeypatch.setattr(
        CockpitService, "get_instance", classmethod(lambda cls: fake_service)
    )

    app = FastAPI()
    app.include_router(router, prefix="/api/cockpit")
    client = TestClient(app)

    response = client.post(
        "/api/cockpit/action/execute",
        json={
            "action_id": "show_candlestick",
            "args": {
                "ticker": "BHP",
                "mode_flag": "-f",
                "mode_value": "reports/candles/BHP_candles_1d.csv",
                "timeframe": "1d",
            },
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["result"] == "Candlestick chart rendered for BHP (1d)."
    assert "BHP Candlestick Dashboard" in payload["chart"]["html"]


def test_cockpit_execute_action_can_queue_long_running_action(
    tmp_path,
    monkeypatch,
) -> None:
    class FakeActionRegistry:
        @staticmethod
        def preview(action_id: str, args: dict[str, object]) -> SimpleNamespace:
            return SimpleNamespace(
                timeout_seconds=5400,
                command=["python", "scripts/fetch_daily_news.py"],
                args=args,
            )

    fake_service = SimpleNamespace(
        repo_root=tmp_path,
        action_registry=FakeActionRegistry(),
        state_store=SimpleNamespace(),
        artifact_store=SimpleNamespace(logs_dir=tmp_path / "logs"),
    )

    monkeypatch.setattr(
        CockpitService, "get_instance", classmethod(lambda cls: fake_service)
    )
    monkeypatch.setattr(
        "app.routes.cockpit_api._launch_action_job",
        lambda **kwargs: {
            "ok": True,
            "action_id": kwargs["action_id"],
            "result": "Queued action daily_news_ingest",
            "exit_code": 0,
            "job_id": "job-123",
            "status": "queued",
            "queued": True,
        },
    )

    app = FastAPI()
    app.include_router(router, prefix="/api/cockpit")
    client = TestClient(app)

    response = client.post(
        "/api/cockpit/action/execute",
        json={
            "action_id": "daily_news_ingest",
            "args": {"tickers": "BHP"},
            "wait": False,
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["queued"] is True
    assert payload["job_id"] == "job-123"
    assert payload["status"] == "queued"


def test_cockpit_action_job_status_reads_persisted_job(
    tmp_path,
    monkeypatch,
) -> None:
    stdout_path = tmp_path / "job.out.log"
    stdout_path.write_text("completed successfully", encoding="utf-8")

    class FakeStateStore:
        @staticmethod
        def get_job(job_id: str):
            if job_id != "job-123":
                return None
            return {
                "job_id": "job-123",
                "action_id": "daily_news_ingest",
                "args": {"tickers": "BHP"},
                "started_at": "2026-04-09T10:00:00+00:00",
                "ended_at": "2026-04-09T10:01:00+00:00",
                "status": "success",
                "exit_code": 0,
                "stdout_path": str(stdout_path),
                "stderr_path": None,
                "artifacts": [],
            }

    fake_service = SimpleNamespace(state_store=FakeStateStore())
    monkeypatch.setattr(
        CockpitService, "get_instance", classmethod(lambda cls: fake_service)
    )

    app = FastAPI()
    app.include_router(router, prefix="/api/cockpit")
    client = TestClient(app)

    response = client.get("/api/cockpit/action/jobs/job-123")

    assert response.status_code == 200
    payload = response.json()
    assert payload["job_id"] == "job-123"
    assert payload["status"] == "success"
    assert payload["result"] == "completed successfully"
