from __future__ import annotations

from pathlib import Path
import subprocess

from autodev.runtime.worker_interface import WorkerRequest
from autodev.runtime.workers import llm_patch_worker


def _run(cmd: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, cwd=cwd, text=True, capture_output=True, check=False)


def _must_run(cmd: list[str], cwd: Path) -> None:
    proc = _run(cmd, cwd)
    if proc.returncode != 0:
        raise RuntimeError(f"command failed: {' '.join(cmd)}\n{proc.stderr}")


def _init_repo(repo: Path) -> None:
    _must_run(["git", "init"], repo)
    _must_run(["git", "add", "-A"], repo)
    _must_run(
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
        repo,
    )


def _repo_with_sample(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    (repo / "autodev/work").mkdir(parents=True, exist_ok=True)
    (repo / "autodev/work/sample.py").write_text("value = 1\n", encoding="utf-8")
    _init_repo(repo)
    return repo


def _request(repo: Path) -> WorkerRequest:
    return WorkerRequest(
        task_id="T1",
        task_slug="llm-test",
        task_description="Update target file",
        allowed_paths=("autodev/",),
        repo_root=repo,
        branch_name="agent/2026-03-05/llm-test",
        max_changed_lines_per_attempt=300,
        max_changed_files_per_attempt=20,
        allow_network=False,
        llm_provider_balanced="ollama",
        llm_provider_heavy="ollama",
        protected_paths=(".github/",),
        run_dir=repo / "autodev/reports/runs/r1",
        attempt_index=1,
    )


def _selection(request: WorkerRequest) -> llm_patch_worker.ModelSelection:
    return llm_patch_worker._select_model(request.task_description, request)


def test_get_repo_tree_lists_tracked_files(tmp_path: Path) -> None:
    repo = _repo_with_sample(tmp_path)
    tree = llm_patch_worker.get_repo_tree(repo)
    assert "autodev/work/sample.py" in tree.splitlines()


def test_generate_file_edits_accepts_tracked_file_outside_prompt_tree(tmp_path: Path, monkeypatch) -> None:
    repo = tmp_path / "repo"
    for idx in range(120):
        path = repo / "autodev" / "work" / f"file_{idx:03d}.py"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(f"value = {idx}\n", encoding="utf-8")
    target = repo / "autodev" / "work" / "zz_target.py"
    target.write_text("value = 1\n", encoding="utf-8")
    _init_repo(repo)

    request = _request(repo)
    selection = _selection(request)
    target_rel = "autodev/work/zz_target.py"

    assert target_rel not in llm_patch_worker.get_repo_tree(repo).splitlines()
    monkeypatch.setattr(llm_patch_worker, "search_repository", lambda query, top_k, repo_path: [target_rel])
    monkeypatch.setattr(llm_patch_worker, "load_context", lambda files, repo_path: "")
    monkeypatch.setattr(
        llm_patch_worker,
        "run_ollama",
        lambda *args, **kwargs: f"FILE: {target_rel}\nvalue = 2\n",
    )

    edits = llm_patch_worker.generate_file_edits(
        "update target value",
        repo_path=repo,
        allow_network=False,
        selection=selection,
        request=request,
    )
    assert edits == {target_rel: "value = 2\n"}


def test_extract_file_blocks() -> None:
    raw = """
Some text ignored.
FILE: autodev/work/sample.py
value = 2

FILE: autodev/work/other.py
def x():
    return 1
""".strip()
    blocks = llm_patch_worker.extract_file_blocks(raw)
    assert "autodev/work/sample.py" in blocks
    assert blocks["autodev/work/sample.py"] == "value = 2\n"
    assert "autodev/work/other.py" in blocks
    assert "def x():" in blocks["autodev/work/other.py"]


def test_generate_file_edits_uses_repair_and_retries(tmp_path: Path, monkeypatch) -> None:
    repo = _repo_with_sample(tmp_path)
    request = _request(repo)
    selection = _selection(request)
    responses = iter(
        [
            "Not in FILE format.",
            """
FILE: autodev/work/sample.py
value = 3
""".strip(),
        ]
    )
    monkeypatch.setattr(llm_patch_worker, "run_ollama", lambda *args, **kwargs: next(responses))
    edits = llm_patch_worker.generate_file_edits(
        "bump sample value",
        repo_path=repo,
        allow_network=False,
        selection=selection,
        request=request,
    )
    assert edits == {"autodev/work/sample.py": "value = 3\n"}


def test_generate_file_edits_repairs_invalid_paths_with_repo_tree(tmp_path: Path, monkeypatch) -> None:
    repo = _repo_with_sample(tmp_path)
    request = _request(repo)
    selection = _selection(request)
    responses = iter(
        [
            "FILE: path/to/file\nvalue = 5\n",
            "FILE: path/to/file\nvalue = 5\n",
            "FILE: autodev/work/sample.py\nvalue = 5\n",
        ]
    )
    monkeypatch.setattr(llm_patch_worker, "run_ollama", lambda *args, **kwargs: next(responses))
    edits = llm_patch_worker.generate_file_edits(
        "set sample value",
        repo_path=repo,
        allow_network=False,
        selection=selection,
        request=request,
    )
    assert edits == {"autodev/work/sample.py": "value = 5\n"}


def test_generate_file_edits_fails_after_attempts(tmp_path: Path, monkeypatch) -> None:
    repo = _repo_with_sample(tmp_path)
    request = _request(repo)
    selection = _selection(request)
    monkeypatch.setattr(llm_patch_worker, "run_ollama", lambda *args, **kwargs: "still invalid")
    try:
        llm_patch_worker.generate_file_edits(
            "task",
            repo_path=repo,
            allow_network=False,
            selection=selection,
            request=request,
        )
        assert False, "Expected generate_file_edits to fail"
    except RuntimeError as exc:
        assert "Failed to generate file edits" in str(exc)


def test_llm_patch_worker_writes_files_and_generates_patch(tmp_path: Path, monkeypatch) -> None:
    repo = _repo_with_sample(tmp_path)
    request = _request(repo)

    monkeypatch.setattr(
        llm_patch_worker,
        "generate_file_edits",
        lambda *args, **kwargs: {"autodev/work/sample.py": "value = 2\n"},
    )

    result = llm_patch_worker.run_llm_patch_worker(request)
    assert result.status == "changed"
    assert result.summary == "Generated patch via LLM worker using qwen2.5-coder:7b (balanced)"
    assert "autodev/work/sample.py" in result.files_changed
    assert (repo / "autodev/work/sample.py").read_text(encoding="utf-8") == "value = 2\n"
    patch_path = repo / "autodev_work/llm_patch.diff"
    assert patch_path.exists()
    patch = patch_path.read_text(encoding="utf-8")
    assert patch.startswith("diff --git")
    assert "autodev/work/sample.py" in patch


def test_llm_patch_worker_rejects_out_of_scope_paths(tmp_path: Path, monkeypatch) -> None:
    repo = _repo_with_sample(tmp_path)

    monkeypatch.setattr(
        llm_patch_worker,
        "generate_file_edits",
        lambda *args, **kwargs: {"scripts/bad.py": "x = 1\n"},
    )

    result = llm_patch_worker.run_llm_patch_worker(_request(repo))
    assert result.status == "error"
    assert result.block_reason is not None
    assert result.block_reason.get("reason") == "llm_patch_failed"
    assert "outside allowed scope" in result.summary
