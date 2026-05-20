# M3 - Strategy Lab Artifact Contract

Primary output: `artifact_schema_v1.md`.

## Contract Position

Strategy Lab artifacts are Evaluation/Reporting artifacts. They are not financial truth, memory truth, broker state, or canonical market data.

Every artifact must:

- be immutable after creation; amendments create a new revision;
- include provenance and source-of-idea fields;
- include parameters, assumptions, data source, benchmark, timestamp, limitations, result status, and evidence label;
- distinguish raw external results from Tenn interpretation;
- carry `production_data_access=false` unless a future task card explicitly authorizes otherwise;
- use `DATA_MISSING` rather than fabricated missing data;
- be reviewable by a human before any result affects Cockpit guidance, Watchlist priority, thesis memory, or portfolio decisions.

## Artifact Families

| Artifact | Purpose | Primary Lane | Canonical Truth? |
| --- | --- | --- | --- |
| Strategy idea | Capture an investable hypothesis or trading rule idea. | Evaluation | no |
| Backtest run | Record one executed historical test. | Evaluation | no |
| Parameter sweep | Compare parameterized backtest variants. | Evaluation | no |
| Factor test | Assess whether a factor signal has explanatory or ranking value. | Evaluation | no |
| Regime breakdown | Segment performance by market/regime state. | Evaluation | no |
| Risk report | Describe drawdown, concentration, liquidity, and fragility risks. | Evaluation/Reporting | no |
| Portfolio experiment | Simulate allocation or rebalancing choices. | Evaluation | no |
| Autonomous opportunity note | Record a machine-suggested research opportunity. | Evaluation/Memory support | no |
| Human review decision | Capture approval/rejection/deferral. | Evaluation/Reporting | no |

## Evidence Labels

Recommended initial labels:

- `external_tool_context`: QuantDinger or another sidecar produced the artifact.
- `backtest_result`: historical backtest output, non-canonical and non-predictive.
- `parameter_sweep_result`: optimizer/tuning output, non-canonical.
- `regime_context`: regime classifier/comparator output.
- `portfolio_simulation`: portfolio experiment, not holdings truth.
- `human_reviewed`: operator reviewed the artifact.
- `missing_required_evidence`: required input/result unavailable.
- `blocked_execution_surface`: live/paper/broker action was requested or implied and blocked.

These labels should map into Tenn's existing source-label taxonomy without becoming `financial_truth`.

## Required Common Envelope

See `artifact_schema_v1.md` for the detailed schema. The common envelope is:

- `schema_version`
- `artifact_id`
- `artifact_type`
- `job_id`
- `created_at`
- `created_by`
- `tenant_scope`
- `production_data_access`
- `source_of_idea`
- `external_engine`
- `provenance`
- `parameters`
- `assumptions`
- `data_source`
- `benchmark`
- `limitations`
- `result_status`
- `evidence_label`
- `evidence_labels`
- `review_status`
- `canonical_financial_truth`
- `storage_policy`
- `data_missing`
- `raw_result_ref`
- `derived_summary`

## Human Review Rules

- `PENDING_REVIEW`: default for all machine-generated artifacts.
- `APPROVED_FOR_RESEARCH`: may be surfaced in Strategy Lab and Chat as research context.
- `REJECTED`: must not influence prompts except as negative training/review context.
- `NEEDS_MORE_EVIDENCE`: may trigger a future non-mutating job, not a trade.
- `PROMOTED_TO_TASK_CARD`: creates an implementation/evaluation task card outline only.

No review state promotes data to financial truth.

## DATA_MISSING

- No existing Strategy Lab schema exists in the repo.
- No QuantDinger result payload was available for exact field mapping.
- No current artifact storage directory outside this report was created.
