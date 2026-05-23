# Preservation Model

## Decision

Preserve the Strategy Lab evidence by separating authoritative candidates,
pending-review helper evidence, report/task-history evidence, archive-only
duplicates, and generated exclusions. Do not move, commit, stage, unstage,
copy, clean, or delete anything in Phase 3F.

## Authoritative Candidate Set

These are the candidate files most likely to become baseline Strategy Lab
evidence under a future approved consolidation task:

- Phase 2 `docs/strategy_lab/artifact_schema_v1.md`
- Phase 2 `docs/strategy_lab/artifact_schema_v1.schema.json`
- Phase 2 `docs/strategy_lab/artifact_fixtures/*.json`
- Phase 3A `docs/strategy_lab/adapter_contract_v1.md`
- Phase 3A `docs/strategy_lab/adapter_tool_policy_v1.md`
- Phase 3A `docs/strategy_lab/adapter_request_response_envelopes_v1.md`
- Phase 3A `docs/strategy_lab/adapter_quarantine_policy_v1.md`
- Phase 3A `docs/strategy_lab/adapter_mock_test_plan_v1.md`
- Phase 3A `docs/strategy_lab/mock_payloads/*.json`
- Phase 3B `docs/strategy_lab/mock_test_vectors/*.json`
- Phase 3B `tests/strategy_lab/test_strategy_lab_mocked_adapter_phase3b_reconciled.py`
- Phase 3C `docs/strategy_lab/mock_transport/*.md`
- Phase 3C `docs/strategy_lab/mock_transport_fixtures/*.json`
- Phase 3C `tests/strategy_lab/test_strategy_lab_offline_mock_transport_phase3c.py`

The authoritative line remains:

- `strategy_lab_artifact_v1` is the authoritative envelope.
- `strategy_lab_sidecar_artifact_v1` is pending-review pre-envelope evidence
  only.
- `backtest_run` and `regime_breakdown` are the only evidence-backed local
  sidecar artifact types today.
- `parameter_sweep`, broad `risk_report`, `factor_test`, and
  `portfolio_experiment` remain `DATA_MISSING` or default-hold.

## Report Evidence To Preserve

The report bundles should be preserved as audit/history evidence if the project
wants the Phase 2 to Phase 3F chain to survive checkout cleanup:

- Phase 2 schema report bundle.
- Phase 2B helper report bundle, including raw payload summaries and normalized
  helper artifacts.
- Phase 3A design report bundle.
- Phase 3B mocked-test report bundle.
- Phase 3C mock-transport report bundle.
- Phase 3D contract-review report bundle.
- Phase 3E implementation-plan report bundle.
- Phase 3F consolidation/save-plan report bundle.

Because `reports/` is ignored, a future save task must explicitly decide
whether to force-add report evidence or leave it as external local evidence.

## Helper Candidate Material

Phase 2B should be retained only as pending-review helper evidence:

- `docs/strategy_lab_quantdinger_artifact_schema.md`
- `financial-engine_v2/backend/app/services/strategy_lab_artifact_schema.py`
- `financial-engine_v2/scripts/test_strategy_lab_artifact_schema.py`
- `financial-engine_v2/scripts/fixtures/strategy_lab_artifact_schema/*.json`
- Phase 2B raw payload summaries.
- Phase 2B normalized helper artifacts.

This material should not be wired into runtime/backend/product code and should
not supersede the Phase 2 authoritative schema without separate review.

## Duplicate Or Superseded Material

Archive, but do not promote as current baseline:

- Older `strategy_lab_quantdinger_framework_v1_20260520` report bundles copied
  under Phase 3B and Phase 3C worktrees.
- Copied Phase 2 schema files inside Phase 3B/3C should be treated as copies
  for local tests, not independent sources.
- Any Phase 2B helper schema semantics that conflict with
  `strategy_lab_artifact_v1` should be superseded by the authoritative schema.

## Generated Exclusions

Exclude generated files from preservation:

- Phase 3B `tests/strategy_lab/__pycache__/**`
- Phase 3C `tests/strategy_lab/__pycache__/**`

## Task Cards

Preserve these task cards as task-history evidence if preserving the phase chain:

- Phase 2 task card.
- Phase 2B task card.
- Phase 3A task card.
- Phase 3B task card.
- Phase 3C task card.
- Phase 3D task card.
- Phase 3E task card.
- Phase 3F task card.

The current checkout specifically has untracked Phase 3D and Phase 3E task
cards. They should be resolved by a future task-history preservation decision,
not cleaned by Phase 3F.

## Preservation Boundary

No preservation action should be performed until a later task card explicitly
allows the exact paths to be committed, force-added, archived, copied, staged,
unstaged, or cleaned.
