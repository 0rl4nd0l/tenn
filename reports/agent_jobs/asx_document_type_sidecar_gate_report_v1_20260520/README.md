# ASX Document-Type Sidecar Gate Report v1

## Executive Verdict

`ASX_SIDECAR_GATE_PASS`

The ASX document-type fixture, pure classifier, and sidecar artifact generator are internally consistent as offline metadata artifacts. This gate does not promote the sidecar into parser routing or production extraction.

## Confirmed Facts

- Runtime preflight was taken from `/home/l4nd0/tenn-runtime`, resolving to `/home/l4nd0/tenn-nvme-clean-baseline-reconstruct-v1` on branch `migration/clean-runtime-baseline-reconstruct-v1` at `8e38d26725e3`.
- The runtime registry had `active_jobs=[]`.
- The runtime worktree had one unrelated untracked task card: `docs/agent_tasks/route_parity_home_news_status_audit_v1_20260521.md`.
- To preserve that unrelated dirt and satisfy overlap checks, this gate ran in clean isolated worktree `/home/l4nd0/tenn-asx-document-type-sidecar-gate-report-v1-20260520` from the same `8e38d26725e3` baseline.
- The isolated task card validated with `ok=true`, registry overlap was `ok=true`, and the registry claim succeeded.
- All fixture JSON files parse.
- All fixture and manifest records set `canonical_write=false`.
- Fixture expected document-type coverage includes every required type: `annual_report, half_year_report, appendix_4c, appendix_4d, appendix_4e, appendix_5b, other_asx_announcement, unknown_or_abstain`.
- Focused fixture contract tests passed: `9 passed, 1 warning`.
- Focused classifier tests passed: `9 passed, 1 warning`.
- Focused sidecar tests passed: `11 passed, 1 warning`.
- Combined ASX gate passed: `29 passed, 1 warning`.
- Compile gate passed with no cache workaround needed.
- Sidecar generation wrote exactly 9 JSON sidecars under `reports/agent_jobs/asx_document_type_sidecar_gate_report_v1_20260520/generated_sidecars`.
- Generated sidecars validated with `jq empty`.
- Every generated sidecar has `artifact_type=asx_document_type_sidecar_v1` and `canonical_write=false`.
- No production routing file checked imports `asx_document_type_classifier` or `asx_document_type_sidecar`.
- No backend app file imports the classifier or sidecar outside the two ASX service modules.

## Inferred Facts

- Because the generator consumes only the manifest-listed fixtures and writes only to the explicit report directory, the generated sidecars are report artifacts only, not production outputs.
- Because sidecars include compact evidence fields and omit surrogate/full-text keys, they do not contain full PDF text or large source blobs.
- Because the classifier imports only standard-library roots and the sidecar only imports the classifier plus standard-library modules, this stack is isolated from backend startup and runtime services.

## DATA_MISSING

None for the ASX sidecar gate. The runtime `check-overlap` caveat is environmental dirt from an unrelated task card, not missing ASX evidence; the clean isolated worktree overlap check passed.

## Test Results

- Fixture JSON parse loop: passed.
- Fixture contract: `uv run --with pytest python -m pytest financial-engine_v2/backend/tests/test_asx_document_type_fixture_contract.py -q` -> `9 passed, 1 warning`.
- Pure classifier: `uv run --with pytest python -m pytest financial-engine_v2/backend/tests/test_asx_document_type_classifier.py -q` -> `9 passed, 1 warning`.
- Sidecar: `uv run --with pytest python -m pytest financial-engine_v2/backend/tests/test_asx_document_type_sidecar.py -q` -> `11 passed, 1 warning`.
- Combined ASX: `uv run --with pytest python -m pytest financial-engine_v2/backend/tests/test_asx_document_type_fixture_contract.py financial-engine_v2/backend/tests/test_asx_document_type_classifier.py financial-engine_v2/backend/tests/test_asx_document_type_sidecar.py -q` -> `29 passed, 1 warning`.
- Compileall: passed.

## Generated Sidecars

- Count: `9`.
- Expected count: `9`.
- Path: `reports/agent_jobs/asx_document_type_sidecar_gate_report_v1_20260520/generated_sidecars`.
- Validation: `jq empty` passed for every generated JSON file.

