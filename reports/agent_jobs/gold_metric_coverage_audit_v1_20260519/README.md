# Gold Metric Coverage Audit v1

Job: `gold_metric_coverage_audit_v1_20260519`
Mode: `AUDIT ONLY`
Primary lane: Evaluation
Supporting lane: Financial Truth
Worktree: `/home/l4nd0/tenn-runtime` -> `/home/l4nd0/tenn-nvme-clean-baseline-reconstruct-v1`
Branch/HEAD: `migration/clean-runtime-baseline-reconstruct-v1` / `2e73de32ac77`

## 1. Executive verdict

Current scorecard status: Tenn already has three scorecard concepts in code, but only the first two are attached to current real-gold required scoring. `canonical_core` is the strict 10-document no-regression anchor with `24` expected checks across `revenue`, `operating_cash_flow`, and `net_debt`. `expanded_required` is the current full real-gold required subset with `15` documents and `39` expected checks over the same three metric families. `confirmed_metric_coverage` exists as a read-only broader coverage profile over `15` backend eval fixtures with `146` metric expectations, `73` scorable rows, `70` candidate rows, `3` ambiguous rows, and `0` unsupported rows.

Current evidence does not support a broad production extraction coverage claim. It supports a narrow no-regression claim for `canonical_core`, a broader required-subset stability claim for `expanded_required`, and an inventory/readiness claim for `confirmed_metric_coverage`. No current generated extraction-run artifact was found that scores all confirmed coverage rows against fresh extracted payloads.

Gold Metric Coverage Audit v1 is complete as an audit and scorecard design report. It is not blocked by missing extraction execution because extraction execution is outside the hard boundary. The remaining gaps are classified as `DATA_MISSING` rather than filled by running extraction or mutating gold labels.

## 2. Confirmed facts

Exact high-signal files and reports inspected:

- `docs/validation_baseline.md`
- `docs/architecture/12_evaluation_and_drift_monitoring.md`
- `docs/extraction/metric_extraction_contract.md`
- `docs/extraction/supplemental_metric_normalization_report.md`
- `docs/extraction/supplemental_metric_normalization_registry.yaml`
- `docs/ops/extraction-truth/phase-02-accuracy-report.md`
- `docs/ops/extraction-truth/phase-03-contract-map.md`
- `docs/ops/extraction-truth/phase-05-canonical-eval-policy.md`
- `financial-engine_v2/data/extraction_gold_real/README.md`
- `financial-engine_v2/data/extraction_gold_real/*.json`
- `financial-engine_v2/backend/tests/eval_fixtures/*.json`
- `financial-engine_v2/backend/tests/fixtures/extraction_eval/*.json`
- `financial-engine_v2/backend/tests/fixtures/extraction_gold/*.json`
- `financial-engine_v2/backend/app/services/extraction_eval.py`
- `financial-engine_v2/backend/app/services/extraction_gold_eval.py`
- `financial-engine_v2/backend/app/services/extraction_gold_eval_scorecard.py`
- `financial-engine_v2/backend/app/services/confirmed_metric_coverage_review.py`
- `financial-engine_v2/backend/app/services/multipass_extraction.py`
- `financial-engine_v2/backend/app/services/validation/extraction_schemas.py`
- `financial-engine_v2/backend/app/main.py`
- `financial-engine_v2/backend/tests/test_extraction_gold_eval_scorecard.py`
- `financial-engine_v2/backend/tests/test_confirmed_metric_coverage_api.py`
- `financial-engine_v2/backend/tests/test_confirmed_metric_coverage_review.py`
- `financial-engine_v2/backend/tests/test_extraction_eval.py`
- `financial-engine_v2/backend/tests/eval_config.json`
- `scripts/run_real_extraction_eval.py`
- `scripts/extraction_gold_eval_scorecard.py`
- `financial-engine_v2/reports/extraction_baseline.json`
- `reports/agent_jobs/appendix5b_fifth_doc_approval_packet_v1_20260517/README.md`
- `reports/agent_jobs/appendix5b_fifth_doc_approval_packet_v1_20260517/approval_packet.json`
- `cockpit-ui/components/cockpit/verification/tabs/gold-eval-tab-panel.tsx`
- `cockpit-ui/components/cockpit/verification/tabs/metric-coverage-tab-panel.tsx`

