---
job_id: extraction_aau_runtime_reload_canary_approval_packet_v1_20260529
lane: Financial Truth
supporting_lanes:
  - Runtime/Performance
  - Evaluation
  - Provenance
owner: Codex
allowed_files:
  - docs/agent_tasks/extraction_aau_runtime_reload_canary_approval_packet_v1_20260529.md
  - reports/agent_jobs/extraction_aau_runtime_reload_canary_approval_packet_v1_20260529/README.md
  - reports/agent_jobs/extraction_aau_runtime_reload_canary_approval_packet_v1_20260529/status.json
  - reports/agent_jobs/extraction_aau_runtime_reload_canary_approval_packet_v1_20260529/reload_canary_approval_packet.json
  - reports/agent_jobs/extraction_aau_runtime_reload_canary_approval_packet_v1_20260529/diff-check.json
approval_required: false
allow_audit_code_changes: true
timeout_seconds: 3600
output_dir: reports/agent_jobs/extraction_aau_runtime_reload_canary_approval_packet_v1_20260529
mutation_mode: audit_only
production_data_access: false
github_mutation_allowed: none
related_issue: 96
---

# Extraction AAU Runtime Reload Canary Approval Packet V1

## Objective

Prepare an explicit operator approval packet for the next #96 step: reload only
the backend and Celery worker services needed to prove `e2029835` is live, then
submit AAU alone through the approved backend single-document route.

This task does not perform the reload and does not submit AAU.

## Scope

- Primary lane: Financial Truth.
- Supporting lanes: Runtime/Performance, Evaluation, Provenance.
- Mode: AUDIT ONLY / approval-packet generation.
- Branch: `audit/extraction-aau-runtime-reload-canary-approval-packet-v1-20260529`.
- Worktree: `/home/l4nd0/tenn-aau-runtime-reload-canary-approval-packet-v1-20260529`.
- Target baseline HEAD: `e2029835efbd2eb6425f089d703841eb20625bf7`.
- Candidate: AAU `508fc892-ae88-45ec-981f-cd9e124c8375`.

## Contract Check

Target system layers: Extraction, Storage through the existing single-document
backend route, and Evaluation/Provenance reporting.

Relevant contract rules: backend remains sole authority; metric extraction must
use explicit source values only; no direct datastore mutation or broad backfill;
runtime mutation must be bounded and explicitly approved before execution.

What must not change: parser routing, prompts, schemas/migrations, source PDFs,
Postgres/Qdrant/Redis data, news stores, memory stores, Cockpit UI, GitHub
issue state, llama/model/GPU configuration, or any non-AAU canary candidate.

Why safe: this task only creates an approval packet. A later runtime task must
validate and claim its own approval-required task card before executing any
service reload or canary POST.

GPU process check required: no for this report-only task. The later runtime
task must run `scripts/gpu_process_guard.sh --check` before reload and before
AAU submission.

## Hard Stops

- Do not restart, reload, stop, start, or rebuild any service in this task.
- Do not submit AAU or any other document.
- Do not run broad extraction/backfill.
- Do not mutate DB, Qdrant, Redis, news, memory, source PDFs, parser routing,
  prompts, schemas, runtime/model/GPU config, Cockpit UI, or GitHub state.
- Do not include ATM/AM5/AQX/CRS/CLV/CTM in the immediate runtime execution
  scope; they remain blocked until AAU passes.

## Validation

- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/extraction_aau_runtime_reload_canary_approval_packet_v1_20260529.md`
- `python3 scripts/agent_job_registry.py list-active --read-only --repo-root .`
- `python3 scripts/agent_job_registry.py check-overlap docs/agent_tasks/extraction_aau_runtime_reload_canary_approval_packet_v1_20260529.md --repo-root .`
- `python3 scripts/agent_job_registry.py claim docs/agent_tasks/extraction_aau_runtime_reload_canary_approval_packet_v1_20260529.md --repo-root .`
- Confirm current baseline HEAD and current runtime service names.
- JSON validation for generated artifacts.
- `git diff --check`.
- Staged source-PDF and credential-pattern scans.
- `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/extraction_aau_runtime_reload_canary_approval_packet_v1_20260529.md --repo-root .`
- Registry release and final read-only active-job check.

## Final Report Requirements

Report the approval phrase, exact future runtime scope, current evidence used,
validation results, files changed, and the next safe operator action.
