# Control Plane Inventory

## Repo-Backed Skills

Visible repo-backed skills found:

```text
.agents/skills/codex-worker-bridge/SKILL.md
.agents/skills/tenn-explain/SKILL.md
.agents/skills/tenn-financial-metric-extraction/SKILL.md
.agents/skills/tenn-fix/SKILL.md
.agents/skills/tenn-git-guard/SKILL.md
.agents/skills/tenn-goal-report/SKILL.md
.agents/skills/tenn-handoff/SKILL.md
.agents/skills/tenn-improve-codebase-architecture/SKILL.md
.agents/skills/tenn-issue/SKILL.md
.agents/skills/tenn-review-board/SKILL.md
```

Count: 10.

## Control-Plane Scripts Reviewed

| Script | Classification | Notes |
| --- | --- | --- |
| `scripts/agent_job_contract.py` | IMPLEMENTED | Task-card validation, allowed-diff checks, report-artifact checks. |
| `scripts/agent_job_registry.py` | IMPLEMENTED | Shared active-job registry with read-only listing and mutable claim/heartbeat/release commands. |
| `scripts/agent_task_ledger.py` | PARTIAL | Live ledger validates; stale PR #380 state found. |
| `scripts/agent_job_hook.py` | IMPLEMENTED | Codex Stop/BeforeTool hook wrapper for task-card, registry, and diff checks. |
| `scripts/opencode_worker_bridge.py` | IMPLEMENTED | OpenCode probe/run/validate-result/summarize/ledger-entry bridge. |
| `scripts/check_agent_hooks.py` | PARTIAL | Reports stale/missing configured hooks path in this worktree. |
| `scripts/check_runtime_functionality_proof_docs.py` | IMPLEMENTED | Verifies Runtime Functionality Proof docs fields. |
| `scripts/sync_codex_skills.sh` | IMPLEMENTED | Dry-run by default; host mutation only with `--apply`. |
| `scripts/auto_progress.py` | IMPLEMENTED | Dry-run backend for issue/next-action analysis; not a default visible command. |

## Templates Reviewed

```text
docs/dev_flow/templates/BOARD.md
docs/dev_flow/templates/BOARD_DECISION.json
docs/dev_flow/templates/COUNTER_LINEAGE.md
docs/dev_flow/templates/DECISIONS.md
docs/dev_flow/templates/DOCS_IMPACT.md
docs/dev_flow/templates/EXPLAIN.md
docs/dev_flow/templates/FRAME.md
docs/dev_flow/templates/HANDOFF.md
docs/dev_flow/templates/HANDOFF_NEXT_GOAL.md
docs/dev_flow/templates/ISSUE.md
docs/dev_flow/templates/MILESTONES.md
docs/dev_flow/templates/MODEL_ROUTING.md
docs/dev_flow/templates/NEXT_GOAL.md
docs/dev_flow/templates/OPENCODE_WORKER_META.json
docs/dev_flow/templates/OPERATOR_NOTES.md
docs/dev_flow/templates/PR_REVIEW.md
docs/dev_flow/templates/STATE.md
docs/dev_flow/templates/TASK_LEDGER_ENTRY.json
docs/dev_flow/templates/TASK_LEDGER_SUMMARY.md
docs/dev_flow/templates/WORKER_RESULT.md
docs/dev_flow/templates/WORKER_TASK.md
```

## Codex Hook And Config Inventory

Repo files:

```text
.codex/config.toml
.codex/hooks.json
.codex/skills/cockpit-flag-orchestrator/SKILL.md
```

Findings:

- `.codex/config.toml` enables hooks with `[features] hooks = true`.
- `.codex/hooks.json` parses as JSON.
- `.codex/hooks.json` configures a Stop hook that calls `scripts/agent_job_hook.py`.
- `.codex/hooks.json` also configures a conditional graphify PreToolUse message.
- `.codex/skills/cockpit-flag-orchestrator/SKILL.md` is legacy/custom and should not be a default Orlando workflow.

## Host-Only Goal Evidence

Host-only commands found:

```text
/home/l4nd0/.local/bin/codex-goal
/home/l4nd0/.local/bin/codex-goal-monitor
/home/l4nd0/.local/bin/codex-goal-handoff
```

`codex-goal-monitor --help` worked. `codex-goal-monitor --current --json` returned an empty array for this thread.

No repo-backed `/goal monitor` implementation was found.