## Sidecar Schema Summary

Generated sidecars use these fields: `abstain, abstain_reasons, artifact_type, canonical_write, classifier_version, confidence_band, document_id, document_type, fixture_id, generated_at, input_checksum, negative_evidence, positive_evidence, schema_version, source, ticker, warnings`.

The sidecar artifact is metadata-only. It records document identity, fixture identity, ticker, classifier version, document type, confidence band, abstain status, compact positive/negative evidence, abstain reasons, warnings, generation timestamp, input checksum, schema version, and `canonical_write=false`.

## Fixture Expectation Comparison

| Fixture | Expected | Sidecar | Abstain | Canonical Write |
| --- | --- | --- | --- | --- |
| `ambiguous_appendix_4d_4e_abstain` | `unknown_or_abstain` | `unknown_or_abstain` | `true` | `false` |
| `annual_report_basic` | `annual_report` | `annual_report` | `false` | `false` |
| `appendix_4c_quarterly_cashflow` | `appendix_4c` | `appendix_4c` | `false` | `false` |
| `appendix_4d_half_year_results` | `appendix_4d` | `appendix_4d` | `false` | `false` |
| `appendix_4e_preliminary_final` | `appendix_4e` | `appendix_4e` | `false` | `false` |
| `appendix_5b_mining_cashflow` | `appendix_5b` | `appendix_5b` | `false` | `false` |
| `half_year_report_basic` | `half_year_report` | `half_year_report` | `false` | `false` |
| `other_asx_announcement_investor_presentation` | `other_asx_announcement` | `other_asx_announcement` | `false` | `false` |
| `unknown_low_signal` | `unknown_or_abstain` | `unknown_or_abstain` | `true` | `false` |

## Production-Boundary Import Check

Checked production routing files:

- `financial-engine_v2/backend/app/services/multipass_extraction.py`
- `financial-engine_v2/backend/app/services/method_isolated_extraction.py`
- `financial-engine_v2/backend/app/services/pipeline.py`
- `financial-engine_v2/backend/app/services/docling_extract.py`

Result: no imports of `asx_document_type_classifier` or `asx_document_type_sidecar` were found in those files. An app-wide grep excluding the two ASX service modules also found no imports in backend routes, Qdrant, news, memory, Cockpit, or Home surfaces.

## Canonical Write Confirmation

- Fixture manifest `canonical_write=false`: yes.
- Every fixture `canonical_write=false`: yes.
- Every classifier result `canonical_write=false`: yes.
- Every generated sidecar `canonical_write=false`: yes.

## Explicit Non-Promotion Statement

- This does not approve parser routing.
- This does not approve canonical writes.
- This does not approve extraction integration.

## What This Enables Next

- A future approval-gated promotion discussion can cite one checkpointed gate report instead of scattered test output.
- Future parser-routing design can consume this as evidence that the offline metadata stack is coherent, but only after a separate task card explicitly authorizes routing work.
- Evaluation/provenance work can reference the report-local sidecars as metadata examples without touching production extraction.

## What Remains Blocked

- Parser routing and extraction integration remain blocked.
- Canonical writes and financial truth persistence remain blocked.
- Production data access, DB/Qdrant/memory/news/Cockpit/Home/runtime/model/GPU changes remain blocked.
- Gold-label and canonical scorecard changes remain blocked.

## Final Git Status

- Isolated gate worktree: expected clean after the gate packet commit is created.
- Runtime worktree after fast-forwarding the committed packet should still show only the pre-existing unrelated task card: `?? docs/agent_tasks/route_parity_home_news_status_audit_v1_20260521.md`.
- No source-code dirt and no uncommitted gate-report dirt are expected after closeout.

## Registry Release Status

- Claimed: yes.
- Released: yes.
- Release command result: `ok=true`.
- Removed active record: `/mnt/sdb2/home/l4nd0/tenn/.git/tenn-agent-registry/active/asx_document_type_sidecar_gate_report_v1_20260520.json`.
- Final `list-active`: `active_jobs=[]`.

## Project Memory Save Recommendation

Save this gate after the final commit hash is known: ASX document-type sidecar gate passed as an offline metadata artifact only, with 9 generated report-local sidecars, `canonical_write=false` throughout, no production routing imports, and no parser/extraction promotion.