Existing corpora and manifests found:

- `canonical_core`: `financial-engine_v2/data/extraction_gold_real plus profile canonical_core`; docs `10`; metrics labelled `{'net_debt': 7, 'operating_cash_flow': 10, 'revenue': 7}`; current use: Strict Docling no-regression anchor only. Limitation: Ten-document subset and three metric families only; not production coverage.
- `expanded_required`: `financial-engine_v2/data/extraction_gold_real plus profile expanded_required`; docs `15`; metrics labelled `{'net_debt': 12, 'operating_cash_flow': 15, 'revenue': 12}`; current use: Full current real-gold required-metric subset for stability tracking. Limitation: Still restricted to three supported required metrics and missing source URLs for all fixtures.
- `confirmed_metric_coverage`: `financial-engine_v2/backend/tests/eval_fixtures plus read-only coverage profile`; docs `15`; metrics labelled `{'capex': 12, 'cash_end': 15, 'ebit': 11, 'financing_cf': 15, 'investing_cf': 15, 'net_debt': 11, 'np_attributable': 13, 'operating_cf': 15, 'revenue': 13, 'shares_outstanding': 13}`; current use: Read-only breadth inventory and future coverage scorecard input; current profile has no extracted payload scoring in this audit. Limitation: No current generated report artifact found under reports/extraction_eval; candidate and ambiguous rows must not be counted as extractor failures.
- `synthetic_extraction_eval_fixtures`: `financial-engine_v2/backend/tests/fixtures/extraction_eval`; docs `16`; metrics labelled `{'cash_end': 1, 'ebit': 4, 'net_debt': 1, 'np_attributable': 2, 'operating_cf': 3, 'revenue': 11, 'shares_outstanding': 1}`; current use: Evaluator behavior and no-regression unit coverage. Limitation: Synthetic fixtures do not prove production document extraction accuracy.
- `real_gold_evaluator_unit_fixtures`: `financial-engine_v2/backend/tests/fixtures/extraction_gold`; docs `4`; metrics labelled `{'capex': 1, 'ebit': 2, 'net_debt': 1, 'np_attributable': 1, 'operating_cf': 1, 'revenue': 2}`; current use: Unit tests for real-gold scorer semantics. Limitation: Not a production corpus.
- `appendix5b_local_approval_packet`: `reports/agent_jobs/appendix5b_fifth_doc_approval_packet_v1_20260517`; docs `1`; metrics labelled `{'operating_cash_flow': 1}`; current use: Evidence packet only in this branch; not active gate scoring. Limitation: Current branch lacks Appendix 5B scorer/gate scripts referenced by prior task language.
- `supplemental_metric_normalization_spec`: `docs/extraction/supplemental_metric_normalization_registry.yaml`; docs `DATA_MISSING`; metrics labelled `{'curated_supplemental_raw_names': 337, 'curated_supplemental_datapoints': 539, 'exhaustive_row_labels': 2999, 'exhaustive_datapoints': 18652}`; current use: Design reference for future breadth; explicitly spec-only. Limitation: Does not change runtime extraction, evaluator behavior, canonical labels, or production scoring.
- `legacy_extraction_baseline_report`: `financial-engine_v2/reports/extraction_baseline.json`; docs `9`; metrics labelled `{'metric_count': 10}`; current use: Historical baseline only. Limitation: Locked 2026-03-27 and not the current canonical10 or confirmed coverage profile.

Canonical10 document IDs:

- `bhp_a_2021-06-30_difficult`
- `bhp_a_2025-06-30`
- `eqr_q_2025-12-31`
- `gre_q_2024-12-31`
- `gre_q_2025-09-30`
- `min_h_2025-12-31`
- `qbe_h_2025-06-30`
- `rio_a_2023-12-31`
- `rio_a_2024-12-31`
- `tls_h_2025-12-31`

Existing scorecards and what they prove:

- `canonical_core`: code-defined profile in `financial-engine_v2/backend/app/services/extraction_gold_eval_scorecard.py`; `10` documents, `24` required checks. Proves strict no-regression only for the canonical subset.
- `expanded_required`: same real-gold corpus source, `15` documents, `39` required checks. Proves current required-subset stability only.
- `confirmed_metric_coverage`: read-only profile over backend eval fixtures. It inventories broader schema-supported source-evidenced metrics and can score only eligible confirmed rows if extracted payloads are supplied. No extracted payloads were supplied in this audit.

Existing validation baselines and what they prove:

- `docs/validation_baseline.md` records canonical evaluation and financial metric validation commands, but does not by itself prove current broad production extraction coverage.
- `financial-engine_v2/reports/extraction_baseline.json` is a historical 2026-03-27 baseline with 9 fixtures, 10 metric fields, and model/backend metadata. It is not the current canonical10 strict Docling scorecard.
- `docs/ops/extraction-truth/phase-02-accuracy-report.md` records historical real-gold accuracy over 10 docs and explicitly notes remaining open items and unit-only improvements. It must not be reused as a current production breadth claim.
- `financial-engine_v2/backend/tests/test_confirmed_metric_coverage_api.py` asserts the current read-only profile shape: 15 fixtures, 146 expectations, 73 scorable, 70 candidate, 3 ambiguous, 0 unsupported. That is inventory/readiness evidence, not a fresh extraction accuracy run.

## 3. Inferred facts

Scoring is intentionally narrow. Current real-gold required scoring accepts only `revenue`, `operating_cash_flow`, and `net_debt`. The runtime extractor schema supports more fields, but those additional fields are not promoted into `canonical_core` or `expanded_required` scoring.

Confirmed-but-unscored metrics likely exist in the backend eval fixtures. The current profile reports 73 scorable confirmed expectations across the broader fixture set, including `ebit`, `np_attributable`, `investing_cf`, `financing_cf`, `capex`, `cash_end`, and `shares_outstanding`, but these are not part of the current real-gold required scorecards.

Some documentation and UI surfaces can overclaim if read casually. `gold-eval-tab-panel.tsx` displays metric/context/trust accuracy for the real-gold runner without front-loading that the score is narrow. `docs/architecture/12_evaluation_and_drift_monitoring.md` still says the fixture pool is 13 JSON fixtures while the current repo has 15. `financial-engine_v2/backend/tests/eval_config.json` still describes a 6-fixture regression gate. These are wording/staleness risks, not evidence of broad coverage.

## 4. Speculative claims

The repo appears to be partway through a transition from a narrow no-regression scorecard toward broader confirmed metric coverage. That transition is represented in code and tests, but the current branch does not include a current generated confirmed coverage report artifact or live extraction result for that broader profile.

## 5. DATA_MISSING

See `reports/agent_jobs/gold_metric_coverage_audit_v1_20260519/DATA_MISSING.md` for the machine-readable gap list. Highest-impact gaps are:

- No current generated real-gold extraction result artifact was found in this worktree.
- No current generated confirmed metric coverage artifact was found under `reports/extraction_eval`.
- Current branch lacks the Appendix 5B gate scripts named in the task prompt.
- `source_url` is missing for all current real-gold fixtures.
- Tier 2 and Tier 3 metric acceptance criteria are incomplete for EBITDA, EPS, free cash flow, margins, ratios, segment metrics, and derived net debt.

## 6. Corpus inventory

The full structured inventory is `corpus_inventory.json`. Summary:

