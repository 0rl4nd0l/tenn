from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

from scripts import check_agent_hooks


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "check_agent_hooks.py"
PRE_PUSH_SOURCE = Path(__file__).resolve().parents[1] / ".githooks" / "pre-push"
ZERO_SHA = "0" * 40


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


def git_output(repo: Path, *args: str) -> str:
    return subprocess.run(
        ["git", *args],
        cwd=repo,
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    ).stdout.strip()


def configure_git_identity(repo: Path) -> None:
    run_git(repo, "config", "user.email", "hooks@example.invalid")
    run_git(repo, "config", "user.name", "Hook Tests")


def commit_file(repo: Path, path: str, content: str, message: str) -> str:
    target = repo / path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")
    run_git(repo, "add", path)
    run_git(repo, "commit", "-m", message)
    return git_output(repo, "rev-parse", "HEAD")


def install_pre_push(repo: Path) -> Path:
    hook = repo / ".githooks" / "pre-push"
    hook.parent.mkdir(parents=True, exist_ok=True)
    hook.write_text(PRE_PUSH_SOURCE.read_text(encoding="utf-8"), encoding="utf-8")
    hook.chmod(0o755)
    return hook


def install_ruff_capture(repo: Path) -> Path:
    ruff = repo / "financial-engine_v2" / ".venv" / "bin" / "ruff"
    ruff.parent.mkdir(parents=True, exist_ok=True)
    capture = repo / "ruff-args.txt"
    ruff.write_text(
        "#!/usr/bin/env bash\nprintf '%s\\n' \"$@\" > \"$PWD/ruff-args.txt\"\n",
        encoding="utf-8",
    )
    ruff.chmod(0o755)
    return capture


def install_ruff_nul_capture(repo: Path) -> Path:
    ruff = repo / "financial-engine_v2" / ".venv" / "bin" / "ruff"
    ruff.parent.mkdir(parents=True, exist_ok=True)
    capture = repo / "ruff-args.bin"
    ruff.write_text(
        "#!/usr/bin/env bash\nprintf '%s\\0' \"$@\" > \"$PWD/ruff-args.bin\"\n",
        encoding="utf-8",
    )
    ruff.chmod(0o755)
    return capture


def install_markdown_probe(repo: Path, *, exit_code: int = 0) -> Path:
    script = repo / "scripts" / "check_markdown_hygiene.sh"
    script.parent.mkdir(parents=True, exist_ok=True)
    sentinel = repo / "markdown-hygiene-ran"
    script.write_text(
        "#!/usr/bin/env bash\nprintf 'ran\\n' > \"$PWD/markdown-hygiene-ran\"\n"
        f"exit {exit_code}\n",
        encoding="utf-8",
    )
    script.chmod(0o755)
    return sentinel


def run_pre_push(repo: Path, hook: Path, refs: list[tuple[str, str, str, str]]) -> subprocess.CompletedProcess[str]:
    stdin = "".join(" ".join(ref) + "\n" for ref in refs)
    return subprocess.run(
        [str(hook), "origin", "unused"],
        cwd=repo,
        input=stdin,
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )


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


def test_pre_push_lints_all_commits_introduced_by_new_branch(tmp_path: Path) -> None:
    repo = git_repo(tmp_path)
    configure_git_identity(repo)
    hook = install_pre_push(repo)
    base = commit_file(repo, "README.md", "base\n", "base")
    run_git(repo, "update-ref", "refs/remotes/origin/main", base)
    commit_file(repo, "committed.py", "value = 1\n", "add committed python")
    head = commit_file(repo, "README.md", "followup\n", "add non-python followup")
    capture = install_ruff_capture(repo)

    completed = run_pre_push(
        repo,
        hook,
        [("refs/heads/topic", head, "refs/heads/topic", ZERO_SHA)],
    )

    assert completed.returncode == 0, completed.stderr
    assert capture.read_text(encoding="utf-8").splitlines() == [
        "check",
        "--",
        "committed.py",
    ]


