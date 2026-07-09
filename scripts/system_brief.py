#!/usr/bin/env python3
"""Read-only Tenn session brief.

The brief surfaces approval and review work without mutating GitHub, timers,
runtime state, data stores, reports, branches, or product files.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Callable, Sequence

try:
    from scripts.report_review_status import load_report_review_status
except ModuleNotFoundError:  # pragma: no cover - used when run as scripts/system_brief.py
    from report_review_status import load_report_review_status

try:
    from scripts.automation_candidate_store import candidate_items_for_brief
except ModuleNotFoundError:  # pragma: no cover - used when run as scripts/system_brief.py
    from automation_candidate_store import candidate_items_for_brief


SAFE_ISSUE_RISKS = {"risk:low", "risk:medium"}
SAFE_ISSUE_MODES = {"mode:safe-extension", "mode:audit", "mode:result-review"}
SAFE_ISSUE_LANES = {
    "lane:reporting",
    "lane:repo-hygiene",
    "lane:evaluation",
    "lane:query-orchestration",
}
FORBIDDEN_ISSUE_LANES = {
    "lane:runtime",
    "lane:financial-truth",
    "lane:data",
    "lane:provenance",
}
TOKEN_ANOMALY_THRESHOLD = 2_000_000
LOG_TAIL_BYTES = 256 * 1024
COMMAND_TIMEOUT_SECONDS = 30
SOURCE_PRIORITY = {
    "candidate_state": 0,
    "report_markers": 1,
    "automation_reports": 2,
    "experiment_branches": 3,
    "github_prs": 4,
    "github_issues": 5,
    "token_usage": 6,
}


@dataclass(frozen=True)
class CommandResult:
    returncode: int
    stdout: str
    stderr: str


@dataclass(frozen=True)
class RepoState:
    repo_root: str
    branch: str
    head: str
    dirty: bool
    status_lines: list[str]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class BriefItem:
    priority: int
    status: str
    source: str
    title: str
    detail: str
    owner_action: str
    risk: str
    evidence: str
    recommended_command: str
    url: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class Brief:
    repo_state: RepoState
    items: list[BriefItem]
    sources: dict[str, str]

    def to_dict(self) -> dict[str, Any]:
        return {
            "read_only": True,
            "repo_state": self.repo_state.to_dict(),
            "sources": self.sources,
            "recommended": self.items[0].to_dict() if self.items else None,
            "items": [item.to_dict() for item in self.items],
        }


Runner = Callable[[list[str], Path | None], CommandResult]


def run_command(command: list[str], cwd: Path | None = None) -> CommandResult:
    try:
        proc = subprocess.run(
            command,
            cwd=cwd,
            check=False,
            text=True,
            capture_output=True,
            timeout=COMMAND_TIMEOUT_SECONDS,
        )
    except subprocess.TimeoutExpired as exc:
        return CommandResult(
            124,
            _timeout_output(exc.stdout),
            f"command timed out after {COMMAND_TIMEOUT_SECONDS}s: {' '.join(command)}",
        )
    return CommandResult(proc.returncode, proc.stdout, proc.stderr)


def _timeout_output(value: str | bytes | None) -> str:
    if value is None:
        return ""
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    return value


def _json_from_command(command: list[str], cwd: Path | None, runner: Runner) -> tuple[Any | None, str | None]:
    result = runner(command, cwd)
    if result.returncode != 0:
        message = (result.stderr or result.stdout or "command failed").strip()
        return None, f"{' '.join(command)} failed: {message}"
    try:
        return json.loads(result.stdout or "null"), None
    except json.JSONDecodeError as exc:
        return None, f"{' '.join(command)} returned invalid JSON: {exc}"


def _text_from_command(command: list[str], cwd: Path, runner: Runner) -> str:
    result = runner(command, cwd)
    if result.returncode != 0:
        return "DATA_MISSING"
    return result.stdout.strip() or "DATA_MISSING"


def collect_repo_state(repo_root: Path, runner: Runner = run_command) -> RepoState:
    branch = _text_from_command(["git", "branch", "--show-current"], repo_root, runner)
    head = _text_from_command(["git", "rev-parse", "--short", "HEAD"], repo_root, runner)
    status_result = runner(["git", "status", "--short", "--untracked-files=all"], repo_root)
    status_lines = status_result.stdout.splitlines() if status_result.returncode == 0 else ["DATA_MISSING"]
    return RepoState(
        repo_root=str(repo_root),
        branch=branch,
        head=head,
        dirty=bool(status_lines and status_lines != ["DATA_MISSING"]),
        status_lines=status_lines,
    )


def label_names(record: dict[str, Any]) -> set[str]:
    labels = record.get("labels", [])
    names: set[str] = set()
    for label in labels:
        if isinstance(label, dict):
            name = label.get("name")
        else:
            name = label
        if isinstance(name, str) and name:
            names.add(name)
    return names


def is_eligible_ready_issue(issue: dict[str, Any]) -> bool:
    names = label_names(issue)
    lane_labels = {name for name in names if name.startswith("lane:")}
    return (
        "state:ready" in names
        and bool(names & SAFE_ISSUE_RISKS)
        and bool(names & SAFE_ISSUE_MODES)
        and bool(names & SAFE_ISSUE_LANES)
        and lane_labels.issubset(SAFE_ISSUE_LANES)
        and not bool(names & FORBIDDEN_ISSUE_LANES)
    )


def normalize_status(value: object) -> str:
    if not isinstance(value, str) or not value.strip():
        return "DATA_MISSING"
    return value.strip().lower().replace("-", "_")


def item_priority(status: str) -> int:
    return {
        "failed_validation": 10,
        "failed_schema_validation": 10,
        "owner_decision_required": 20,
        "needs_review": 30,
        "pending_review": 30,
        "needs_more_evidence": 30,
        "parked_experiment": 40,
        "draft_pr": 50,
        "state_ready_issue": 60,
        "deferred": 70,
        "defer": 70,
        "token_anomaly": 80,
        "stale_draft_pr": 85,
        "stale_report": 90,
        "data_missing": 95,
    }.get(status, 75)


def _queue_item(
    *,
    status: str,
    source: str,
    title: str,
    detail: str,
    owner_action: str,
    risk: str,
    evidence: str,
    recommended_command: str,
    url: str | None = None,
) -> BriefItem:
    normalized = normalize_status(status)
    return BriefItem(
        priority=item_priority(normalized),
        status=normalized,
        source=source,
        title=title,
        detail=detail,
        owner_action=owner_action,
        risk=risk,
        evidence=evidence,
        recommended_command=recommended_command,
        url=url,
    )


def collect_candidate_items(automation_root: Path) -> tuple[list[BriefItem], str]:
    path = automation_root / "state" / "candidates.jsonl"
    if not path.exists():
        item = _queue_item(
            status="DATA_MISSING",
            source="candidate_state",
            title="Candidate state file is absent",
            detail=f"No candidate state found at {path}.",
            owner_action="none",
            risk="low",
            evidence=str(path),
            recommended_command="python3 scripts/system_brief.py --json",
        )
        return [item], "DATA_MISSING"

    candidate_items, summary = candidate_items_for_brief(path)
    items = [
        _queue_item(
            status=str(item.get("status") or "DATA_MISSING"),
            source="candidate_state",
            title=str(item.get("title") or "Candidate item"),
            detail=str(item.get("detail") or item.get("status") or "DATA_MISSING"),
            owner_action=str(item.get("owner_action") or "review this"),
            risk=str(item.get("risk") or "unknown"),
            evidence=str(item.get("evidence") or path),
            recommended_command=str(item.get("recommended_command") or f"python3 scripts/automation_candidate_store.py --state-path {path} list --include-summary"),
            url=item.get("url") if isinstance(item.get("url"), str) else None,
        )
        for item in candidate_items
    ]
    issues = summary.get("issues")
    if isinstance(issues, list):
        for issue in issues[:3]:
            items.append(
                _queue_item(
                    status="failed_validation",
                    source="candidate_state",
                    title="Candidate state parse issue",
                    detail=str(issue),
                    owner_action="review this",
                    risk="medium",
                    evidence=str(path),
                    recommended_command=f"python3 scripts/automation_candidate_store.py --state-path {path} summarize",
                )
            )
    return items, "ok"


def collect_report_marker_items(repo_root: Path, recent_report_limit: int) -> tuple[list[BriefItem], str]:
    reports_root = repo_root / "reports" / "agent_jobs"
    if not reports_root.exists():
        return [
            _queue_item(
                status="DATA_MISSING",
                source="report_markers",
                title="Report directory is absent",
                detail=f"No reports root found at {reports_root}.",
                owner_action="none",
                risk="low",
                evidence=str(reports_root),
                recommended_command="find reports/agent_jobs -maxdepth 1 -type d | tail",
            )
        ], "DATA_MISSING"

    report_dirs = [path for path in reports_root.iterdir() if path.is_dir()]
    report_dirs.sort(key=lambda path: path.stat().st_mtime, reverse=True)
    items: list[BriefItem] = []
    unmarked: list[Path] = []
    for report_dir in report_dirs:
        result = load_report_review_status(report_dir, repo_root=repo_root)
        status = normalize_status(result.review_status)
        rel_dir = report_dir.relative_to(repo_root)
        if not result.marker_exists:
            if len(unmarked) < recent_report_limit:
                unmarked.append(rel_dir)
            continue
        if status in {"reviewed_accepted", "superseded"}:
            continue
        if status == "parked":
            mapped_status = "deferred"
        elif status == "failed_schema_validation":
            mapped_status = "failed_validation"
        else:
            mapped_status = status
        summary = ""
        if result.payload and isinstance(result.payload.get("summary"), str):
            summary = result.payload["summary"]
        items.append(
            _queue_item(
                status=mapped_status,
                source="report_markers",
                title=f"{result.job_id}: {result.review_status}",
                detail=summary or "Report marker needs review.",
                owner_action="review this",
                risk="low",
                evidence=str(rel_dir / "REPORT_REVIEW_STATUS.json"),
                recommended_command=f"python3 scripts/report_review_status.py validate {rel_dir}",
            )
        )

    if unmarked:
        preview = ", ".join(str(path) for path in unmarked[:5])
        items.append(
            _queue_item(
                status="stale_report",
                source="report_markers",
                title=f"{len(unmarked)} recent report(s) lack review markers",
                detail=f"Recent unmarked reports include: {preview}",
                owner_action="review this",
                risk="low",
                evidence=str(reports_root.relative_to(repo_root)),
                recommended_command="python3 scripts/report_review_status.py scan reports/agent_jobs --repo-root .",
            )
        )
    return items, "ok"


def collect_automation_report_items(automation_root: Path, recent_report_limit: int) -> tuple[list[BriefItem], str]:
    reports_root = automation_root / "reports"
    if not reports_root.exists():
        return [
            _queue_item(
                status="DATA_MISSING",
                source="automation_reports",
                title="Automation report directory is absent",
                detail=f"No automation reports found at {reports_root}.",
                owner_action="none",
                risk="low",
                evidence=str(reports_root),
                recommended_command=f"find {automation_root} -maxdepth 2 -type d",
            )
        ], "DATA_MISSING"

    paths = sorted(
        [path for path in reports_root.glob("*.md") if path.is_file()],
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )[:recent_report_limit]
    items: list[BriefItem] = []
    for path in paths:
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        lowered = text.lower()
        if "failed_validation" in lowered or "failed validation" in lowered:
            status = "failed_validation"
            action = "review this"
        elif "owner_decision_required" in lowered or "owner decision required" in lowered:
            status = "owner_decision_required"
            action = "review this"
        elif "needs_review" in lowered or "pending_review" in lowered:
            status = "needs_review"
            action = "review this"
        else:
            continue
        items.append(
            _queue_item(
                status=status,
                source="automation_reports",
                title=path.name,
                detail="Recent automation report contains a review or validation marker.",
                owner_action=action,
                risk="unknown",
                evidence=str(path),
                recommended_command=f"sed -n '1,180p' {path}",
            )
        )
    return items, "ok"


def collect_token_items(automation_root: Path, log_limit: int, threshold: int = TOKEN_ANOMALY_THRESHOLD) -> tuple[list[BriefItem], str]:
    logs_root = automation_root / "logs"
    if not logs_root.exists():
        return [
            _queue_item(
                status="DATA_MISSING",
                source="token_usage",
                title="Automation log directory is absent",
                detail=f"No automation logs found at {logs_root}.",
                owner_action="none",
                risk="low",
                evidence=str(logs_root),
                recommended_command=f"find {automation_root} -maxdepth 2 -type d",
            )
        ], "DATA_MISSING"

    logs = sorted(
        [path for path in logs_root.glob("*.jsonl") if path.is_file()],
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )[:log_limit]
    items: list[BriefItem] = []
    for path in logs:
        for usage in _usage_records_from_tail(path):
            input_tokens = usage.get("input_tokens")
            if not isinstance(input_tokens, int) or input_tokens < threshold:
                continue
            job_name = path.name.removesuffix(".jsonl")
            items.append(
                _queue_item(
                    status="token_anomaly",
                    source="token_usage",
                    title=f"{job_name} used {input_tokens:,} input tokens",
                    detail=(
                        f"cached={usage.get('cached_input_tokens', 'DATA_MISSING')}, "
                        f"output={usage.get('output_tokens', 'DATA_MISSING')}, "
                        f"reasoning={usage.get('reasoning_output_tokens', 'DATA_MISSING')}"
                    ),
                    owner_action="defer 30 days",
                    risk="low",
                    evidence=str(path),
                    recommended_command=f"rg -n 'turn.completed|input_tokens' {path}",
                )
            )
    return items, "ok"


def _usage_records_from_tail(path: Path) -> list[dict[str, Any]]:
    try:
        with path.open("rb") as handle:
            handle.seek(0, 2)
            size = handle.tell()
            handle.seek(max(0, size - LOG_TAIL_BYTES))
            text = handle.read().decode("utf-8", errors="replace")
    except OSError:
        return []

    records: list[dict[str, Any]] = []
    for line in text.splitlines():
        if "input_tokens" not in line:
            continue
        try:
            payload = json.loads(line)
        except json.JSONDecodeError:
            continue
        usage = payload.get("usage")
        if isinstance(usage, dict):
            records.append(usage)
    return records


def collect_github_issue_items(repo: str, issue_limit: int, runner: Runner = run_command) -> tuple[list[BriefItem], str]:
    command = [
        "gh",
        "issue",
        "list",
        "--repo",
        repo,
        "--state",
        "open",
        "--limit",
        str(issue_limit),
        "--label",
        "state:ready",
        "--json",
        "number,title,state,labels,url,updatedAt",
    ]
    issues, error = _json_from_command(command, None, runner)
    if error:
        return [
            _queue_item(
                status="DATA_MISSING",
                source="github_issues",
                title="GitHub ready issues could not be read",
                detail=error,
                owner_action="none",
                risk="low",
                evidence="gh issue list",
                recommended_command=" ".join(command),
            )
        ], "DATA_MISSING"
    if not isinstance(issues, list):
        return [], "ok"

    items: list[BriefItem] = []
    for issue in issues:
        if not isinstance(issue, dict) or not is_eligible_ready_issue(issue):
            continue
        number = issue.get("number")
        title = str(issue.get("title") or "Untitled issue")
        items.append(
            _queue_item(
                status="state_ready_issue",
                source="github_issues",
                title=f"#{number} {title}",
                detail="Issue is eligible for a read-only brief recommendation.",
                owner_action="review this",
                risk="low/medium",
                evidence=", ".join(sorted(label_names(issue))),
                recommended_command=f"gh issue view {number} --repo {repo}",
                url=issue.get("url") if isinstance(issue.get("url"), str) else None,
            )
        )
    return items, "ok"


def collect_github_pr_items(repo: str, pr_limit: int, runner: Runner = run_command) -> tuple[list[BriefItem], str]:
    command = [
        "gh",
        "pr",
        "list",
        "--repo",
        repo,
        "--state",
        "open",
        "--limit",
        str(pr_limit),
        "--json",
        "number,title,state,isDraft,headRefName,labels,url,updatedAt",
    ]
    prs, error = _json_from_command(command, None, runner)
    if error:
        return [
            _queue_item(
                status="DATA_MISSING",
                source="github_prs",
                title="GitHub draft PRs could not be read",
                detail=error,
                owner_action="none",
                risk="low",
                evidence="gh pr list",
                recommended_command=" ".join(command),
            )
        ], "DATA_MISSING"
    if not isinstance(prs, list):
        return [], "ok"

    items: list[BriefItem] = []
    for pr in prs:
        if not isinstance(pr, dict) or not pr.get("isDraft"):
            continue
        head = str(pr.get("headRefName") or "")
        title = str(pr.get("title") or "Untitled PR")
        status, risk, detail = _classify_draft_pr(title=title, head=head)
        number = pr.get("number")
        items.append(
            _queue_item(
                status=status,
                source="github_prs",
                title=f"#{number} {title}",
                detail=detail,
                owner_action="review this",
                risk=risk,
                evidence=", ".join(sorted(label_names(pr))) or "draft",
                recommended_command=f"gh pr view {number} --repo {repo}",
                url=pr.get("url") if isinstance(pr.get("url"), str) else None,
            )
        )
    return items, "ok"


def _classify_draft_pr(*, title: str, head: str) -> tuple[str, str, str]:
    text = f"{head} {title}".lower()
    current_terms = ("automation", "system brief", "tenn-system-brief", "[experiment]")
    if head.startswith("control-plane/") or any(term in text for term in current_terms):
        return "draft_pr", "medium", f"Draft PR head: {head}"
    return "stale_draft_pr", "low", f"Older draft PR head: {head}"


def collect_experiment_branch_items(repo_root: Path, runner: Runner = run_command) -> tuple[list[BriefItem], str]:
    result = runner(["git", "branch", "--list", "experiment/*", "--format=%(refname:short)"], repo_root)
    if result.returncode != 0:
        return [
            _queue_item(
                status="DATA_MISSING",
                source="experiment_branches",
                title="Experiment branches could not be listed",
                detail=(result.stderr or result.stdout or "git branch failed").strip(),
                owner_action="none",
                risk="low",
                evidence="git branch --list experiment/*",
                recommended_command="git branch --list 'experiment/*' --format='%(refname:short)'",
            )
        ], "DATA_MISSING"
    items = [
        _queue_item(
            status="parked_experiment",
            source="experiment_branches",
            title=branch,
            detail="Local high-risk experiment branch needs review, parking, or explicit verifier routing.",
            owner_action="review this",
            risk="high",
            evidence=branch,
            recommended_command=f"git show --stat --oneline {branch}",
        )
        for branch in result.stdout.splitlines()
        if branch.strip()
    ]
    return items, "ok"


def build_brief(
    *,
    repo_root: Path,
    automation_root: Path,
    repo: str,
    issue_limit: int,
    pr_limit: int,
    recent_report_limit: int,
    log_limit: int,
    runner: Runner = run_command,
) -> Brief:
    sources: dict[str, str] = {}
    item_groups: list[list[BriefItem]] = []

    repo_state = collect_repo_state(repo_root, runner)
    collectors: list[tuple[str, Callable[[], tuple[list[BriefItem], str]]]] = [
        ("candidate_state", lambda: collect_candidate_items(automation_root)),
        ("report_markers", lambda: collect_report_marker_items(repo_root, recent_report_limit)),
        ("automation_reports", lambda: collect_automation_report_items(automation_root, recent_report_limit)),
        ("token_usage", lambda: collect_token_items(automation_root, log_limit)),
        ("experiment_branches", lambda: collect_experiment_branch_items(repo_root, runner)),
        ("github_prs", lambda: collect_github_pr_items(repo, pr_limit, runner)),
        ("github_issues", lambda: collect_github_issue_items(repo, issue_limit, runner)),
    ]
    for name, collect in collectors:
        items, status = collect()
        sources[name] = status
        item_groups.append(items)

    items = [item for group in item_groups for item in group]
    items.sort(key=lambda item: (item.priority, SOURCE_PRIORITY.get(item.source, 50), item.title))
    return Brief(repo_state=repo_state, items=items, sources=sources)


def format_brief(brief: Brief, max_items: int) -> str:
    state = brief.repo_state
    status_text = "dirty" if state.dirty else "clean"
    lines = [
        "Tenn system brief (read-only)",
        f"Repo: {state.repo_root}",
        f"Branch: {state.branch} @ {state.head} ({status_text})",
        "",
    ]
    if brief.items:
        first = brief.items[0]
        lines.extend(
            [
                f"I found {len(brief.items)} queue item(s). Recommended first:",
                f"- [{first.status}] {first.title}",
                f"  Source: {first.source}",
                f"  Why: {first.detail}",
                f"  Owner action: {first.owner_action}",
                f"  Command: {first.recommended_command}",
                "",
                "Top queue:",
            ]
        )
        for index, item in enumerate(brief.items[:max_items], 1):
            lines.append(
                f"{index}. [{item.status}] {item.title} "
                f"({item.source}; action: {item.owner_action})"
            )
        lines.extend(
            [
                "",
                "No writes were performed.",
                "Use explicit approval language such as `review this`, `approve safe fix`, "
                "`create draft PR`, `start high-risk experiment`, `park it`, or `defer 30 days`.",
            ]
        )
    else:
        lines.extend(
            [
                "No queue items were found from the scanned sources.",
                "No writes were performed.",
            ]
        )

    missing = sorted(name for name, status in brief.sources.items() if status == "DATA_MISSING")
    if missing:
        lines.extend(["", f"DATA_MISSING sources: {', '.join(missing)}"])
    return "\n".join(lines)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=Path.cwd())
    parser.add_argument("--automation-root", type=Path, default=Path.home() / ".codex" / "automations" / "tenn")
    parser.add_argument("--repo", default="0rl4nd0l/tenn")
    parser.add_argument("--issue-limit", type=int, default=50)
    parser.add_argument("--pr-limit", type=int, default=30)
    parser.add_argument("--recent-report-limit", type=int, default=10)
    parser.add_argument("--log-limit", type=int, default=20)
    parser.add_argument("--max-items", type=int, default=8)
    parser.add_argument("--json", action="store_true")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    brief = build_brief(
        repo_root=args.repo_root.resolve(),
        automation_root=args.automation_root.expanduser().resolve(),
        repo=args.repo,
        issue_limit=args.issue_limit,
        pr_limit=args.pr_limit,
        recent_report_limit=args.recent_report_limit,
        log_limit=args.log_limit,
    )
    if args.json:
        print(json.dumps(brief.to_dict(), indent=2, sort_keys=True))
    else:
        print(format_brief(brief, args.max_items))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
