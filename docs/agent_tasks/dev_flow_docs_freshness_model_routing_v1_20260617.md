---
job_id: dev_flow_docs_freshness_model_routing_v1_20260617
lane: Reporting
supporting_lanes:
  - Repo Hygiene
owner: Codex
approval_required: false
allow_unapproved_safe_extension: true
allow_audit_code_changes: true
timeout_seconds: 7200
output_dir: reports/agent_jobs/dev_flow_docs_freshness_model_routing_v1_20260617
mutation_mode: safe_extension
production_data_access: false
allowed_files:
  - .agents/skills/tenn-fix/SKILL.md
  - .agents/skills/tenn-worker/SKILL.md
  - .agents/skills/tenn-review-board/SKILL.md
  - .agents/skills/tenn-code-reviewer/SKILL.md
  - .agents/skills/tenn-git-guard/SKILL.md
  - docs/dev_flow/templates/WORKER_RESULT.md
  - docs/dev_flow/templates/PR_REVIEW.md
  - docs/dev_flow/templates/HANDOFF.md
  - docs/dev_flow/templates/DOCS_IMPACT.md
  - docs/dev_flow/templates/MODEL_ROUTING.md
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
  - docs/agent_tasks/dev_flow_docs_freshness_model_routing_v1_20260617.md
  - reports/agent_jobs/dev_flow_docs_freshness_model_routing_v1_20260617/README.md
  - reports/agent_jobs/dev_flow_docs_freshness_model_routing_v1_20260617/VALIDATION.md
  - reports/agent_jobs/dev_flow_docs_freshness_model_routing_v1_20260617/PR_REVIEW.md
---

# Dev Flow Docs Freshness And Model Routing V1

## Objective

Implement the docs freshness and model/subagent routing rules recommended by the
skills-bloat audit. Preserve the audit task/report artifacts if they are still
local and not canonical. Do not implement skill deletion, trimming, script
automation, product/runtime changes, or host-global changes in this run.

## Scope

- Add a Docs Impact Check closeout gate to implementation/review control-plane
  skills.
- Add model and worker routing tiers, fields, and decision limits to the
  bounded implementation, worker, review board, and code-review workflows.
- Add reusable docs-impact and model-routing templates.
- Update worker, PR-review, and handoff templates to reference the new fields.
- Keep wording focused on Codex development tooling and repo control-plane
  behavior. Use Tenn-specific naming only where the workflow depends on this
  repo's task-card registry, owner-boundary rules, extraction boundaries, or
  financial-truth safety constraints.

## Hard Boundaries

- Do not touch product, runtime, data, extraction, source-PDF, gold-label,
  prompt, schema, service, model, GPU, DB, Qdrant, Redis, news, memory, or
  count-24 paths.
- Do not mutate host-global files under `/home/l4nd0/.codex`,
  `/home/l4nd0/.agents`, plugin cache directories, or any home-directory skill
  roots.
- Do not delete, rename, rehome, or trim skills in this run.
- Do not implement `scripts/docs_impact.py` or any complex validation script.
- Do not add model-provider-specific secrets, config, runtime selection, or
  dependency files.
- Do not clean, delete branches, remove worktrees, merge, rebase, reset, stash,
  cherry-pick, prune, or force-push.
- Do not mutate GitHub except pushing this branch and opening the approved PR
  after validation.
- Do not interfere with the open task-ledger/runtime/handoff PR.

## Preflight Evidence Required

- Fetched `origin/migration/clean-runtime-baseline-reconstruct-v1`.
- Clean sibling worktree created from canonical base.
- Current worktree, branch, HEAD, upstream, origin, and dirty status.
- Read-only registry state.
- Live and committed task ledger availability.
- Duplicate-work search for docs freshness, docs impact, model routing,
  subagent routing, skill trimming, skills bloat, handoff, and task ledger
  runtime.
- Classification of related open PR #367 before editing overlapping
  control-plane files.

## Required Validation

- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/dev_flow_docs_freshness_model_routing_v1_20260617.md`
- Parse changed `SKILL.md` files.
- Markdown/template field check for docs impact and model routing fields.
- `git diff --check`
- `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/dev_flow_docs_freshness_model_routing_v1_20260617.md --no-write-report`
- `python3 scripts/agent_job_contract.py check-report-artifacts docs/agent_tasks/dev_flow_docs_freshness_model_routing_v1_20260617.md`
- Changed-path guard proving only approved control-plane docs, skills,
  templates, task cards, and report artifacts changed.
- Product/runtime/data/extraction guard.
- Count-24 guard.
- Host-global guard.
- Final `git status --short --untracked-files=all`.

## Definition Of Done

- Docs freshness is required in fix and review closeout, and the handoff
  template records the same fields.
- Worker/model routing policy is documented and templated.
- Skills-bloat audit artifacts are preserved in this branch because they were
  local-only on canonical at preflight.
- Future agents can choose worker/model tier based on difficulty and risk.
- No product/runtime/extraction/data/count-24 or host-global mutation occurred.
