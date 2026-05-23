# Input Inventory

## Summary

All named local input paths for Phase 2, Phase 2B, Phase 3A, Phase 3B, Phase 3C,
and Phase 3D were available. No web or network fallback was used.

The inputs are usable for a planning-only report, but Phase 2/2B/3A/3B/3C are
not safe to treat as committed baselines because they contain untracked or
staged work.

## Phase 3D Contract Review

Path:
`/home/l4nd0/tenn-nvme-clean-baseline-reconstruct-v1/reports/agent_jobs/strategy_lab_offline_adapter_contract_review_phase3d_v1_20260521`

All required Phase 3D report inputs were present:

- `README.md`
- `contract_completeness.md`
- `safety_boundary_review.md`
- `artifact_boundary_review.md`
- `gaps_and_risks.md`
- `go_no_go_phase3e.md`
- `status.json`
- supporting `preflight.md`, `input_inventory.md`, and `diff-check.json`

Phase 3D confirmed:

- recommendation: `GO_PHASE3E_OFFLINE_IMPLEMENTATION_PLAN_ONLY`
- Phase 3C is sufficient for future implementation-plan-only work;
- Phase 3C is not sufficient for runtime, client, store, token, transport, or
  trading implementation;
- `strategy_lab_artifact_v1` remains authoritative;
- `strategy_lab_sidecar_artifact_v1` remains pre-envelope only;
- helper output cannot replace the authoritative envelope;
- only `backtest_run` and `regime_breakdown` are evidence-backed for local
  pending artifact emission;
- Phase 2/3A/3B/3C worktrees contain uncommitted, staged, or untracked
  additions.

Classification: report-only evidence and active candidate planning input.

## Worktree Inventory

| Phase | Path | Branch | HEAD | Status | Baseline safety | Classification |
|---|---|---|---|---|---|---|
| Phase 2 authoritative artifact schema | `/home/l4nd0/tenn-strategy-lab-artifact-schema-phase2-v1-20260520` | `safe/strategy-lab-artifact-schema-phase2-v1-20260520` | `6c6748fe87e57b9d3b6c890e8551e7c288bc51b0` | untracked task card, `docs/strategy_lab/**`; ignored report bundle | unsafe as committed baseline | active candidate input plus report-only evidence |
| Phase 2B helper candidate | `/home/l4nd0/tenn-strategy-lab-quantdinger-phase2-artifact-schema-v1-20260521` | `audit/strategy-lab-quantdinger-phase2-artifact-schema-v1-20260521` | `6c6748fe87e57b9d3b6c890e8551e7c288bc51b0` | untracked helper doc, service module, script test, fixtures; ignored report bundle | unsafe as committed baseline | pending-review helper candidate |
| Phase 3A mocked adapter design | `/home/l4nd0/tenn-strategy-lab-mocked-adapter-design-phase3-v1-20260520` | `safe/strategy-lab-mocked-adapter-design-phase3-v1-20260520` | `6c6748fe87e57b9d3b6c890e8551e7c288bc51b0` | staged additions in task card, `docs/strategy_lab/**`, and reports | unsafe as committed baseline | active candidate design input and report-only evidence |
| Phase 3B reconciled mocked adapter tests | `/home/l4nd0/tenn-strategy-lab-mocked-adapter-tests-phase3b-reconciled-v1-20260521` | `safe/strategy-lab-mocked-adapter-tests-phase3b-reconciled-v1-20260521` | `76042591ab19ae3ed1aba554b1635919e51d5844` | untracked task card, `docs/strategy_lab/**`, test file; ignored reports and pycache | unsafe as committed baseline | active candidate test input plus report-only evidence |
| Phase 3C offline mock transport bundle | `/home/l4nd0/tenn-strategy-lab-offline-mock-transport-phase3c-v1-20260521` | `safe/strategy-lab-offline-mock-transport-phase3c-v1-20260521` | `76042591ab19ae3ed1aba554b1635919e51d5844` | untracked task card, `docs/strategy_lab/**`, test file; ignored reports and pycache | unsafe as committed baseline | active candidate transport input plus report-only evidence |
| Phase 3D current checkout | `/home/l4nd0/tenn-nvme-clean-baseline-reconstruct-v1` | `migration/clean-runtime-baseline-reconstruct-v1` | `2bff733e2d7f8fadfde6d492a5ff48212b710f59` | pre-existing untracked Phase 3D task card plus Phase 3E task card/report work | unsafe for registry claim due unrelated dirty file | current report workspace and Phase 3D evidence host |

## File Categories

### Phase 2

Untracked active candidate inputs:

- `docs/agent_tasks/strategy_lab_artifact_schema_phase2_v1_20260520.md`
- `docs/strategy_lab/artifact_schema_v1.md`
- `docs/strategy_lab/artifact_schema_v1.schema.json`
- nine artifact fixtures under `docs/strategy_lab/artifact_fixtures/`

Ignored report-only evidence:

- `reports/agent_jobs/strategy_lab_artifact_schema_phase2_v1_20260520/README.md`
- `phase1_payload_mapping.md`
- `schema_invariants.md`
- `validation_notes.md`
- `go_no_go_phase3.md`
- `status.json`
- `diff-check.json`

### Phase 2B Helper Candidate

