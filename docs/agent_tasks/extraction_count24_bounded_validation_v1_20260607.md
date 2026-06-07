---
job_id: extraction_count24_bounded_validation_v1_20260607
lane: Evaluation
supporting_lanes:
  - Financial Truth
  - Query Orchestration
  - Provenance
owner: Codex
allowed_files:
  - docs/agent_tasks/extraction_count24_bounded_validation_v1_20260607.md
  - reports/agent_jobs/extraction_count24_bounded_validation_v1_20260607/README.md
  - reports/agent_jobs/extraction_count24_bounded_validation_v1_20260607/accepted_output_audit.json
  - reports/agent_jobs/extraction_count24_bounded_validation_v1_20260607/classification.json
  - reports/agent_jobs/extraction_count24_bounded_validation_v1_20260607/diff-check.json
  - reports/agent_jobs/extraction_count24_bounded_validation_v1_20260607/failure_taxonomy.json
  - reports/agent_jobs/extraction_count24_bounded_validation_v1_20260607/low_confidence_taxonomy.json
  - reports/agent_jobs/extraction_count24_bounded_validation_v1_20260607/preflight.json
  - reports/agent_jobs/extraction_count24_bounded_validation_v1_20260607/raw_commands.log
  - reports/agent_jobs/extraction_count24_bounded_validation_v1_20260607/run_bounded_count24.py
  - reports/agent_jobs/extraction_count24_bounded_validation_v1_20260607/sample_manifest.json
  - reports/agent_jobs/extraction_count24_bounded_validation_v1_20260607/sample_results.json
  - reports/agent_jobs/extraction_count24_bounded_validation_v1_20260607/side_effect_audit.json
  - reports/agent_jobs/extraction_count24_bounded_validation_v1_20260607/status.json
  - reports/agent_jobs/extraction_count24_bounded_validation_v1_20260607/validation.json
approval_required: false
timeout_seconds: 7200
output_dir: reports/agent_jobs/extraction_count24_bounded_validation_v1_20260607
mutation_mode: audit_only
production_data_access: false
github_mutation_allowed: false
allow_audit_code_changes: true
---

# Count-24 Bounded Extraction Validation

## Objective

Run exactly one bounded count-24 Tenn extraction validation from canonical
`bfe3a77ec6692d5052eefec7454461e75459f7e3`, using the PR #309 approval packet
at `reports/agent_jobs/extraction_count24_approval_packet_v1_20260607/README.md`.

## Operator Approval

The operator approved count-24 only for canonical
`bfe3a77ec6692d5052eefec7454461e75459f7e3`, with no count-32, broad extraction,
backfill, or full ticker-universe extraction.

## Hard Stops

- Do not run count-32.
- Do not run broad extraction, backfill, or full ticker-universe extraction.
- Do not mutate DB, Qdrant, Redis, news stores, memory, source PDFs, prompts,
  gold labels, runtime config, schema, services, models, or GPU config.
- Do not edit extraction source code.
- Stop before extraction if canonical ancestry, task-card validation, registry,
  queue, GPU/process, loaded-commit, source-path, candidate-pool, or selected
  manifest gates fail.
- Stop after exactly one count-24 attempt.

## Required Outputs

- selected document manifest before extraction
- ok / ok_low_confidence / failed / exceptions
- failure taxonomy
- low-confidence taxonomy
- accepted-output audit
- side-effect audit for DB, Qdrant, risk-note, news, memory, and source PDFs
- count-24 success/failure verdict
- count-32 decision
- explicit no broad extraction/backfill statement
