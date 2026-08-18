---
job_id: extraction_native_currency_scale_policy_v1_20260529
lane: Financial Truth
supporting_lanes:
  - Evaluation
  - Provenance
owner: Codex
allowed_files:
  - docs/agent_tasks/extraction_native_currency_scale_policy_v1_20260529.md
  - reports/agent_jobs/extraction_native_currency_scale_policy_v1_20260529/README.md
  - reports/agent_jobs/extraction_native_currency_scale_policy_v1_20260529/status.json
  - reports/agent_jobs/extraction_native_currency_scale_policy_v1_20260529/diff-check.json
  - docs/extraction/metric_extraction_contract.md
  - docs/architecture/12_evaluation_and_drift_monitoring.md
  - docs/architecture/16_currency_and_fx_policy.md
  - docs/claude/STATE.md
  - financial-engine_v2/backend/app/services/multipass_extraction.py
  - financial-engine_v2/backend/tests/test_multipass_extraction.py
  - financial-engine_v2/backend/tests/test_extraction_pre_canary_truth_gates.py
approval_required: false
allow_unapproved_safe_extension: true
timeout_seconds: 3600
output_dir: reports/agent_jobs/extraction_native_currency_scale_policy_v1_20260529
mutation_mode: safe_extension
production_data_access: false
related_issue: 96
---

# Extraction Native Currency Scale Policy V1

## Objective

Close the explicit non-AUD/Rp trillion Scale Policy V1 blocker before any
third #96 canary batch.

This task adds deterministic support for source-explicit Indonesian rupiah
high-denomination units without adding FX conversion, inference, or broad
non-AUD normalization.

## Lane

Primary lane: Financial Truth.

Supporting lanes: Evaluation and Provenance.

## Execution Mode

SAFE EXTENSION, code/test/docs only.

## Session Declaration

Agent: Codex

Worktree: `/home/l4nd0/tenn-nvme-clean-baseline-reconstruct-v1`

Branch: `migration/clean-runtime-baseline-reconstruct-v1`

Issue: #96

Intended files: this task card, `multipass_extraction.py`, focused extraction
tests, extraction/currency/evaluation docs, `docs/claude/STATE.md`, and this
task's report artifacts.

Contested surfaces touched: none from the explicit contested-surface list.

Collision risk: HIGH because this touches financial-truth extraction policy,
resolved only after empty registry, task-card validation, overlap check, and
claim.

Decision: proceed after validation and registry claim.

## Contract Check

Target system layer: Extraction.

Relevant contract rules: metric extraction must extract explicit values only;
normalization may convert source-explicit units; missing or unsafe values must
fail or remain low-confidence; no fallback, parallel pipeline, canonical truth
mutation, or client-side financial interpretation is introduced.

What must not change: production extraction/backfill, production DB writes,
direct SQL mutation, Qdrant/news/memory mutation, parser routing, prompts
beyond allowed scale vocabulary, gold labels, source PDFs, runtime/model/GPU
config, services, schemas, migrations, and Cockpit UI.

Why safe: the change only recognizes explicit source-unit/currency markers
already present in table headers or row evidence, stores native values as-is,
and keeps non-AUD results marked `ok_low_confidence` with no FX conversion.

GPU process check required: no. This task does not spawn, restart, stop, or
depend on `llama-server`.

## Hard Stops

- Do not run a third canary batch.
- Do not run broad backfill.
- Do not run production extraction.
- Do not perform production DB writes.
- Do not perform direct SQL mutation.
- Do not mutate Qdrant, news, or memory stores.
- Do not edit, move, copy, delete, or commit source PDFs.
- Do not change parser routing.
- Do not mutate gold labels.
- Do not change runtime, model, or GPU config.
- Do not restart services.
- Do not implement Cockpit UI.
- Do not add schema migrations.
- Do not perform unrelated cleanup, stash, reset, delete, merge, or rebase
  operations.

## Required Behavior

- Detect explicit `Rp`, `IDR`, and rupiah table currency markers as `IDR`.
- Detect explicit `trillion`/`trillions` scale markers as `trillions`.
- Apply a deterministic `trillions` multiplier only when scale evidence is
  explicit.
- Keep non-AUD native-currency values stored as-is and return
  `ok_low_confidence` after all hard gates pass.
- Avoid using the AUD-like $500B sanity cap to reject source-explicit IDR
  trillion native values.
- Preserve existing AUD/USD million, raw-dollar units, unknown-scale, and
  source-unit mismatch gates.
- Do not add FX conversion or any inferred currency conversion.

## Validation

- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/extraction_native_currency_scale_policy_v1_20260529.md`
- `python3 scripts/agent_job_registry.py check-overlap docs/agent_tasks/extraction_native_currency_scale_policy_v1_20260529.md --repo-root .`
- `python3 scripts/agent_job_registry.py claim docs/agent_tasks/extraction_native_currency_scale_policy_v1_20260529.md`
- `python3 -m py_compile financial-engine_v2/backend/app/services/multipass_extraction.py financial-engine_v2/backend/tests/test_multipass_extraction.py financial-engine_v2/backend/tests/test_extraction_pre_canary_truth_gates.py`
- Focused pytest for touched extraction tests.
- Ruff for touched Python files.
- JSON validation for report artifacts.
- `git diff --check`.
- Source PDF/new binary staging check.
- `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/extraction_native_currency_scale_policy_v1_20260529.md`
- `python3 scripts/agent_job_registry.py release extraction_native_currency_scale_policy_v1_20260529`
- Final registry read-only check and git status.

## Final Report Requirements

Report branch, HEAD, worktree, task card path, registry status, files changed,
tests run with exact results, how the policy handles IDR/Rp trillion without FX
conversion, confirmation that no third canary/backfill/datastore mutation ran,
remaining blockers before full accurate extraction graduation, and final git
status.
