# Phase 2 Strategy Lab Artifact Schema

Job: `strategy_lab_artifact_schema_phase2_v1_20260520`

Mode: schema-only safe extension, report and docs only.

Go/no-go for Phase 3: `GO_PHASE3_MOCKED_ADAPTER_DESIGN_ONLY`.

## Confirmed Facts

- The requested `/home/l4nd0/tenn` path is a broken symlink to `/mnt/hdd-data/home/l4nd0/tenn`; `/mnt/hdd-data/home` is absent in this session.
- The shared fast checkout `/home/l4nd0/tenn-fast-dev-storage-v1` had unrelated dirty Cockpit, docs, Appendix 5B, parser, and script work.
- This Phase 2 job used a clean isolated worktree: `/home/l4nd0/tenn-strategy-lab-artifact-schema-phase2-v1-20260520`.
- Branch: `safe/strategy-lab-artifact-schema-phase2-v1-20260520`.
- HEAD: `6c6748fe87e57b9d3b6c890e8551e7c288bc51b0`.
- Task card validated.
- Registry `list-active` returned `active_jobs: []` before claim.
- Registry `check-overlap` passed in the isolated worktree.
- Registry claim succeeded.
- Phase 1 raw backtest and regime payloads were available and inspected.
- R+B-only Phase 1 token proof, W/T denials, T-scope issuance denial, no credential use, no paper/live execution, and full QuantDinger cleanup were confirmed from Phase 1 reports.
- `docs/strategy_lab/**` did not exist before this job in the isolated worktree.
- No Tenn runtime, Cockpit, DB, Qdrant, news, memory, financial-truth, parser, extraction, gold-label, Docker, systemd, env, secret, QuantDinger service, MCP service, token, broker, exchange, paper, or live execution surface was modified.

## Inferred Facts

- QuantDinger Phase 1 backtest output is strong enough to shape `backtest_run` artifacts.
- QuantDinger Phase 1 regime output is strong enough to shape `regime_breakdown` artifacts.
- `risk_report` can later reuse some backtest risk metrics, but a dedicated risk schema remains partial.
- `parameter_sweep`, `factor_test`, and `portfolio_experiment` need more payload evidence before they can become more than provisional artifact types.

## Speculative Ideas

- A future offline validator could recursively scan for hidden credential and execution fields before artifact review.
- A future mocked adapter design could normalize saved Phase 1 payloads without starting QuantDinger.
- A future Strategy Lab review queue could use these artifacts as research context only.

## DATA_MISSING

- Benchmark object and benchmark returns in Phase 1 backtest.
- Explicit upstream provider field in Phase 1 payloads.
- Strategy code hash.
- Raw payload SHA-256 values in this schema-only job.
- Backtest volatility, Sortino, turnover, exposure, and drawdown series.
- Regime sample size by regime and non-null segment start/end times.
- Structured tuning / parameter sweep result shape.
- Factor-test result shape.
- Portfolio-experiment result shape.
- Dedicated risk-report result shape.
- Live MCP transport schemas.
- Exact audit retention policy.
- Exact GHCR image-to-source commit provenance.

## Files Written

- `docs/agent_tasks/strategy_lab_artifact_schema_phase2_v1_20260520.md`
- `docs/strategy_lab/artifact_schema_v1.md`
- `docs/strategy_lab/artifact_schema_v1.schema.json`
- `docs/strategy_lab/artifact_fixtures/valid_backtest_run_v1.json`
- `docs/strategy_lab/artifact_fixtures/valid_regime_breakdown_v1.json`
- `docs/strategy_lab/artifact_fixtures/valid_strategy_idea_v1.json`
- `docs/strategy_lab/artifact_fixtures/invalid_canonical_truth_v1.json`
- `docs/strategy_lab/artifact_fixtures/invalid_execution_allowed_v1.json`
- `docs/strategy_lab/artifact_fixtures/invalid_missing_provenance_v1.json`
- `docs/strategy_lab/artifact_fixtures/invalid_financial_truth_label_v1.json`
- `docs/strategy_lab/artifact_fixtures/invalid_credentials_field_v1.json`
- `docs/strategy_lab/artifact_fixtures/invalid_memory_or_financial_truth_write_v1.json`
- `reports/agent_jobs/strategy_lab_artifact_schema_phase2_v1_20260520/README.md`
- `reports/agent_jobs/strategy_lab_artifact_schema_phase2_v1_20260520/phase1_payload_mapping.md`
- `reports/agent_jobs/strategy_lab_artifact_schema_phase2_v1_20260520/schema_invariants.md`
- `reports/agent_jobs/strategy_lab_artifact_schema_phase2_v1_20260520/validation_notes.md`
- `reports/agent_jobs/strategy_lab_artifact_schema_phase2_v1_20260520/go_no_go_phase3.md`
- `reports/agent_jobs/strategy_lab_artifact_schema_phase2_v1_20260520/status.json`
- `reports/agent_jobs/strategy_lab_artifact_schema_phase2_v1_20260520/diff-check.json`

## Phase 1 Inputs Inspected

- `README.md`
- `preflight.md`
- `runtime_footprint.md`
- `permission_token_proof.md`
- `mcp_api_observed.md`
- `backtest_payload_observed.md`
- `schema_fit_phase1.md`
- `security_risks_phase1.md`
- `go_no_go_phase2.md`
- `raw_payloads/backtest_raw.json`
- `raw_payloads/backtest_normalized_summary.json`
- `raw_payloads/regime_detect_raw.json`
- `raw_payloads/regime_detect_normalized_summary.json`
- `raw_payloads/capability_probe_raw.json`
- `raw_payloads/startup_probe_raw.json`