def test_pre_push_includes_python_from_new_branch_merge_commit(tmp_path: Path) -> None:
    repo = git_repo(tmp_path)
    configure_git_identity(repo)
    hook = install_pre_push(repo)
    base = commit_file(repo, "README.md", "base\n", "base")
    main_branch = git_output(repo, "branch", "--show-current")

    run_git(repo, "checkout", "-b", "side", base)
    side = commit_file(repo, "merged.py", "value = 1\n", "side python")
    run_git(repo, "checkout", main_branch)
    main = commit_file(repo, "main.txt", "main\n", "main change")
    run_git(repo, "update-ref", "refs/remotes/origin/main", main)
    run_git(repo, "update-ref", "refs/remotes/origin/side", side)
    run_git(repo, "merge", "--no-ff", "side", "-m", "merge side")
    merge_sha = git_output(repo, "rev-parse", "HEAD")
    capture = install_ruff_capture(repo)

    completed = run_pre_push(
        repo,
        hook,
        [("refs/heads/topic", merge_sha, "refs/heads/topic", ZERO_SHA)],
    )

    assert completed.returncode == 0, completed.stderr
    assert capture.read_text(encoding="utf-8").splitlines() == [
        "check",
        "--",
        "merged.py",
    ]


def test_pre_push_handles_deletion_rename_and_multiple_refs(tmp_path: Path) -> None:
    repo = git_repo(tmp_path)
    configure_git_identity(repo)
    hook = install_pre_push(repo)
    base = commit_file(repo, "old.py", "value = 1\n", "base python")

    run_git(repo, "checkout", "-b", "delete", base)
    run_git(repo, "rm", "old.py")
    run_git(repo, "commit", "-m", "delete python")
    delete_sha = git_output(repo, "rev-parse", "HEAD")

    run_git(repo, "checkout", "-b", "rename", base)
    run_git(repo, "mv", "old.py", "renamed.py")
    run_git(repo, "commit", "-m", "rename python")
    rename_sha = git_output(repo, "rev-parse", "HEAD")
    capture = install_ruff_capture(repo)

    completed = run_pre_push(
        repo,
        hook,
        [
            ("(delete)", ZERO_SHA, "refs/heads/gone", base),
            ("refs/heads/delete", delete_sha, "refs/heads/delete", base),
            ("refs/heads/rename", rename_sha, "refs/heads/rename", base),
        ],
    )

    assert completed.returncode == 0, completed.stderr
    assert capture.read_text(encoding="utf-8").splitlines() == [
        "check",
        "--",
        "renamed.py",
    ]


def test_pre_push_fails_closed_for_python_on_divergent_ref_tip(
    tmp_path: Path,
) -> None:
    repo = git_repo(tmp_path)
    configure_git_identity(repo)
    hook = install_pre_push(repo)
    base = commit_file(repo, "README.md", "base\n", "base")
    current_branch = git_output(repo, "branch", "--show-current")

    run_git(repo, "checkout", "-b", "divergent", base)
    divergent_sha = commit_file(
        repo,
        "divergent.py",
        "value = 1\n",
        "add divergent python",
    )
    run_git(repo, "checkout", current_branch)
    capture = install_ruff_capture(repo)

    completed = run_pre_push(
        repo,
        hook,
        [
            (
                "refs/heads/divergent",
                divergent_sha,
                "refs/heads/divergent",
                base,
            )
        ],
    )

    assert completed.returncode != 0
    assert "divergent pushed ref" in completed.stderr
    assert not capture.exists()


def test_pre_push_preserves_non_ascii_python_paths(tmp_path: Path) -> None:
    repo = git_repo(tmp_path)
    configure_git_identity(repo)
    hook = install_pre_push(repo)
    base = commit_file(repo, "README.md", "base\n", "base")
    head = commit_file(repo, "café.py", "value = 1\n", "add unicode python")
    capture = install_ruff_capture(repo)

    completed = run_pre_push(
        repo,
        hook,
        [("refs/heads/topic", head, "refs/heads/topic", base)],
    )

    assert completed.returncode == 0, completed.stderr
    assert capture.read_text(encoding="utf-8").splitlines() == [
        "check",
        "--",
        "café.py",
    ]