- `canonical_core`: `10` docs, `24` checks, metrics `['revenue', 'operating_cash_flow', 'net_debt']`. Use: no-regression. Limitation: not broad production coverage.
- `expanded_required`: `15` docs, `39` checks, same metrics `['revenue', 'operating_cash_flow', 'net_debt']`. Use: broader required-subset stability. Limitation: still only three metric families.
- `confirmed_metric_coverage`: `15` fixtures, `146` expectations, `73` scorable, `70` candidate, `3` ambiguous. Use: read-only breadth profile. Limitation: no extracted payload scoring in this audit.
- `synthetic_extraction_eval_fixtures`: `16` unit fixtures. Use: evaluator behavior. Limitation: synthetic fixtures are not production accuracy evidence.
- `real_gold_evaluator_unit_fixtures`: unit fixtures for trusted/abstain/quarantine semantics. Limitation: not production corpus.
- `appendix5b_local_approval_packet`: `1` PRM OCF evidence packet. Use: source evidence only. Limitation: not active gate scoring in this branch.
- `supplemental_metric_normalization_spec`: spec-only supplemental breadth inventory. Use: design reference. Limitation: does not change runtime/evaluator/canonical labels.
- `legacy_extraction_baseline_report`: historical baseline. Use: historical context only. Limitation: not current canonical10.

## 7. Metric inventory

The full structured inventory is `metric_inventory.json`. Summary:

- `revenue`: tier `Tier 1`; schema `True`; classification `REQUIRED_SCORED`; scoring `canonical_core and expanded_required real-gold profiles`; evidence `financial-engine_v2/data/extraction_gold_real, financial-engine_v2/backend/tests/eval_fixtures, financial-engine_v2/backend/app/services/multipass_extraction.py, financial-engine_v2/backend/app/services/extraction_gold_eval_scorecard.py`; notes: Tier 1 top-line metric. Required in real-gold profiles where visible and schema-supported.
- `operating_cash_flow`: tier `Tier 1`; schema `True`; classification `REQUIRED_SCORED`; scoring `canonical_core and expanded_required real-gold profiles`; evidence `financial-engine_v2/data/extraction_gold_real, financial-engine_v2/backend/tests/eval_fixtures, financial-engine_v2/backend/app/services/multipass_extraction.py, financial-engine_v2/backend/app/services/extraction_gold_eval_scorecard.py`; notes: Tier 1 alias for operating_cf. Required in all current real-gold documents.
- `net_debt`: tier `Tier 1`; schema `True`; classification `REQUIRED_SCORED`; scoring `canonical_core and expanded_required real-gold profiles`; evidence `financial-engine_v2/data/extraction_gold_real, financial-engine_v2/backend/tests/eval_fixtures, financial-engine_v2/backend/app/services/multipass_extraction.py, financial-engine_v2/backend/app/services/extraction_gold_eval_scorecard.py`; notes: Tier 1 in current real-gold profiles when explicitly labelled; derived debt-minus-cash net debt must stay ambiguous until definition is agreed.
- `ebit`: tier `Tier 2`; schema `True`; classification `CONFIRMED_UNSCORED`; scoring `confirmed_metric_coverage profile only; not canonical/expanded real-gold required scoring`; evidence `financial-engine_v2/backend/tests/eval_fixtures, financial-engine_v2/backend/app/services/multipass_extraction.py, financial-engine_v2/backend/app/services/extraction_gold_eval_scorecard.py`; notes: Tier 2 schema-supported extraction field and confirmed coverage candidate/scored row, but not part of current real-gold required scoring.
- `np_attributable`: tier `Tier 2`; schema `True`; classification `CONFIRMED_UNSCORED`; scoring `confirmed_metric_coverage profile only; not canonical/expanded real-gold required scoring`; evidence `financial-engine_v2/backend/tests/eval_fixtures, financial-engine_v2/backend/app/services/multipass_extraction.py, financial-engine_v2/backend/app/services/extraction_gold_eval_scorecard.py`; notes: Tier 2 schema-supported profit attributable field and confirmed coverage candidate/scored row, but not current canonical/expanded required scoring.
- `investing_cf`: tier `Tier 3`; schema `True`; classification `CONFIRMED_UNSCORED`; scoring `confirmed_metric_coverage profile only; not canonical/expanded real-gold required scoring`; evidence `financial-engine_v2/backend/tests/eval_fixtures, financial-engine_v2/backend/app/services/multipass_extraction.py, financial-engine_v2/backend/app/services/extraction_gold_eval_scorecard.py`; notes: Schema-supported cash-flow field present in backend eval fixtures; not in real-gold required profiles.
- `financing_cf`: tier `Tier 3`; schema `True`; classification `CONFIRMED_UNSCORED`; scoring `confirmed_metric_coverage profile only; not canonical/expanded real-gold required scoring`; evidence `financial-engine_v2/backend/tests/eval_fixtures, financial-engine_v2/backend/app/services/multipass_extraction.py, financial-engine_v2/backend/app/services/extraction_gold_eval_scorecard.py`; notes: Schema-supported cash-flow field present in backend eval fixtures; not in real-gold required profiles.
- `capex`: tier `Tier 2`; schema `True`; classification `CONFIRMED_UNSCORED`; scoring `confirmed_metric_coverage profile only; not canonical/expanded real-gold required scoring`; evidence `financial-engine_v2/backend/tests/eval_fixtures, financial-engine_v2/backend/app/services/multipass_extraction.py, financial-engine_v2/backend/app/services/extraction_gold_eval_scorecard.py`; notes: Tier 2 if explicitly reported with agreed convention. Schema-supported, but definition can vary across capex, PP&E purchases, and investing sub-items.
- `cash_end`: tier `Tier 2`; schema `True`; classification `CONFIRMED_UNSCORED for cash_end; generic cash remains AMBIGUOUS_OR_DERIVED`; scoring `confirmed_metric_coverage profile only; not canonical/expanded real-gold required scoring`; evidence `financial-engine_v2/backend/tests/eval_fixtures, financial-engine_v2/backend/app/services/multipass_extraction.py, financial-engine_v2/backend/app/services/extraction_gold_eval_scorecard.py`; notes: Tier 2 cash equivalent when it means ending cash/cash equivalents. Generic cash must not be collapsed into this without evidence.
- `shares_outstanding`: tier `Tier 2`; schema `True`; classification `CONFIRMED_UNSCORED`; scoring `confirmed_metric_coverage profile only; not canonical/expanded real-gold required scoring`; evidence `financial-engine_v2/backend/tests/eval_fixtures, financial-engine_v2/backend/app/services/multipass_extraction.py, financial-engine_v2/backend/app/services/extraction_gold_eval_scorecard.py`; notes: Tier 2 only when explicitly reported with period-end count and scale evidence. Schema-supported and present in confirmed coverage fixtures.
- `total_debt`: tier `Tier 2`; schema `False`; classification `EXTRACTOR_OUTPUT_BUT_NOT_GOLD`; scoring `internal extractor capture/derivation support only; not persisted or gold-scored`; evidence `financial-engine_v2/backend/app/services/multipass_extraction.py`; notes: Extractor prompt can capture total_debt internally for derived net_debt, but it is not in the final persisted metric field set or real-gold scoring.
- `ebitda`: tier `Tier 2`; schema `False`; classification `UNSUPPORTED`; scoring `not supported by current runtime extraction schema or real-gold scorer`; evidence `docs/extraction/supplemental_metric_normalization_registry.yaml`; notes: Tier 2/3 depending definition. Not runtime schema-supported in current extraction/gold scorer; supplemental registry mentions underlying_ebitda as spec-only.
- `eps`: tier `Tier 2`; schema `False`; classification `UNSUPPORTED`; scoring `not supported by current runtime extraction schema or real-gold scorer`; evidence `docs/extraction/supplemental_metric_normalization_registry.yaml`; notes: Tier 2 if explicitly reported, but not runtime schema-supported or gold-scored; supplemental spec notes currency/scale caveats.
- `cash`: tier `Tier 2`; schema `False`; classification `AMBIGUOUS_OR_DERIVED`; scoring `do not hard-score without explicit schema/evidence/definition agreement`; evidence `DATA_MISSING`; notes: Ambiguous generic family. Use cash_end only when source definition matches ending cash/cash equivalents.
- `free_cash_flow`: tier `Tier 2`; schema `False`; classification `AMBIGUOUS_OR_DERIVED`; scoring `do not hard-score without explicit schema/evidence/definition agreement`; evidence `docs/extraction/supplemental_metric_normalization_registry.yaml`; notes: Tier 2 only when explicitly reported and definition agreed. Current runtime schema does not support it as a stored extraction field.
- `margins`: tier `Tier 3`; schema `False`; classification `AMBIGUOUS_OR_DERIVED`; scoring `do not hard-score without explicit schema/evidence/definition agreement`; evidence `DATA_MISSING`; notes: Tier 3 derived ratios. Do not hard-score without source definition and schema support.
- `ratios`: tier `Tier 3`; schema `False`; classification `AMBIGUOUS_OR_DERIVED`; scoring `do not hard-score without explicit schema/evidence/definition agreement`; evidence `DATA_MISSING`; notes: Tier 3. Derived or definition-dependent; not current extraction gold scoring.
- `growth_rates`: tier `Tier 3`; schema `False`; classification `AMBIGUOUS_OR_DERIVED`; scoring `do not hard-score without explicit schema/evidence/definition agreement`; evidence `DATA_MISSING`; notes: Tier 3 derived/comparative metrics; not current extraction gold scoring.
- `segment_metrics`: tier `Tier 3`; schema `False`; classification `AMBIGUOUS_OR_DERIVED`; scoring `do not hard-score without explicit schema/evidence/definition agreement`; evidence `DATA_MISSING`; notes: Tier 3 breadth. Requires separate schema and segment identity definitions before scoring.
- `peer_relative_metrics`: tier `Tier 3`; schema `False`; classification `AMBIGUOUS_OR_DERIVED`; scoring `do not hard-score without explicit schema/evidence/definition agreement`; evidence `DATA_MISSING`; notes: Tier 3 comparative analytics, not document extraction gold labels.