## Phase 1 Payload Fields Mapped

Backtest:

- Request fields: `market`, `symbol`, `timeframe`, `start_date`, `end_date`, `initial_capital`, `commission`, `slippage`, `leverage`, `trade_direction`, `code`.
- Job fields: `job_id`, `kind`, `status`, `request`, `result`, `error`, `progress`, `created_at`, `started_at`, `finished_at`.
- Result fields: `annualReturn`, `equityCurve`, `executionAssumptions`, `maxDrawdown`, `profitFactor`, `sharpeRatio`, `totalCommission`, `totalProfit`, `totalReturn`, `totalTrades`, `trades`, `winRate`.

Regime:

- Request fields: corrected `market`, `symbol`, `timeframe`, `startDate`, `endDate`.
- Failed first attempt: snake_case dates returned `time data 'None' does not match format '%Y-%m-%d'`.
- Result fields: `version`, `market`, `symbol`, `timeframe`, `regime`, `label`, `confidence`, `features`, `strategyFamilies`, `segments`.

## Schema Invariants

- All safety/truth flags must remain literal `false`.
- Sidecar artifacts must default to `review_status=PENDING_REVIEW`.
- `financial_truth` and generic `source-backed` labels are forbidden for sidecar outputs.
- QuantDinger artifacts require `raw_payload_ref`.
- Backtest and regime artifacts require `data_source`.
- Benchmark must be present or explicitly explained as `DATA_MISSING`.
- Limitations must be non-empty.
- Broker/exchange credential fields and hidden order/execution fields are rejected or quarantined.
- `human_review_decision` is Tenn-owned only.

## Invalid Fixture Cases

- `invalid_canonical_truth_v1.json`
- `invalid_execution_allowed_v1.json`
- `invalid_missing_provenance_v1.json`
- `invalid_financial_truth_label_v1.json`
- `invalid_credentials_field_v1.json`
- `invalid_memory_or_financial_truth_write_v1.json`

## Risks

- QuantDinger is trading-capable; future tasks must continue denying W/C/T/N unless explicitly approved.
- Public backtest output can look precise but is not financial truth.
- Missing benchmark/provider/hash fields could create false confidence if not kept visible.
- A future adapter could drift into runtime integration unless kept mocked and report-only.
- A future review UI could accidentally present pending artifacts as recommendations unless labels and limitations are enforced.

## Hard Boundaries

- No artifact store implemented.
- No adapter implemented.
- No Cockpit code changed.
- No Tenn runtime code changed.
- No production data touched.
- No Tenn stores written.
- No QuantDinger, MCP, Docker, or systemd services started.
- No token issued.
- No broker, exchange, paper, or live execution happened.
- No parser, extraction, or gold-label files changed.
- No autonomous loops or scheduled jobs added.

## Validation Results

- Task-card validation: PASS.
- Registry `list-active` before claim: PASS, `active_jobs=[]`.
- Registry `check-overlap`: PASS in isolated worktree.
- Registry claim: PASS.
- JSON parse validation for schema: PASS.
- JSON parse validation for all fixtures: PASS.
- `jsonschema` dependency: not installed; no dependency added.
- Runtime validator implementation: not done by design.
- Markdown/doc sanity: report files are plain Markdown; no repo markdown linter was found or run.
- `git diff --check`: PASS.
- `agent_job_contract.py check-diff`: PASS; `disallowed_files=[]`, report written to `diff-check.json`.
- QuantDinger container check: PASS; no `quantdinger` / `tenn_quantdinger` matches in `docker ps`.
- QuantDinger volume check: PASS; no `quantdinger` / `tenn_quantdinger` matches in `docker volume ls`.
- Phase 1 sandbox listener check: PASS; no listeners on `15080`, `15432`, `16379`, or `18888`.
- Phase 1 `/tmp` sandbox check: PASS; `/tmp/tenn-quantdinger-phase1-sandbox-v1-20260520` absent.

## Go / No-Go For Phase 3

Recommendation: `GO_PHASE3_MOCKED_ADAPTER_DESIGN_ONLY`.

This does not authorize artifact-store implementation, live adapter implementation, Cockpit/backend/runtime integration, QuantDinger startup, token issuance, production data access, store writes, or trading execution.

## Save Recommendation

Save this Phase 2 bundle as the Strategy Lab artifact-schema baseline. Do not save any QuantDinger output as Tenn canonical financial truth.

## Final Branch / HEAD / Status

- Branch: `safe/strategy-lab-artifact-schema-phase2-v1-20260520`.
- HEAD: `6c6748fe87e57b9d3b6c890e8551e7c288bc51b0`.
- Final `git status --short --untracked-files=all`: visible changes are only the task card and `docs/strategy_lab/**`.
- Report files are under ignored `reports/agent_jobs/strategy_lab_artifact_schema_phase2_v1_20260520/**`.

## Registry Release Status

- Registry release: PASS.
- Final registry `list-active`: PASS, `active_jobs=[]`.
- Release status path: `reports/agent_jobs/strategy_lab_artifact_schema_phase2_v1_20260520/status.json`.
