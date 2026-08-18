#!/usr/bin/env python3
"""Report Tenn control-plane effective-state drift without changing it."""

from __future__ import annotations

import argparse
import fnmatch
import hashlib
import json
import re
import subprocess
import sys
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable


SCHEMA_VERSION = "tenn_control_plane_doctor_v1"
PASS = "PASS"
WARN = "WARN"
FAIL = "FAIL"
DATA_MISSING = "DATA_MISSING"
STATUSES = (PASS, WARN, FAIL, DATA_MISSING)

DEFAULT_CANONICAL_REF = "origin/migration/clean-runtime-baseline-reconstruct-v1"
DEFAULT_DEPLOYED_ROOT = Path("/home/l4nd0/tenn-codex-automations-v1-20260516")
DEFAULT_HOST_SKILLS_ROOT = Path("/home/l4nd0/.agents/skills")
DEFAULT_HOOKS_FILE = Path("/home/l4nd0/.codex/hooks.json")
DEFAULT_INSTALLED_UNITS_ROOT = Path.home() / ".config/systemd/user"
DEFAULT_CANDIDATE_STATE = Path.home() / ".codex/automations/tenn/state/candidates.jsonl"


@dataclass(frozen=True)
class Config:
    repo_root: Path
    canonical_ref: str = DEFAULT_CANONICAL_REF
    deployed_root: Path | None = DEFAULT_DEPLOYED_ROOT
    host_skills_root: Path = DEFAULT_HOST_SKILLS_ROOT
    hooks_file: Path = DEFAULT_HOOKS_FILE
    installed_units_root: Path = DEFAULT_INSTALLED_UNITS_ROOT
    candidate_state: Path = DEFAULT_CANDIDATE_STATE
    docs: tuple[Path, ...] = ()


def result(check_id: str, status: str, summary: str, **evidence: Any) -> dict[str, Any]:
    if status not in STATUSES:
        raise ValueError(f"unsupported status: {status}")
    severity = {PASS: "info", WARN: "warning", DATA_MISSING: "warning", FAIL: "error"}[status]
    return {
        "id": check_id,
        "status": status,
        "severity": severity,
        "summary": summary,
        "evidence": evidence,
    }


def run(args: list[str], *, cwd: Path, timeout: int = 30) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        args,
        cwd=cwd,
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=timeout,
    )


def git(repo: Path, *args: str) -> tuple[str | None, str | None]:
    completed = run(["git", *args], cwd=repo)
    if completed.returncode:
        return None, completed.stderr.strip() or completed.stdout.strip() or f"exit {completed.returncode}"
    return completed.stdout.strip(), None


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def remote_tracking_parts(repo: Path, canonical_ref: str) -> tuple[str, str] | None:
    if canonical_ref.startswith("refs/remotes/"):
        relative = canonical_ref.removeprefix("refs/remotes/")
    else:
        relative = canonical_ref
    if "/" not in relative:
        return None
    remote, branch = relative.split("/", 1)
    remotes, error = git(repo, "remote")
    if error or remotes is None or remote not in remotes.splitlines():
        return None
    return remote, branch


def remote_canonical_sha(repo: Path, canonical_ref: str) -> tuple[str | None, str | None, str | None]:
    parts = remote_tracking_parts(repo, canonical_ref)
    if parts is None:
        return None, None, "canonical ref is not a configured remote-tracking ref"
    remote, branch = parts
    remote_ref = f"refs/heads/{branch}"
    completed = run(["git", "ls-remote", "--exit-code", remote, remote_ref], cwd=repo)
    if completed.returncode:
        error = completed.stderr.strip() or completed.stdout.strip() or f"exit {completed.returncode}"
        return None, remote_ref, error
    rows = [line.split() for line in completed.stdout.splitlines() if line.strip()]
    if len(rows) != 1 or len(rows[0]) < 2:
        return None, remote_ref, "remote canonical lookup returned an unexpected result"
    return rows[0][0], remote_ref, None


