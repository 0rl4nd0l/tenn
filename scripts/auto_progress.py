#!/usr/bin/env python3
"""Read-only Tenn auto-progress planner.

This script is intentionally dry-run only. It reads GitHub issue/milestone
state, ranks candidate work, emits compact report artifacts, and drafts task
card packets under the selected output directory. It never writes GitHub,
commits, pushes, starts services, or edits product/runtime/data files.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any


def run_json(command: list[str]) -> Any:
    proc = subprocess.run(command, check=False, text=True, capture_output=True)
    if proc.returncode != 0:
        raise SystemExit(
            f"command failed ({proc.returncode}): {' '.join(command)}\n{proc.stderr}"
        )
    try:
        return json.loads(proc.stdout)
    except json.JSONDecodeError as exc:
        raise SystemExit(f"invalid JSON from {' '.join(command)}: {exc}") from exc


def labels(issue: dict[str, Any]) -> set[str]:
    return {label.get("name", "") for label in issue.get("labels", [])}


def label_value(names: set[str], prefix: str) -> str | None:
    for name in names:
        if name.startswith(prefix):
            return name[len(prefix) :]
    return None


def has_any(names: set[str], values: set[str]) -> bool:
    return bool(names.intersection(values))


def milestone_title(issue: dict[str, Any]) -> str:
    milestone = issue.get("milestone") or {}
    return milestone.get("title") or ""


@dataclass
class RankedIssue:
    issue: dict[str, Any]
    score: int
    reasons: list[str]
    cautions: list[str]


def score_issue(issue: dict[str, Any], milestone_filter: str | None) -> RankedIssue:
    names = labels(issue)
    score = 0
    reasons: list[str] = []
    cautions: list[str] = []

    if "state:ready" in names:
        score += 20
        reasons.append("ready")
    if "state:data-missing" in names:
        score -= 8
        cautions.append("data-missing")

    priority = label_value(names, "priority:")
    priority_scores = {"p0": 12, "p1": 8, "p2": 5, "p3": 2}
    if priority in priority_scores:
        score += priority_scores[priority]
        reasons.append(f"priority:{priority}")

    risk = label_value(names, "risk:")
    risk_scores = {"low": 15, "medium": 10, "high": -30}
    if risk in risk_scores:
        score += risk_scores[risk]
        if risk == "high":
            cautions.append("high-risk")
        else:
            reasons.append(f"risk:{risk}")

    if has_any(names, {"lane:repo-hygiene", "lane:evaluation"}):
        score += 10
        reasons.append("repo-hygiene/evaluation")
    if "type:control-plane" in names:
        score += 20
        reasons.append("control-plane")
    if "type:automation" in names:
        score += 4
        reasons.append("automation")
    if has_any(names, {"mode:audit", "mode:safe-extension"}):
        score += 10
        reasons.append("audit/safe-extension")

    if "lane:runtime" in names:
        score -= 15
        cautions.append("runtime-adjacent")
    if "lane:financial-truth" in names:
        score -= 25
        cautions.append("financial-truth-adjacent")
    if "lane:query-orchestration" in names:
        score -= 6
        cautions.append("product-adjacent")

    title_text = issue.get("title", "").lower()
    if "root-owned" in title_text or "cleanup" in title_text or "cache dirs" in title_text:
        score -= 30
        cautions.append("filesystem-cleanup-boundary")

    title = milestone_title(issue)
    if milestone_filter and title == milestone_filter:
        score += 10
        reasons.append(f"milestone:{milestone_filter}")

    if issue.get("number") == 291:
        score -= 25
        cautions.append("controller-issue")

    return RankedIssue(issue=issue, score=score, reasons=reasons, cautions=cautions)


def write_json(path: Path, payload: Any) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")


def write_text(path: Path, text: str) -> None:
    path.write_text(text.rstrip() + "\n")


def issue_table(rows: list[RankedIssue]) -> str:
    lines = [
        "| Rank | Issue | Score | Labels | Reasons | Cautions |",
        "| ---: | --- | ---: | --- | --- | --- |",
    ]
    for index, ranked in enumerate(rows, 1):
        issue = ranked.issue
        names = sorted(labels(issue))
        lines.append(
            "| {rank} | [#{num}]({url}) {title} | {score} | {labels} | {reasons} | {cautions} |".format(
                rank=index,
                num=issue["number"],
                url=issue["url"],
                title=issue["title"].replace("|", "\\|"),
                score=ranked.score,
                labels=", ".join(names),
                reasons=", ".join(ranked.reasons) or "-",
                cautions=", ".join(ranked.cautions) or "-",
            )
        )
    return "\n".join(lines)


def command_triage(args: argparse.Namespace) -> int:
    if not args.dry_run:
        raise SystemExit("triage-issues requires --dry-run")

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    issue_command = [
        "gh",
        "issue",
        "list",
        "--repo",
        args.repo,
        "--state",
        "open",
        "--limit",
        str(args.limit),
        "--json",
        "number,title,state,labels,milestone,updatedAt,url",
    ]
    for label in args.labels:
        issue_command.extend(["--label", label])

    issues = run_json(issue_command)
    milestones = run_json(
        [
            "gh",
            "api",
            f"repos/{args.repo}/milestones",
            "--paginate",
            "--jq",
            "[.[] | {number,title,state,open_issues,closed_issues,due_on,updated_at,description}]",
        ]
    )

    risk_allow = {value.strip() for value in args.risk.split(",") if value.strip()}
    ranked: list[RankedIssue] = []
    for issue in issues:
        names = labels(issue)
        risk = label_value(names, "risk:")
        if risk_allow and risk and risk not in risk_allow:
            continue
        if args.milestone and milestone_title(issue) not in {"", args.milestone}:
            continue
        ranked.append(score_issue(issue, args.milestone))

    ranked.sort(key=lambda item: (-item.score, item.issue["number"]))
    top = ranked[: args.max_candidates]

    write_json(output_dir / "ISSUES.json", issues)
    write_json(output_dir / "MILESTONES.json", milestones)
    write_json(
        output_dir / "TRIAGE_RESULT.json",
        [
            {
                "number": item.issue["number"],
                "title": item.issue["title"],
                "url": item.issue["url"],
                "score": item.score,
                "reasons": item.reasons,
                "cautions": item.cautions,
                "labels": sorted(labels(item.issue)),
                "milestone": milestone_title(item.issue),
            }
            for item in top
        ],
    )

    write_text(
        output_dir / "ISSUE_SCAN.md",
        "# Issue Scan\n\n"
        f"Repository: `{args.repo}`\n\n"
        f"Open issues fetched: `{len(issues)}`\n\n"
        f"Applied labels: `{', '.join(args.labels) or 'none'}`\n\n"
        f"Risk filter: `{args.risk}`\n\n"
        "The scan is read-only and uses GitHub issue JSON. Issue #291 is treated "
        "as the controlling workflow issue, not as the default execution target.",
    )
    write_text(
        output_dir / "MILESTONE_SCAN.md",
        "# Milestone Scan\n\n"
        + "\n".join(
            f"- #{milestone['number']} `{milestone['title']}`: "
            f"{milestone['open_issues']} open, {milestone['closed_issues']} closed"
            for milestone in milestones
        ),
    )
    write_text(
        output_dir / "CANDIDATE_RANKING.md",
        "# Candidate Ranking\n\n" + issue_table(top),
    )
    write_text(
        output_dir / "MANDATE_CLASSIFICATION.md",
        "# Mandate Classification\n\n"
        "| Mandate | Applies | Boundary |\n"
        "| --- | --- | --- |\n"
        "| `REPORT_AUTONOMY` | read-only scans, rankings, context packs, draft packets | stop before source/product/runtime/data/GitHub mutation |\n"
        "| `ISSUE_291_READONLY_PLANNER` | issue #291 planner and dry-run script | stop before execution |\n"
        "| `OWNER_APPROVAL_REQUIRED` | commits, pushes, GitHub writes, runtime/data/source changes | explicit owner approval only |",
    )
    return 0


def extract_required_task_card(body: str, issue_number: int) -> str:
    match = re.search(r"`(docs/agent_tasks/[^`]+\.md)`", body)
    if match:
        return match.group(1)
    return f"docs/agent_tasks/issue_{issue_number}_task_v1.md"


def command_issue_to_card(args: argparse.Namespace) -> int:
    if not args.dry_run:
        raise SystemExit("issue-to-card requires --dry-run")

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    issue = run_json(
        [
            "gh",
            "issue",
            "view",
            str(args.issue),
            "--repo",
            args.repo,
            "--json",
            "number,title,state,labels,milestone,updatedAt,url,body",
        ]
    )
    write_json(output_dir / f"ISSUE_{args.issue}.json", issue)

    names = labels(issue)
    task_card = extract_required_task_card(issue.get("body", ""), args.issue)
    report_dir = task_card.replace("docs/agent_tasks/", "reports/agent_jobs/").removesuffix(".md")
    report_dir += "/"

    write_text(
        output_dir / "CONTEXT_PACK.md",
        "# Context Pack\n\n"
        f"Issue: [#{issue['number']}]({issue['url']}) {issue['title']}\n\n"
        f"State: `{issue['state']}`\n\n"
        f"Labels: `{', '.join(sorted(names))}`\n\n"
        f"Milestone: `{milestone_title(issue) or 'none'}`\n\n"
        "Planner read: this is a report-first candidate. The dry-run packet "
        "must stop before artifact restoration, GitHub mutation, product code, "
        "runtime state, or extraction/data mutation.",
    )

    draft = f"""---
