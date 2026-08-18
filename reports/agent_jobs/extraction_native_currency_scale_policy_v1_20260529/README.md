# Extraction Native Currency Scale Policy V1

## Scope

SAFE EXTENSION in the Financial Truth lane. This job closes the explicit
non-AUD/Rp trillion scale-policy blocker without running extraction, canary,
backfill, or datastore mutation.

## Implemented

- Added deterministic `trillions` scale support with multiplier
  `1_000_000_000_000`.
- Added deterministic IDR currency detection for explicit `Rp`, `IDR`, and
  rupiah source markers.
- Extended source-unit row evidence parsing so `Rp 12.5 trillion` participates
  in the existing source-unit mismatch gate.
- Added a currency-specific native sanity cap for IDR so valid rupiah trillion
  native values are not rejected by the AUD-like `$500B` cap.
- Preserved non-AUD `ok_low_confidence` behavior after all hard gates pass.

## Boundaries

- No FX conversion was added.
- No third canary batch was run.
- No broad backfill was run.
- No production extraction was run.
- No production DB or direct SQL mutation was performed.
- No Qdrant, news, memory, source-PDF, parser-routing, gold-label, runtime,
  model, GPU, service, schema, migration, or Cockpit UI changes were made.

## Validation

Completed:

- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/extraction_native_currency_scale_policy_v1_20260529.md`
- `python3 scripts/agent_job_registry.py check-overlap docs/agent_tasks/extraction_native_currency_scale_policy_v1_20260529.md --repo-root .`
- `python3 scripts/agent_job_registry.py claim docs/agent_tasks/extraction_native_currency_scale_policy_v1_20260529.md`
- `python3 -m py_compile financial-engine_v2/backend/app/services/multipass_extraction.py financial-engine_v2/backend/tests/test_multipass_extraction.py financial-engine_v2/backend/tests/test_extraction_pre_canary_truth_gates.py`
- `financial-engine_v2/.venv/bin/python -m pytest financial-engine_v2/backend/tests/test_multipass_extraction.py financial-engine_v2/backend/tests/test_extraction_pre_canary_truth_gates.py -q` (`169 passed`)
- `financial-engine_v2/.venv/bin/ruff check financial-engine_v2/backend/app/services/multipass_extraction.py financial-engine_v2/backend/tests/test_multipass_extraction.py financial-engine_v2/backend/tests/test_extraction_pre_canary_truth_gates.py`
- `jq empty reports/agent_jobs/extraction_native_currency_scale_policy_v1_20260529/status.json reports/agent_jobs/extraction_native_currency_scale_policy_v1_20260529/diff-check.json`
- `git diff --check`
- source-PDF/new binary staging check (`no output`)
- `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/extraction_native_currency_scale_policy_v1_20260529.md`
- Post-change code review pass: no critical findings, warnings, or suggestions.

## Remaining Blockers

- Third #96 canary still requires explicit operator approval.
- Global `ok_low_confidence` surfacing policy remains report-only.
- Full graduation to accurate extraction still requires an approved third canary
  and broader accuracy evidence after this policy slice.
