---
job_id: extraction_atm_idr_scale_normalization_fix_v1_20260601
lane: Financial Truth
supporting_lanes:
  - Evaluation
  - Provenance
owner: Codex
allowed_files:
  - docs/agent_tasks/extraction_atm_idr_scale_normalization_fix_v1_20260601.md
  - docs/claude/STATE.md
  - financial-engine_v2/backend/app/services/multipass_extraction.py
  - financial-engine_v2/backend/tests/test_multipass_extraction.py
  - reports/agent_jobs/extraction_atm_idr_scale_normalization_fix_v1_20260601/README.md
  - reports/agent_jobs/extraction_atm_idr_scale_normalization_fix_v1_20260601/status.json
  - reports/agent_jobs/extraction_atm_idr_scale_normalization_fix_v1_20260601/validation.json
  - reports/agent_jobs/extraction_atm_idr_scale_normalization_fix_v1_20260601/diff-check.json
approval_required: true
timeout_seconds: 7200
output_dir: reports/agent_jobs/extraction_atm_idr_scale_normalization_fix_v1_20260601
mutation_mode: safe_extension
requested_mutation_mode: atm_idr_scale_normalization_code_fix
production_data_access: false
github_mutation_allowed: none
related_issue: 96
operator_approval_source: "User approved full production runtime necessary to complete the extraction goal; the immediately preceding bounded canary scorecard at e4a20c91 proved the remaining blocker is ATM scale quarantine."
---

# Extraction ATM IDR Scale Normalization Fix V1

## Objective

Fix the remaining ATM canary scale blocker proven by
`reports/agent_jobs/extraction_post_truth_hardening_canary_rerun_v1_20260601/canary_real_gold_scorecard.json`.

The runtime accepted all seven documents, but ATM still quarantines on
`context_mismatch:scale` because the runtime payload reports values in IDR
millions while the source-reviewed real-gold fixture expects raw IDR units.

## Approved Scope

Allowed code surface:

- `financial-engine_v2/backend/app/services/multipass_extraction.py`

Allowed tests:

- `financial-engine_v2/backend/tests/test_multipass_extraction.py`

Allowed reports/docs:

- this task card
- `docs/claude/STATE.md`
- this task report bundle

Not approved:

- runtime extraction rerun
- backend/worker/router restart
- direct DB mutation
- broad backfill
- source PDF mutation
- fixture/gold-label mutation
- parser routing or prompt redesign outside the scale normalization bug
- schema/migration changes
- Qdrant/news/memory/Cockpit/GitHub mutation

## Session Declaration

Agent: Codex

Branch: `migration/clean-runtime-baseline-reconstruct-v1`

Worktree: `/home/l4nd0/tenn-nvme-clean-baseline-reconstruct-v1`

Lane: Financial Truth

Execution mode: SAFE EXTENSION, code/test only.

Intended files: this task card, `multipass_extraction.py`,
`test_multipass_extraction.py`, report bundle, and `docs/claude/STATE.md`.

Contested surfaces touched: extraction service logic only.

Collision risk: HIGH because this changes financial-truth scale normalization.
Proceed only after registry claim and overlap check.

Decision: proceed after task-card validation, overlap check, and claim.

## Contract Check

Target system layers: Metric Extraction normalization and Evaluation.

Relevant contract rules: `SYSTEM_CONTRACT.md` §1.1 backend source of truth,
§2 mandatory flow, §3.3 explicit-only metric extraction, and §3.5
normalization.

What must not change: source PDFs, gold fixtures, database rows, parser routing,
prompts, schemas/migrations, Qdrant/news/memory/Cockpit/GitHub state, and
non-ATM canary behavior except through general scale normalization rules.

Why safe: the fix is bounded to deterministic normalization of explicit source
statement units already extracted from the document, adds regression coverage,
and performs no runtime or datastore write in this card.

GPU process check required: no, this code/test card does not spawn or depend on
llama-server runtime.

## Validation

- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/extraction_atm_idr_scale_normalization_fix_v1_20260601.md --write-report`
- `python3 scripts/agent_job_registry.py list-active --read-only --repo-root .`
- `python3 scripts/agent_job_registry.py check-overlap docs/agent_tasks/extraction_atm_idr_scale_normalization_fix_v1_20260601.md --repo-root .`
- `python3 scripts/agent_job_registry.py claim docs/agent_tasks/extraction_atm_idr_scale_normalization_fix_v1_20260601.md --repo-root .`
- Focused failing regression for ATM IDR millions normalization.
- Focused multipass extraction regression tests.
- Targeted Ruff on touched files.
- `python3 -m py_compile financial-engine_v2/backend/app/services/multipass_extraction.py`
- `git diff --check`
- `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/extraction_atm_idr_scale_normalization_fix_v1_20260601.md --repo-root .`
- Registry release and final active-job read-only check.
