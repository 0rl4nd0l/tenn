---
job_id: extraction_gold_source_path_resolution_v1_20260529
lane: Evaluation
supporting_lanes:
  - Provenance
owner: Codex
allowed_files:
  - docs/agent_tasks/extraction_gold_source_path_resolution_v1_20260529.md
  - financial-engine_v2/backend/tests/test_extraction_gold_eval.py
  - reports/agent_jobs/extraction_gold_source_path_resolution_v1_20260529/README.md
  - reports/agent_jobs/extraction_gold_source_path_resolution_v1_20260529/status.json
  - reports/agent_jobs/extraction_gold_source_path_resolution_v1_20260529/diff-check.json
  - docs/claude/STATE.md
approval_required: false
allow_unapproved_safe_extension: true
timeout_seconds: 3600
output_dir: reports/agent_jobs/extraction_gold_source_path_resolution_v1_20260529
mutation_mode: safe_extension
production_data_access: false
github_mutation_allowed: none
related_issue: 96
---

# Extraction Gold Source Path Resolution V1

## Objective

Remove the false missing-source signal from the real-gold eval corpus test by
using the existing allowlisted source-PDF resolver instead of checking only
`PROJECT_ROOT / source_file`.

## Scope

- Primary lane: Evaluation.
- Supporting lane: Provenance.
- Mode: SAFE EXTENSION.
- Branch: `safe/extraction-bhp-canary-gold-fixture-v1-20260529`.
- Worktree: `/home/l4nd0/tenn-extraction-bhp-canary-gold-fixture-v1-20260529`.

## Contract Check

Target system layer: Evaluation/Provenance test validation for source-asset
reviewability. This task does not invoke extraction, storage, retrieval, or
analysis.

Relevant contract rules: backend remains the sole authority; source evidence
must not be fabricated; evaluation must distinguish missing evidence from
valid host-mounted source assets; no fallback extraction, prompt change,
datastore write, parser route, runtime/model/GPU/service, schema, or Cockpit UI
change is allowed.

What must not change: production extraction/backfill behavior, canonical
financial truth persistence, DB/Qdrant/news/memory stores, source PDFs, parser
routing, extraction prompts, runtime/model/GPU/service config, schemas, Cockpit
UI, GitHub state, and canary approval packets.

Why safe: this task changes only the eval test's source-asset existence check.
The resolver is already used for confirmed metric coverage review and enforces
local PDF paths under the ASX docs allowlist.

GPU process check required: no. This task must not start, restart, or depend on
`llama-server` and must not run live extraction jobs.

## Source Evidence

- The failing 10X real-gold fixture source path:
  `data/asx/docs/10X/financial_performance/2026-01-29_quarterly-activities-appendix-5b-cash-flow-report_28f2a7c8-c61d-4d1b-90ff-4c41d75d23cb.pdf`
- The source exists on this host at:
  `/data/asx/docs/10X/financial_performance/2026-01-29_quarterly-activities-appendix-5b-cash-flow-report_28f2a7c8-c61d-4d1b-90ff-4c41d75d23cb.pdf`
- The old test failed because it checked only:
  `financial-engine_v2/data/asx/docs/10X/...`

## Hard Stops

- Do not copy or move source PDFs into the repo.
- Do not create symlinks for source PDFs.
- Do not run extraction, canaries, or backfills.
- Do not mutate production DB, Qdrant, news, memory, or source PDFs.
- Do not change parser routing, extraction prompts, schemas, runtime/model/GPU
  config, services, Cockpit UI, or GitHub state.

## Required Behavior

- Reuse the existing allowlisted source resolver for corpus source-file
  existence checks.
- Keep the test failing on genuinely missing or out-of-allowlist source PDFs.
- Preserve BHP/AAU/CLV/CTM canary regression behavior.

## Validation

- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/extraction_gold_source_path_resolution_v1_20260529.md`
- `python3 scripts/agent_job_registry.py list-active --read-only --repo-root .`
- `python3 scripts/agent_job_registry.py check-overlap docs/agent_tasks/extraction_gold_source_path_resolution_v1_20260529.md --repo-root .`
- `python3 scripts/agent_job_registry.py claim docs/agent_tasks/extraction_gold_source_path_resolution_v1_20260529.md --repo-root .`
- Full focused gold-eval pytest for
  `financial-engine_v2/backend/tests/test_extraction_gold_eval.py`.
- Targeted Ruff and `py_compile`.
- `git diff --check`.
- Source PDF/new binary staging check.
- `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/extraction_gold_source_path_resolution_v1_20260529.md --repo-root .`
- Registry release and final active-job read-only check.

## Final Report Requirements

Report branch, HEAD, worktree, task card, changed files, validation commands and
results, whether any runtime/datastore/source mutation occurred, and remaining
blockers for #96.