Untracked helper candidate files:

- `docs/agent_tasks/strategy_lab_quantdinger_phase2_artifact_schema_v1_20260521.md`
- `docs/strategy_lab_quantdinger_artifact_schema.md`
- `financial-engine_v2/backend/app/services/strategy_lab_artifact_schema.py`
- `financial-engine_v2/scripts/test_strategy_lab_artifact_schema.py`
- two fixture summaries under
  `financial-engine_v2/scripts/fixtures/strategy_lab_artifact_schema/`

Ignored report-only helper evidence:

- report README, preflight, schema contract, validation, security boundaries,
  status, diff-check;
- raw payload summaries;
- normalized pending-review `backtest_run` and `regime_breakdown` helper
  artifacts.

Classification: pending-review helper candidate. It is not authoritative.

### Phase 3A

Staged active candidate inputs:

- task card;
- five adapter design docs under `docs/strategy_lab/`;
- ten mock payloads under `docs/strategy_lab/mock_payloads/`;
- eight report files under
  `reports/agent_jobs/strategy_lab_mocked_adapter_design_phase3_v1_20260520/`.

Classification: active candidate design input. Staged state makes it unsafe to
treat as a committed baseline.

### Phase 3B

Untracked active candidate inputs:

- task card;
- authoritative Phase 2 schema/docs/fixtures copied into `docs/strategy_lab/`;
- Phase 3A adapter docs and mock payloads;
- five mock test-vector files;
- `tests/strategy_lab/test_strategy_lab_mocked_adapter_phase3b_reconciled.py`.

Ignored report-only evidence:

- Phase 3B report bundle under
  `reports/agent_jobs/strategy_lab_mocked_adapter_tests_phase3b_reconciled_v1_20260521/`.

Ignored non-source artifact:

- `tests/strategy_lab/__pycache__/test_strategy_lab_mocked_adapter_phase3b_reconciled.cpython-310.pyc`

Classification: active candidate test input plus report-only evidence. Unsafe
as committed baseline.

### Phase 3C

Untracked active candidate inputs:

- task card;
- Phase 2 schema/docs/fixtures;
- Phase 3A adapter docs and mock payloads;
- Phase 3B mock test vectors;
- two mock transport design docs;
- twelve mock transport fixtures;
- `tests/strategy_lab/test_strategy_lab_offline_mock_transport_phase3c.py`.

Ignored report-only evidence:

- Phase 3C report bundle under
  `reports/agent_jobs/strategy_lab_offline_mock_transport_phase3c_v1_20260521/`.

Ignored non-source artifact:

- `tests/strategy_lab/__pycache__/test_strategy_lab_offline_mock_transport_phase3c.cpython-310.pyc`

Classification: active candidate transport input plus report-only evidence.
Unsafe as committed baseline.

## Evidence Highlights

Phase 2 evidence:

- `strategy_lab_artifact_v1` is the authoritative schema.
- Machine-generated sidecar artifacts default to `PENDING_REVIEW`.
- Promotion to memory, financial truth, holdings, watchlist, thesis state,
  execution, paper trading, or live trading is outside the schema.
- `backtest_run` and `regime_breakdown` are evidence-backed; broader artifact
  types remain provisional or `DATA_MISSING`.

Phase 2B helper evidence:

- helper schema version is `strategy_lab_sidecar_artifact_v1`;
- helper artifacts are `PENDING_REVIEW`;
- non-observed artifact types remain `DATA_MISSING`;
- helper output is candidate pre-envelope evidence only.

Phase 3A evidence:

- mocked adapter design defines policy-before-dispatch, request/response
  envelopes, quarantine policy, and mock-only test plan;
- forbidden surfaces include credentials, paper/live orders, bot activation,
  admin token changes, runtime/Cockpit integration, store writes, parser/gold
  label writes, and source-registry writes.

Phase 3B evidence:

- tests cover helper-to-authoritative mapping, hard false flags, blocked
  surfaces, quarantine behavior, `DATA_MISSING`, and no-store-write invariants;
- no real adapter/client, runtime/backend/Cockpit code, artifact store,
  production data, Tenn store, service, token, dependency, or paper/live trading
  action was reported.

Phase 3C evidence:

- mock transport covers only offline fixtures;
- allowed mock operations include capabilities, market snapshot read, submit
  mock backtest, poll mock result, regime detect, and local mock artifact
  conversion;
- default-held operations remain `DATA_MISSING`;
- sidecar unavailable and timeout are simulated, not operational proof;
- no real API, MCP, Docker, QuantDinger service, broker/exchange, token,
  artifact store, runtime route, store write, production data, or trading
  behavior is authorized.

## DATA_MISSING

- Safe committed/consolidated baseline for Phase 2/2B/3A/3B/3C is
  `DATA_MISSING` because those worktrees contain untracked or staged work.
- Real sidecar capability, auth, transport, retry, timeout values, rate-limit
  behavior, token behavior, and raw-output storage paths remain `DATA_MISSING`.
- Evidence for `parameter_sweep`, broad `risk_report`, `factor_test`,
  `portfolio_experiment`, and production artifact-store behavior remains
  `DATA_MISSING`.
- Phase 3E did not verify production runtime behavior, production data, external
  API behavior, or live service behavior by design.
