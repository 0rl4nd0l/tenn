# Extraction Pre-Canary Truth Gate Hardening

Date: 2026-05-28
Job: `extraction_pre_canary_truth_gate_hardening_v1_20260528`
Lane: Financial Truth
Supporting lanes: Evaluation, Provenance, Query Orchestration
Mode: audit first / narrow safe extension

## Verdict

Narrow pre-persistence guards were implemented and validated for the CLV/CTM
failure classes that previously reached canonical financial rows and `asx_docs`
Qdrant points.

Third #96 canary batch: **needs explicit approval before running**. The
CLV/CTM-like unsafe persistence classes are now blocked before row upsert and
before document chunks are embedded, but selector-side advisory exclusion and
broader raw-dollar/non-AUD policy work remain outside this patch.

No canary, extraction batch, broad backfill, production DB write, direct SQL
mutation, Qdrant/news/memory mutation, source PDF edit, prompt change, parser
routing change, gold-label mutation, runtime/model/GPU config change, service
restart, schema migration, or Cockpit UI implementation was performed.

## Evidence Audited

- Second canary failure taxonomy:
  `/home/l4nd0/tenn-extraction-second-canary-failure-taxonomy-audit-v1-20260527/reports/agent_jobs/extraction_second_canary_failure_taxonomy_audit_v1_20260527/`
- CLV/CTM exposure audit:
  `/home/l4nd0/tenn-extraction-canary-output-exposure-audit-clv-ctm-v1-20260527/reports/agent_jobs/extraction_canary_output_exposure_audit_clv_ctm_v1_20260527/`
- CLV/CTM containment:
  `reports/agent_jobs/extraction_canary_output_containment_clv_ctm_v1_20260528/`

## Guards Implemented

| Guard | Location | Behavior | CLV/CTM mapping |
| --- | --- | --- | --- |
| Advisory-only document block | `run_multipass_extraction` before Pass 1 LLM | Fails exact advisory-only titles/text such as `Quarterly Report Advisory` before metric extraction | SFR-like selector mistake is blocked before persistence, but true canary-selection exclusion remains report-only |
| Metric-label mismatch | `_validate_gate` | Fails when canonical `ebit` has row/provenance evidence explicitly naming EBITDA | Blocks CLV EBITDA-to-EBIT contamination |
| Explicit source-unit value mismatch | `_validate_gate` | Fails when row/provenance evidence has explicit million/billion values and payload magnitude differs by 100x or more | Blocks CLV `$44.1 million` becoming `$44.1 billion` |
| Source-period mismatch | `_validate_gate` | Fails when explicit source-period evidence, such as annual `year ended`, conflicts with payload `period_type` | Blocks CTM annual source persisted as `H` |

The guards fail closed. They do not correct values, infer period type, mutate
rows, mutate Qdrant points, alter prompts, alter parser routing, or add schema.

## Audit Answers

1. Advisory-only documents can be blocked at two layers. The best place is the
   canary candidate selector before submission; that selector is outside this
   task's allowed files, so it remains report-only. A narrow persistence-side
   safety net was added in `run_multipass_extraction`.
2. Metric-label mismatch is source-bound at `_validate_gate`, using row refs and
   provenance only. EBITDA cannot populate canonical `ebit`.
3. Period/source mismatch is source-bound by explicit first-page/title period
   evidence captured into the payload and checked before persistence.
4. Scale sanity now has two layers: the existing broad plausible-scale gate and
   the new row-evidence unit-value mismatch gate for explicit million/billion
   evidence.
5. Safe blockers now: advisory-only exact title/text, EBITDA-as-EBIT, explicit
   source-unit value mismatch, explicit source-period mismatch. Report-only for
   now: candidate-selector exclusion, raw-dollar policy, non-AUD/Rp trillion
   normalization, and low-confidence row surface policy.
6. Tests prove CLV/CTM-like failures fail and matching valid cases still pass in
   `financial-engine_v2/backend/tests/test_extraction_pre_canary_truth_gates.py`.

## Tests And Validation

Passed:

