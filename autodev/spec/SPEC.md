# SPEC

## Scope
- Provide a safe autonomous development loop for incremental repository work.
- Accept user-authored milestones and tasks from markdown files.
- Support deterministic task discovery that appends candidate tasks to `TASKS.md`.
- Execute deterministic gates (lint, unit tests, evals) before any PR handoff.
- Produce durable run and daily reports for auditability.

## Invariants
- Never commit directly to `main` or `master`.
- Work only on `agent/YYYY-MM-DD/<task_slug>` branches.
- Do not mark milestones done unless all required gates and thresholds pass.
- Log every executed command with stdout, stderr, exit code, and duration.
- Default to no network access in runners.
- Block dangerous commands outside an explicit allowlist.
- Task discovery may only write `autodev/spec/TASKS.md`; it must not edit source files.

## Inputs
- `autodev/spec/MILESTONES.md`
- `autodev/spec/TASKS.md`
- Environment variables prefixed with `AUTODEV_`
- Optional `autodev/autodev.yaml`

## Outputs
- Run report directory under `autodev/reports/runs/<run_id>/`
- Daily summary file under `autodev/reports/daily/YYYY-MM-DD.md`
- Eval artifact `autodev/evals/results.json`
- PR handoff artifact (GitHub PR URL or local patch instructions)

## Runtime Flow
1. Optionally discover tasks (when `AUTODEV_ENABLE_TASK_DISCOVERY=1`).
2. Select next incomplete task from `TASKS.md`.
3. Run selected worker (for example `local_patch` or `llm_patch`).
4. Run debate checks (pre-change and post-change) when enabled.
5. Run gates in milestone order (`ruff`, `pytest`, `eval` by default).
6. Evaluate regression guard against baseline metrics.
7. Produce run report and next-action decision.

## Control Interface
Supported control commands:
- `python -m autodev.runtime.control run-once`
- `python -m autodev.runtime.control status`
- `python -m autodev.runtime.control latest-report`
- `python -m autodev.runtime.control list-runs`
- `python -m autodev.runtime.control tail --file <report|worker|gates|commands>`
- `python -m autodev.runtime.control discover`

## Data Schema

### Task line schema (`TASKS.md`)
Each non-comment line uses pipe-delimited fields:

`- [ ] <task_id> | milestone:<milestone_id> | slug:<task_slug> | title:<title>`

Status markers:
- `[ ]` pending
- `[x]` complete

### Milestone schema (`MILESTONES.md`)
Each milestone block must include:
- `id: <milestone_id>`
- `dod: <description>`
- `commands: <comma-delimited gate ids>`
- `required_artifacts: <comma-delimited paths>`
- `thresholds: <metric>=<value>[,<metric>=<value>]`

Example:
- `thresholds: demo_pass_rate=1.0`

### Eval results schema (`autodev/evals/results.json`)
```json
{
  "metrics": {
    "demo_pass_rate": 1.0
  },
  "artifacts": [
    "autodev/evals/results.json"
  ]
}
```

## Discovery Rules
Current deterministic task discovery checks include:
- `TODO` and `FIXME` comments in Python files.
- Large files (`> 800` lines).
- Large functions (`> 150` lines).
- Potentially slow functions (nested loops / high iteration-node count).
- Missing tests for modules under `autodev/`.
- Missing function docstrings.
- Dead imports (basic static usage check).

## Config Flags (Selected)
- `AUTODEV_WORKER` (`local_patch` default, `llm_patch` optional).
- `AUTODEV_ENABLE_TASK_DISCOVERY` (`0` default, `1` enables pre-run discovery).
- `AUTODEV_MAX_RETRIES`
- `AUTODEV_USE_DOCKER`
- `AUTODEV_ALLOW_NETWORK`
- `AUTODEV_ENABLE_DEBATE`

## Non-goals
- Autonomous merge into protected branches.
- Automatic dependency installation.
- OpenClaw-specific scheduler format generation.
- Multi-agent parallel coding orchestration by default.