def check_git_parity(config: Config) -> dict[str, Any]:
    local_sha, local_error = git(config.repo_root, "rev-parse", "HEAD")
    canonical_sha, canonical_error = git(config.repo_root, "rev-parse", config.canonical_ref)
    if local_error or canonical_error:
        return result(
            "git_sha_parity",
            FAIL,
            "could not resolve local or canonical Git SHA",
            local_error=local_error,
            canonical_error=canonical_error,
        )

    remote_sha, remote_ref, remote_error = remote_canonical_sha(config.repo_root, config.canonical_ref)
    canonical_ref_fresh = remote_sha == canonical_sha if remote_sha is not None else None

    deployed_sha: str | None = None
    deployed_error: str | None = None
    if config.deployed_root is not None:
        if config.deployed_root.is_dir():
            deployed_sha, deployed_error = git(config.deployed_root, "rev-parse", "HEAD")
        else:
            deployed_error = "deployed root does not exist"

    if remote_error:
        status = DATA_MISSING
        summary = "remote canonical Git SHA is unavailable"
    elif canonical_ref_fresh is False:
        status = WARN
        summary = "cached canonical ref differs from remote canonical"
    elif deployed_error:
        status = DATA_MISSING
        summary = "deployed Git SHA is unavailable"
    elif deployed_sha != remote_sha:
        status = WARN
        summary = "deployed Git SHA differs from verified remote canonical"
    else:
        status = PASS
        summary = "deployed Git SHA matches verified remote canonical"
    return result(
        "git_sha_parity",
        status,
        summary,
        local_sha=local_sha,
        canonical_ref=config.canonical_ref,
        canonical_sha=canonical_sha,
        remote_canonical_ref=remote_ref,
        remote_canonical_sha=remote_sha,
        remote_canonical_error=remote_error,
        canonical_ref_fresh=canonical_ref_fresh,
        local_matches_canonical=local_sha == canonical_sha,
        deployed_root=str(config.deployed_root) if config.deployed_root else None,
        deployed_sha=deployed_sha,
        deployed_error=deployed_error,
    )


def check_runner_policy(config: Config) -> dict[str, Any]:
    runner = config.repo_root / "scripts/codex_automation_runner.py"
    if not runner.is_file():
        return result("runner_policy", DATA_MISSING, "repo automation runner is missing", path=str(runner))
    completed = run([sys.executable, str(runner), "list"], cwd=config.repo_root)
    if completed.returncode:
        return result(
            "runner_policy",
            FAIL,
            "runner policy listing failed",
            path=str(runner),
            error=completed.stderr.strip() or completed.stdout.strip(),
        )
    try:
        jobs = json.loads(completed.stdout)
    except json.JSONDecodeError as exc:
        return result("runner_policy", FAIL, "runner policy listing was not JSON", error=str(exc))
    if not isinstance(jobs, dict):
        return result("runner_policy", FAIL, "runner policy listing must be an object")

    small_jobs: dict[str, dict[str, Any]] = {}
    invalid_small_jobs: list[str] = []
    for name, payload in sorted(jobs.items()):
        if not isinstance(payload, dict) or payload.get("model_policy") != "small":
            continue
        selection = payload.get("model_selection")
        small_jobs[name] = selection if isinstance(selection, dict) else {}
        if not isinstance(selection, dict) or not selection.get("model") or not selection.get("reasoning_effort"):
            invalid_small_jobs.append(name)

    if not small_jobs:
        return result("runner_policy", WARN, "no small-policy jobs were listed", job_count=len(jobs))
    status = FAIL if invalid_small_jobs else PASS
    summary = "small-model policy is incomplete" if invalid_small_jobs else "small-model policy is explicit"
    evidence: dict[str, Any] = {
        "path": str(runner),
        "sha256": sha256(runner),
        "job_count": len(jobs),
        "small_jobs": small_jobs,
        "invalid_small_jobs": invalid_small_jobs,
    }
    if config.deployed_root is not None:
        deployed_runner = config.deployed_root / "scripts/codex_automation_runner.py"
        evidence["deployed_runner"] = str(deployed_runner)
        evidence["deployed_sha256"] = sha256(deployed_runner) if deployed_runner.is_file() else None
        evidence["runner_hash_match"] = (
            evidence["deployed_sha256"] == evidence["sha256"] if evidence["deployed_sha256"] else None
        )
        if evidence["runner_hash_match"] is False and status == PASS:
            status = WARN
            summary = "runner policy is explicit but deployed runner hash differs"
    return result("runner_policy", status, summary, **evidence)


