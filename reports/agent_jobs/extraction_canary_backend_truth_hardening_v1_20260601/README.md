# Extraction Canary Backend Truth Hardening V1

Status: code/test slice complete, runtime canary not rerun.

## Scope

This task hardened backend metric extraction for three source-reviewed canary
truth defects without running extraction, restarting services, or mutating
canonical stores.

- AAU-style `np_attributable` selection now repairs away from total
  comprehensive owner rows to explicit profit-after-tax rows.
- AQX-style generic profit/loss-before-tax rows now fail the canonical `ebit`
  validation gate unless explicitly labeled EBIT or operating profit/income.
- ATM-style filings now prefer explicit Indonesian statement units in millions
  over unrelated Rp-trillion summary context and retain immediate
  income-statement continuation rows for parent-owner profit selection.

## Boundaries

- No backend reload, worker reload, GPU worker action, or model/runtime spawn.
- No canary extraction, broad extraction, backfill, production DB write, direct
  SQL mutation, Qdrant write, memory write, Cockpit UI change, source-PDF
  mutation, schema migration, or GitHub mutation.
- This proves backend code/test behavior only. Corrected runtime payloads remain
  unproven until the approved backend route is rerun and scored.

## Validation

- Task-card validate: passed.
- Registry overlap: passed, only unrelated Reporting job active in a separate
  worktree.
- `test_multipass_extraction.py`: 169 passed.
- `test_extraction_pre_canary_truth_gates.py`: 16 passed.
- Targeted bundle:
  `test_multipass_extraction.py`,
  `test_extraction_pre_canary_truth_gates.py`,
  `test_prompt_model_matrix.py`,
  `test_db_integrity.py`,
  `test_extraction_gold_eval.py`,
  `test_extraction_capability_guards.py`,
  `test_pipeline_stages.py`: 269 passed, 5 existing warnings.
- Ruff on touched Python files: passed.
- `py_compile` on touched Python files: passed.
- `git diff --check`: passed.
- Task-card `check-diff`: passed with no disallowed files.

## Remaining Blockers

- Runtime canary success is still DATA_MISSING; no backend route rerun happened
  in this task.
- Full extraction across all tickers remains unproven until the corrected
  backend is rerun through bounded canary scoring and later broader evaluation.
