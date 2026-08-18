---
job_id: extraction_third_canary_runtime_preflight_v1_20260529
lane: Financial Truth
supporting_lanes:
  - Evaluation
  - Provenance
  - Query Orchestration
owner: Codex
allowed_files:
  - docs/agent_tasks/extraction_third_canary_runtime_preflight_v1_20260529.md
  - reports/agent_jobs/extraction_third_canary_runtime_preflight_v1_20260529/**
  - docs/claude/STATE.md
approval_required: true
timeout_seconds: 7200
output_dir: reports/agent_jobs/extraction_third_canary_runtime_preflight_v1_20260529
mutation_mode: blocked
requested_mutation_mode: runtime_canary
production_data_access: false
github_mutation_allowed: none
related_issue: 96
operator_approval_source: "APPROVE #96 THIRD CANARY extraction_third_canary_approval_packet_refresh_v1_20260529"
---

# Extraction Third Canary Runtime Preflight V1

## Objective

Use the operator-approved packet
`extraction_third_canary_approval_packet_refresh_v1_20260529` to run immediate
pre-run gates for the seven-document #96 third canary, and submit no documents
unless every runtime, queue, GPU, loaded-code, and source-path gate is clean.

## Scope

- Primary lane: Financial Truth.
- Supporting lanes: Evaluation, Provenance, Query Orchestration.
- Mode: BLOCKED runtime preflight report. No document submission unless gates
  pass.
- Risk: HIGH for runtime/data mutation if execution proceeds.
- Related issue: #96.

## Contract Check

- Target system layers: Extraction and Storage through the canonical backend
  single-document API; Evaluation and Provenance only for report artifacts.
- Relevant contract rules: backend remains sole authority; metric extraction
  must use explicit values only; no inference, substitution, direct datastore
  mutation, alternate pipeline, broad backfill, or source-PDF mutation.
- What must not change: source PDFs, parser routing, extraction prompts, gold
  labels, schemas/migrations, runtime/model/GPU/service config, Cockpit UI,
  GitHub issue state, memory/news state, broad queue behavior, or any
  unapproved document.
- Why safe: this card records the approval phrase and stops before canary
  execution when required pre-run gates cannot prove safe runtime state.
- GPU process check required: yes. The canary may depend on the live LLM/GPU
  runtime.

## Approved Packet

- Packet:
  `reports/agent_jobs/extraction_third_canary_approval_packet_refresh_v1_20260529/canary_approval_packet.json`
- Approval phrase:
  `APPROVE #96 THIRD CANARY extraction_third_canary_approval_packet_refresh_v1_20260529`
- Approved route:
  `POST /api/process/document/{document_id}`
- Approved ordering:
  AAU, ATM, AM5, AQX, CRS, CLV, CTM.

## Abort Decision

Do not run the canary unless all of these gates are clean immediately before
the first POST:

- Registry task card validated and claimed.
- No overlapping extraction/backfill/runtime job.
- `scripts/gpu_process_guard.sh --check` and raw GPU health are clean.
- Backend `/api/health` is OK.
- Live backend and worker loaded code are current HEAD or a documented
  descendant without requiring a restart.
- All source paths exist and no source sidecar is present.
- No approved document is queued/running/orphaned.
- No service restart, parser/prompt/schema change, direct SQL, bulk route, or
  broad backfill is required.

## Validation

- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/extraction_third_canary_runtime_preflight_v1_20260529.md`
- `python3 scripts/agent_job_registry.py list-active --read-only`
- `python3 scripts/agent_job_registry.py check-overlap docs/agent_tasks/extraction_third_canary_runtime_preflight_v1_20260529.md --repo-root .`
- `python3 scripts/agent_job_registry.py claim docs/agent_tasks/extraction_third_canary_runtime_preflight_v1_20260529.md --repo-root .`
- Preflight commands recorded in
  `reports/agent_jobs/extraction_third_canary_runtime_preflight_v1_20260529/preflight.json`.
- `python3 -m json.tool` for generated JSON reports.
- `git diff --check`
- `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/extraction_third_canary_runtime_preflight_v1_20260529.md --repo-root .`
- Registry release and final list-active.

## Final Report Requirements

Report the approval receipt, canary execution verdict, every failed or
unproven gate, confirmation that no canary/backfill/document POST ran, and the
next safe approval needed if a runtime reload is required.
