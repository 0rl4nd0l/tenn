# Handoff

Status: PARTIAL

## Start Here

Worktree: `/home/l4nd0/tenn-extraction-broad-approved15-current-canonical-v1-20260628`
Branch: `safe/extraction-broad-approved15-current-canonical-v1-20260628`
Head: `7a0bab4ca9337c6c9d735f23d5898d9b306ecc2d` plus local task diff
Base: `origin/migration/clean-runtime-baseline-reconstruct-v1`
Latest fetched origin head: `87e49247a0ddbf5e35fd6b7c2b61ea5a1fe9d74c`

Read in order:
1. `README.md`
2. `validation.json`
3. `source_inspection.json`
4. `scorecard_gate_after_fix.json`
5. `failure_classes_after_fix.json`
6. `row_level_failure_matrix_after_fix.json`

## What Changed

- `financial-engine_v2/backend/app/services/multipass_extraction.py`: prior SEG split-section shares fix is preserved; this continuation adds a narrow CSL-style revenue source-text reject path.
- `financial-engine_v2/backend/app/services/multipass_extraction.py`: future-sales narrative revenue can be overwritten from formal statement text when recoverable; if still sourced from rejected narrative text after statement-text recovery, only `revenue` is cleared.
- `financial-engine_v2/backend/tests/test_multipass_extraction.py`: added a CSL-style regression for narrative future-sales revenue replacement, alongside the existing SEG split-section share tests.
- Task card and report artifacts updated under this job directory.

## Evidence

Full post-SEG approved-15 replay:
- status: PARTIAL
- cases: 15
- accepted: 11
- fail_closed: 4
- infrastructure failures: 0
- side_effect_pass: true

Focused CSL replay after the new fix:
- status: PASS
- payload status: `ok_low_confidence`
- accepted: 1
- fail_closed: 0
- failed: 0
- revenue retained: false
- non-null metric count: 9
- side_effect_pass: true

Final scorecard after focused CSL replay:
- actual payload documents: 12
- result summary: `{'ambiguous_quarantined': 73, 'missing_evidence': 0, 'missing_expected_metric': 4, 'not_evaluated_no_actual_payload': 18, 'present_correct': 49, 'present_wrong_value': 2, 'unsupported_correctly_abstained': 0, 'wrong_period': 0, 'wrong_unit_currency_scale': 0}`
- gate: `blocked`
- blocking rows: 97
- note: aggregate counts are unchanged after CSL because CSL fixture rows remain `ambiguous_quarantined` under the current #97 scoring policy.

Canonical drift audit:
- latest fetched origin is seven commits ahead of this worktree head
- extraction-scope changed files: none
- drift is chat/API/test/report/task-card work outside this lane
- no merge, rebase, branch cleanup, or GitHub write was performed

## Remaining Work

- Scorecard gate remains blocked.
- Recommended next single blocker: RMS cash-flow missing metrics or QBE revenue source-text false positive.
- Keep DXS mixed scale/source selection and BHP/MIN `np_attributable` wrong-value rows parked unless explicitly selected as the one blocker class.

## Hard Boundaries

Do not mutate DB, Qdrant, Redis, news, runtime, backfills, production data, source PDFs, gold labels, prompts/models/services, branches, or GitHub issues without explicit approval.

Report-only complete; system functionality not proven.