def test_pre_push_preserves_newline_in_python_path(tmp_path: Path) -> None:
    repo = git_repo(tmp_path)
    configure_git_identity(repo)
    hook = install_pre_push(repo)
    base = commit_file(repo, "README.md", "base\n", "base")
    path = "line\nbreak.py"
    head = commit_file(repo, path, "value = 1\n", "add newline python")
    capture = install_ruff_nul_capture(repo)

    completed = run_pre_push(
        repo,
        hook,
        [("refs/heads/topic", head, "refs/heads/topic", base)],
    )

    assert completed.returncode == 0, completed.stderr
    assert capture.read_bytes().split(b"\0") == [
        b"check",
        b"--",
        path.encode(),
        b"",
    ]


def test_pre_push_peels_annotated_tag_at_current_head(tmp_path: Path) -> None:
    repo = git_repo(tmp_path)
    configure_git_identity(repo)
    hook = install_pre_push(repo)
    base = commit_file(repo, "README.md", "base\n", "base")
    run_git(repo, "update-ref", "refs/remotes/origin/main", base)
    head = commit_file(repo, "tagged.py", "value = 1\n", "add tagged python")
    run_git(repo, "tag", "-a", "v1", "-m", "version one")
    tag_sha = git_output(repo, "rev-parse", "refs/tags/v1")
    capture = install_ruff_capture(repo)

    completed = run_pre_push(
        repo,
        hook,
        [
            ("refs/heads/topic", head, "refs/heads/topic", base),
            ("refs/tags/v1", tag_sha, "refs/tags/v1", ZERO_SHA),
        ],
    )

    assert completed.returncode == 0, completed.stderr
    assert capture.read_text(encoding="utf-8").splitlines() == [
        "check",
        "--",
        "tagged.py",
        "tagged.py",
    ]


def test_pre_push_fails_all_refs_before_missing_ruff_warning(tmp_path: Path) -> None:
    repo = git_repo(tmp_path)
    configure_git_identity(repo)
    hook = install_pre_push(repo)
    base = commit_file(repo, "README.md", "base\n", "base")
    head = commit_file(repo, "changed.py", "value = 1\n", "python change")
    markdown_sentinel = install_markdown_probe(repo)
    invalid_remote = "f" * 40

    completed = run_pre_push(
        repo,
        hook,
        [
            ("refs/heads/valid", head, "refs/heads/valid", base),
            ("refs/heads/invalid", head, "refs/heads/invalid", invalid_remote),
        ],
    )

    assert completed.returncode != 0
    assert "failed to enumerate" in completed.stderr
    assert "fatal:" not in completed.stderr.lower()
    assert "ruff unavailable" not in completed.stderr
    assert not markdown_sentinel.exists()


def test_pre_push_warns_for_missing_ruff_only_after_successful_enumeration(
    tmp_path: Path,
) -> None:
    repo = git_repo(tmp_path)
    configure_git_identity(repo)
    hook = install_pre_push(repo)
    base = commit_file(repo, "README.md", "base\n", "base")
    head = commit_file(repo, "changed.py", "value = 1\n", "python change")
    markdown_sentinel = install_markdown_probe(repo)

    completed = run_pre_push(
        repo,
        hook,
        [("refs/heads/topic", head, "refs/heads/topic", base)],
    )

    assert completed.returncode == 0, completed.stderr
    assert completed.stderr.count("ruff unavailable") == 1
    assert markdown_sentinel.read_text(encoding="utf-8") == "ran\n"


def test_pre_push_propagates_markdown_hygiene_failure_after_enumeration(
    tmp_path: Path,
) -> None:
    repo = git_repo(tmp_path)
    configure_git_identity(repo)
    hook = install_pre_push(repo)
    head = commit_file(repo, "README.md", "base\n", "base")
    markdown_sentinel = install_markdown_probe(repo, exit_code=23)

    completed = run_pre_push(
        repo,
        hook,
        [("refs/heads/topic", head, "refs/heads/topic", head)],
    )

    assert completed.returncode == 23
    assert markdown_sentinel.read_text(encoding="utf-8") == "ran\n"
