---
job_id: skill_surface_freshness_semantics_v1_20260626
lane: Reporting
supporting_lanes:
  - Repo Hygiene
owner: Codex
approval_required: false
allow_unapproved_safe_extension: true
allow_audit_code_changes: false
timeout_seconds: 3600
output_dir: reports/agent_jobs/skill_surface_freshness_semantics_v1_20260626
mutation_mode: safe_extension
production_data_access: false
closeout_scope: control_plane_only
allowed_files:
  - docs/agent_tasks/skill_surface_freshness_semantics_v1_20260626.md
  - docs/dev_flow/SKILLS_SURFACE.md
  - reports/agent_jobs/skill_surface_freshness_semantics_v1_20260626/README.md
  - reports/agent_jobs/skill_surface_freshness_semantics_v1_20260626/STATE.md
  - reports/agent_jobs/skill_surface_freshness_semantics_v1_20260626/DECISIONS.md
  - reports/agent_jobs/skill_surface_freshness_semantics_v1_20260626/VALIDATION.md
  - reports/agent_jobs/skill_surface_freshness_semantics_v1_20260626/PR_REVIEW.md
  - reports/agent_jobs/skill_surface_freshness_semantics_v1_20260626/diff-check.json
  - reports/agent_jobs/skill_surface_freshness_semantics_v1_20260626/ledger_entry_claimed.json
github_writes_allowed:
  - push branch control-plane/skill-surface-freshness-semantics-v1-20260626
  - open draft PR against migration/clean-runtime-baseline-reconstruct-v1
---

# Skill Surface Freshness Semantics V1

## Objective

Patch the `docs/dev_flow/SKILLS_SURFACE.md` freshness model so agents stop
treating `last_verified_commit` as needing exact equality with the current
canonical branch HEAD after every metadata PR merge.

## Scope

- Define `last_verified_commit` as the audited source/canonical commit for the
  skill-surface snapshot.
- State that freshness is valid when the verified commit is an ancestor of
  current canonical and none of the `stale_if_files` changed after it.
- Keep `last_verified_pr` as the PR that produced or validated the snapshot.
- Update the refresh procedure and evidence wording so future agents do not
  chase self-invalidating canonical-HEAD equality.
- Preserve the visible repo-backed skill surface and legacy `.codex/skills`
  absent-directory-safe check.
- Write closeout evidence under the report bundle.

## Hard Boundaries

- Do not touch product, runtime, backend, extraction, parser, prompt,
  gold-label, evaluator, schema, migration, service, model, GPU, DB, Qdrant,
  Redis, news, memory, source-document, or production-data behavior.
- Do not touch host-global Codex, agent, plugin, shell, service, or runtime
  configuration.
- Do not add or remove repo-backed skills.
- Do not mutate branch history, merge, rebase, reset, stash, prune, delete
  branches, or clean worktrees.
- GitHub writes are limited to pushing this branch and opening a draft PR.

## Required Validation

- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/skill_surface_freshness_semantics_v1_20260626.md`
- `python3 scripts/agent_job_registry.py list-active --read-only --repo-root .`
- `python3 scripts/agent_task_ledger.py --repo-root . validate`
- `find .agents/skills -maxdepth 2 -name SKILL.md | sort`
- `[ ! -d .codex/skills ] || find .codex/skills -maxdepth 2 -name SKILL.md | sort`
- `git merge-base --is-ancestor b3b3a154590f36e61d297c1ac79fe623526f0b28 origin/migration/clean-runtime-baseline-reconstruct-v1`
- `git diff --check`
- `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/skill_surface_freshness_semantics_v1_20260626.md --repo-root .`
- `python3 scripts/agent_job_contract.py check-report-artifacts docs/agent_tasks/skill_surface_freshness_semantics_v1_20260626.md --repo-root .`
- `python3 scripts/agent_job_contract.py check-closeout docs/agent_tasks/skill_surface_freshness_semantics_v1_20260626.md --repo-root .`

## Definition Of Done

- `SKILLS_SURFACE.md` no longer requires exact equality between
  `last_verified_commit` and current canonical HEAD after a docs metadata PR
  merge.
- The refresh procedure describes the ancestor-plus-stale-file rule.
- Repo-backed skill count remains 12.
- Legacy `.codex/skills` check remains absent-directory-safe.
- No product/runtime/extraction/data or host-global paths change.
- A draft PR is opened from
  `control-plane/skill-surface-freshness-semantics-v1-20260626`.
