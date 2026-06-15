---
job_id: extraction_lbl_pass3a_timeout_v1_20260615
lane: Financial Truth
supporting_lanes:
  - Evaluation
  - Reporting
owner: Codex
allowed_files:
  - docs/agent_tasks/extraction_lbl_pass3a_timeout_v1_20260615.md
  - financial-engine_v2/backend/app/services/multipass_extraction.py
  - financial-engine_v2/backend/tests/test_extraction_pre_canary_truth_gates.py
  - financial-engine_v2/backend/tests/test_multipass_extraction.py
  - reports/agent_jobs/extraction_lbl_pass3a_timeout_v1_20260615/README.md
  - reports/agent_jobs/extraction_lbl_pass3a_timeout_v1_20260615/status.json
  - reports/agent_jobs/extraction_lbl_pass3a_timeout_v1_20260615/validation.json
  - reports/agent_jobs/extraction_lbl_pass3a_timeout_v1_20260615/diff-check.json
  - reports/agent_jobs/extraction_lbl_pass3a_timeout_v1_20260615/serial_canary.log
approval_required: false
allow_unapproved_safe_extension: true
timeout_seconds: 14400
output_dir: reports/agent_jobs/extraction_lbl_pass3a_timeout_v1_20260615
mutation_mode: safe_extension
allow_audit_code_changes: true
production_data_access: false
---

# Extraction LBL Pass3a Timeout Follow-Up

## Objective

Diagnose the LBL targeted canary failure where pass3a table LLM calls timed out
and final validation failed with `validation_gate:insufficient_metrics:0`.
Apply one narrow safe extension only if current evidence proves a code change is
needed; otherwise validate the existing supported runtime setting and stop.

## Scope

Worktree:
`/home/l4nd0/tenn-lbl-pass3a-timeout-v1-20260615`.

Branch:
`safe/extraction-lbl-pass3a-timeout-v1-20260615`.

Stacked base:
`safe/extraction-lbl-companion-period-provenance-v1-20260614` at
`e13f616fca2869cd3863dd29fedd606456ed57c8`.

Mode: SAFE_EXTENSION-ELIGIBLE / STRICTLY BOUNDED / VALIDATION-FIRST.

## Input Evidence

- PR #346 targeted canary result: period binding passed, but final status failed
  with `validation_gate:insufficient_metrics:0` after local Ollama `qwen2.5:32b`
  pass3a table calls timed out.
- Source PDF:
  `/mnt/tenn-nvme2/tenn/financial-engine_v2/data/asx/docs/LBL/financial_performance/2026-02-20_1h-fy26-results-presentation_551c6b84-1053-405c-a833-4ecc018e2045.pdf`.
- User approval on 2026-06-15: proceed using subagents and goals.

## Hard Stops

- Do not broaden metric ontology, canonical coverage, or prompt semantics.
- Do not mutate DB, Qdrant, Redis, news stores, memory, source PDFs, prompts,
  gold labels, schemas, runtime config, model config, or GPU/service config.
- Do not run count-24, count-32, random samples, broad replays, backfills,
  service routes, or production mutations.
- Runtime extraction validation is limited to targeted LBL canary attempts with
  `DATA_ROOT` redirected outside the repo and no persistence to production
  stores.
- Do not modify PR #346's published branch in place.

## Required Work

- Use read-only subagents for independent diagnosis.
- First test the existing serial table extraction mode with
  `EXTRACTION_PARALLEL=0`.
- If that canary passes, report the runtime fix and do not change code.
- Write focused RED coverage before implementation when a safe code seam is
  identified.
- Keep implementation in `multipass_extraction.py`.
- Prefer deterministic table/payload reduction, retry behavior, or timeout
  containment over model/runtime configuration changes.
- Preserve source-bound period provenance and target table-local scale behavior.

## Validation

- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/extraction_lbl_pass3a_timeout_v1_20260615.md`
- focused pytest for changed pass3a behavior, only if code changes are made
- `python3 -m py_compile financial-engine_v2/backend/app/services/multipass_extraction.py`, only if code changes are made
- `git diff --check`
- JSON validation for report artifacts
- `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/extraction_lbl_pass3a_timeout_v1_20260615.md`
- At most targeted LBL canary attempts with `DATA_ROOT=/tmp/...`