job_id: issue_{issue['number']}_dry_run_packet_v1
owner: Codex
lane: Evaluation
supporting_lanes:
  - Repo Hygiene
status: draft_only
approval_required: true
mutation_mode: audit_only
production_data_access: false
output_dir: {report_dir.rstrip('/')}
allowed_files:
  - {task_card}
  - {report_dir}README.md
  - {report_dir}EVIDENCE.md
  - {report_dir}CLASSIFICATION.md
  - {report_dir}APPROVAL_PACKET.md
  - {report_dir}DATA_MISSING.md
  - {report_dir}VALIDATION.md
timeout_seconds: 3600
---

# Issue {issue['number']} Dry-Run Task Card Packet

## Objective

Draft a report-only task-card candidate for issue #{issue['number']}:
`{issue['title']}`.

## Allowed Actions

- Refresh issue #{issue['number']} read-only.
- Inspect relevant report/control artifacts needed to classify the issue.
- Write only the task-card and report files listed in `allowed_files`.
- Stop before execution.

## Forbidden Actions

- Do not mutate product, runtime, extraction, data, prompt, source-PDF,
  gold-label, DB, Qdrant, news, memory, service, model/GPU, production-data, or
  live-system files.
- Do not mutate GitHub.
- Do not commit, push, merge, rebase, cherry-pick, reset, stash, clean, delete
  branches, or remove worktrees.

