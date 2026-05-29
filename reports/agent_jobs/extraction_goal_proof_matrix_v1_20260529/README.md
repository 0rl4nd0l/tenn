# Extraction Goal Proof Matrix

Job: `extraction_goal_proof_matrix_v1_20260529`

Branch: `safe/extraction-goal-proof-matrix-v1-20260529`

Baseline audited: `migration/clean-runtime-baseline-reconstruct-v1` at
`e2029835efbd2eb6425f089d703841eb20625bf7`

Mode: AUDIT MODE, report-only.

## Decision

The active ten-item extraction goal is **not complete**.

The current baseline proves several scoped hardening slices, but it does not
prove full accurate extraction graduation. The third canary has not been run
under a fresh approval-required runtime task card, actual future canary payloads
have not been scored through the #97 gate, issues #96-#99 remain open, and the
open extraction PR stack still has failing checks.

No runtime reload, canary run, `POST /api/process/document`, broad extraction,
backfill, production DB write, Qdrant/news/memory mutation, source-PDF mutation,
parser/prompt/gold-label/schema change, service/GPU/model config change,
Cockpit UI work, or GitHub issue/PR mutation was performed by this task.

## Current Proof Summary

Proven for current baseline scope:

- Truth-gate hardening is present in baseline commit `5788b18a` and the
  matching report status is `completed_validated_released`.
- Advisory-only candidate exclusion is present in baseline commit `a64d2295`;
  the refreshed canary packet excludes PLS and SFR as `advisory_only_document`.
- Source-document classification is documented in
  `docs/extraction/metric_extraction_contract.md` and covered by focused tests.
- Scale Policy V1 is documented and baseline commit `26ca0c4a` covers explicit
  Rp/IDR trillion units.
- AAU period semantics hardening is integrated into baseline through `c45f8f57`
  and release commit `e2029835`.
- The pre-persistence scorecard gate exists in baseline commit `47508882` and
  remains report-local.

Partial or unproven:

- Metric ontology hardening is partially proven by contract parity and
  `metric_ontology_bridge` tests, but issue #98 remains open for persisted
  metric schema alignment.
- Real-gold/eval corpus work is partial: AAU is integrated, BHP and source-path
  portability branches are published, but the audited baseline still fails the
  targeted real-gold source-path test on the 10X host-local PDF assumption.
- The third canary approval packet exists, but it explicitly does not approve
  execution. A fresh approval-required runtime task card is still required.
- Full accurate extraction graduation remains unproven.

## Current Validation

Passed:

- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/extraction_goal_proof_matrix_v1_20260529.md`
- `python3 scripts/agent_job_registry.py check-overlap docs/agent_tasks/extraction_goal_proof_matrix_v1_20260529.md --repo-root .`
- `python3 scripts/agent_job_registry.py claim docs/agent_tasks/extraction_goal_proof_matrix_v1_20260529.md`
- JSON validation for:
  - `reports/agent_jobs/extraction_third_canary_approval_packet_refresh_v1_20260529/canary_approval_packet.json`
  - `reports/agent_jobs/extraction_pre_persistence_scorecard_gate_v1_20260529/pre_persistence_scorecard_gate_sample.json`
  - `reports/agent_jobs/extraction_contract_parity_guard_v1_20260526/metric_contract_parity_matrix.json`
- `/home/l4nd0/tenn-nvme-clean-baseline-reconstruct-v1/financial-engine_v2/.venv/bin/python -m pytest -q financial-engine_v2/backend/tests/test_extraction_pre_canary_truth_gates.py financial-engine_v2/backend/tests/test_extraction_gold_eval_scorecard.py financial-engine_v2/backend/tests/test_multipass_extraction.py financial-engine_v2/backend/tests/test_metric_ontology_bridge.py`:
  `227 passed in 2.36s`.

Expected current baseline failure:

- `/home/l4nd0/tenn-nvme-clean-baseline-reconstruct-v1/financial-engine_v2/.venv/bin/python -m pytest -q financial-engine_v2/backend/tests/test_extraction_gold_eval.py::test_load_real_gold_corpus_accepts_operating_cash_flow_alias_and_assets_exist`:
  failed on missing repo-local 10X source PDF path
  `data/asx/docs/10X/financial_performance/2026-01-29_quarterly-activities-appendix-5b-cash-flow-report_28f2a7c8-c61d-4d1b-90ff-4c41d75d23cb.pdf`.

Published branch evidence for that failure:

- `safe/extraction-real-gold-source-path-validation-baseline-v1-20260529` at
  `5395d9fb318d2c706dab7e269435aea88a88278b`.
- `safe/extraction-real-gold-source-path-resolver-v1-20260529` at
  `9fbcac9b585805151c16b03684904d87a0bed75a`.
- `safe/extraction-bhp-canary-gold-fixture-v1-20260529` at
  `fc16f2e7760e68bc7674c7af73895db899809937`.

## Open External State

Issues still open:

- #96 `[Query Orchestration] Most PDF-path documents lack terminal extraction`
- #97 `[Evaluation] Generate extracted-payload scorecard for confirmed metric coverage`
- #98 `[Financial Truth] Align persisted metric schema with extractor contract`
- #99 `[Provenance] Make real-gold source PDFs reviewable without committing raw filings`

Extraction PRs still open with failing `lint-and-test`:

- #125 `[codex] guard pre-canary truth persistence`
- #126 `[codex] exclude advisory canary candidates`
- #127 `[codex] capture BHP canary eval regression`
- #128 `[codex] resolve real-gold source path validation`

The #127 and #128 source-path-specific failure is removed on their latest heads,
but broad unrelated backend/Cockpit failures remain. #125 and #126 are older and
still show the stale source-path assertion in their CI logs.

## Next Safe Step

Do not mark the goal complete. The next non-runtime-safe cleanup is to either
update or supersede the stale extraction PR stack so the published source-path
portability evidence is not split across draft branches.

The next runtime step remains approval-gated: create a fresh
approval-required runtime task card only after exact operator approval, rerun all
immediate pre-run gates, then submit the seven documents from the approval packet
one at a time and score actual payloads through the #97 pre-persistence gate.
