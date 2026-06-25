---
job_id: skill_surface_freshness_pr409_v1_20260625
lane: Reporting
supporting_lanes:
  - Repo Hygiene
owner: Codex
approval_required: false
allow_unapproved_safe_extension: true
allow_audit_code_changes: true
timeout_seconds: 3600
output_dir: reports/agent_jobs/skill_surface_freshness_pr409_v1_20260625
mutation_mode: safe_extension
production_data_access: false
closeout_scope: control_plane_only
allowed_files:
  - docs/agent_tasks/skill_surface_freshness_pr409_v1_20260625.md
  - docs/dev_flow/SKILLS_SURFACE.md
  - reports/agent_jobs/skill_surface_freshness_pr409_v1_20260625/README.md
  - reports/agent_jobs/skill_surface_freshness_pr409_v1_20260625/STATE.md
  - reports/agent_jobs/skill_surface_freshness_pr409_v1_20260625/VALIDATION.md
  - reports/agent_jobs/skill_surface_freshness_pr409_v1_20260625/PR_REVIEW.md
  - reports/agent_jobs/skill_surface_freshness_pr409_v1_20260625/diff-check.json
---

# Skill Surface Freshness PR409 V1

## Objective

Patch only `docs/dev_flow/SKILLS_SURFACE.md` freshness metadata after PR #409
merged, then rerun the same skill-surface checks.

## Scope

- Refresh `last_verified_at`, `last_verified_commit`, `last_verified_pr`, and
  directly related freshness/data-missing evidence in
  `docs/dev_flow/SKILLS_SURFACE.md`.
- Keep the visible skill surface unchanged.
- Preserve the absent-directory-safe legacy `.codex/skills` check.
- Write closeout evidence under the report bundle.

## Hard Boundaries

- Do not touch product, runtime, backend, extraction, parser, prompt,
  gold-label, evaluator, schema, migration, service, model, GPU, DB, Qdrant,
  Redis, news, memory, source-document, or production-data behavior.
- Do not touch host-global Codex, agent, plugin, shell, service, or runtime
  configuration.
- Do not add or remove repo-backed skills.
- Do not create, push, merge, delete branches, prune, reset, rebase, stash, or
  mutate GitHub without separate explicit approval.

## Required Validation

- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/skill_surface_freshness_pr409_v1_20260625.md`
- `python3 scripts/agent_job_registry.py list-active --read-only --repo-root .`
- `python3 scripts/agent_task_ledger.py --repo-root . validate`
- `find .agents/skills -maxdepth 2 -name SKILL.md | sort`
- `[ ! -d .codex/skills ] || find .codex/skills -maxdepth 2 -name SKILL.md | sort`
- `uv run --with pytest --with pyyaml pytest tests/test_agent_task_ledger.py`
- `git diff --check`
- `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/skill_surface_freshness_pr409_v1_20260625.md --repo-root .`
- `python3 scripts/agent_job_contract.py check-report-artifacts docs/agent_tasks/skill_surface_freshness_pr409_v1_20260625.md --repo-root .`
- `python3 scripts/agent_job_contract.py check-closeout docs/agent_tasks/skill_surface_freshness_pr409_v1_20260625.md --repo-root .`

## Definition Of Done

- `SKILLS_SURFACE.md` freshness metadata references current canonical
  `b3b3a154590f36e61d297c1ac79fe623526f0b28` and PR #409.
- Repo-backed skill count remains 12.
- Legacy `.codex/skills` check remains absent-directory-safe.
- No product/runtime/extraction/data or host-global paths change.