- `PYTHONPATH=financial-engine_v2/backend uv run --no-project --python 3.10 --with-requirements requirements.txt --with-requirements financial-engine_v2/backend/requirements-dev.txt pytest -q financial-engine_v2/backend/tests/test_extraction_pre_canary_truth_gates.py`
  - `7 passed`
- `PYTHONPATH=financial-engine_v2/backend uv run --no-project --python 3.10 --with-requirements requirements.txt --with-requirements financial-engine_v2/backend/requirements-dev.txt pytest -q financial-engine_v2/backend/tests/test_extraction_pre_canary_truth_gates.py financial-engine_v2/backend/tests/test_multipass_extraction.py`
  - `161 passed`
- `PYTHONPATH=financial-engine_v2/backend uv run --no-project --python 3.10 --with-requirements requirements.txt --with-requirements financial-engine_v2/backend/requirements-dev.txt pytest -q financial-engine_v2/backend/tests/test_extraction_pre_canary_truth_gates.py financial-engine_v2/backend/tests/test_multipass_extraction.py -k 'validate_gate or source_period_evidence or run_multipass_blocks_advisory'`
  - `12 passed, 149 deselected`
- `PYTHONPATH=financial-engine_v2/backend uv run --no-project --python 3.10 --with-requirements requirements.txt --with-requirements financial-engine_v2/backend/requirements-dev.txt pytest -q financial-engine_v2/backend/tests/test_multipass_extraction.py`
  - `161 passed`
- `uv run --no-project --python 3.10 --with ruff ruff check financial-engine_v2/backend/app/services/multipass_extraction.py financial-engine_v2/backend/tests/test_extraction_pre_canary_truth_gates.py`
  - passed
- `python3 -m py_compile financial-engine_v2/backend/app/services/multipass_extraction.py financial-engine_v2/backend/tests/test_extraction_pre_canary_truth_gates.py`
  - passed
- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/extraction_pre_canary_truth_gate_hardening_v1_20260528.md`
  - passed
- `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/extraction_pre_canary_truth_gate_hardening_v1_20260528.md --repo-root . --no-write-report`
  - passed
- `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/extraction_pre_canary_truth_gate_hardening_v1_20260528.md --repo-root .`
  - passed and wrote `diff-check.json`
- `python3 -m json.tool` for `status.json` and `diff-check.json`
  - passed
- `git diff --check`
  - passed
- Source PDF/new staged check
  - no matching source/PDF paths
- `python3 scripts/agent_job_registry.py release extraction_pre_canary_truth_gate_hardening_v1_20260528 --repo-root .`
  - released
- `python3 scripts/agent_job_registry.py list-active --read-only --repo-root .`
  - active jobs empty

## Architecture Review

Architecture-check was required because backend extraction code changed. The
`.cursor/rules/` rule files were absent in this checkout, so exact rule-file
validation remains `DATA_MISSING`.

The patch does not change embedding models, vector dimensions, vector IDs,
Qdrant distance metrics, document ID format, schema, parser routing, prompts, or
runtime config. It only changes pre-persistence extraction validation and tests.

## Remaining DATA_MISSING

- `.cursor/rules/` architecture rule files are absent from this worktree.
- Canary candidate-selection code was not changed, so advisory-only documents
  are not yet excluded before canary selection.
- Raw-dollar scale policy for AM5/AQX/CRS-like cases remains unresolved. Those
  cases abstained safely in the second canary, but the policy is not improved by
  this patch.
- Non-AUD/Rp trillion handling remains abstain/quarantine policy work.
- `ok_low_confidence` financial-row surface policy remains report-only; this
  patch blocks CLV by source evidence rather than changing low-confidence row
  semantics globally.
- No live canary/backfill smoke was run by instruction.

## GitHub Update

GitHub auth was available. A status-only comment was posted to #96:
`https://github.com/0rl4nd0l/tenn/issues/96#issuecomment-4562123193`

No issue closure, relabel, assignment, milestone change, or body edit was made.

## Project Memory

Project Memory save is recommended. Durable takeaway: CLV/CTM unsafe persistence
is now guarded by source-bound pre-persistence validation, while third-canary
execution still needs explicit approval because selector-side and broader scale
policy work remains incomplete.
