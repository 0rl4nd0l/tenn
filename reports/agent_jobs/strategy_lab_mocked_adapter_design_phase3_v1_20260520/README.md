# Phase 3A Strategy Lab Mocked Adapter Design

## Confirmed Facts

- Mode was design-only safe extension: docs, mock JSON fixtures, and report outputs only.
- Requested cwd `/home/l4nd0/tenn` is a symlink to `/mnt/hdd-data/home/l4nd0/tenn`; the target was unavailable in this session.
- Phase 3A used isolated worktree `/home/l4nd0/tenn-strategy-lab-mocked-adapter-design-phase3-v1-20260520`.
- Branch: `safe/strategy-lab-mocked-adapter-design-phase3-v1-20260520`.
- Base HEAD: `6c6748fe87e57b9d3b6c890e8551e7c288bc51b0`.
- Phase 2 recommended `GO_PHASE3_MOCKED_ADAPTER_DESIGN_ONLY`.
- Phase 2 schema requires sidecar artifacts to remain pending-review evidence, not canonical financial truth.
- Phase 1 showed read/backtest/regime result shapes for public BTC/USDT sandbox evidence, but Phase 3A did not start or call QuantDinger.
- Registry validation, overlap check, and claim succeeded before output generation.

## Inferred Facts

- A future Tenn-owned wrapper can be split into `StrategyLabSidecarClient`, `StrategyLabToolPolicy`, `StrategyLabArtifactAdapter`, `MarketDataResearchClient`, `BacktestResearchClient`, and `RegimeResearchClient`.
- Phase 1/2 evidence is sufficient for a mocked `backtest_run` and `regime_breakdown` contract.
- `parameter_sweep` / `structured_tune` should remain default-hold until mocked tests and result-shape evidence exist.
- `risk_report` can only be provisional/context unless a later payload proves dedicated risk fields.

## Speculative Ideas

- A future adapter could support structured tuning as `parameter_sweep` after a separate mock-only proof of compute caps and result schema.
- A future Tenn-owned artifact store could persist quarantined raw payloads, but Phase 3A did not design or implement storage.
- Future Cockpit display could show pending-review Strategy Lab artifacts, but Cockpit is outside this task.

## DATA_MISSING

- Live MCP transport schemas.
- Structured tuning result shape.
- Experiment pipeline result shape.
- AI optimization shape.
- Benchmark fields for backtests.
- Explicit data provider field in Phase 1 backtest/regime payloads.
- Exact QuantDinger audit retention policy.
- Exact controls to disable all nonessential background workers.
- Exact GHCR image-to-source commit provenance.
- Raw payload SHA-256 for Phase 3A design fixtures.

## Phase 2 Inputs Inspected

- `artifact_schema_v1.md`
- `artifact_schema_v1.schema.json`
- `artifact_fixtures/*.json`
- `README.md`
- `phase1_payload_mapping.md`
- `schema_invariants.md`
- `validation_notes.md`
- `go_no_go_phase3.md`

Full source path:

- `/home/l4nd0/tenn-strategy-lab-artifact-schema-phase2-v1-20260520/`

## Files Written

Docs:

- `docs/strategy_lab/adapter_contract_v1.md`
- `docs/strategy_lab/adapter_tool_policy_v1.md`
- `docs/strategy_lab/adapter_request_response_envelopes_v1.md`
- `docs/strategy_lab/adapter_quarantine_policy_v1.md`
- `docs/strategy_lab/adapter_mock_test_plan_v1.md`

Mock payloads:

- `docs/strategy_lab/mock_payloads/mock_list_capabilities_result_v1.json`
- `docs/strategy_lab/mock_payloads/mock_market_snapshot_result_v1.json`
- `docs/strategy_lab/mock_payloads/mock_submit_backtest_result_v1.json`
- `docs/strategy_lab/mock_payloads/mock_get_job_result_v1.json`
- `docs/strategy_lab/mock_payloads/mock_regime_detect_result_v1.json`
- `docs/strategy_lab/mock_payloads/mock_policy_denied_trading_scope_v1.json`
- `docs/strategy_lab/mock_payloads/mock_sidecar_unavailable_v1.json`
- `docs/strategy_lab/mock_payloads/mock_schema_invalid_v1.json`
- `docs/strategy_lab/mock_payloads/mock_missing_benchmark_result_v1.json`
- `docs/strategy_lab/mock_payloads/mock_data_missing_result_v1.json`

Reports:

- `reports/agent_jobs/strategy_lab_mocked_adapter_design_phase3_v1_20260520/README.md`
- `reports/agent_jobs/strategy_lab_mocked_adapter_design_phase3_v1_20260520/phase2_schema_review.md`
- `reports/agent_jobs/strategy_lab_mocked_adapter_design_phase3_v1_20260520/tool_policy_matrix.md`
- `reports/agent_jobs/strategy_lab_mocked_adapter_design_phase3_v1_20260520/mock_envelope_review.md`
- `reports/agent_jobs/strategy_lab_mocked_adapter_design_phase3_v1_20260520/quarantine_and_error_policy.md`
- `reports/agent_jobs/strategy_lab_mocked_adapter_design_phase3_v1_20260520/go_no_go_phase3b.md`
- `reports/agent_jobs/strategy_lab_mocked_adapter_design_phase3_v1_20260520/status.json`
- `reports/agent_jobs/strategy_lab_mocked_adapter_design_phase3_v1_20260520/diff-check.json`

Task card:

- `docs/agent_tasks/strategy_lab_mocked_adapter_design_phase3_v1_20260520.md`

## Mock Tool Policy

