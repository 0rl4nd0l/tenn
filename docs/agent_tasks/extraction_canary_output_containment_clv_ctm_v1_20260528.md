---
job_id: extraction_canary_output_containment_clv_ctm_v1_20260528
lane: Financial Truth
supporting_lanes:
  - Provenance
  - Evaluation
  - Query Orchestration
owner: Codex
mutation_mode: safe_extension
requested_mutation_mode: controlled_containment_minimal_mutation
approval_required: true
production_data_access: false
production_data_access_requested: true
user_authorized_live_state_mutation: true
related_issue: 96
output_dir: reports/agent_jobs/extraction_canary_output_containment_clv_ctm_v1_20260528
allowed_files:
  - docs/agent_tasks/extraction_canary_output_containment_clv_ctm_v1_20260528.md
  - reports/agent_jobs/extraction_canary_output_containment_clv_ctm_v1_20260528/README.md
  - reports/agent_jobs/extraction_canary_output_containment_clv_ctm_v1_20260528/status.json
  - reports/agent_jobs/extraction_canary_output_containment_clv_ctm_v1_20260528/containment_ledger.json
  - reports/agent_jobs/extraction_canary_output_containment_clv_ctm_v1_20260528/pre_mutation_inventory.json
  - reports/agent_jobs/extraction_canary_output_containment_clv_ctm_v1_20260528/post_containment_verification.json
  - reports/agent_jobs/extraction_canary_output_containment_clv_ctm_v1_20260528/diff-check.json
allowed_repo_files:
  - docs/agent_tasks/extraction_canary_output_containment_clv_ctm_v1_20260528.md
  - reports/agent_jobs/extraction_canary_output_containment_clv_ctm_v1_20260528/**
timeout_seconds: 14400
---

# #96 CLV/CTM Canary Output Containment

## Objective

Contain exactly the two unsafe #96 canary outputs identified by the exposure
audit:

- CLV `source_document_id=da9f9ea5-6596-464f-af14-5acf12f9b050`,
  row identity `(CLV, 2026-01-31, H)`, and matching `asx_docs` Qdrant points.
- CTM `source_document_id=035c6758-7aed-41a6-9e84-ad154125d431`,
  row identity `(CTM, 2025-12-31, H)`, and matching `asx_docs` Qdrant points.

Then verify those outputs no longer surface through financial-truth APIs or
retrieval paths.

## Contract Notes

The repo task-card validator only supports `mutation_mode` values
`audit_only`, `safe_extension`, and `blocked`, and it hard-requires
`production_data_access: false`. This card therefore records the real requested
mode as `requested_mutation_mode: controlled_containment_minimal_mutation` and
the user-authorized live-state exception as
`user_authorized_live_state_mutation: true`.

## Allowed Live-State Mutation

Only these live-state writes are allowed:

- Delete or suppress the exact CLV financial row matching ticker, period end,
  period type, and source document id.
- Delete or suppress the exact CTM financial row matching ticker, period end,
  period type, and source document id.
- Delete the exact `asx_docs` Qdrant points whose payload document ids match
  the two source document ids.

If a supported quarantine/review state exists, prefer it. If no supported
quarantine/review state exists, use the smallest reversible deletion path and
record the full pre-mutation inventory in the report artifacts.

## Hard Stops

- Do not run any canary, extraction, or backfill.
- Do not mutate rows or points outside the exact CLV/CTM identities above.
- Do not delete source documents, source PDFs, extraction runs, gold labels, or
  source assets.
- Do not perform broad SQL updates/deletes.
- Do not mutate Qdrant collections other than exact matching `asx_docs` points.
- Do not mutate news, memory, prompts, parser routing, runtime/model/GPU
  config, or schema migrations.
- Do not restart services.
- Stop and report if exact identity checks find more than one financial row per
  target identity or unexpected document ids.

## Required Evidence

- Preflight repo path, branch, HEAD, remote, git status, worktree list, and
  registry state.
- Pre-mutation inventory for both rows and both Qdrant document point sets.
- Containment method and exact affected row/point counts.
- Post-containment verification for `/api/context/ticker`,
  `/api/context/company_dump`, financial-truth provider exposure, and Qdrant
  document scroll/search exposure.
- Explicit statement that no canary/extraction/backfill ran.

## Output Artifacts

- `reports/agent_jobs/extraction_canary_output_containment_clv_ctm_v1_20260528/README.md`
- `reports/agent_jobs/extraction_canary_output_containment_clv_ctm_v1_20260528/status.json`
- `reports/agent_jobs/extraction_canary_output_containment_clv_ctm_v1_20260528/containment_ledger.json`
- `reports/agent_jobs/extraction_canary_output_containment_clv_ctm_v1_20260528/pre_mutation_inventory.json`
- `reports/agent_jobs/extraction_canary_output_containment_clv_ctm_v1_20260528/post_containment_verification.json`

## Validation

- JSON validation for report artifacts.
- Task-card validation.
- Task-card `check-diff`.
- `git diff --check`.
- Final registry `list-active --read-only`.
- Final git status.