def matching_files(root: Path, patterns: Iterable[str]) -> dict[str, Path]:
    matches: dict[str, Path] = {}
    if not root.is_dir():
        return matches
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        relative = path.relative_to(root).as_posix()
        if any(fnmatch.fnmatch(relative, pattern) or fnmatch.fnmatch(path.name, pattern) for pattern in patterns):
            matches[relative] = path
    return matches


def check_hash_tree(
    check_id: str,
    expected_root: Path,
    actual_root: Path,
    patterns: Iterable[str],
) -> dict[str, Any]:
    expected = matching_files(expected_root, patterns)
    actual = matching_files(actual_root, patterns)
    if not expected:
        return result(check_id, DATA_MISSING, "no expected files found", expected_root=str(expected_root))
    missing = sorted(set(expected) - set(actual))
    extra = sorted(set(actual) - set(expected))
    mismatched = sorted(name for name in set(expected) & set(actual) if sha256(expected[name]) != sha256(actual[name]))
    matched = sorted(name for name in set(expected) & set(actual) if name not in mismatched)
    status = WARN if missing or mismatched else PASS
    summary = "effective files differ from repo definitions" if status == WARN else "effective files match repo definitions"
    return result(
        check_id,
        status,
        summary,
        expected_root=str(expected_root),
        actual_root=str(actual_root),
        expected_count=len(expected),
        matched=matched,
        missing=missing,
        mismatched=mismatched,
        extra=extra,
    )


def check_unit_templates(config: Config) -> dict[str, Any]:
    return check_hash_tree(
        "installed_unit_templates",
        config.repo_root / "systemd/user",
        config.installed_units_root,
        ("tenn-codex-*.service", "tenn-codex-*.timer"),
    )


def check_skill_hashes(config: Config) -> dict[str, Any]:
    return check_hash_tree(
        "host_repo_skills",
        config.repo_root / ".agents/skills",
        config.host_skills_root,
        ("*/SKILL.md",),
    )


def strings(value: Any) -> Iterable[str]:
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for item in value.values():
            yield from strings(item)
    elif isinstance(value, list):
        for item in value:
            yield from strings(item)


ABSOLUTE_PYTHON_PATH = re.compile(r"(?<![A-Za-z0-9_.-])(/[^\s;|&\"']+\.py)\b")


