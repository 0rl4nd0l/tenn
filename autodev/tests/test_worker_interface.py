from __future__ import annotations

from pathlib import Path

from autodev.runtime import worker_interface
from autodev.runtime.worker_interface import WorkerRequest, WorkerResult


def _request(tmp_path: Path) -> WorkerRequest:
    return WorkerRequest(
        task_id="T1",
        task_slug="worker-interface",
        task_description="desc",
        allowed_paths=("autodev/",),
        repo_root=tmp_path,
        branch_name="agent/2026-03-05/worker-interface",
        max_changed_lines_per_attempt=300,
        max_changed_files_per_attempt=20,
        allow_network=False,
        protected_paths=(),
        run_dir=tmp_path / "autodev/reports/runs/r1",
        attempt_index=1,
    )


def test_list_workers_includes_llm_patch() -> None:
    workers = worker_interface.list_workers()
    assert "local_patch" in workers
    assert "llm_patch" in workers


def test_run_worker_dispatches_llm_patch(tmp_path: Path, monkeypatch) -> None:
    expected = WorkerResult(
        status="changed",
        summary="Generated patch via LLM worker",
        files_changed=["autodev/x.py"],
        lines_changed=1,
        commit_created=False,
        block_reason=None,
        artifacts=["autodev_work/llm_patch.diff"],
    )

    from autodev.runtime.workers import llm_patch_worker

    monkeypatch.setattr(llm_patch_worker, "run_llm_patch_worker", lambda request: expected)
    result = worker_interface.run_worker(_request(tmp_path), "llm_patch")
    assert result == expected
