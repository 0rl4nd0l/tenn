---
job_id: dev_flow_ground_up_reset_audit_v1_20260616
lane: Evaluation
supporting_lanes:
  - Reporting
  - Repo Hygiene
owner: Codex
approval_required: false
timeout_seconds: 14400
output_dir: reports/agent_jobs/dev_flow_ground_up_reset_audit_v1_20260616
mutation_mode: audit_only
allow_audit_code_changes: true
production_data_access: false
allowed_files:
  - docs/agent_tasks/dev_flow_ground_up_reset_audit_v1_20260616.md
  - reports/agent_jobs/dev_flow_ground_up_reset_audit_v1_20260616/README.md
  - reports/agent_jobs/dev_flow_ground_up_reset_audit_v1_20260616/INVENTORY.md
  - reports/agent_jobs/dev_flow_ground_up_reset_audit_v1_20260616/SKILLS_MATRIX.md
  - reports/agent_jobs/dev_flow_ground_up_reset_audit_v1_20260616/RULES_AND_AGENTS_MATRIX.md
  - reports/agent_jobs/dev_flow_ground_up_reset_audit_v1_20260616/HOOKS_MATRIX.md
  - reports/agent_jobs/dev_flow_ground_up_reset_audit_v1_20260616/HOST_CODEX_SURFACE.md
  - reports/agent_jobs/dev_flow_ground_up_reset_audit_v1_20260616/WORKTREE_MATRIX.md
  - reports/agent_jobs/dev_flow_ground_up_reset_audit_v1_20260616/GIT_HYGIENE_INTEGRATION.md
  - reports/agent_jobs/dev_flow_ground_up_reset_audit_v1_20260616/OPERATOR_WORKFLOW.md
  - reports/agent_jobs/dev_flow_ground_up_reset_audit_v1_20260616/OVERLAPS_AND_CONFLICTS.md
  - reports/agent_jobs/dev_flow_ground_up_reset_audit_v1_20260616/TARGET_ARCHITECTURE.md
  - reports/agent_jobs/dev_flow_ground_up_reset_audit_v1_20260616/DEPRECATION_PLAN.md
  - reports/agent_jobs/dev_flow_ground_up_reset_audit_v1_20260616/IMPLEMENTATION_SEQUENCE.md
  - reports/agent_jobs/dev_flow_ground_up_reset_audit_v1_20260616/OWNER_DECISIONS.md
  - reports/agent_jobs/dev_flow_ground_up_reset_audit_v1_20260616/VALIDATION.md
  - reports/agent_jobs/dev_flow_ground_up_reset_audit_v1_20260616/COMPILED_AUDIT.md
---

# Dev Flow Ground-Up Reset Audit V1

## Objective

Run a report-only, ground-up audit of Tenn's development workflow and
control-plane operating system: skills, rules, hooks, Git Hygiene, worktrees,
task-card conventions, registry surfaces, report conventions, host Codex
surfaces, and relevant read-only GitHub issue/PR context.

This is Tenn development workflow/control-plane work only. It is not Tenn
product, runtime, data, extraction, prompt, schema, source-PDF, gold-label, DB,
Qdrant, Redis, news, memory, model, GPU, or service work.

## Scope

- Inventory dev-flow related repo surfaces on current
  `origin/migration/clean-runtime-baseline-reconstruct-v1`.
- Inspect host/global Codex surfaces read-only where present.
- Classify every Tenn worktree using read-only Git evidence.
- Inspect relevant GitHub issues and PRs read-only.
- Produce the requested report bundle under `output_dir`.
- Design a lean future hands-off operating model and native Git Hygiene guard.

## Hard Boundaries

- Do not implement cleanup or new skills.
- Do not touch product/runtime/data/extraction code or source artifacts.
- Do not touch source PDFs, gold labels, DB, Qdrant, Redis, news, memory,
  prompts, schema, runtime/model/GPU config, services, or backfills.
- Do not touch the count-24 extraction approval packet.
- Do not mutate host-global Codex files.
- Do not mutate GitHub.
- Do not delete branches or worktrees.
- Do not clean, reset, stash, merge, rebase, cherry-pick, prune, or force-push.
- Do not create a cleanup PR.
- Do not run broad validation.

## Required Evidence

- Current repo path, branch, HEAD, remote, base branch, and dirty state.
- Task-card validation.
- Read-only registry status.
- Root and nested `AGENTS.md` files.
- `.agents/skills/**`, `.codex/**`, rules, hooks, agent-job scripts, registry
  docs, task-card conventions, report conventions, and dev-flow docs.
- Host/global Codex files and schemas listed in the user request when present,
  read-only.
- `git worktree list --porcelain` and per-worktree read-only classification.
- Relevant read-only GitHub issue/PR context for dev-flow, automation, skills,
  hooks, rules, Git Hygiene, Frame/Scribe/Watcher/Goal Report, auto-progress,
  diagnose, explain, architecture, and code-reviewer workflows.

## Required Validation

- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/dev_flow_ground_up_reset_audit_v1_20260616.md`
- `python3 scripts/agent_job_registry.py list-active --read-only`
- `git diff --check`
- Changed-path guard proving only this task card and the report bundle changed.
- Confirm no product/runtime/data/extraction files changed.
- Confirm no host-global files changed.
- Confirm no GitHub mutation occurred.
- Confirm no branch/worktree deletion occurred.

## Definition Of Done

- Every dev-flow skill found is inventoried and explained.
- Existing diagnose, explain, architecture/improve-codebase, and code-reviewer
  workflows are specifically evaluated.
- Rule, hook, `AGENTS.md`, registry, task-card, report, Frame/Scribe/Watcher,
  Goal Report, Git Hygiene, and auto-progress surfaces are mapped.
- Every Tenn worktree is classified.
- Native Git Hygiene integration is designed as a backend guard.
- Overlaps and contradictions are listed.
- A lean target hands-off architecture and implementation sequence are defined.
- Existing pieces are assigned one required classification each.
- No cleanup or mutation occurs outside this task card and the report bundle.