## 8. Current scorecard critique

What `canonical_core` proves: strict no-regression for a fixed 10-document subset under the canonical real-gold profile. It checks required metric values and context/trust behavior for `revenue`, `operating_cash_flow`, and `net_debt` only.

What `canonical_core` does not prove: broad production extraction coverage, Tier 2 metric correctness, Tier 3 derived metric correctness, live runtime quality outside the canonical tuple, or coverage over all schema-supported extractor fields.

What `expanded_required` proves: stability over the current 15-document real-gold required subset, still using the same three supported required metric families.

What `expanded_required` does not prove: all schema-supported metric coverage, all production-relevant metric breadth, or confirmed coverage for EBIT, NPAT, capex, cash, shares, EPS, EBITDA, free cash flow, margins, ratios, segments, or peer-relative metrics.

Why `confirmed_metric_coverage` is needed: current extraction truth work has more evidence than the narrow required metrics, but those rows need a separate scorecard so Tenn can report breadth without polluting canonical no-regression semantics. It also prevents candidate, ambiguous, unsupported, and missing-evidence rows from being silently counted as extractor failures.

## 9. Proposed scorecard design

- `canonical_core`: purpose Strict stable no-regression anchor. Eligibility: Only explicit required real-gold metrics in the canonical 10-document subset: revenue, operating_cash_flow, net_debt. Acceptance language: canonical_core passed; this is a no-regression result for the strict canonical subset only.
- `expanded_required`: purpose Current required-metric subset across the larger/evolving real-gold corpus. Eligibility: Same supported required metrics as real-gold scorer: revenue, operating_cash_flow, net_debt across all current real-gold fixtures. Acceptance language: expanded_required passed for the current required-metric subset; it does not measure all schema-supported or production-relevant metrics.
- `confirmed_metric_coverage`: purpose Production-relevant breadth over confirmed, source-evidenced, schema-supported metrics. Eligibility: Score only metrics with source_status/source evidence, schema support, and non-ambiguous definition. Candidate, ambiguous, unsupported, and DATA_MISSING rows remain inventory rows, not failures. Acceptance language: confirmed_metric_coverage reports breadth over confirmed schema-supported evidence. Candidate, ambiguous, unsupported, and DATA_MISSING rows are disclosed separately and are not silently counted as extractor failures.

