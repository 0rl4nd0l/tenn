#!/usr/bin/env python3
"""Run Tenn audit-only Codex automations with stable logs and reports."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Callable


AUTOMATION_WORKTREE = Path(os.environ.get("TENN_CODEX_AUTOMATION_WORKTREE", "/home/l4nd0/tenn-codex-automations-v1-20260516"))
TARGET_WORKTREE = Path(os.environ.get("TENN_CODEX_AUTOMATION_TARGET_WORKTREE", "/home/l4nd0/tenn"))
OUTPUT_ROOT = Path(os.environ.get("TENN_CODEX_AUTOMATION_OUTPUT_ROOT", "~/.codex/automations/tenn")).expanduser()
CODEX_CANDIDATES = (
    Path(os.environ["TENN_CODEX_AUTOMATION_CODEX_BIN"])
    if os.environ.get("TENN_CODEX_AUTOMATION_CODEX_BIN")
    else None,
    Path("/home/l4nd0/.nvm/versions/node/v22.22.0/bin/codex"),
)
FAILURE_LOG_TAIL_CHARS = 4000


@dataclass(frozen=True)
class AutomationJob:
    name: str
    title: str
    prompt_builder: Callable[[], str]


@dataclass(frozen=True)
class HealthExpectation:
    name: str
    cadence: str
    report_glob: str
    log_glob: str
    max_age: timedelta | None
    required: bool = True


HEALTH_EXPECTATIONS = (
    HealthExpectation("automation-health", "daily 07:45", "*-automation-health.md", "*-automation-health.*", timedelta(hours=26)),
    HealthExpectation("repo-hygiene", "daily 08:00", "*-repo-hygiene.md", "*-repo-hygiene.jsonl", timedelta(hours=26)),
    HealthExpectation(
        "extraction-regression",
        "daily 08:30",
        "*-extraction-regression.md",
        "*-extraction-regression.jsonl",
        timedelta(hours=26),
    ),
    HealthExpectation("bug-regression", "daily 09:00", "*-bug-regression.md", "*-bug-regression.jsonl", timedelta(hours=26)),
    HealthExpectation(
        "daily-closeout",
        "daily 20:30",
        "*-daily-closeout.md",
        "*-daily-closeout.jsonl",
        timedelta(hours=26),
    ),
    HealthExpectation("doc-drift", "Mon/Wed/Fri 12:00", "*-doc-drift.md", "*-doc-drift.jsonl", timedelta(days=4), required=False),
    HealthExpectation(
        "future-opportunities",
        "Tue 15:00",
        "*-future-opportunities.md",
        "*-future-opportunities.jsonl",
        timedelta(days=8),
        required=False,
    ),
    HealthExpectation("memory-drift", "Fri 11:00", "*-memory-drift.md", "*-memory-drift.jsonl", timedelta(days=8), required=False),
)


def _base_prompt(title: str) -> str:
    return f"""# Tenn Automated Codex Audit: {title}

You are running as an automated Tenn Codex audit job.

Hard constraints:
- AUDIT ONLY.
- Do not edit files.
- Do not commit, stash, reset, clean, move, delete, archive, or checkpoint anything.
- Do not run migrations.
- Do not write to DBs, Qdrant, news DBs, company memory, user memory, or production data.
- Treat production_data_access as false.
- Use only current-turn command evidence.
- Mark unsupported claims as DATA_MISSING.
- Prefer exact paths, branch names, HEAD SHAs, commands run, and concise evidence.
- If a command would mutate state, do not run it.

Primary worktree to inspect: {TARGET_WORKTREE}
Automation worktree: {AUTOMATION_WORKTREE}
Output expected: report plus suggested task-card candidates where useful.
"""


def _repo_hygiene_prompt() -> str:
    return _base_prompt("Daily Repo Hygiene / Collision Scanner") + """
Purpose:
Protect Tenn from worktree/branch/task-card/report/registry collisions before new agent work starts.

Inspect:
- git branch for the primary worktree
- git HEAD
- git status --short --untracked-files=all
- git worktree list
- recent commits
- docs/agent_tasks/
- reports/agent_jobs/
- python3 scripts/agent_job_registry.py list-active if available
- unreviewed reports
- stale task cards
- untracked or unrelated files

Output exactly these sections:

Confirmed:
- Current branch:
- Current HEAD:
- Clean/dirty status:
- Active registry jobs:
- Unreviewed reports:
- Stale task cards:

Dirty work by lane:
- Financial Truth:
- Evaluation:
- Provenance:
- Query Orchestration:
- Memory:
- Reporting:

Collision risk:
- LOW / MEDIUM / HIGH

Recommended next safe step:
- ...

Suggested task-card candidates:
- ...

Do not fix anything.
"""


def _extraction_regression_prompt() -> str:
    return _base_prompt("Extraction Regression Scout") + """
Purpose:
Watch for risky changes around Tenn metric extraction, parser routing, gold labels, evaluator scoring, fallback behavior, and canonical truth assumptions.

Scan changed/recently touched files and reports around:
- financial-engine_v2/backend/**extraction**
- financial-engine_v2/backend/**docling**
- financial-engine_v2/backend/**metric**
- financial-engine_v2/backend/**gold**
- financial-engine_v2/backend/**evaluator**
- scripts/run_*extraction*
- reports/extraction*
- reports/agent_jobs/*extraction*
- docs/agent_tasks/*extraction*

Also inspect task/report claims mentioning:
- canonical10
- required_metrics
- confirmed_metric_coverage
- Docling
- PyMuPDF
- parser routing
- fallback
- gold labels
- runtime :8002

For every finding, output:

Finding:
- <what changed or appears risky>

Risk type:
- parser routing / fallback behavior / prompt change / gold label change / evaluator scoring / canonical truth write / runtime drift / unsupported production coverage claim

Evidence:
- file/report/task card path
- commit if available
- exact claim or changed surface

Classification:
- Confirmed / Inferred / Speculative / DATA_MISSING

Recommended action:
- no action / GPT review / audit-only Codex task / block implementation until reviewed

Do not run broad extraction jobs, change parser routing, edit labels, write canonical truth, improve prompts, or promote comparator outputs.
"""


def _memory_drift_prompt() -> str:
    return _base_prompt("Project Memory Drift Scanner") + """
Purpose:
Check whether GPT-facing Project Memory sources are stale, fragmented, duplicate, or contradictory. Do not edit memory.

Compare where present:
- TENN_SOURCE_INDEX_ACTIVE_MEMORY_MAP.md
- TENN_PROMPT_PROCESS_RULES.md
- TENN_LESSONS_LEARNED_LEDGER.md
- TENN_AGENT_CONTROL_PROTOCOL.md
- TENN_REPO_GITHUB_CODEX_AUDIT_PROTOCOL.md
- TENN_FAILURE_PATTERN_REGRESSION_SEED_LEDGER.md
- TENN_PROJECT_MEMORY_CATEGORY_TEMPLATES.md
- current consolidated Project Memory export
- recent /save candidates
- recent reports/agent_jobs/

If these artifacts are absent from the inspected worktree, report DATA_MISSING with the exact search paths and commands.

Output:

Memory health:
- OK / WATCH / SPLIT

Confirmed stale items:
- ...

Possible stale items:
- ...

Recommended consolidation:
- target artifact
- save class
- replace/archive recommendation

Do not automatically save:
- list of items requiring GPT/user review

Do not rewrite Project Memory, edit ChatGPT Project sources, treat raw zip archives as active truth, or merge candidates without review.
"""


def _automation_health_prompt() -> str:
    return _base_prompt("Automation Health Monitor") + """
Purpose:
Check whether Tenn Codex automations are observable, scheduled, and producing reports.

Inspect:
- systemctl --user list-timers 'tenn-codex-*' --all
- systemctl --user --failed
- systemctl --user status for tenn-codex services where useful
- latest files under ~/.codex/automations/tenn/logs/
- latest files under ~/.codex/automations/tenn/reports/
- latest files under ~/.codex/automations/tenn/prompts/
- report output root size
- stale or missing reports relative to expected timer cadence
- whether the codex CLI path used by scripts/codex_automation_runner.py exists

Output:

Confirmed:
- Timers:
- Last/next scheduled runs:
- Latest reports:
- Failed services:
- Output root size:
- Codex binary:

Inferred:
- ...

Speculative:
- ...

DATA_MISSING:
- ...

Primary lane:
- Query Orchestration

Collision risk:
- LOW / MEDIUM / HIGH

Suggested task card:
- ...

Do not touch:
- systemd unit files
- timer state
- logs/reports other than this run's report
- product code
- DBs/Qdrant/news/company-memory/runtime config

Next safe step:
- ...
"""


def _bug_regression_prompt() -> str:
    return _base_prompt("Bug / Regression Finder") + """
Purpose:
Find likely Tenn bugs/regressions and produce structured bug-registry candidate entries. Audit-only first: do not edit docs/dev/bug_registry.md yet.

Inspect:
- recent commits
- git diff against an appropriate main/preserve baseline if discoverable
- test failures in reports
- TODO/FIXME/HACK comments
- known failure signatures
- unreviewed Codex reports
- route/API mismatches
- error handling gaps
- silent fallbacks
- source-label overclaiming
- extraction/evaluator drift
- docs/dev/bug_registry.md if it exists, for dedupe only

For each candidate, output this exact structure:

## BUG-YYYYMMDD-001 - <short title>

Status:
- open / investigating / fixed / rejected / duplicate

Primary lane:
- Financial Truth / Evaluation / Provenance / Query Orchestration / Memory / Reporting

Severity:
- critical / high / medium / low

Evidence:
- file paths:
- reports:
- tests:
- logs:

Observed behavior:
-

Expected behavior:
-

Blast radius:
- isolated / likely class-wide / unknown

Recommended next step:
- audit-only / safe extension / blocked / no action

Suggested task card:
- docs/agent_tasks/<job_id>.md

Notes:
-

Classification:
- Confirmed / Inferred / Speculative / DATA_MISSING

Do not fix bugs. Do not edit docs/dev/bug_registry.md. Do not run broad tests unless already available reports are insufficient and the command is read-only.
"""


def _daily_closeout_prompt() -> str:
    return _base_prompt("Daily Closeout / Lock-Up Audit") + """
Purpose:
Produce an end-of-day operating closeout for Tenn. Summarize what is safe,
what remains blocked, and the next best operator prompt without mutating repo,
runtime, GitHub, data stores, or systemd state.

Inspect:
- git branch, HEAD, and dirty status for the primary worktree
- git worktree list
- open local task cards under docs/agent_tasks/
- latest reports under reports/agent_jobs/
- latest automation reports, logs, and prompts under ~/.codex/automations/tenn/
- installed tenn-codex user timers and failed user units
- open PRs and issues only if gh auth is available and the read is cheap
- merge parking registry if present
- AGENTS.md/CLAUDE.md instruction drift only when directly relevant

Output exactly these sections:

Lane:
- Query Orchestration

Closeout status:
- READY_FOR_NEXT_OPERATOR / WATCH / BLOCKED

Confirmed today:
- <current-turn evidence only>

Open P0/P1 blockers:
- <blocker, evidence, suggested owner or task card>

Dirty or collision risks:
- <paths, branches, worktrees, active jobs, DATA_MISSING where needed>

Automation health:
- <timers, reports, failed units, stale or missing outputs>

PR / issue queue:
- <only high-signal items with current evidence, or DATA_MISSING>

Unsafe actions avoided:
- <mutating commands not run>

Next recommended prompt:
- <one concrete prompt for the next session>

Do not:
- edit files
- create, update, comment on, close, or reopen GitHub issues or PRs
- commit, merge, rebase, stash, reset, clean, delete, prune, park, unpark, or checkpoint branches
- install, enable, start, stop, restart, reload, or edit live systemd units
- write DBs, Qdrant, Redis, news stores, company memory, market memory, user thesis memory, source PDFs, gold labels, canonical financial truth, model config, GPU config, or runtime state
- run broad extraction, backfill, ingestion, migration, or dependency-install commands
"""


def _doc_drift_prompt() -> str:
    return _base_prompt("Documentation Drift Updater") + """
Purpose:
Find docs that appear stale relative to current code, reports, task cards, commits, scripts, and automation state. Proposal-only: do not edit docs.

Inspect:
- README.md
- docs/setup/
- docs/architecture/
- docs/entrypoints.md
- docs/dev/
- AGENTS.md
- CLAUDE.md
- .codex/
- recent commits
- reports/agent_jobs/
- scripts/
- systemd/user/

Look for:
- commands that no longer exist
- wrong ports
- wrong worktree paths
- stale runtime descriptions
- old task-card workflow
- docs referring to HDD worktree where NVMe/automation path is now relevant
- docs saying manual process where automation now exists
- missing documentation for new systemd timers

Output:

Confirmed:
- <doc drift with evidence>

Inferred:
- <possible drift with evidence>

Speculative:
- <uncertain drift>

DATA_MISSING:
- <exact evidence needed>

Primary lane:
- Query Orchestration / Reporting / Evaluation / Memory / Financial Truth / Provenance

Collision risk:
- LOW / MEDIUM / HIGH

Suggested task card:
- docs/agent_tasks/<job_id>.md

Do not touch:
- financial-engine_v2/**
- cockpit-ui/**
- scripts/**
- runtime config
- DBs
- Qdrant
- memory stores

Next safe step:
- proposal-only / docs safe extension / blocked / no action
"""


def _future_opportunities_prompt() -> str:
    return _base_prompt("Future Upgrade / Opportunity Scout") + """
Purpose:
Find small, lane-scoped future improvement candidates from repeated friction, reports, commits, and manual pain points. Proposal-only: do not edit docs/dev/future_opportunities.md yet.

Inspect:
- recent reports/agent_jobs/
- recent commits
- docs/dev/bug_registry.md if present
- automation reports
- repeated dirty-work collisions
- slow or repeated commands
- missing eval coverage
- missing UI route checks
- weak source labels
- untracked user pain points
- small tools that would reduce future work

Good examples:
- Add route-level degraded-runtime smoke fixture for /api/cockpit/chat.
- Add systemd timer status tile to Operations tab.
- Add bug registry reader to repo hygiene scanner.
- Add extraction report summarizer for canonical10/confirmed_metric_coverage separation.

Bad examples:
- Refactor all extraction.
- Add autonomous trading agent.
- Replace Docling.
- Rebuild Cockpit.

For each opportunity, output:

## <Opportunity>

Status:
- idea / research candidate / audit candidate / deferred / rejected / promoted

Primary lane:
-

Supporting lanes:
-

Value hypothesis:
-

Evidence:
-

Risks:
-

Prerequisites:
-

Suggested first safe step:
-

Do not do yet:
-

Classification:
- Confirmed / Inferred / Speculative / DATA_MISSING

Do not create broad "do everything" tasks. Do not edit docs/dev/future_opportunities.md.
"""


JOBS: dict[str, AutomationJob] = {
    "automation-health": AutomationJob("automation-health", "Automation Health Monitor", _automation_health_prompt),
    "bug-regression": AutomationJob("bug-regression", "Bug / Regression Finder", _bug_regression_prompt),
    "daily-closeout": AutomationJob("daily-closeout", "Daily Closeout / Lock-Up Audit", _daily_closeout_prompt),
    "doc-drift": AutomationJob("doc-drift", "Documentation Drift Updater", _doc_drift_prompt),
    "repo-hygiene": AutomationJob("repo-hygiene", "Daily Repo Hygiene / Collision Scanner", _repo_hygiene_prompt),
    "extraction-regression": AutomationJob("extraction-regression", "Extraction Regression Scout", _extraction_regression_prompt),
    "future-opportunities": AutomationJob("future-opportunities", "Future Upgrade / Opportunity Scout", _future_opportunities_prompt),
    "memory-drift": AutomationJob("memory-drift", "Project Memory Drift Scanner", _memory_drift_prompt),
}


def _timestamp() -> str:
    return datetime.now().astimezone().strftime("%Y%m%dT%H%M%S%z")


def _ensure_dirs() -> None:
    for child in ("logs", "reports", "prompts"):
        (OUTPUT_ROOT / child).mkdir(parents=True, exist_ok=True)


def _write_prompt(job: AutomationJob, timestamp: str, prompt: str) -> Path:
    prompt_path = OUTPUT_ROOT / "prompts" / f"{timestamp}-{job.name}.md"
    prompt_path.write_text(prompt, encoding="utf-8")
    return prompt_path


def _command(job: AutomationJob, prompt_path: Path, timestamp: str) -> list[str]:
    codex_path = next((candidate for candidate in CODEX_CANDIDATES if candidate is not None and candidate.exists()), None)
    codex = str(codex_path) if codex_path is not None else shutil.which("codex")
    if not codex:
        raise RuntimeError("codex CLI not found on PATH")

    return [
        codex,
        "exec",
        "--cd",
        str(AUTOMATION_WORKTREE),
        "--sandbox",
        "read-only",
        "--json",
        "--output-last-message",
        str(OUTPUT_ROOT / "reports" / f"{timestamp}-{job.name}.md"),
        "-",
    ]


def _run_text_command(args: list[str]) -> tuple[int, str]:
    completed = subprocess.run(args, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, check=False)
    return completed.returncode, completed.stdout.strip()


def _log_tail(log_path: Path, *, limit: int = FAILURE_LOG_TAIL_CHARS) -> str:
    if not log_path.exists():
        return "DATA_MISSING: log file was not created"
    text = log_path.read_text(encoding="utf-8", errors="replace").strip()
    if not text:
        return "DATA_MISSING: log file is empty"
    return text[-limit:]


def _write_failure_report(
    *,
    job: AutomationJob,
    timestamp: str,
    report_path: Path,
    log_path: Path,
    returncode: int,
) -> bool:
    if report_path.exists() and report_path.stat().st_size > 0:
        return False

    report = f"""# Tenn Automated Codex Audit Failure: {job.title}

Status: BROKEN
Job: {job.name}
Timestamp: {timestamp}
Automation worktree: {AUTOMATION_WORKTREE}
Target worktree: {TARGET_WORKTREE}
Report path: {report_path}
Log path: {log_path}
Return code: {returncode}

## Summary

The Codex child process exited non-zero before producing the expected final
report through `--output-last-message`. This file was generated by
`scripts/codex_automation_runner.py` so automation health can classify the run
from report evidence instead of only a log file.

## Runtime Functionality Proof

| Field | Required evidence |
| --- | --- |
| intended output | Final audit report for `{job.name}`. |
| live output location | `{report_path}` and `{log_path}`. |
| pre-run max timestamp or count | DATA_MISSING |
| post-run max timestamp or count | Failure report generated by the runner after child exit. |
| rows/files inserted or updated after run start | One failure report if this file did not already exist. |
| readiness/gate status | Child process failed before normal report completion. |
| exact command/query used | `scripts/codex_automation_runner.py {job.name}` |
| result: WORKING / PARTIAL / BROKEN / DATA_MISSING | BROKEN |
| remaining blocker | Inspect the log tail and rerun only after the underlying Codex/connectivity/tooling issue is resolved. |

## Log Tail

```text
{_log_tail(log_path)}
```
"""
    report_path.write_text(report, encoding="utf-8")
    return True


def _latest_files(directory: Path, pattern: str, limit: int = 8) -> list[Path]:
    if not directory.exists():
        return []
    return sorted(directory.glob(pattern), key=lambda path: path.stat().st_mtime, reverse=True)[:limit]


def _latest_file(directory: Path, pattern: str) -> Path | None:
    matches = _latest_files(directory, pattern, limit=1)
    return matches[0] if matches else None


def _format_age(now: datetime, path: Path | None) -> str:
    if path is None:
        return "DATA_MISSING"
    age = now - datetime.fromtimestamp(path.stat().st_mtime, tz=now.tzinfo)
    total_minutes = max(0, int(age.total_seconds() // 60))
    hours, minutes = divmod(total_minutes, 60)
    if hours:
        return f"{hours}h {minutes}m"
    return f"{minutes}m"


def _report_declares_broken(path: Path | None) -> bool:
    if path is None:
        return False
    text = path.read_text(encoding="utf-8", errors="replace")[:4000]
    return "Status: BROKEN" in text or "result: WORKING / PARTIAL / BROKEN / DATA_MISSING | BROKEN" in text


def _health_rows(now: datetime) -> tuple[list[str], list[str], list[dict[str, object]]]:
    rows = [
        "| Job | Cadence | Latest report | Report age | Latest log | Status |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    issues: list[str] = []
    records: list[dict[str, object]] = []
    report_dir = OUTPUT_ROOT / "reports"
    log_dir = OUTPUT_ROOT / "logs"

    for expectation in HEALTH_EXPECTATIONS:
        latest_report = _latest_file(report_dir, expectation.report_glob)
        latest_log = _latest_file(log_dir, expectation.log_glob)
        latest_report_age = None
        stale = False
        incomplete = False
        broken_report = _report_declares_broken(latest_report)
        if latest_report is not None:
            report_mtime = datetime.fromtimestamp(latest_report.stat().st_mtime, tz=now.tzinfo)
            latest_report_age = now - report_mtime
            stale = expectation.max_age is not None and latest_report_age > expectation.max_age
            if latest_log is not None:
                log_mtime = datetime.fromtimestamp(latest_log.stat().st_mtime, tz=now.tzinfo)
                incomplete = log_mtime > report_mtime + timedelta(minutes=1)
        elif latest_log is not None:
            incomplete = True

        if latest_report is None:
            status = "INCOMPLETE_RUN" if incomplete else "MISSING_REPORT" if expectation.required else "not due or missing"
        elif broken_report:
            status = "BROKEN_REPORT"
        elif incomplete:
            status = "INCOMPLETE_RUN"
        elif stale:
            status = "STALE_REPORT"
        else:
            status = "ok"

        if status in {"MISSING_REPORT", "STALE_REPORT", "INCOMPLETE_RUN", "BROKEN_REPORT"}:
            issues.append(f"{expectation.name}: {status}")

        rows.append(
            "| {name} | {cadence} | {report} | {age} | {log} | {status} |".format(
                name=expectation.name,
                cadence=expectation.cadence,
                report=latest_report.name if latest_report else "DATA_MISSING",
                age=_format_age(now, latest_report),
                log=latest_log.name if latest_log else "DATA_MISSING",
                status=status,
            )
        )
        records.append(
            {
                "name": expectation.name,
                "cadence": expectation.cadence,
                "latest_report": str(latest_report) if latest_report else None,
                "latest_log": str(latest_log) if latest_log else None,
                "status": status,
                "report_age_seconds": int(latest_report_age.total_seconds()) if latest_report_age else None,
            }
        )
    return rows, issues, records


def _format_command(name: str, args: list[str]) -> tuple[str, dict[str, object]]:
    returncode, output = _run_text_command(args)
    block = [f"### {name}", "", f"`{' '.join(args)}`", "", f"Exit code: `{returncode}`", ""]
    if output:
        block.extend(["```text", output[:4000], "```", ""])
    else:
        block.append("No output.\n")
    return "\n".join(block), {"name": name, "args": args, "returncode": returncode, "output": output}


def _run_automation_health_native(dry_run: bool = False) -> int:
    _ensure_dirs()
    timestamp = _timestamp()
    report_path = OUTPUT_ROOT / "reports" / f"{timestamp}-automation-health.md"
    log_path = OUTPUT_ROOT / "logs" / f"{timestamp}-automation-health.json"

    codex_path = next((candidate for candidate in CODEX_CANDIDATES if candidate is not None and candidate.exists()), None)
    codex = str(codex_path) if codex_path is not None else shutil.which("codex")
    summary = {
        "job": "automation-health",
        "title": "Automation Health Monitor",
        "automation_worktree": str(AUTOMATION_WORKTREE),
        "target_worktree": str(TARGET_WORKTREE),
        "report_path": str(report_path),
        "log_path": str(log_path),
        "dry_run": dry_run,
        "native": True,
        "codex_binary": codex,
    }
    print(json.dumps(summary, indent=2, sort_keys=True))

    if dry_run:
        return 0

    command_blocks: list[str] = []
    command_logs: list[dict[str, object]] = []
    for name, args in (
        ("Timers", ["systemctl", "--user", "list-timers", "tenn-codex-*", "--all"]),
        ("Failed user units", ["systemctl", "--user", "--failed"]),
        ("Repo hygiene timer", ["systemctl", "--user", "status", "tenn-codex-repo-hygiene.timer", "--no-pager"]),
        ("Automation health timer", ["systemctl", "--user", "status", "tenn-codex-automation-health.timer", "--no-pager"]),
        ("Output root size", ["du", "-sh", str(OUTPUT_ROOT)]),
    ):
        block, log = _format_command(name, args)
        command_blocks.append(block)
        command_logs.append(log)

    branch_code, branch_output = _run_text_command(["git", "-C", str(AUTOMATION_WORKTREE), "branch", "--show-current"])
    branch = branch_output if branch_code == 0 and branch_output else "DATA_MISSING"
    reports = _latest_files(OUTPUT_ROOT / "reports", "*.md")
    logs = _latest_files(OUTPUT_ROOT / "logs", "*")
    prompts = _latest_files(OUTPUT_ROOT / "prompts", "*.md")
    health_rows, health_issues, health_records = _health_rows(datetime.now().astimezone())
    codex_status = "present" if codex else "missing"
    report = f"""Lane: Query Orchestration
Branch: {branch}
Worktree: {AUTOMATION_WORKTREE}
Execution mode: AUDIT MODE
Collision risk: LOW
Decision: audit only

Confirmed:
- Automation output root: `{OUTPUT_ROOT}`
- Codex binary: {codex_status}{f" at `{codex}`" if codex else ""}
- Latest reports: {", ".join(path.name for path in reports[:5]) if reports else "DATA_MISSING"}
- Latest logs: {", ".join(path.name for path in logs[:5]) if logs else "DATA_MISSING"}
- Latest prompts: {", ".join(path.name for path in prompts[:5]) if prompts else "DATA_MISSING"}

Inferred:
- Report freshness requires comparing the timer schedule below with the latest report names.

Speculative:
- None.

DATA_MISSING:
- Any service state command with a non-zero exit below needs host/user-bus follow-up.
- Missing expected reports: {", ".join(health_issues) if health_issues else "none"}

Primary lane:
- Query Orchestration

Collision risk:
- LOW

Suggested task card:
- Create one if a timer is failed, report freshness is missing after the expected cadence, or the Codex binary is missing.

Do not touch:
- Product code, runtime config, DBs, Qdrant, news stores, company memory, market memory, gold labels, canonical financial truth.

Next safe step:
- Review failed units and missing reports if any are shown below.

Command evidence:

{''.join(command_blocks)}
Expected report freshness:

{chr(10).join(health_rows)}
"""
    report_path.write_text(report, encoding="utf-8")
    log_path.write_text(
        json.dumps(
            {
                **summary,
                "commands": command_logs,
                "latest_reports": [str(path) for path in reports],
                "latest_logs": [str(path) for path in logs],
                "latest_prompts": [str(path) for path in prompts],
                "health_records": health_records,
                "health_issues": health_issues,
            },
            indent=2,
            sort_keys=True,
        ),
        encoding="utf-8",
    )
    return 0


def run_job(job_name: str, dry_run: bool = False) -> int:
    if job_name == "automation-health":
        return _run_automation_health_native(dry_run=dry_run)

    job = JOBS[job_name]
    _ensure_dirs()

    timestamp = _timestamp()
    prompt = job.prompt_builder()
    prompt_path = _write_prompt(job, timestamp, prompt)
    log_path = OUTPUT_ROOT / "logs" / f"{timestamp}-{job.name}.jsonl"
    report_path = OUTPUT_ROOT / "reports" / f"{timestamp}-{job.name}.md"
    cmd = _command(job, prompt_path, timestamp)

    summary = {
        "job": job.name,
        "title": job.title,
        "automation_worktree": str(AUTOMATION_WORKTREE),
        "target_worktree": str(TARGET_WORKTREE),
        "prompt_path": str(prompt_path),
        "log_path": str(log_path),
        "report_path": str(report_path),
        "dry_run": dry_run,
        "command": cmd[:-1] + ["<prompt-stdin>"],
    }
    print(json.dumps(summary, indent=2, sort_keys=True))

    if dry_run:
        return 0

    env = os.environ.copy()
    env.update(
        {
            "TENN_AUTOMATION_MODE": "audit_only",
            "TENN_AUTOMATION_PRODUCTION_DATA_ACCESS": "false",
            "TENN_AGENT_TASK_CARD": "",
        }
    )
    with prompt_path.open("r", encoding="utf-8") as prompt_in, log_path.open("w", encoding="utf-8") as log_out:
        completed = subprocess.run(
            cmd,
            stdin=prompt_in,
            stdout=log_out,
            stderr=subprocess.STDOUT,
            check=False,
            text=True,
            env=env,
        )
    if completed.returncode != 0:
        _write_failure_report(
            job=job,
            timestamp=timestamp,
            report_path=report_path,
            log_path=log_path,
            returncode=completed.returncode,
        )
    return completed.returncode


def list_jobs() -> int:
    print(json.dumps({name: {"title": job.title} for name, job in JOBS.items()}, indent=2, sort_keys=True))
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("job", choices=sorted(JOBS) + ["list"])
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)

    if args.job == "list":
        return list_jobs()
    return run_job(args.job, dry_run=args.dry_run)


if __name__ == "__main__":
    raise SystemExit(main())
