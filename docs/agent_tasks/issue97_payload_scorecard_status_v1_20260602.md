---
job_id: issue97_payload_scorecard_status_v1_20260602
lane: Evaluation
supporting_lanes:
  - Financial Truth
  - Provenance
  - Reporting
owner: Codex
mutation_mode: audit_only
allow_audit_code_changes: true
production_data_access: false
approval_required: false
timeout_seconds: 1800
output_dir: reports/agent_jobs/issue97_payload_scorecard_status_v1_20260602
allowed_files:
  - docs/agent_tasks/issue97_payload_scorecard_status_v1_20260602.md
  - reports/agent_jobs/issue97_payload_scorecard_status_v1_20260602/README.md
  - reports/agent_jobs/issue97_payload_scorecard_status_v1_20260602/status.json
  - reports/agent_jobs/issue97_payload_scorecard_status_v1_20260602/validation.json
  - reports/agent_jobs/issue97_payload_scorecard_status_v1_20260602/diff-check.json
  - reports/agent_jobs/issue97_payload_scorecard_status_v1_20260602/issue97_evidence_matrix.md
github_comment_targets:
  - 97
inspect_only_surfaces:
  - docs/agent_tasks/extraction_payload_scorecard_builder_v1_20260526.md
  - reports/agent_jobs/extraction_payload_scorecard_builder_v1_20260526/**
  - docs/agent_tasks/extraction_payload_scorecard_cli_gate_v1_20260531.md
  - reports/agent_jobs/extraction_payload_scorecard_cli_gate_v1_20260531/**
  - docs/agent_tasks/extraction_payload_actuals_coverage_gate_v1_20260531.md
  - reports/agent_jobs/extraction_payload_actuals_coverage_gate_v1_20260531/**
  - docs/agent_tasks/extraction_canary_actual_payload_exporter_v1_20260601.md
  - reports/agent_jobs/extraction_canary_actual_payload_exporter_v1_20260601/**
  - docs/agent_tasks/extraction_contract_parity_guard_v1_20260526.md
  - reports/agent_jobs/extraction_contract_parity_guard_v1_20260526/**
  - docs/agent_tasks/extraction_source_asset_manifest_metadata_safe_extension_v1_20260526.md
  - reports/agent_jobs/extraction_source_asset_manifest_metadata_safe_extension_v1_20260526/**
  - financial-engine_v2/backend/app/services/extraction_gold_eval_scorecard.py
  - financial-engine_v2/backend/tests/test_extraction_gold_eval_scorecard.py
  - scripts/export_extraction_run_actual_payloads.py
---

# Task

Post a current, evidence-grounded #97 status update that distinguishes completed scorecard plumbing from the remaining DATA_MISSING blocker.

# Boundaries

- Do not close #97.
- Do not edit product/backend/frontend/runtime/data files.
- Do not mutate DB, Qdrant, news, memory, canonical financial truth, source PDFs, gold labels, parser routing, extraction prompts, runtime, model, GPU, or service config.
- Do not run broad extraction, broad backfill, canary execution, or live persistence.
- Do not claim broad extracted-payload accuracy unless actual confirmed-metric fixture payloads prove it.
- If the only available actual payloads are unmatched canary outputs, record that as DATA_MISSING for #97 rather than treating it as a pass.

# Validation

Run:

- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/issue97_payload_scorecard_status_v1_20260602.md`
- `python3 scripts/agent_job_registry.py list-active`
- `python3 scripts/agent_job_registry.py check-overlap docs/agent_tasks/issue97_payload_scorecard_status_v1_20260602.md`
- `python3 scripts/agent_job_registry.py claim docs/agent_tasks/issue97_payload_scorecard_status_v1_20260602.md`
- fresh `gh issue view 97`
- duplicate/coverage PR search for #97
- repo evidence search for current #97 scorecard plumbing and blockers
- JSON parse checks for generated report artifacts
- `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/issue97_payload_scorecard_status_v1_20260602.md`
- `git diff --check`
- `git diff --cached --check`
- `python3 scripts/agent_job_registry.py release issue97_payload_scorecard_status_v1_20260602`

# Definition Of Done

- #97 has a current status comment grounded in current repo and GitHub evidence.
- The report records why #97 remains open, what is implemented, what is still DATA_MISSING, and the next safe step.
- No forbidden surface is changed.
