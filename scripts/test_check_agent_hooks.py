from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

from scripts import check_agent_hooks


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "check_agent_hooks.py"


def run_git(repo: Path, *args: str) -> None:
    subprocess.run(
        ["git", *args],
        cwd=repo,
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )


def git_repo(tmp_path: Path) -> Path:
    tmp_path.mkdir(parents=True, exist_ok=True)
    run_git(tmp_path, "init")
    return tmp_path


def test_build_report_passes_for_executable_hooks_with_fingerprints(tmp_path: Path) -> None:
    repo = git_repo(tmp_path)
    hooks = repo / ".git" / "hooks"
    pre_commit = hooks / "pre-commit"
    pre_push = hooks / "pre-push"
    pre_commit.write_text("#!/usr/bin/env bash\npython3 scripts/agent_job_hook.py\n", encoding="utf-8")
    pre_push.write_text("#!/usr/bin/env bash\npython3 -m pytest scripts\n", encoding="utf-8")
    pre_commit.chmod(0o755)
    pre_push.chmod(0o755)

    report = check_agent_hooks.build_report(
        repo_root=repo,
        expected_fingerprints={
            "pre-commit": "agent_job_hook.py",
            "pre-push": "pytest",
        },
    )

    assert report.ok
    assert report.issues == []
    assert report.effective_hooks_dir_exists
    assert report.effective_hooks_dir_is_dir
    assert [hook.name for hook in report.hooks] == ["pre-commit", "pre-push"]
    assert all(hook.executable for hook in report.hooks)


def test_build_report_detects_missing_and_non_executable_hooks(tmp_path: Path) -> None:
    repo = git_repo(tmp_path)
    pre_commit = repo / ".git" / "hooks" / "pre-commit"
    pre_commit.write_text("#!/usr/bin/env bash\ntrue\n", encoding="utf-8")
    pre_commit.chmod(0o644)

    report = check_agent_hooks.build_report(repo_root=repo)

    assert not report.ok
    assert any("pre-commit is not executable" in issue for issue in report.issues)
    assert any("pre-push missing" in issue for issue in report.issues)


def test_build_report_uses_configured_relative_hooks_path(tmp_path: Path) -> None:
    repo = git_repo(tmp_path)
    hooks = repo / ".githooks"
    hooks.mkdir()
    for name in ("pre-commit", "pre-push"):
        hook = hooks / name
        hook.write_text("#!/usr/bin/env bash\ntrue\n", encoding="utf-8")
        hook.chmod(0o755)
    run_git(repo, "config", "core.hooksPath", ".githooks")

    report = check_agent_hooks.build_report(repo_root=repo)

    assert report.ok
    assert report.configured_hooks_path == ".githooks"
    assert report.effective_hooks_dir == str(hooks.resolve())


def test_cli_outputs_json_and_zero_for_missing_hooks_by_default(tmp_path: Path) -> None:
    repo = git_repo(tmp_path)

    completed = subprocess.run(
        [sys.executable, str(SCRIPT), "--repo-root", str(repo)],
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    payload = json.loads(completed.stdout)
    assert completed.returncode == 0
    assert payload["ok"] is False
    assert payload["issues"]
    assert completed.stderr == ""


def test_cli_strict_outputs_nonzero_for_missing_hooks(tmp_path: Path) -> None:
    repo = git_repo(tmp_path)

    completed = subprocess.run(
        [sys.executable, str(SCRIPT), "--repo-root", str(repo), "--strict"],
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    payload = json.loads(completed.stdout)
    assert completed.returncode == 1
    assert payload["ok"] is False


def test_cli_accepts_custom_hook_and_fingerprint(tmp_path: Path) -> None:
    repo = git_repo(tmp_path)
    hook = repo / ".git" / "hooks" / "pre-commit"
    hook.write_text("#!/usr/bin/env bash\npython3 scripts/agent_job_hook.py\n", encoding="utf-8")
    hook.chmod(0o755)

    completed = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--repo-root",
            str(repo),
            "--hook",
            "pre-commit",
            "--expect-fingerprint",
            "pre-commit=agent_job_hook.py",
        ],
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    payload = json.loads(completed.stdout)
    assert completed.returncode == 0
    assert payload["ok"] is True
    assert payload["hooks"][0]["fingerprint_present"] is True


def test_build_report_marks_non_matching_fingerprint(tmp_path: Path) -> None:
    repo = git_repo(tmp_path)
    hook = repo / ".git" / "hooks" / "pre-commit"
    hook.write_text("#!/usr/bin/env bash\ntrue\n", encoding="utf-8")
    hook.chmod(0o755)

    report = check_agent_hooks.build_report(
        repo_root=repo,
        hook_names=["pre-commit"],
        expected_fingerprints={"pre-commit": "agent_job_hook.py"},
    )

    assert not report.ok
    assert report.hooks[0].fingerprint_present is False
    assert any("expected fingerprint" in issue for issue in report.issues)


def test_pre_push_lints_committed_python_changes_from_ref_stdin(tmp_path: Path) -> None:
    repo = git_repo(tmp_path)
    hooks = repo / ".githooks"
    hooks.mkdir()
    pre_push = hooks / "pre-push"
    pre_push.write_text((Path(__file__).resolve().parents[1] / ".githooks" / "pre-push").read_text(), encoding="utf-8")
    pre_push.chmod(0o755)
    run_git(repo, "config", "user.email", "hooks@example.invalid")
    run_git(repo, "config", "user.name", "Hook Tests")
    source = repo / "committed.py"
    source.write_text("value = 1\n", encoding="utf-8")
    run_git(repo, "add", "committed.py")
    run_git(repo, "commit", "-m", "add committed python")
    (repo / "README.md").write_text("second commit\n", encoding="utf-8")
    run_git(repo, "add", "README.md")
    run_git(repo, "commit", "-m", "add non-python followup")
    head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=repo, check=True, text=True, stdout=subprocess.PIPE).stdout.strip()
    ruff = repo / "financial-engine_v2" / ".venv" / "bin" / "ruff"
    ruff.parent.mkdir(parents=True)
    capture = repo / "ruff-args.txt"
    ruff.write_text(f"#!/usr/bin/env bash\nprintf '%s\\n' \"$@\" > {capture}\n", encoding="utf-8")
    ruff.chmod(0o755)

    completed = subprocess.run(
        [str(pre_push)],
        cwd=repo,
        input=f"refs/heads/topic {head} refs/heads/topic {'0' * 40}\n",
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    assert completed.returncode == 0, completed.stderr
    assert capture.read_text(encoding="utf-8").splitlines() == ["check", "committed.py"]
