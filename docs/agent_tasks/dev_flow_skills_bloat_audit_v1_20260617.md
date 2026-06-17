---
job_id: dev_flow_skills_bloat_audit_v1_20260617
lane: Evaluation
supporting_lanes:
  - Repo Hygiene
  - Reporting
owner: Codex
approval_required: false
allow_audit_code_changes: true
timeout_seconds: 7200
output_dir: reports/agent_jobs/dev_flow_skills_bloat_audit_v1_20260617
mutation_mode: audit_only
production_data_access: false
allowed_files:
  - docs/agent_tasks/dev_flow_skills_bloat_audit_v1_20260617.md
  - reports/agent_jobs/dev_flow_skills_bloat_audit_v1_20260617/README.md
  - reports/agent_jobs/dev_flow_skills_bloat_audit_v1_20260617/SKILLS_INVENTORY.md
  - reports/agent_jobs/dev_flow_skills_bloat_audit_v1_20260617/SKILL_RECOMMENDATIONS.md
  - reports/agent_jobs/dev_flow_skills_bloat_audit_v1_20260617/OVERLAPS_AND_BLOAT.md
  - reports/agent_jobs/dev_flow_skills_bloat_audit_v1_20260617/USER_FACING_COMMAND_SET.md
  - reports/agent_jobs/dev_flow_skills_bloat_audit_v1_20260617/BACKEND_GUARDRAILS.md
  - reports/agent_jobs/dev_flow_skills_bloat_audit_v1_20260617/DOCS_FRESHNESS_DESIGN.md
  - reports/agent_jobs/dev_flow_skills_bloat_audit_v1_20260617/MODEL_ROUTING_DESIGN.md
  - reports/agent_jobs/dev_flow_skills_bloat_audit_v1_20260617/SUBAGENT_DELEGATION_DESIGN.md
  - reports/agent_jobs/dev_flow_skills_bloat_audit_v1_20260617/HOST_SKILLS_REVIEW.md
  - reports/agent_jobs/dev_flow_skills_bloat_audit_v1_20260617/OWNER_DECISIONS.md
  - reports/agent_jobs/dev_flow_skills_bloat_audit_v1_20260617/NEXT_IMPLEMENTATION_PROMPT.md
  - reports/agent_jobs/dev_flow_skills_bloat_audit_v1_20260617/VALIDATION.md
---

# Dev Flow Skills Bloat Audit V1

## Objective

Run a report-only audit of Tenn repo skills, host/global skills, rules, hooks,
templates, docs, and development-flow ergonomics. The output should decide what
to keep, merge, rename, rehome, deprecate, or trim later, and should design docs
freshness plus model/subagent routing additions for a future implementation PR.

## Scope

- Inventory repo skills, host/global skills, repo rules, hooks, task-card
  conventions, report templates, agent registry docs, and adjacent dev-flow
  worktrees/PRs.
- Explain each skill in plain English.
- Identify overlaps, stale or risky skill triggers, report-only loops, and
  operator-facing bloat.
- Produce a report bundle under the configured `output_dir`.
- Produce the next implementation prompt only; do not implement changes.

## Hard Boundaries

- Do not touch product, runtime, data, extraction, source-PDF, gold-label,
  prompt, schema, service, model, GPU, DB, Qdrant, Redis, news, memory, or
  count-24 paths.
- Do not mutate host-global files under `/home/l4nd0/.codex`,
  `/home/l4nd0/.agents`, plugin cache directories, or any home-directory skill
  roots.
- Do not delete, rename, rehome, or edit skills in this run.
- Do not edit hooks, scripts, templates, AGENTS.md, docs, or task cards other
  than this audit task card and the exact report bundle files.
- Do not implement docs freshness, model routing, subagent routing, handoff, or
  ledger runtime changes.
- Do not clean, delete branches, remove worktrees, merge, rebase, reset, stash,
  cherry-pick, prune, push, force-push, or mutate GitHub.
- Do not interfere with the sibling Agent Task Ledger runtime and handoff
  workflow.

## Required Evidence

- Current repo path, branch, HEAD, upstream, origin, status, fetched
  `origin/migration/clean-runtime-baseline-reconstruct-v1`, and selected base.
- Read-only active registry state.
- Task Ledger availability and fallback duplicate-work search.
- Related worktrees, branches, task cards, reports, open PRs, and issues for
  skill audit, skill cleanup, docs freshness, model/subagent routing, handoff,
  task ledger, and dev-flow optimization.
- Repo skill inventory from `.agents/skills/**/SKILL.md` and legacy repo
  `.codex/skills/**` if present.
- Host/global skill inventory from readable host skill roots, with no host
  mutation.
- Rules/hooks/templates/docs inventory for the requested control-plane surfaces.

## Required Validation

- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/dev_flow_skills_bloat_audit_v1_20260617.md`
- `python3 scripts/agent_job_registry.py list-active --read-only --repo-root .`
- `git diff --check`
- Changed-path guard proving only this task card and the exact report bundle
  files changed.
- Product/runtime/data/extraction/count-24 guard.
- Host-global guard.
- Final `git status --short --untracked-files=all`.

## Definition Of Done

- Every repo and readable host/global skill in scope is inventoried.
- Skill bloat and overlap are clearly mapped.
- Keep, backend-keep, merge, rename/rehome, deprecate, delete-candidate, owner
  boundary, or unknown recommendations exist.
- Docs Freshness design exists.
- Model/Subagent Routing design exists.
- Next implementation prompt exists.
- No product/runtime/extraction/data, skill, hook, script, GitHub, or
  host-global mutation occurred.
