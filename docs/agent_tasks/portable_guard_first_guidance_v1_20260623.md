---
job_id: portable_guard_first_guidance_v1_20260623
lane: Reporting
supporting_lanes:
  - Repo Hygiene
owner: Codex
approval_required: false
allow_unapproved_safe_extension: true
timeout_seconds: 3600
output_dir: reports/agent_jobs/portable_guard_first_guidance_v1_20260623
mutation_mode: safe_extension
production_data_access: false
task_scope: docs_only
closeout_scope: docs_only
allowed_files:
  - docs/agent_tasks/portable_guard_first_guidance_v1_20260623.md
  - AGENTS.md
  - docs/README.md
  - docs/dev_flow/CONTROL_PLANE_STATUS.md
  - docs/dev_flow/CODEX_OPERATOR_GUIDE.md
  - docs/dev_flow/SKILLS_SURFACE.md
  - .agents/skills/tenn-git-guard/SKILL.md
  - .agents/skills/tenn-handoff/SKILL.md
  - .agents/skills/tenn-financial-metric-extraction/SKILL.md
  - reports/agent_jobs/portable_guard_first_guidance_v1_20260623/README.md
  - reports/agent_jobs/portable_guard_first_guidance_v1_20260623/VALIDATION.md
  - reports/agent_jobs/portable_guard_first_guidance_v1_20260623/CODE_REVIEW.md
  - reports/agent_jobs/portable_guard_first_guidance_v1_20260623/PR_REVIEW.md
  - reports/agent_jobs/portable_guard_first_guidance_v1_20260623/diff-check.json
---

# Portable Guard First Guidance

## Objective

Make the portable repo-backed `tenn-git-guard` runner the first-class preflight
command in active operator guidance after PR #395.

## Scope

- Control-plane docs and repo-backed skill wording only.
- Start from canonical
  `origin/migration/clean-runtime-baseline-reconstruct-v1` at
  `1a0f1a03741d692089a0125ecb2f10691b8da597`.
- Keep visible repo-backed skill count at 10.
- Preserve repo-local `scripts/agent_job_registry.py`,
  `scripts/agent_task_ledger.py`, and `scripts/agent_job_contract.py` as
  Tenn-control-plane-local validation/check commands, not runtime/product repo
  preflight assumptions.

## Forbidden

- Product, runtime, data, extraction, count-24, source-PDF, gold-label, prompt,
  DB, Qdrant, Redis, news, memory, service, model/GPU, production-data, or
  Greyhound runtime mutation.
- Host-global file mutation.
- Visible skill additions.
- Historical task-card or report rewrites.
- Inspection or mutation of
  `/home/l4nd0/tenn-cockpit-bff-proxy-missions-v1-20260623`.
- Cleaning stale registry records, deleting branches, removing worktrees,
  rebasing, resetting, stashing, or pruning.

## Required Validation

- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/portable_guard_first_guidance_v1_20260623.md`
- `python3 /home/l4nd0/.agents/skills/tenn-git-guard/scripts/tenn_git_guard.py preflight --repo-root . --topic "portable guard first-class active guidance" --json`
- Grep active guidance to prove the portable guard command is documented before
  repo-local `scripts/agent_*` commands.
- Visible repo-backed skill count is exactly 10.
- Skill frontmatter/H1 check for every repo-backed skill.
- `git diff --check`
- `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/portable_guard_first_guidance_v1_20260623.md --repo-root .`
- `python3 scripts/agent_job_contract.py check-report-artifacts docs/agent_tasks/portable_guard_first_guidance_v1_20260623.md --repo-root .`
- Forbidden product/runtime/data/extraction/count-24 path guard.
- Host-global path guard.

## Definition Of Done

- Active operator guidance says to run the portable guard first.
- Repo-local Tenn scripts are described as Tenn-control-plane-local checks or
  fallback validation, not as required runtime/product repo files.
- The task is docs-only; no runtime functionality claim is made.
