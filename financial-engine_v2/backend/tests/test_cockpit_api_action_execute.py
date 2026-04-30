from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace

from fastapi import FastAPI
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import app.routes.cockpit_api as cockpit_api_module
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


def test_cockpit_execute_action_show_candlestick_fails_when_chart_html_is_empty(
    tmp_path,
    monkeypatch,
) -> None:
    class FakeArtifactStore:
        def write_text(self, rel_path: str, content: str) -> str:
            return str(tmp_path / rel_path)

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
                "price_state": {"current": {"close": 42.0}},
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
        repo_root=tmp_path,
        action_registry=FakeActionRegistry(),
        artifact_store=FakeArtifactStore(),
        tool_router=FakeToolRouter(),
    )

    monkeypatch.setattr(
        CockpitService, "get_instance", classmethod(lambda cls: fake_service)
    )
    monkeypatch.setattr(
        "cockpit.core.plotly_html.build_candlestick_dashboard_html",
        lambda payload: "   ",
    )

    app = FastAPI()
    app.include_router(router, prefix="/api/cockpit")
    client = TestClient(app)

    response = client.post(
        "/api/cockpit/action/execute",
        json={"action_id": "show_candlestick", "args": {"ticker": "BHP", "timeframe": "1d"}},
    )

    assert response.status_code == 502
    assert "empty chart payload" in response.json()["detail"]


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


