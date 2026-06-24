---
job_id: control_plane_key_tenn_skills_only_v1_20260624
lane: Reporting
supporting_lanes:
  - Repo Hygiene
owner: Codex
approval_required: false
allow_unapproved_safe_extension: true
allow_audit_code_changes: true
timeout_seconds: 7200
output_dir: reports/agent_jobs/control_plane_key_tenn_skills_only_v1_20260624
mutation_mode: safe_extension
production_data_access: false
closeout_scope: control_plane_only
allowed_files:
  - docs/agent_tasks/control_plane_key_tenn_skills_only_v1_20260624.md
  - docs/README.md
  - docs/agents/skill-registry.md
  - docs/dev_flow/CODEX_OPERATOR_GUIDE.md
  - docs/dev_flow/CONTROL_PLANE_OPEN_WORK.md
  - docs/dev_flow/CONTROL_PLANE_STATUS.md
  - docs/dev_flow/GOAL_AND_MONITOR_RUNBOOK.md
  - docs/dev_flow/OPENCODE_WORKER_BRIDGE_RUNBOOK.md
  - docs/dev_flow/SKILLS_SURFACE.md
  - .agents/skills/caveman/SKILL.md
  - .agents/skills/codex-worker-bridge/SKILL.md
  - .agents/skills/tenn-financial-metric-extraction/SKILL.md
  - .agents/skills/tenn-goal-report/SKILL.md
  - .agents/skills/tenn-improve-codebase-architecture/SKILL.md
  - .agents/skills/tenn-issue/SKILL.md
  - .agents/skills/zoom-out/SKILL.md
  - .codex/skills/cockpit-flag-orchestrator/SKILL.md
  - .codex/skills/cockpit-flag-orchestrator/agents/openai.yaml
  - .codex/skills/cockpit-flag-orchestrator/references/subagent-prompts.md
  - reports/agent_jobs/control_plane_key_tenn_skills_only_v1_20260624/README.md
  - reports/agent_jobs/control_plane_key_tenn_skills_only_v1_20260624/STATE.md
  - reports/agent_jobs/control_plane_key_tenn_skills_only_v1_20260624/VALIDATION.md
  - reports/agent_jobs/control_plane_key_tenn_skills_only_v1_20260624/PR_REVIEW.md
  - reports/agent_jobs/control_plane_key_tenn_skills_only_v1_20260624/diff-check.json
---

# Control Plane Tenn Narrative Skill Surface V1

## Objective

Trim the repo-local Codex skill surface so fresh Tenn sessions keep the key Tenn
entrypoints plus explicitly requested narrative/support skills:

- `tenn-fix`
- `tenn-review-board`
- `tenn-handoff`
- `tenn-explain`
- `tenn-git-guard`
- `tenn-issue`
- `tenn-goal-report`
- `tenn-financial-metric-extraction`
- `codex-worker-bridge`
- `tenn-improve-codebase-architecture`
- `zoom-out`
- `caveman`

## Scope

- Remove non-narrative repo-local skill entrypoints.
- Remove the legacy/custom `.codex/skills/cockpit-flag-orchestrator` entrypoint.
- Refresh the skill-surface docs and current docs snapshot so the visible count
  and routing guidance match the new surface.
- Preserve host/global skill roots unchanged.

## Hard Boundaries

Closeout scope: control-plane-only.

- Do not touch product, runtime, extraction, source PDF, gold label, prompt,
  schema, service, model, GPU, DB, Qdrant, Redis, news, memory, or production
  data paths.
- Do not mutate host-global files under `/home/l4nd0/.codex`,
  `/home/l4nd0/.agents`, plugin caches, or any home-directory skill roots.
- Do not delete branches, remove worktrees, merge, rebase, reset, stash,
  cherry-pick, prune, force-push, or mutate GitHub.
- Do not install dependencies, start services, or run runtime/product
  validation.

## Required Validation

- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/control_plane_key_tenn_skills_only_v1_20260624.md`
- `python3 scripts/agent_job_registry.py list-active --read-only --repo-root .`
- `python3 scripts/agent_task_ledger.py --repo-root . validate`
- `find .agents/skills -maxdepth 2 -name SKILL.md | sort`
- `find .codex/skills -maxdepth 2 -name SKILL.md | sort`
- focused key-skill allowlist check
- `git diff --check`
- `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/control_plane_key_tenn_skills_only_v1_20260624.md --repo-root .`
- `python3 scripts/agent_job_contract.py check-report-artifacts docs/agent_tasks/control_plane_key_tenn_skills_only_v1_20260624.md --repo-root .`
- final `git status --short --untracked-files=all`

## Definition Of Done

- Only the 12 approved repo-local `.agents/skills/*/SKILL.md` entrypoints remain
  visible.
- Legacy/custom `.codex/skills` exposes no `SKILL.md` entrypoint.
- Docs reflect the new count and the host-global no-mutation boundary.
- No product/runtime/data/extraction or host-global paths change.
