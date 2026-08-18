---
job_id: extraction_azj_edu_pass3a_provenance_capture_v1_20260607
lane: Financial Truth
supporting_lanes:
  - Evaluation
  - Provenance
  - Query Orchestration
  - Repo Hygiene
owner: Codex
allowed_files:
  - docs/agent_tasks/extraction_azj_edu_pass3a_provenance_capture_v1_20260607.md
  - reports/agent_jobs/extraction_azj_edu_pass3a_provenance_capture_v1_20260607/README.md
  - reports/agent_jobs/extraction_azj_edu_pass3a_provenance_capture_v1_20260607/capture_runner.py
  - reports/agent_jobs/extraction_azj_edu_pass3a_provenance_capture_v1_20260607/provenance_capture.json
  - reports/agent_jobs/extraction_azj_edu_pass3a_provenance_capture_v1_20260607/status.json
  - reports/agent_jobs/extraction_azj_edu_pass3a_provenance_capture_v1_20260607/validation.json
  - reports/agent_jobs/extraction_azj_edu_pass3a_provenance_capture_v1_20260607/raw_commands.log
  - financial-engine_v2/backend/app/services/multipass_extraction.py
  - financial-engine_v2/backend/tests/test_multipass_extraction.py
approval_required: false
timeout_seconds: 7200
output_dir: reports/agent_jobs/extraction_azj_edu_pass3a_provenance_capture_v1_20260607
mutation_mode: safe_extension
production_data_access: false
github_mutation_allowed: true
allow_audit_code_changes: true
allow_unapproved_safe_extension: true
---

# AZJ/EDU Pass 3a Provenance Capture

## Objective

Run no-write exact-document Pass 3a / multipass provenance capture for AZJ and
EDU only, after the selected-table provenance diagnostic. Decide whether both
documents prove the same missed selected-table scale propagation path.

## Target Documents

- AZJ `488d6f1a-0180-4fca-8dcf-c4cdfc0f342e`
- EDU `ac3c9ab0-e01a-4996-95f9-6466388ddc9c`

Use the exact document identities and source paths from the existing count-24
artifacts under:

- `/home/l4nd0/tenn-count24-bounded-validation-v1-20260607/reports/agent_jobs/extraction_count24_bounded_validation_v1_20260607/`
- `/home/l4nd0/tenn-count24-bounded-validation-v1-20260607/reports/agent_jobs/extraction_scale_table_source_evidence_after_count24_v1_20260607/`

## Mode

HIGH-AUTONOMY TARGETED PROVENANCE CAPTURE / SAFE EXTENSION ONLY IF PROVEN.

Risk: HIGH for financial truth.

## Hard Stops

- Do not run count-24 again.
- Do not run count-32.
- Do not run a random sample.
- Do not run broad extraction, broad backfill, or full ticker-universe
  extraction.
- Do not mutate DB, Qdrant, Redis, news stores, memory, source PDFs, prompts,
  gold labels, schema, runtime config, model config, GPU config, or production
  data.
- Do not edit source PDFs.
- Do not implement broad scale inference, nearest-$100k policy changes,
  validation-gate loosening, canonical metric expansion, disclosure promotion,
  or broad fuzzy heuristics.
- Do not merge, rebase, or absorb the dirty parent checkout.

## Required Capture Fields

For each target document:

- exact document ID, title, ticker, and source path;
- selected tables and page numbers;
- selected table headers;
- table-local scale markers;
- same-page scale markers;
- document-level scale markers;
- metric row labels selected;
- metric value cells selected where recoverable from Pass 3a markdown;
- runtime row refs if available;
- runtime per-metric source scale if available;
- runtime metric scale source labels if available;
- Pass 3a LLM output if available;
- `_common_metric_source_scale` inputs and output, or equivalent trace;
- final gate status if computable without mutation.

Mark unavailable fields as `DATA_MISSING`.

## Allowed Implementation

Allowed report-local behavior:

- read exact source PDFs;
- read exact existing parser-cache JSON and count-24 report artifacts;
- run exact-doc multipass/Pass 3a capture without DB, Qdrant, news, source-PDF,
  prompt, schema, service-config, model-config, or GPU-config mutation;
- write only the allowed report artifacts under this task's output directory.

Allowed safe extension only if AZJ and EDU prove the same root cause:

- one narrow selected-table scale binding fix when explicit table-local or
  same-page source evidence exists;
- one narrow source-bound selected-table-page scale propagation fix;
- one stricter fail-closed guard when provenance is insufficient;
- focused tests for the changed extraction contract.

## GitHub Scope

GitHub mutation is limited to:

- opening a scoped PR if the branch is clean; and
- one concise issue #96 milestone comment after meaningful completion.

Do not close, relabel, assign, milestone, or edit issue bodies.

## Validation

If report-only:

- validate this task card;
- JSON-validate report artifacts;
- run `py_compile` on the report-local runner;
- run `git diff --check`;
- run task-card `check-diff`;
- verify no source PDFs are staged;
- inspect registry active state through safe read-only evidence or record
  `DATA_MISSING`.

If code/tests change, additionally run focused pytest, `py_compile` for the
changed module, ruff if available, `git diff --cached --check`, and commit only
scoped allowed files.

## Final Decision

End with exactly one:

- `READY_FOR_COUNT24_RERUN_APPROVAL_PACKET`
- `NEEDS_ONE_TARGETED_REPAIR`
- `NEEDS_SCALE_TABLE_HARNESS`
- `NEEDS_PARSER_TABLE_COVERAGE_WORK`
- `BLOCKED_BY_PROVENANCE_DATA_MISSING`
- `BLOCKED_BY_POLICY`
