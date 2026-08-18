---
job_id: control_surface_instructions_refine_v1_20260625
lane: Reporting
supporting_lanes:
  - Repo Hygiene
owner: Codex
approval_required: false
allow_unapproved_safe_extension: true
allow_audit_code_changes: true
timeout_seconds: 7200
output_dir: reports/agent_jobs/control_surface_instructions_refine_v1_20260625
mutation_mode: safe_extension
production_data_access: false
closeout_scope: control_plane_only
allowed_files:
  - docs/agent_tasks/control_surface_instructions_refine_v1_20260625.md
  - docs/dev_flow/SKILLS_SURFACE.md
  - docs/dev_flow/templates/HANDOFF.md
  - .agents/skills/tenn-handoff/SKILL.md
  - tests/test_agent_task_ledger.py
  - reports/agent_jobs/control_surface_instructions_refine_v1_20260625/README.md
  - reports/agent_jobs/control_surface_instructions_refine_v1_20260625/STATE.md
  - reports/agent_jobs/control_surface_instructions_refine_v1_20260625/VALIDATION.md
  - reports/agent_jobs/control_surface_instructions_refine_v1_20260625/PR_REVIEW.md
  - reports/agent_jobs/control_surface_instructions_refine_v1_20260625/diff-check.json
---

# Control Surface Instructions Refine V1

## Objective

Fix and refine the Tenn Codex control surface from current canonical without
touching product, runtime, extraction, data, or host-global files.

## Scope

- Repair the handoff template/test contract mismatch by using one canonical
  milestone heading.
- Make legacy `.codex/skills` verification instructions safe when the directory
  is absent, which is the current canonical state.
- Refresh only directly affected control-plane instructions and report evidence.

## Hard Boundaries

Closeout scope: control-plane-only.

- Do not edit product, runtime, backend, extraction, parser, prompt, gold-label,
  evaluator, schema, migration, service, model, GPU, DB, Qdrant, Redis, news,
  memory-store, source-document, or production-data behavior.
- Do not mutate host-global files under `/home/l4nd0/.codex`,
  `/home/l4nd0/.agents`, plugin caches, or any home-directory skill roots.
- Do not create a repo `/goal monitor`.
- Do not add or remove visible repo-backed skills.
- Do not merge, rebase, reset, stash, delete branches, delete worktrees,
  force-push, prune, or mutate GitHub without separate explicit approval.

## Required Validation

- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/control_surface_instructions_refine_v1_20260625.md`
- `python3 scripts/agent_job_registry.py list-active --read-only --repo-root .`
- `python3 scripts/agent_task_ledger.py --repo-root . validate`
- `find .agents/skills -maxdepth 2 -name SKILL.md | sort`
- `[ ! -d .codex/skills ] || find .codex/skills -maxdepth 2 -name SKILL.md | sort`
- `uv run --with pytest --with pyyaml pytest tests/test_agent_task_ledger.py`
- `git diff --check`
- `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/control_surface_instructions_refine_v1_20260625.md --repo-root .`
- `python3 scripts/agent_job_contract.py check-report-artifacts docs/agent_tasks/control_surface_instructions_refine_v1_20260625.md --repo-root .`
- final `git status --short --untracked-files=all`

## Definition Of Done

- Handoff template, handoff skill instructions, and test expectations agree.
- Legacy custom `.codex/skills` checks pass whether the directory is absent or
  empty.
- The active repo skill surface remains the current 12 approved `.agents`
  entrypoints.
- No product/runtime/data/extraction or host-global path changes.