Recommended shared reporting rule: every accuracy or coverage number must be printed with `profile`, `document_count`, `metric_check_count`, `eligible_metric_count`, `candidate_count`, `ambiguous_count`, `unsupported_count`, and `DATA_MISSING_count`. Reports must say whether the number is no-regression, required-subset stability, or confirmed coverage.

## 10. Safe implementation roadmap

1. Scorecard schema/reporting design: add or finalize output schemas that force profile names and separate accuracy, trust, coverage, candidate, ambiguous, unsupported, and DATA_MISSING counts.
2. Evaluator inventory fixtures: add tests that load current fixtures and assert the profile split without running extraction.
3. Confirmed metric coverage read-only profile: generate and store a current report artifact from existing fixtures only, with no extraction execution and no canonical label writes.
4. Tests to prevent overclaiming: enforce wording/output rules so canonical results cannot be labelled as production coverage.
5. Later evaluator implementation: only after the above, wire optional extracted payload scoring for eligible confirmed rows.

No parser, prompt, canonical-write, DB, Qdrant, runtime, or production extraction changes are needed for the next task.

## 11. Hard stops / do-not-do

- Do not promote Tier 3 metrics into hard scoring without explicit source evidence, schema support, and definition agreement.
- Do not treat unsupported, ambiguous, candidate, or DATA_MISSING metrics as extractor failures.
- Do not run live extraction, Docling extraction, service starts, runtime restarts, DB writes, Qdrant writes, memory writes, or canonical gold label edits to close this audit.
- Do not merge Appendix 5B approval-packet evidence into an active gate unless the gate stack exists in the target branch and a separate bounded implementation task is approved.
- Do not use `canonical_core` or historical `extraction_baseline.json` as a broad production extraction accuracy claim.

## 12. Validation commands run

