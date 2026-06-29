---
job_id: agents_constitution_slim_v1_20260628
lane: Reporting
supporting_lanes:
  - Repo Hygiene
owner: Codex
approval_required: false
allow_unapproved_safe_extension: true
allow_audit_code_changes: true
timeout_seconds: 7200
output_dir: reports/agent_jobs/agents_constitution_slim_v1_20260628
mutation_mode: safe_extension
production_data_access: false
closeout_scope: docs_only
allowed_files:
  - AGENTS.md
  - docs/agent_tasks/agents_constitution_slim_v1_20260628.md
  - docs/dev_flow/CODEX_OPERATOR_GUIDE.md
  - docs/dev_flow/SKILLS_SURFACE.md
  - reports/agent_jobs/agents_constitution_slim_v1_20260628/README.md
  - reports/agent_jobs/agents_constitution_slim_v1_20260628/STATE.md
  - reports/agent_jobs/agents_constitution_slim_v1_20260628/VALIDATION.md
  - reports/agent_jobs/agents_constitution_slim_v1_20260628/PR_REVIEW.md
  - reports/agent_jobs/agents_constitution_slim_v1_20260628/diff-check.json
---

# Agents Constitution Slim V1

## Objective

Reduce `AGENTS.md` bloat while preserving the hard Tenn guardrails. Keep the
root file constitutional and route repeatable procedures to existing
repo-backed skills and `docs/dev_flow` operator docs.

## Scope

- Slim `AGENTS.md` by removing duplicated procedure detail.
- Preserve source-of-truth hierarchy, safety boundaries, runtime functionality
  proof, task-card discipline, worktree preflight, and evidence-label rules.
- Refresh operator routing docs only where needed to make the new split clear.
- Keep this task docs-only and control-plane-only.

## Hard Boundaries

- Do not touch product, runtime, extraction, parser, source PDF, gold label,
  prompt, schema, service, model, GPU, DB, Qdrant, Redis, news, memory,
  production data, or count-24 paths.
- Do not mutate host-global files under `/home/l4nd0/.codex`,
  `/home/l4nd0/.agents`, plugin caches, or home-directory skill roots.
- Do not install dependencies, start services, run runtime/product validation,
  or mutate DB/runtime/service state.
- Do not merge, rebase, reset, stash, cherry-pick, prune, delete branches,
  delete worktrees, push, open PRs, or mutate GitHub.

## Later Owner Approval

After the docs-only local commit and review, Orlando explicitly approved:

- pushing `control-plane/agents-constitution-slim-v1-20260628`;
- opening draft PR #462;
- fixing review feedback in the report bundle;
- refreshing the PR branch against current canonical.

All other hard boundaries remain in force.

## Required Validation

- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/agents_constitution_slim_v1_20260628.md`
- `python3 scripts/agent_job_registry.py list-active --read-only --repo-root .`
- `python3 scripts/agent_task_ledger.py --repo-root . validate`
- `git diff --check`
- `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/agents_constitution_slim_v1_20260628.md --repo-root .`
- `python3 scripts/agent_job_contract.py check-closeout docs/agent_tasks/agents_constitution_slim_v1_20260628.md --repo-root .`
- `python3 scripts/agent_job_contract.py check-report-artifacts docs/agent_tasks/agents_constitution_slim_v1_20260628.md --repo-root .`
- `git status --short --untracked-files=all`

## Definition Of Done

- `AGENTS.md` is materially shorter and still preserves the hard gates.
- Procedure detail has a clear home in existing repo-backed skills and
  `docs/dev_flow` docs.
- No product/runtime/data/extraction/count-24 or host-global paths changed.
- Validation and report artifacts show this was docs-only; system
  functionality is not claimed.