def test_cockpit_execute_action_handles_strategy_thesis_actions(
    tmp_path,
    monkeypatch,
) -> None:
    fake_service = SimpleNamespace(repo_root=tmp_path)
    monkeypatch.setattr(
        CockpitService, "get_instance", classmethod(lambda cls: fake_service)
    )
    monkeypatch.setattr(
        "app.services.user_thesis_memory.UserThesisMemoryStore.create_proposal",
        lambda self, **kwargs: {"proposal_id": "thp_123", **kwargs, "status": "pending"},
    )
    monkeypatch.setattr(
        "app.services.user_thesis_memory.UserThesisMemoryStore.confirm_proposal",
        lambda self, proposal_id, note=None: {  # noqa: ARG005
            "proposal_id": proposal_id,
            "status": "confirmed",
        },
    )
    monkeypatch.setattr(
        "app.services.user_thesis_memory.UserThesisMemoryStore.apply_confirmed_proposal",
        lambda self, proposal_id: {  # noqa: ARG005
            "proposal": {"proposal_id": proposal_id, "status": "applied"},
            "entry": {"entry_id": 7, "statement": "Copper growth supports rerating."},
        },
    )

    app = FastAPI()
    app.include_router(router, prefix="/api/cockpit")
    client = TestClient(app)

    response = client.post(
        "/api/cockpit/action/execute",
        json={
            "action_id": "create_thesis",
            "args": {
                "ticker": "BHP",
                "thesis": "Copper growth supports rerating.",
                "signal": "BUY",
            },
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["action_id"] == "create_thesis"
    assert payload["status"] == "success"
    assert "proposal_id=thp_123" in payload["result"]


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


def test_launch_action_job_registers_ops_tracker_events(
    tmp_path,
    monkeypatch,
) -> None:
    class FakeStateStore:
        def __init__(self) -> None:
            self.rows: list[dict[str, object]] = []

        def add_job(self, payload: dict[str, object]) -> None:
            self.rows.append(payload)

        def update_job_progress(
            self, job_id: str, stage: str, pct: float | None = None
        ) -> None:
            self.rows.append(
                {"job_id": job_id, "progress_stage": stage, "progress_pct": pct}
            )

        def update_job_status(
            self,
            job_id: str,
            *,
            status: str,
            exit_code: int | None,
            ended_at: str,
        ) -> None:
            self.rows.append(
                {
                    "job_id": job_id,
                    "status": status,
                    "exit_code": exit_code,
                    "ended_at": ended_at,
                }
            )

    class FakeTracker:
        def __init__(self) -> None:
            self.calls: list[tuple[str, tuple[object, ...], dict[str, object]]] = []

        def create_job(self, *args, **kwargs):
            self.calls.append(("create_job", args, kwargs))

        def add_artifact(self, *args, **kwargs):
            self.calls.append(("add_artifact", args, kwargs))

        def start_job(self, *args, **kwargs):
            self.calls.append(("start_job", args, kwargs))

        def change_phase(self, *args, **kwargs):
            self.calls.append(("change_phase", args, kwargs))

        def record_progress(self, *args, **kwargs):
            self.calls.append(("record_progress", args, kwargs))

        def complete_job(self, *args, **kwargs):
            self.calls.append(("complete_job", args, kwargs))

        def fail_job(self, *args, **kwargs):
            self.calls.append(("fail_job", args, kwargs))

        def cancel_job(self, *args, **kwargs):
            self.calls.append(("cancel_job", args, kwargs))

    class ImmediateThread:
        def __init__(self, *, target, daemon=None, name=None):
            self._target = target

        def start(self) -> None:
            self._target()

    fake_tracker = FakeTracker()
    fake_service = SimpleNamespace(
        repo_root=tmp_path,
        action_registry=SimpleNamespace(
            get=lambda action_id: SimpleNamespace(label="Daily News Ingest")
        ),
        state_store=FakeStateStore(),
        artifact_store=SimpleNamespace(logs_dir=tmp_path / "logs"),
    )

    monkeypatch.setattr("app.services.job_tracker.get_tracker", lambda: fake_tracker)
    monkeypatch.setattr(
        cockpit_api_module,
        "_run_action_subprocess_streaming",
        lambda **kwargs: (0, "[progress] ticker_index=1/2\n", ""),
    )
    monkeypatch.setattr(cockpit_api_module.threading, "Thread", ImmediateThread)

    queued = cockpit_api_module._launch_action_job(
        service=fake_service,
        action_id="daily_news_ingest",
        args={"tickers": "BHP"},
        normalized_command=["python", "scripts/fetch_daily_news.py"],
        action_env={},
        timeout_seconds=120,
    )

    assert queued["queued"] is True
    assert queued["job_id"]
    create_calls = [call for call in fake_tracker.calls if call[0] == "create_job"]
    assert create_calls
    assert create_calls[0][2]["job_id"] == queued["job_id"]
    assert create_calls[0][2]["job_type"] == "daily_news_ingest"
    assert any(call[0] == "start_job" for call in fake_tracker.calls)
    assert any(call[0] == "complete_job" for call in fake_tracker.calls)
    assert sum(1 for call in fake_tracker.calls if call[0] == "add_artifact") == 2


def test_cockpit_action_job_stop_terminates_registered_process(
    monkeypatch,
) -> None:
    class DummyProc:
        def __init__(self) -> None:
            self.terminated = False
            self.wait_called = False
            self.killed = False

        def terminate(self) -> None:
            self.terminated = True

        def wait(self, timeout: int | float | None = None) -> None:
            self.wait_called = True

        def kill(self) -> None:
            self.killed = True

    dummy_proc = DummyProc()
    cockpit_api_module._ACTION_JOB_PROCS["job-123"] = dummy_proc
    fake_service = SimpleNamespace(
        state_store=SimpleNamespace(get_job=lambda job_id: {"job_id": job_id, "status": "running"})
    )
    monkeypatch.setattr(
        CockpitService, "get_instance", classmethod(lambda cls: fake_service)
    )

    app = FastAPI()
    app.include_router(router, prefix="/api/cockpit")
    client = TestClient(app)

    try:
        response = client.post("/api/cockpit/action/jobs/job-123/stop")
    finally:
        cockpit_api_module._ACTION_JOB_PROCS.pop("job-123", None)
        cockpit_api_module._ACTION_JOB_CANCEL_REQUESTS.discard("job-123")

    assert response.status_code == 200
    payload = response.json()
    assert payload["job_id"] == "job-123"
    assert payload["status"] == "cancelling"
    assert dummy_proc.terminated is True
    assert dummy_proc.wait_called is True
    assert dummy_proc.killed is False


def test_cockpit_action_job_stop_kills_process_when_wait_times_out(
    monkeypatch,
) -> None:
    class DummyProc:
        def __init__(self) -> None:
            self.terminated = False
            self.wait_called = False
            self.killed = False

        def terminate(self) -> None:
            self.terminated = True

        def wait(self, timeout: int | float | None = None) -> None:
            self.wait_called = True
            raise TimeoutError("still running")

        def kill(self) -> None:
            self.killed = True

    dummy_proc = DummyProc()
    cockpit_api_module._ACTION_JOB_PROCS["job-124"] = dummy_proc
    fake_service = SimpleNamespace(
        state_store=SimpleNamespace(get_job=lambda job_id: {"job_id": job_id, "status": "running"})
    )
    monkeypatch.setattr(
        CockpitService, "get_instance", classmethod(lambda cls: fake_service)
    )

    app = FastAPI()
    app.include_router(router, prefix="/api/cockpit")
    client = TestClient(app)

    try:
        response = client.post("/api/cockpit/action/jobs/job-124/stop")
    finally:
        cockpit_api_module._ACTION_JOB_PROCS.pop("job-124", None)
        cockpit_api_module._ACTION_JOB_CANCEL_REQUESTS.discard("job-124")

    assert response.status_code == 200
    payload = response.json()
    assert payload["job_id"] == "job-124"
    assert payload["status"] == "cancelling"
    assert dummy_proc.terminated is True
    assert dummy_proc.wait_called is True
    assert dummy_proc.killed is True


def test_cockpit_action_job_stop_requests_pipeline_cancellation(
    monkeypatch,
) -> None:
    requested: list[tuple[str, str]] = []

    class FakeTracker:
        def __init__(self) -> None:
            self.store = SimpleNamespace(
                get_job_run=lambda job_id: {
                    "job_id": job_id,
                    "job_type": "extraction",
                    "job_family": "pipeline",
                    "status": "running",
                    "metadata": {"supports_cancellation": True},
                }
            )

        def request_cancellation(self, job_id: str, reason: str = "") -> bool:
            requested.append((job_id, reason))
            return True

    fake_service = SimpleNamespace(
        state_store=SimpleNamespace(get_job=lambda job_id: None)
    )
    monkeypatch.setattr(
        CockpitService, "get_instance", classmethod(lambda cls: fake_service)
    )
    monkeypatch.setattr(cockpit_api_module, "_get_backend_job_tracker", lambda: FakeTracker())

    app = FastAPI()
    app.include_router(router, prefix="/api/cockpit")
    client = TestClient(app)

    response = client.post("/api/cockpit/action/jobs/extract-1/stop")

    assert response.status_code == 200
    payload = response.json()
    assert payload["job_id"] == "extract-1"
    assert payload["status"] == "cancelling"
    assert requested == [
        ("extract-1", "Cancellation requested from Cockpit.")
    ]
