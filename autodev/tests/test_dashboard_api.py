from __future__ import annotations

from contextlib import asynccontextmanager
import importlib
import json
from pathlib import Path
import subprocess
from types import SimpleNamespace

import pytest

httpx = pytest.importorskip("httpx")
create_app = importlib.import_module("autodev.dashboard.server").create_app
pytestmark = pytest.mark.asyncio


def _mk_run(repo: Path, run_id: str, task_title: str, gate_pass: bool = True) -> Path:
    run_dir = repo / "autodev" / "reports" / "runs" / run_id
    logs = run_dir / "logs"
    logs.mkdir(parents=True, exist_ok=True)

    (run_dir / "report.md").write_text(
        "\n".join(
            [
                "# Autodev Run Report",
                "- task id: `T1`",
                f"- task title: {task_title}",
                "",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    (run_dir / "commands.json").write_text(
        json.dumps(
            {
                "gate_commands": [
                    {"name": "ruff", "passed": gate_pass},
                    {"name": "pytest", "passed": gate_pass},
                ],
                "worker": [{"worker_name": "local_patch"}],
            }
        )
        + "\n",
        encoding="utf-8",
    )
    (run_dir / "worker.json").write_text(
        json.dumps({"selected_worker": "local_patch", "result": {"status": "changed"}}) + "\n",
        encoding="utf-8",
    )
    (logs / "gate_ruff.json").write_text(
        json.dumps({"duration_seconds": 0.4, "started_at": "2026-03-05T08:00:00+00:00"}) + "\n",
        encoding="utf-8",
    )
    (logs / "gate_pytest.json").write_text(
        json.dumps({"duration_seconds": 1.6, "started_at": "2026-03-05T08:00:01+00:00"}) + "\n",
        encoding="utf-8",
    )
    return run_dir


def _mk_repo(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    (repo / "autodev" / "reports" / "runs").mkdir(parents=True, exist_ok=True)
    (repo / "autodev" / "dashboard" / "static").mkdir(parents=True, exist_ok=True)
    (repo / "autodev" / "dashboard" / "static" / "index.html").write_text(
        "<html><body><h1>AutoDev Dashboard</h1></body></html>",
        encoding="utf-8",
    )
    (repo / "autodev_work").mkdir(parents=True, exist_ok=True)

    subprocess.run(["git", "init"], cwd=repo, check=True, capture_output=True, text=True)
    subprocess.run(["git", "add", "-A"], cwd=repo, check=True, capture_output=True, text=True)
    subprocess.run(
        [
            "git",
            "-c",
            "user.name=autodev-test",
            "-c",
            "user.email=autodev-test@example.com",
            "commit",
            "-m",
            "init",
        ],
        cwd=repo,
        check=True,
        capture_output=True,
        text=True,
    )
    return repo


@asynccontextmanager
async def _client(repo: Path):
    app = create_app(repo)
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        yield client


async def test_status_endpoint_parses_control_output(tmp_path: Path, monkeypatch) -> None:
    repo = _mk_repo(tmp_path)
    run_id = "20260305T000000Z"
    _mk_run(repo, run_id, "Status task", gate_pass=True)

    fake_stdout = "\n".join(
        [
            "daemon_running=True",
            "pid=123",
            f"last_run_id={run_id}",
            "last_result=pass",
            "task_id=T1",
            "regression=pass",
            "debate_veto=none",
            "failure_reason=unknown",
        ]
    )

    monkeypatch.setattr(
        "autodev.dashboard.server.subprocess.run",
        lambda *args, **kwargs: SimpleNamespace(returncode=0, stdout=fake_stdout, stderr=""),
    )

    async with _client(repo) as client:
        res = await client.get("/status")
        assert res.status_code == 200
        payload = res.json()
        assert payload["daemon_running"] is True
        assert payload["pid"] == 123
        assert payload["last_run_id"] == run_id
        assert payload["latest_task_title"] == "Status task"


async def test_runs_endpoint_returns_last_20_and_fields(tmp_path: Path) -> None:
    repo = _mk_repo(tmp_path)
    for idx in range(25):
        run_id = f"20260305T{idx:06d}Z"
        _mk_run(repo, run_id, f"Task {idx}", gate_pass=(idx % 2 == 0))

    async with _client(repo) as client:
        res = await client.get("/runs?limit=20")
        assert res.status_code == 200
        runs = res.json()["runs"]
        assert len(runs) == 20
        assert runs[0]["run_id"] > runs[-1]["run_id"]
        assert set(["run_id", "task", "gates", "worker", "duration_seconds", "started_at"]).issubset(runs[0])


async def test_run_endpoint_returns_artifacts(tmp_path: Path) -> None:
    repo = _mk_repo(tmp_path)
    run_id = "20260305T000111Z"
    _mk_run(repo, run_id, "Artifact task")

    async with _client(repo) as client:
        res = await client.get(f"/run/{run_id}")
        assert res.status_code == 200
        payload = res.json()
        assert payload["run_id"] == run_id
        assert "Artifact task" in payload["report_markdown"]
        assert isinstance(payload["commands"], dict)
        assert isinstance(payload["worker"], dict)
        assert "gate_ruff.json" in payload["gate_logs"]

        bad_format = await client.get("/run/not-a-run-id")
        assert bad_format.status_code == 400

        missing = await client.get("/run/20260305T999999Z")
        assert missing.status_code == 404


async def test_experiments_endpoint_handles_missing_and_present_dir(tmp_path: Path) -> None:
    repo = _mk_repo(tmp_path)
    async with _client(repo) as client:
        empty_res = await client.get("/experiments")
        assert empty_res.status_code == 200
        assert empty_res.json()["experiments"] == []

        exp_dir = repo / "autodev" / "reports" / "experiments"
        exp_dir.mkdir(parents=True, exist_ok=True)
        (exp_dir / "experiment_20260305T000000Z.json").write_text(
            json.dumps(
                {
                    "task": "optimize parser",
                    "variants": [
                        {"patch_id": "variant_1", "benchmark_score": -1.2},
                        {"patch_id": "variant_2", "benchmark_score": -0.8},
                    ],
                    "winner": "variant_2",
                    "benchmark_score": -0.8,
                    "generated_at": "2026-03-05T00:00:00+00:00",
                }
            )
            + "\n",
            encoding="utf-8",
        )

        res = await client.get("/experiments")
        assert res.status_code == 200
        experiments = res.json()["experiments"]
        assert len(experiments) == 1
        assert experiments[0]["task"] == "optimize parser"
        assert experiments[0]["winner"] == "variant_2"
        assert experiments[0]["variants"] == 2


async def test_diff_endpoint_prefers_run_patch_then_fallback(tmp_path: Path) -> None:
    repo = _mk_repo(tmp_path)
    run_id = "20260305T000222Z"
    run_dir = _mk_run(repo, run_id, "Diff task")

    run_patch = run_dir / "pr_patch.diff"
    global_patch = repo / "autodev_work" / "llm_patch.diff"
    run_patch.write_text("diff --git a/a.py b/a.py\n", encoding="utf-8")
    global_patch.write_text("diff --git a/g.py b/g.py\n", encoding="utf-8")

    async with _client(repo) as client:
        res_run = await client.get(f"/diff/{run_id}")
        assert res_run.status_code == 200
        payload_run = res_run.json()
        assert payload_run["source"].endswith(f"autodev/reports/runs/{run_id}/pr_patch.diff")
        assert "a/a.py" in payload_run["diff"]

        run_patch.unlink()
        res_global = await client.get(f"/diff/{run_id}")
        assert res_global.status_code == 200
        payload_global = res_global.json()
        assert payload_global["source"] == "autodev_work/llm_patch.diff"

        global_patch.unlink()
        res_missing = await client.get(f"/diff/{run_id}")
        assert res_missing.status_code == 404


async def test_root_serves_dashboard_html(tmp_path: Path) -> None:
    repo = _mk_repo(tmp_path)
    async with _client(repo) as client:
        res = await client.get("/")
        assert res.status_code == 200
        assert "AutoDev Dashboard" in res.text
