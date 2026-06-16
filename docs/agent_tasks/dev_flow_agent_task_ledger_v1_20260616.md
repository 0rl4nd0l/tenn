---
job_id: dev_flow_agent_task_ledger_v1_20260616
lane: Evaluation
supporting_lanes:
  - Repo Hygiene
  - Reporting
owner: Codex
approval_required: false
allow_unapproved_safe_extension: true
timeout_seconds: 7200
output_dir: reports/agent_jobs/dev_flow_agent_task_ledger_v1_20260616
mutation_mode: safe_extension
production_data_access: false
allowed_files:
  - docs/agent_tasks/dev_flow_agent_task_ledger_v1_20260616.md
  - AGENTS.md
  - .agents/skills/tenn-git-guard/SKILL.md
  - .agents/skills/tenn-issue/SKILL.md
  - .agents/skills/tenn-review-board/SKILL.md
  - .agents/skills/tenn-fix/SKILL.md
  - .agents/skills/tenn-worker/SKILL.md
  - .agents/skills/tenn-explain/SKILL.md
  - docs/dev_flow/templates/TASK_LEDGER_ENTRY.json
  - docs/dev_flow/templates/TASK_LEDGER_SUMMARY.md
  - docs/agent_registry/task_ledger/README.md
  - reports/agent_jobs/dev_flow_agent_task_ledger_v1_20260616/README.md
---

# Dev Flow Agent Task Ledger V1

## Objective

Add instruction and template support for an Agent Task Ledger so future Tenn
implementation-capable sessions check for duplicate active, open, merged, stale,
or owner-boundary work before coding.

This is Tenn development workflow/control-plane work only. It does not implement
a ledger script and does not mutate product, runtime, data, extraction, source,
gold-label, prompt, schema, service, model, GPU, or host-global state.

## Scope

- Add a concise duplicate-work prevention rule to `AGENTS.md`.
- Make `tenn-git-guard` own detailed Task Ledger preflight and duplicate-work
  classification.
- Update `/issue`, `/review-board`, `/fix`, `/worker`, and branch/PR/report
  explanation wrappers to use ledger evidence before recommending or starting
  implementation.
- Add task-ledger entry and summary templates.
- Add optional documentation for the future committed task-ledger registry.
- Create this task card and closeout report.

## Hard Boundaries

- Do not touch product, frontend, backend runtime, data, extraction, source-PDF,
  gold-label, prompt, schema, DB, Qdrant, Redis, news, memory, service,
  production-data, model, GPU, or count-24 paths.
- Do not mutate `<git-common-dir>/tenn-agent-registry/task-ledger.jsonl` in this
  run.
- Do not create a ledger script in this run.
- Do not install dependencies or start services.
- Do not run cleanup, delete branches, remove worktrees, merge, rebase, reset,
  stash, cherry-pick, prune, or force-push.
- Do not mutate GitHub except opening the approved PR after validation.
- Do not merge the PR.

## Required Evidence

- Current repo path, branch, HEAD, upstream, origin, and status.
- PR #359 merged state and proof that the selected base contains it.
- Task Ledger availability:
  - `<git-common-dir>/tenn-agent-registry/task-ledger.jsonl`
  - `docs/agent_registry/task_ledger/LEDGER.jsonl`
- Bounded duplicate-work fallback search across task cards, reports, branches,
  worktrees, open/merged PRs, and related issues.
- Read-only active registry state when available.

## Required Validation

- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/dev_flow_agent_task_ledger_v1_20260616.md`
- `python3 scripts/agent_job_registry.py list-active --read-only --repo-root .`
- Parse changed `SKILL.md` files.
- `python3 -m json.tool docs/dev_flow/templates/TASK_LEDGER_ENTRY.json`
- `git diff --check`
- Changed-path guard proving only approved control-plane docs, skills,
  templates, task-card, and report paths changed.
- Product/runtime/data/extraction guard.
- Host-global guard.
- Final `git status --short --untracked-files=all`.

## Definition Of Done

- `AGENTS.md` contains the concise duplicate-work prevention rule.
- `tenn-git-guard` owns detailed ledger preflight.
- `/issue`, `/review-board`, `/fix`, worker, and explanation wrappers know how
  to use ledger state.
- Templates exist.
- No ledger script is implemented.
- Validation passes.
- A local commit exists, the branch is pushed, and an unmerged PR is open
  against `migration/clean-runtime-baseline-reconstruct-v1`.
