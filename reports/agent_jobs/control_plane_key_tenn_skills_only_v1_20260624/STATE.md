# State

## Current State

- Worktree: `/home/l4nd0/tenn-key-tenn-skills-only-v1-20260624`
- Branch: `control-plane/key-tenn-skills-only-v1-20260624`
- Base: `origin/migration/clean-runtime-baseline-reconstruct-v1`
- Starting HEAD: `6a777b3d8cff7b250a189aea76e30fa3ec4388b4`
- Primary lane: `Reporting`
- Supporting lane: `Repo Hygiene`
- Task tier: `medium`
- Recommended model: `standard coding model`
- Actual model: `GPT-5 Codex`
- Worker model allowed: `no`
- Worker decision limit: `none`
- Escalation needed: `no`

## Implementation

- Kept the approved Tenn orchestration skills plus narrative/support entrypoints
  requested after the first trim: `caveman`, `zoom-out`,
  `tenn-improve-codebase-architecture`, `tenn-issue`, `tenn-goal-report`,
  `tenn-financial-metric-extraction`, and `codex-worker-bridge`.
- Removed the legacy/custom `.codex/skills/cockpit-flag-orchestrator` files.
- Updated the skill surface, registry, source map, operator guide, goal
  runbook, OpenCode runbook, open-work register, and control-plane status docs
  so active docs match the 12-skill `.agents` surface and empty `.codex/skills`
  visible surface.
- Preserved host-global skill roots unchanged.

## Guard And Ledger

- Portable guard decision: `pass`
- Path ownership: `VALID_TASK_WORKTREE`
- Registry read-only status: no active jobs
- Ledger status: live and committed sources validated
- Duplicate-work classification: no matching active work found

## Docs Impact

- docs_impact: `DOCS_UPDATED`
- docs_checked: `AGENTS.md`, `docs/README.md`,
  `docs/agents/skill-registry.md`, `docs/dev_flow/SKILLS_SURFACE.md`
- docs_changed: `docs/README.md`, `docs/agents/skill-registry.md`,
  `docs/dev_flow/SKILLS_SURFACE.md`,
  `docs/dev_flow/CODEX_OPERATOR_GUIDE.md`,
  `docs/dev_flow/CONTROL_PLANE_OPEN_WORK.md`,
  `docs/dev_flow/CONTROL_PLANE_STATUS.md`,
  `docs/dev_flow/GOAL_AND_MONITOR_RUNBOOK.md`,
  `docs/dev_flow/OPENCODE_WORKER_BRIDGE_RUNBOOK.md`
- docs_followup: `none`
- reason: skill visibility and routing behavior changed

## Runtime Functionality

Not applicable. This is docs/control-plane skill-surface work. No runtime,
daemon, ingestion, extraction, automation, collector, scheduler, service, or
pipeline functionality is claimed.

## Residual Risk

- Host picker/autocomplete visibility was not probed in this session.
- Host-global skills under `/home/l4nd0/.codex`, `/home/l4nd0/.agents`, and
  plugin caches are intentionally untouched.
- Merge/push was not completed: `git push --dry-run origin
  HEAD:refs/heads/migration/clean-runtime-baseline-reconstruct-v1` was blocked
  by the local pre-push hook because
  `financial-engine_v2/.venv/bin/ruff` and
  `financial-engine_v2/.venv/bin/pytest` are missing. The suggested bypass flag
  was not used.