- `pwd` -> `/home/l4nd0/tenn-nvme-clean-baseline-reconstruct-v1`
- `readlink -f /home/l4nd0/tenn-runtime` -> `/home/l4nd0/tenn-nvme-clean-baseline-reconstruct-v1`
- `git branch --show-current` -> `migration/clean-runtime-baseline-reconstruct-v1`
- `git rev-parse --short=12 HEAD` -> `2e73de32ac77`
- `git status --short` -> pre-existing unrelated untracked task cards plus this audit card after creation.
- `git worktree list` -> current worktree plus many safe/appendix5b and related worktrees; no active claim came from this command.
- `git show --stat --oneline --no-renames HEAD` -> `2e73de32 milestone(evaluation): checkpoint nvme runtime audit artifacts`, 20 report/task artifacts changed in HEAD.
- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/gold_metric_coverage_audit_v1_20260519.md` -> passed.
- `python3 scripts/agent_job_registry.py list-active` -> one active Query Orchestration job, `cockpit_chat_control_prompt_guard_tests_v1_20260519`.
- `python3 scripts/agent_job_registry.py check-overlap docs/agent_tasks/gold_metric_coverage_audit_v1_20260519.md` -> blocked only by unrelated untracked task-card files outside this audit scope; no active Evaluation/Financial Truth overlap found, so report-only work continued without claiming registry.
- `rg`, `find`, `sed`, and read-only Python/JQ-style JSON inventory commands -> inspected docs, tests, scorecard helpers, fixtures, and reports listed in this report.
- `financial-engine_v2/.venv/bin/python` read-only profile import -> current profile inventory: canonical_core 10 docs/24 checks; expanded_required 15 docs/39 checks; confirmed_metric_coverage 15 fixtures/146 expectations/73 scorable/70 candidate/3 ambiguous/0 unsupported.
- `financial-engine_v2/.venv/bin/python` JSON sanity check over `corpus_inventory.json`, `metric_inventory.json`, and `scorecard_proposal.json` -> all parsed successfully.
- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/gold_metric_coverage_audit_v1_20260519.md` after report write -> passed with `ok: true`.
- `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/gold_metric_coverage_audit_v1_20260519.md` -> wrote `reports/agent_jobs/gold_metric_coverage_audit_v1_20260519/diff-check.json` and returned `ok: false` only because two unrelated pre-existing untracked Cockpit chat task cards are outside this card's `allowed_files`.
- `git status --short --untracked-files=all` -> three untracked task cards: two unrelated Cockpit chat cards plus this audit card.
- `git status --short --ignored --untracked-files=all docs/agent_tasks/gold_metric_coverage_audit_v1_20260519.md reports/agent_jobs/gold_metric_coverage_audit_v1_20260519` -> audit card is untracked and all report artifacts are ignored report files.
- `find reports/agent_jobs/gold_metric_coverage_audit_v1_20260519 -maxdepth 1 -type f -printf '%P %s bytes\n' | sort` -> confirmed `DATA_MISSING.md`, `README.md`, `corpus_inventory.json`, `diff-check.json`, `metric_inventory.json`, and `scorecard_proposal.json`.
- `python3 scripts/agent_job_registry.py list-active` final check -> `active_jobs: []`.

Final `check-diff` cannot pass in this shared worktree without either broadening this audit card to include unrelated Cockpit chat task cards or cleaning/stashing unrelated user work. Both actions are outside this audit boundary, so the failure is recorded rather than absorbed.

## 13. Final git status

Plain final status:

```text
?? docs/agent_tasks/cockpit_chat_control_prompt_guard_tests_v1_20260519.md
?? docs/agent_tasks/cockpit_chat_orchestration_side_effect_audit_v1_20260519.md
?? docs/agent_tasks/gold_metric_coverage_audit_v1_20260519.md
```

Ignored report status for this audit path:

```text
?? docs/agent_tasks/gold_metric_coverage_audit_v1_20260519.md
!! reports/agent_jobs/gold_metric_coverage_audit_v1_20260519/DATA_MISSING.md
!! reports/agent_jobs/gold_metric_coverage_audit_v1_20260519/README.md
!! reports/agent_jobs/gold_metric_coverage_audit_v1_20260519/corpus_inventory.json
!! reports/agent_jobs/gold_metric_coverage_audit_v1_20260519/diff-check.json
!! reports/agent_jobs/gold_metric_coverage_audit_v1_20260519/metric_inventory.json
!! reports/agent_jobs/gold_metric_coverage_audit_v1_20260519/scorecard_proposal.json
```

## 14. Registry release status

No registry claim was taken. The initial overlap check was blocked by unrelated untracked task-card artifacts, so this audit continued report-only without claiming. Final registry check reported `active_jobs: []`; there is nothing to release.

## 15. Project Memory save recommendation

`SAVE_RECOMMENDED`. This audit establishes naming and claim boundaries that future extraction/evaluation sessions should reuse: `canonical_core` is no-regression only, `expanded_required` is required-subset stability only, and `confirmed_metric_coverage` is the production breadth profile that separates coverage misses from trust failures and candidate/ambiguous/unsupported rows.