def check_hook_targets(hooks_file: Path) -> dict[str, Any]:
    if not hooks_file.is_file():
        return result("hook_targets", DATA_MISSING, "hooks file is missing", path=str(hooks_file))
    try:
        payload = json.loads(hooks_file.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return result("hook_targets", FAIL, "hooks file is unreadable or invalid", path=str(hooks_file), error=str(exc))
    targets = sorted({match for text in strings(payload) for match in ABSOLUTE_PYTHON_PATH.findall(text)})
    missing = sorted(path for path in targets if not Path(path).is_file())
    status = WARN if missing else PASS
    return result(
        "hook_targets",
        status,
        "hook targets are missing" if missing else "all absolute Python hook targets exist",
        path=str(hooks_file),
        targets=targets,
        missing=missing,
    )


def check_candidate_state(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return result("candidate_state", DATA_MISSING, "candidate state is absent", path=str(path))
    invalid_lines: list[int] = []
    row_count = 0
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        row_count += 1
        try:
            payload = json.loads(line)
        except json.JSONDecodeError:
            invalid_lines.append(line_number)
            continue
        if not isinstance(payload, dict):
            invalid_lines.append(line_number)
    if invalid_lines:
        return result(
            "candidate_state",
            FAIL,
            "candidate state contains invalid JSON objects",
            path=str(path),
            row_count=row_count,
            invalid_lines=invalid_lines,
        )
    status = PASS if row_count else WARN
    return result(
        "candidate_state",
        status,
        "candidate state is readable" if row_count else "candidate state is empty",
        path=str(path),
        row_count=row_count,
        invalid_lines=[],
    )


def check_marker_semantics(marker_script: Path, brief_script: Path) -> dict[str, Any]:
    missing = [str(path) for path in (marker_script, brief_script) if not path.is_file()]
    if missing:
        return result("marker_semantics", DATA_MISSING, "marker semantic source is missing", missing=missing)
    marker_text = marker_script.read_text(encoding="utf-8")
    brief_text = brief_script.read_text(encoding="utf-8")
    optional_missing_marker = "marker_exists=False" in marker_text.replace(" ", "") or (
        "marker_exists" in marker_text and "DATA_MISSING" in marker_text
    )
    brief_stale_report_path = "stale_report" in brief_text
    conflict = optional_missing_marker and brief_stale_report_path
    return result(
        "marker_semantics",
        WARN if conflict else PASS,
        "optional missing markers can be rediscovered as stale reports" if conflict else "no static missing-marker conflict detected",
        marker_script=str(marker_script),
        brief_script=str(brief_script),
        optional_missing_marker=optional_missing_marker,
        brief_stale_report_path=brief_stale_report_path,
    )


META_RE = re.compile(r"(?m)^last_verified_commit:\s*`?([0-9a-fA-F]{7,40})`?\s*$")


def stale_patterns(text: str) -> list[str]:
    lines = text.splitlines()
    patterns: list[str] = []
    collecting = False
    for line in lines:
        if line.strip() == "stale_if_files:":
            collecting = True
            continue
        if collecting and line.startswith("- "):
            patterns.append(line[2:].strip().strip("`"))
        elif collecting and line.strip() and not line.startswith((" ", "-")):
            break
    return patterns


def check_docs_freshness(config: Config) -> dict[str, Any]:
    docs = config.docs or (
        config.repo_root / "docs/dev_flow/SKILLS_SURFACE.md",
        config.repo_root / "docs/dev_flow/CONTROL_PLANE_STATUS.md",
    )
    canonical_sha, error = git(config.repo_root, "rev-parse", config.canonical_ref)
    if error or canonical_sha is None:
        return result("docs_freshness", FAIL, "canonical SHA unavailable for docs freshness", error=error)
    rows: list[dict[str, Any]] = []
    stale_docs: list[str] = []
    missing_docs: list[str] = []
    for path in docs:
        if not path.is_file():
            missing_docs.append(str(path))
            continue
        text = path.read_text(encoding="utf-8")
        match = META_RE.search(text)
        patterns = stale_patterns(text)
        row: dict[str, Any] = {"path": str(path), "last_verified_commit": None, "stale_patterns": patterns}
        if not match:
            row["status"] = DATA_MISSING
            stale_docs.append(str(path))
            rows.append(row)
            continue
        verified = match.group(1)
        row["last_verified_commit"] = verified
        ancestor = run(["git", "merge-base", "--is-ancestor", verified, canonical_sha], cwd=config.repo_root)
        row["ancestor_of_canonical"] = ancestor.returncode == 0
        changed_output, changed_error = git(config.repo_root, "diff", "--name-only", f"{verified}..{canonical_sha}")
        changed = changed_output.splitlines() if changed_output is not None else []
        matching_changed = sorted(
            name for name in changed if any(fnmatch.fnmatch(name, pattern) for pattern in patterns)
        )
        row["matching_changed_files"] = matching_changed
        row["status"] = PASS if row["ancestor_of_canonical"] and not matching_changed and not changed_error else WARN
        if row["status"] != PASS:
            stale_docs.append(str(path))
        rows.append(row)
    status = WARN if stale_docs else (DATA_MISSING if missing_docs else PASS)
    return result(
        "docs_freshness",
        status,
        "docs freshness needs review" if status != PASS else "docs freshness metadata is current",
        canonical_sha=canonical_sha,
        docs=rows,
        stale_docs=sorted(stale_docs),
        missing_docs=sorted(missing_docs),
    )


def summarize(checks: list[dict[str, Any]]) -> dict[str, Any]:
    counts = Counter(check["status"] for check in checks)
    if counts[FAIL]:
        status, exit_code = FAIL, 2
    elif counts[WARN] or counts[DATA_MISSING]:
        status, exit_code = WARN, 1
    else:
        status, exit_code = PASS, 0
    return {
        "status": status,
        "exit_code": exit_code,
        "counts": {key: counts[key] for key in STATUSES},
    }


def run_doctor(config: Config) -> tuple[dict[str, Any], int]:
    checks = [
        check_git_parity(config),
        check_runner_policy(config),
        check_unit_templates(config),
        check_skill_hashes(config),
        check_hook_targets(config.hooks_file),
        check_candidate_state(config.candidate_state),
        check_marker_semantics(
            config.repo_root / "scripts/report_review_status.py",
            config.repo_root / "scripts/system_brief.py",
        ),
        check_docs_freshness(config),
    ]
    checks.sort(key=lambda check: check["id"])
    summary = summarize(checks)
    payload = {
        "schema_version": SCHEMA_VERSION,
        "read_only": True,
        "repo_root": str(config.repo_root),
        "canonical_ref": config.canonical_ref,
        "summary": summary,
        "checks": checks,
    }
    return payload, int(summary["exit_code"])


def find_repo_root() -> Path:
    completed = subprocess.run(
        ["git", "rev-parse", "--show-toplevel"],
        check=True,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    return Path(completed.stdout.strip()).resolve()


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path)
    parser.add_argument("--canonical-ref", default=DEFAULT_CANONICAL_REF)
    parser.add_argument("--deployed-root", type=Path, default=DEFAULT_DEPLOYED_ROOT)
    parser.add_argument("--host-skills-root", type=Path, default=DEFAULT_HOST_SKILLS_ROOT)
    parser.add_argument("--hooks-file", type=Path, default=DEFAULT_HOOKS_FILE)
    parser.add_argument("--installed-units-root", type=Path, default=DEFAULT_INSTALLED_UNITS_ROOT)
    parser.add_argument("--candidate-state", type=Path, default=DEFAULT_CANDIDATE_STATE)
    parser.add_argument("--doc", action="append", type=Path, default=[])
    parser.add_argument("--json", action="store_true", help="emit JSON (the only supported output format in v1)")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        repo_root = (args.repo_root or find_repo_root()).resolve()
        config = Config(
            repo_root=repo_root,
            canonical_ref=args.canonical_ref,
            deployed_root=args.deployed_root.resolve() if args.deployed_root else None,
            host_skills_root=args.host_skills_root.resolve(),
            hooks_file=args.hooks_file.resolve(),
            installed_units_root=args.installed_units_root.resolve(),
            candidate_state=args.candidate_state.resolve(),
            docs=tuple(path.resolve() for path in args.doc),
        )
        payload, exit_code = run_doctor(config)
    except (OSError, subprocess.SubprocessError, ValueError) as exc:
        payload = {
            "schema_version": SCHEMA_VERSION,
            "read_only": True,
            "summary": {"status": FAIL, "exit_code": 2},
            "error": str(exc),
        }
        exit_code = 2
    print(json.dumps(payload, indent=2, sort_keys=True))
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
