from __future__ import annotations

import json
from pathlib import Path
import subprocess

from autodev.runtime.repo_rag import index_repository, load_context, search_repository
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


def _repo_with_content(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    (repo / "autodev/runtime").mkdir(parents=True, exist_ok=True)
    (repo / "autodev/work").mkdir(parents=True, exist_ok=True)
    (repo / "docs").mkdir(parents=True, exist_ok=True)
    (repo / "autodev/runtime/sample.py").write_text(
        "\n".join(
            [
                '"""Sample module doc."""',
                "import os",
                "",
                "class SampleClass:",
                '    """Sample class doc."""',
                "    pass",
                "",
                "def sample_function(value: int) -> int:",
                '    """Compute a simple value."""',
                "    return value + 1",
                "",
            ]
        ),
        encoding="utf-8",
    )
    (repo / "autodev/work/sample.py").write_text("value = 1\n", encoding="utf-8")
    (repo / "docs/notes.md").write_text("# Notes\n\nTODO: improve parser\n", encoding="utf-8")
    (repo / "autodev/config.yaml").write_text("name: sample\n", encoding="utf-8")
    (repo / "autodev/meta.json").write_text('{"enabled": true}\n', encoding="utf-8")
    _init_repo(repo)
    return repo


def _request(repo: Path) -> WorkerRequest:
    return WorkerRequest(
        task_id="T1",
        task_slug="repo-rag",
        task_description="Update sample",
        allowed_paths=("autodev/",),
        repo_root=repo,
        branch_name="agent/2026-03-09/repo-rag",
        max_changed_lines_per_attempt=300,
        max_changed_files_per_attempt=20,
        allow_network=False,
        llm_provider_balanced="ollama",
        llm_provider_heavy="ollama",
        protected_paths=(".github/",),
        run_dir=repo / "autodev/reports/runs/r1",
        attempt_index=1,
    )


def test_index_repository_builds_cache(tmp_path: Path) -> None:
    repo = _repo_with_content(tmp_path)
    payload = index_repository(repo)
    index_path = repo / "autodev" / "cache" / "repo_index.json"
    assert index_path.exists()
    assert int(payload["indexed_file_count"]) >= 4
    loaded = json.loads(index_path.read_text(encoding="utf-8"))
    files = loaded.get("files", [])
    sample = next(item for item in files if item["file_path"] == "autodev/runtime/sample.py")
    assert "sample_function" in sample["functions"]
    assert "SampleClass" in sample["classes"]
    assert "os" in sample["imports"]
    assert sample["docstrings"]


def test_search_repository_returns_relevant_files(tmp_path: Path) -> None:
    repo = _repo_with_content(tmp_path)
    index_repository(repo)
    results = search_repository("sample_function parser", top_k=3, repo_path=repo)
    assert results
    assert results[0] == "autodev/runtime/sample.py"


def test_load_context_limits_lines_and_skips_untracked(tmp_path: Path) -> None:
    repo = _repo_with_content(tmp_path)
    long_file = repo / "autodev/runtime/long_file.py"
    long_file.write_text("\n".join(f"line_{i}" for i in range(260)) + "\n", encoding="utf-8")
    _must_run(["git", "add", "autodev/runtime/long_file.py"], repo)
    _must_run(
        [
            "git",
            "-c",
            "user.name=autodev-test",
            "-c",
            "user.email=autodev-test@example.com",
            "commit",
            "-m",
            "add long file",
        ],
        repo,
    )
    (repo / "autodev/runtime/untracked.py").write_text("should_not_load = True\n", encoding="utf-8")

    context = load_context(
        ["autodev/runtime/long_file.py", "autodev/runtime/untracked.py"],
        repo_path=repo,
    )
    assert "FILE: autodev/runtime/long_file.py" in context
    assert "line_199" in context
    assert "line_220" not in context
    assert "untracked.py" not in context


def test_llm_patch_worker_uses_repo_rag_context(tmp_path: Path, monkeypatch) -> None:
    repo = _repo_with_content(tmp_path)
    request = _request(repo)
    selection = llm_patch_worker._select_model("update sample", request)
    captured: dict[str, str] = {}

    monkeypatch.setattr(
        llm_patch_worker,
        "search_repository",
        lambda query, top_k, repo_path: ["autodev/work/sample.py"],
    )
    monkeypatch.setattr(
        llm_patch_worker,
        "load_context",
        lambda files, repo_path: "FILE: autodev/work/sample.py\nvalue = 1\n",
    )

    def fake_run_ollama(prompt: str, *args, **kwargs) -> str:
        captured["prompt"] = prompt
        return "FILE: autodev/work/sample.py\nvalue = 2\n"

    monkeypatch.setattr(llm_patch_worker, "run_ollama", fake_run_ollama)
    edits = llm_patch_worker.generate_file_edits(
        "update sample",
        repo_path=repo,
        allow_network=False,
        selection=selection,
        request=request,
    )
    assert edits["autodev/work/sample.py"] == "value = 2\n"

    prompt = captured["prompt"]
    assert "TASK\nupdate sample" in prompt
    assert "RELEVANT FILES\nautodev/work/sample.py" in prompt
    assert "CODE CONTEXT\nFILE: autodev/work/sample.py" in prompt
    assert "INSTRUCTIONS\nModify only files that appear in the repository." in prompt
