---
job_id: control_plane_runtime_functionality_proof_v1_20260622
lane: Reporting
supporting_lanes:
  - Repo Hygiene
owner: Codex
approval_required: false
allow_unapproved_safe_extension: true
allow_audit_code_changes: true
timeout_seconds: 3600
output_dir: reports/agent_jobs/control_plane_runtime_functionality_proof_v1_20260622
mutation_mode: safe_extension
production_data_access: false
allowed_files:
  - docs/agent_tasks/control_plane_runtime_functionality_proof_v1_20260622.md
  - AGENTS.md
  - docs/dev_flow/SKILLS_SURFACE.md
  - .agents/skills/tenn-fix/SKILL.md
  - .agents/skills/tenn-explain/SKILL.md
  - .agents/skills/tenn-review-board/SKILL.md
  - .agents/skills/tenn-handoff/SKILL.md
  - docs/dev_flow/templates/BOARD.md
  - docs/dev_flow/templates/BOARD_DECISION.json
  - docs/dev_flow/templates/COUNTER_LINEAGE.md
  - docs/dev_flow/templates/EXPLAIN.md
  - docs/dev_flow/templates/HANDOFF.md
  - docs/dev_flow/templates/PR_REVIEW.md
  - docs/dev_flow/templates/STATE.md
  - scripts/check_runtime_functionality_proof_docs.py
  - reports/agent_jobs/control_plane_runtime_functionality_proof_v1_20260622/VALIDATION.md
  - reports/agent_jobs/control_plane_runtime_functionality_proof_v1_20260622/PR_REVIEW.md
---

# Control Plane Runtime Functionality Proof V1

## Objective

Patch Tenn/Codex control-plane instructions so future agents cannot call
daemon, runtime, ingestion, extraction, automation, collector, scheduler,
service, or pipeline work `DONE`, working, functional, or complete unless they
prove fresh intended live output.

## Scope

- Add a hard `Runtime Functionality Proof` rule to `AGENTS.md`.
- Strengthen truthfulness, surprising-number, done-criteria, and skill-surface
  guidance.
- Add concise references to existing core skills and relevant templates.
- Add one lightweight validation script that checks the required AGENTS section
  and proof-table field names.

## Hard Boundaries

- Control-plane docs, repo-backed skills, templates, task card, report-local
  validation notes, and one docs validation script only.
- Do not touch product, runtime, data, extraction implementation, source-PDF,
  gold-label, prompt, schema, service, model, GPU, DB, Qdrant, Redis, news,
  memory, or count-24 paths.
- Do not change greyhound runtime.
- Do not add a new visible skill.
- Do not touch host-global Codex skills under `/home/l4nd0/.codex`,
  `/home/l4nd0/.agents`, or plugin cache skill roots.
- Do not install dependencies, start services, run backfills, mutate runtime
  state, or perform production/data validation.

## Required Validation

- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/control_plane_runtime_functionality_proof_v1_20260622.md`
- `python3 scripts/agent_task_ledger.py resolve-path`
- `python3 scripts/agent_task_ledger.py validate`
- `python3 scripts/agent_job_registry.py list-active --read-only --repo-root .`
- Before/after visible skill count.
- Skill frontmatter/H1 check for visible repo skills.
- `python3 scripts/check_runtime_functionality_proof_docs.py`
- `git diff --check`
- `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/control_plane_runtime_functionality_proof_v1_20260622.md --no-write-report`
- Product/runtime/data/extraction/count-24 guard.
- Host-global guard.
- Final `git status --short --untracked-files=all`.

## Definition Of Done

- `AGENTS.md` requires fresh intended-output proof before DONE/functionality
  claims for runtime/daemon/automation/extraction-like work.
- Existing core skills and templates point to the proof gate without growing the
  visible skill surface.
- Lightweight validation enforces the AGENTS proof section and field names.
- No product/runtime/data/extraction/count-24 or host-global files changed.