## Validation

- Validate this task card.
- Run read-only registry inspection.
- Run markdown whitespace checks.
- Run `git diff --check`.
- Record final status.
"""
    write_text(output_dir / f"DRAFT_TASK_CARD_ISSUE_{args.issue}.md", draft)
    write_text(
        output_dir / "PHASE3_APPROVAL_MANIFEST.md",
        "# Phase 3 Approval Manifest\n\n"
        "Default: no execution approved.\n\n"
        f"Recommended Group A: create and run the report-only issue #{issue['number']} "
        "classification task card from the draft packet. Stop before GitHub "
        "mutation, commits, product/runtime/data/extraction changes, service "
        "starts, or broad validation.",
    )
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Tenn auto-progress read-only planner")
    subparsers = parser.add_subparsers(dest="command", required=True)

    triage = subparsers.add_parser("triage-issues")
    triage.add_argument("--repo", default="0rl4nd0l/tenn")
    triage.add_argument("--milestone")
    triage.add_argument("--labels", action="append", default=[])
    triage.add_argument("--risk", default="low,medium")
    triage.add_argument("--max-candidates", type=int, default=10)
    triage.add_argument("--limit", type=int, default=100)
    triage.add_argument("--output-dir", required=True)
    triage.add_argument("--dry-run", action="store_true")
    triage.set_defaults(func=command_triage)

    issue_to_card = subparsers.add_parser("issue-to-card")
    issue_to_card.add_argument("--repo", default="0rl4nd0l/tenn")
    issue_to_card.add_argument("--issue", type=int, required=True)
    issue_to_card.add_argument("--output-dir", required=True)
    issue_to_card.add_argument("--dry-run", action="store_true")
    issue_to_card.set_defaults(func=command_issue_to_card)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
