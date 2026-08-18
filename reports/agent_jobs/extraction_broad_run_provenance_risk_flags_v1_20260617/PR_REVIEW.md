# Tenn Code Review

Decision: `pass_with_risk`

## Findings

No blocking findings.

## Review Evidence

- Branch: `safe/extraction-broad-run-provenance-risk-flags-v1-20260617`
- HEAD before commit: `6eff52404af61b9717bffb5a250e06209713d517`
- Base: `origin/migration/clean-runtime-baseline-reconstruct-v1`
- Task card: `docs/agent_tasks/extraction_broad_run_provenance_risk_flags_v1_20260617.md`
- Diff scope: allowed files only by `check-diff`

## Scope Review

- The code change is limited to `financial-engine_v2/scripts/broad_extraction_test.py`.
- Tests are limited to `financial-engine_v2/scripts/test_broad_extraction_test.py`.
- No `multipass_extraction.py`, prompt, persistence, validation-gate, schema, runtime, source PDF, gold-label, DB, Qdrant, Redis, news, memory, model, GPU, service, GitHub, push, or PR mutation.

## Behavior Review

- Broad-run records now expose existing payload provenance fields when present.
- Missing provenance is explicit at per-metric and document levels.
- Scale/magnitude risk flags are machine-readable and report-only.
- Summary rollups are added for provenance coverage and risk flags.
- Existing extraction acceptance semantics are unchanged.

## Validation Reviewed

- RED targeted tests failed as expected before implementation.
- Focused GREEN: `3 passed, 6 deselected`.
- Full script tests: `9 passed`.
- `py_compile`: exit `0`.
- `ruff`: exit `0`.
- `git diff --check`: exit `0`.
- task-card validate: `ok: true`.
- task-card check-diff: `ok: true`, `disallowed_files: []`.

## Residual Risk

- No broad-run fixture/replay was run in this slice by design.
- Some deeper table/cell provenance remains `DATA_MISSING` because Pass 4 does not expose those fields yet.
- `field_provenance.excerpt` may currently duplicate `row_ref`; this implementation reports it as-is.
