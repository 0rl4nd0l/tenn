# Inventory

## Canonical Repo Surface

Current origin base inspected:
`origin/migration/clean-runtime-baseline-reconstruct-v1` at
`227e1ce0d4e99c4a13ece8012a44adeba4585cdf`.

| Surface | Evidence | Classification | Recommendation |
| --- | --- | --- | --- |
| Root `AGENTS.md` | Present, current repo constitution. | `CORE_KEEP` | Keep short; route procedures to skills. |
| Nested `AGENTS.md` | `find . -name AGENTS.md` found only root. | `UNKNOWN_NEEDS_OWNER_DECISION` | No nested split needed unless a product subtree needs different rules. |
| `.agents/skills/tenn-auto-progress` | Present in origin and current repo. | `MERGE_INTO_NEW_WORKFLOW` | Use as `/issue` candidate-ranking engine. |
| `.agents/skills/tenn-financial-metric-extraction` | Present. | `OWNER_BOUNDARY` | Keep for Financial Truth only; not dev-flow core. |
| `.agents/skills/tenn-frame-design` | Present. | `MERGE_INTO_NEW_WORKFLOW` | Make default long-run frame template. |
| `.agents/skills/tenn-git-hygiene` | Present. | `MERGE_INTO_NEW_WORKFLOW` | Become `tenn-git-guard` backend. |
| `.agents/skills/tenn-goal-report` | Present. | `CORE_KEEP` | Keep as closeout/report state machine. |
| `.agents/skills/tenn-task-card-registry-safety` | Present. | `CORE_KEEP` | Keep as task-card and registry guard. |
| `.codex/config.toml` | Repo hooks enabled. | `CORE_KEEP` | Keep minimal. |
| `.codex/hooks.json` | Graphify pretool plus Stop task-card hook. | `CORE_KEEP` | Keep; fix path drift through Git guard. |
| `.codex/skills/cockpit-flag-orchestrator` | Repo legacy/custom skill. | `OWNER_BOUNDARY` | Do not fold into dev-flow reset. |
| `.claude/commands/*` | Many command docs mirror host skills. | `RENAME_OR_REHOME` | Treat as Claude reference, not canonical Tenn command set. |
| `.githooks/pre-commit` | Python staged-file Ruff gate. | `CORE_KEEP` | Keep as local Git hook. |
| `.githooks/pre-push` | Ruff, hook/tooling tests, markdown hygiene. | `CORE_KEEP` | Keep, but current file is dirty and owner-bound. |
| `scripts/agent_job_contract.py` | Validates cards, artifacts, diff scope. | `CORE_KEEP` | Make every command call it. |
| `scripts/agent_job_registry.py` | Shared active-job registry. | `CORE_KEEP` | Make every command call read-only list first. |
| `scripts/agent_job_hook.py` | Hook wrapper around card and registry checks. | `CORE_KEEP` | Keep as Stop/BeforeTool guard. |
| `scripts/auto_progress.py` | Present on origin, absent from this older branch working tree. | `MERGE_INTO_NEW_WORKFLOW` | Candidate-ranking engine inside `/issue`. |
| `docs/agents/*` | Skill registry, issue tracker, labels, domain docs. | `CORE_KEEP` | Keep as Tenn adapter layer for generic skills. |
| `docs/agent_registry/merge_parking` | Merge parking registry. | `CORE_KEEP` | Feed Git guard branch/parking checks. |
| `docs/agent_tasks/**` | Large task-card corpus. | `CORE_KEEP` | Keep exact contract, but reduce manual operator burden. |
| `reports/agent_jobs/**` | Evidence/closeout corpus. | `CORE_KEEP` | Keep, but avoid report-only loops through action decisions. |

## Host/Global Surface

| Surface | Evidence | Classification | Recommendation |
| --- | --- | --- | --- |
| `~/.codex/config.toml` | Trusted projects, plugins, hooks, goals, memories. | `OWNER_BOUNDARY` | Read-only for repo commands; do not mutate from Tenn. |
| `~/.codex/hooks/goal_optimizer_pre_tool.py` | High-burn goal warning. | `CORE_KEEP` | Keep as host guard. |
| `~/.codex/hooks/pre_apply_patch.py` | Sensitive path warning. | `CORE_KEEP` | Keep as warning-only host guard. |
| `~/.codex/hooks/post_apply_patch.py` | Ruff/chmod/backend-test side effects. | `UNKNOWN_NEEDS_OWNER_DECISION` | Useful but can surprise Tenn report-only runs. |
| `~/.codex/hooks/stop_check.py` | Uncommitted-state warning. | `MERGE_INTO_NEW_WORKFLOW` | Align with Tenn `tenn-git-guard` messaging. |
| `~/.codex/rules/default.rules` | One path-specific allow rule. | `DEPRECATE` | Not a scalable Tenn rule surface. |
| `~/.codex/goals_1.sqlite` | `thread_goals` schema present. | `CORE_KEEP` | Read-only status source for `/goal` tooling. |

## GitHub Context

| Item | Status | Relevance |
| --- | --- | --- |
| Issue #78 | Open | Broad agent markdown and Codex repo docs refresh tracker. |
| Issue #291 | Open | Auto-progress controller issue and target workflow description. |
| Issue #234 | Open | Current report-first repo hygiene candidate used by auto-progress. |
| PR #300 | Merged | Read-only registry and control-plane refresh. |
| PR #302 | Merged | Added `tenn-frame-design`. |
| PR #303 | Merged | Added `tenn-git-hygiene`. |
| PR #320 | Merged | Formalized two-shot dev-flow autonomy. |
| PR #344 | Merged | Added auto-progress V2 read-only planner. |
| PR #345 | Merged | Fixed terminal Stop-hook loop after handoff. |
