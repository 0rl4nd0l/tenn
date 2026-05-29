---
job_id: extraction_aau_canary_loaded_code_preflight_v1_20260529
lane: Financial Truth
owner: Codex
allowed_files:
  - docs/agent_tasks/extraction_aau_canary_loaded_code_preflight_v1_20260529.md
  - reports/agent_jobs/extraction_aau_canary_loaded_code_preflight_v1_20260529/README.md
  - reports/agent_jobs/extraction_aau_canary_loaded_code_preflight_v1_20260529/status.json
  - reports/agent_jobs/extraction_aau_canary_loaded_code_preflight_v1_20260529/runtime_preflight.json
  - reports/agent_jobs/extraction_aau_canary_loaded_code_preflight_v1_20260529/diff-check.json
approval_required: false
timeout_seconds: 3600
output_dir: reports/agent_jobs/extraction_aau_canary_loaded_code_preflight_v1_20260529
mutation_mode: audit_only
allow_audit_code_changes: true
production_data_access: false
github_mutation_allowed: none
related_issue: 96
---

# Extraction AAU Canary Loaded-Code Preflight V1

## Objective

After the AAU period-semantics integration was fast-forwarded into
`migration/clean-runtime-baseline-reconstruct-v1`, determine whether the
approved #96 third-canary packet can lawfully submit AAU through the live
backend without broadening the packet approval.

## Scope

- Primary lane: Financial Truth.
- Mode: AUDIT ONLY.
- Branch: `audit/extraction-aau-canary-loaded-code-preflight-v1-20260529`.
- Worktree: `/home/l4nd0/tenn-aau-canary-loaded-code-preflight-v1-20260529`.
- Candidate checked: AAU `508fc892-ae88-45ec-981f-cd9e124c8375`.

## Contract Check

Target system layers: Extraction and Evaluation/Provenance preflight only.

Relevant contract rules: backend remains sole authority; extraction must use
explicit source values only; canary execution must use the approved backend
single-document route; no direct datastore mutation or broad backfill is
allowed.

What must not change: backend/worker service state, parser routing, prompts,
schemas/migrations, source PDFs, DB/Qdrant/news/memory stores, Cockpit UI,
GitHub issue state, or any candidate outside the approved packet.

Why safe: this task only reads repo/runtime evidence and records whether the
approved packet's immediate pre-run gates are satisfied. It does not submit a
canary document, restart services, enqueue jobs, or mutate stores.

GPU process check required: read-only check only. No GPU service start/restart
is allowed in this task.

## Hard Stops

- Do not submit AAU or any other document.
- Do not restart backend, workers, containers, or llama-server.
- Do not run broad extraction/backfill.
- Do not mutate DB, Qdrant, news, memory, source PDFs, schemas, parser routing,
  prompts, runtime/model/GPU config, Cockpit UI, or GitHub state.
- Stop if loaded-code proof cannot establish that live backend and workers are
  serving `e2029835efbd2eb6425f089d703841eb20625bf7` or a descendant.

## Validation

- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/extraction_aau_canary_loaded_code_preflight_v1_20260529.md`
- `python3 scripts/agent_job_registry.py list-active --read-only --repo-root .`
- `python3 scripts/agent_job_registry.py check-overlap docs/agent_tasks/extraction_aau_canary_loaded_code_preflight_v1_20260529.md --repo-root .`
- `python3 scripts/agent_job_registry.py claim docs/agent_tasks/extraction_aau_canary_loaded_code_preflight_v1_20260529.md --repo-root .`
- Read-only runtime/container/process checks.
- `scripts/gpu_process_guard.sh --check`.
- JSON validation for generated artifacts.
- `git diff --check`.
- `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/extraction_aau_canary_loaded_code_preflight_v1_20260529.md --repo-root .`
- Registry release and final read-only active-job check.

## Final Report Requirements

Report whether AAU was submitted, the loaded-code proof verdict, the exact
blocking evidence if stopped, validation results, files changed, and the next
safe step toward the approved #96 third canary.