- `list_capabilities`: `allow_mock_only`, no artifact.
- `read_market_snapshot`: `allow_mock_only`, no artifact by default.
- `submit_backtest`: `allow_mock_only`, no artifact at submission.
- `get_backtest_result` / `get_job`: `allow_mock_only`, maps to `backtest_run`.
- `regime_detect`: `allow_mock_only`, maps to `regime_breakdown`.
- `parameter_sweep` / `structured_tune`: `default_hold`.
- `export_artifact`: blocked for sidecar; Tenn-owned only.

Blocked surfaces include credentials, paper/live orders, bot activation, admin token changes, live workspace strategy mutation, quick-trade, kill-switch, Tenn store writes, parser/extraction/gold-label writes, and source-registry writes.

## Mock Request/Response Envelopes

Defined:

- `ToolCallRequest`
- `ToolCallResult`
- `PolicyDecision`
- `RawPayloadRef`
- `QuarantineResult`
- Strategy Lab artifact mapping summary

Every mock request requires `production_data_access=false`, `execution_allowed=false`, `paper_live_scope=none`, and `mock_scope=phase3a_design_only`.

## Artifact Mapping

- `backtest_run`: supported by Phase 1 payload shape, pending review only.
- `regime_breakdown`: supported by Phase 1 payload shape, pending review only.
- `parameter_sweep`: default-hold / `DATA_MISSING`.
- `risk_report`: provisional/context only.
- `strategy_idea`: Tenn/human-origin only.
- `human_review_decision`: Tenn-owned only.

All sidecar-derived artifacts preserve:

```json
{
  "canonical_financial_truth": false,
  "production_data_access": false,
  "may_write_db": false,
  "may_write_qdrant": false,
  "may_write_memory": false,
  "may_write_financial_truth": false,
  "execution_allowed": false,
  "review_status": "PENDING_REVIEW"
}
```

## Quarantine/Error Policy

Invalid output is quarantined, not normalized into a valid artifact.

Quarantine triggers include malformed output, schema failure, missing raw payload ref, hidden credential/trading/order fields, unexpected artifact type, missing assumptions/limitations, forbidden labels, store-write attempts, and suspected live/paper execution surfaces.

Missing benchmark/provider/sample/hash fields must be explicit `DATA_MISSING` or the output is invalid.

## Mock-Only Test Plan

Future Phase 3B mocked tests should cover:

- Policy allowlist tests.
- Blocked-surface tests.
- Schema mapping tests.
- Raw payload quarantine tests.
- `DATA_MISSING` propagation tests.
- Sidecar unavailable tests.
- Artifact flag invariant tests.
- No-store-write tests using mocks.
- No-token/no-service/no-network tests.
- Regression tests for forbidden broker/trading fields.

## Risks

- QuantDinger is trading-capable; policy must continue to deny W/C/T/N and trading/admin/credential surfaces.
- Missing provider and benchmark fields can invite false precision unless `DATA_MISSING` is visible.
- A future artifact store would be a higher-risk runtime/storage task and is not covered here.
- A future UI could accidentally present pending-review context as truth unless labels and review status are enforced.

## Hard Boundaries

- No real adapter/client implemented.
- No QuantDinger startup.
- No MCP startup.
- No Docker startup.
- No token issuance.
- No secrets/env config.
- No dependency installation.
- No Tenn runtime/backend code changed.
- No Cockpit edits.
- No artifact store implemented.
- No DB/Qdrant/news/memory/financial-truth writes.
- No parser/extraction/gold-label changes.
- No source-registry writes.
- No production data access.
- No paper/live/order/bot/kill-switch execution.

## Validation Results

Final validation results:

- Task-card validation: passed.
- Registry list-active/check-overlap/claim: passed.
- Mock payload JSON parse: passed.
- Phase 2 schema/fixture JSON parse: passed.
- Markdown hygiene: passed.
- `git diff --check`: passed.
- `git diff --cached --check`: passed.
- `agent_job_contract.py check-diff`: passed, with no disallowed files.
- Registry release: passed at `2026-05-21T02:30:30.132672Z`.
- Written-file proof: all staged/written files are under the task card, `docs/strategy_lab/**`, or `reports/agent_jobs/strategy_lab_mocked_adapter_design_phase3_v1_20260520/**`.
- Runtime/product proof: no staged/written files are under Tenn runtime/backend code, Cockpit, DB/Qdrant/news/memory/financial-truth stores, parser/extraction/gold-label files, source registry, Docker/systemd/env/secrets, QuantDinger runtime directories, MCP implementation, broker/exchange config, or package/dependency files.
- Service proof: final checks found no QuantDinger process and no listeners on the prior Phase 1 sandbox ports `15080`, `15432`, or `16379`; this task did not start QuantDinger, MCP, Docker, or any token service.

## Go/No-Go For Phase 3B

Recommendation: `GO_PHASE3B_MOCKED_ADAPTER_TESTS_ONLY`.

Phase 3B must remain mock-test-only. It must not authorize a real adapter/client, QuantDinger startup, MCP startup, token issuance, runtime/Cockpit integration, artifact-store implementation, store writes, production data, or paper/live execution.

## Save Recommendation

Save this design bundle as the Phase 3A mocked adapter contract baseline. Do not save any QuantDinger output as canonical Tenn financial truth.

## Final Branch / HEAD / Status

- Branch: `safe/strategy-lab-mocked-adapter-design-phase3-v1-20260520`.
- HEAD: `6c6748fe87e57b9d3b6c890e8551e7c288bc51b0`.
- Final `git status`: staged additions only for the allowlisted task card, Strategy Lab docs/mock payloads, and Phase 3A report bundle.

## Registry Release Status

Released. Final registry `list-active` returned no active jobs.
