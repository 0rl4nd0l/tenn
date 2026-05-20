# Future Task Card Outlines

These are draft outlines only. Do not execute them from this report.

## Phase 0 - Fit Audit

Lane: Evaluation
Mode: `audit_only`
Allowed files: new task card and `reports/agent_jobs/strategy_lab_quantdinger_fit_audit_v1_*/**`
Forbidden surfaces: runtime services, Docker, MCP startup, tokens, broker keys, DB/Qdrant/memory, Cockpit code, backend code.
Validation: task-card validate, registry list/check-overlap, public docs/source inspection, final `git diff --check`, check-diff.
Hard stops: any need for live trading, no safe backtest/read-only path, license/security blocker.
Done criteria: source/API inventory, tool list, risk matrix, go/no-go for sandbox.

## Phase 1 - Isolated Sandbox

Lane: Evaluation
Mode: `audit_only` first, then `safe_extension` only for sandbox scripts if approved
Allowed files: task card, sandbox report bundle, optional sandbox runbook under approved path
Forbidden surfaces: Tenn runtime, production ports, production secrets, broker keys, paper/live execution.
Validation: port preflight, storage preflight, no production mounts, no sidecar start unless explicitly allowed.
Hard stops: Docker would use Tenn data roots, secrets needed, live trading required.
Done criteria: reproducible sandbox plan or no-start dry-run report.

## Phase 2 - Artifact Store/Schema

Lane: Evaluation
Mode: `safe_extension`
Allowed files: Strategy Lab schema files, schema tests, report bundle
Forbidden surfaces: DB/Qdrant/memory/financial truth writes, runtime code outside schema validator.
Validation: schema tests, fixture artifacts, no canonical truth flags.
Hard stops: schema permits execution or financial truth promotion.
Done criteria: versioned schema, validator, sample fixtures, docs.

## Phase 3 - Safe Adapter/MCP Client Wrapper

Lane: Query Orchestration
Mode: `safe_extension`
Allowed files: new adapter under approved client boundary, tests, report bundle
Forbidden surfaces: agent loop rewrite, direct Codex production path, credentials/trading scopes, live/paper execution.
Validation: mocked MCP/API tests, allowlist tests, blocked-tool tests, schema validation tests.
Hard stops: adapter needs admin JWT, broker keys, or non-read/backtest scopes.
Done criteria: Tenn-owned wrapper that can normalize mocked read/backtest outputs only.

## Phase 4 - Chat-First Workflows

Lane: Query Orchestration
Mode: `safe_extension`
Allowed files: chat action proposal/workflow files and tests
Forbidden surfaces: automatic execution, memory writes, financial truth writes, UI tab buildout.
Validation: action-preview tests, no-trade tests, evidence-label tests.
Hard stops: Chat can submit sidecar jobs without human gate.
Done criteria: Chat can propose a Strategy Lab research job and explain limitations.

## Phase 5 - Strategy Lab Tab

Lane: Reporting
Mode: `safe_extension`
Allowed files: Cockpit UI Strategy Lab route/components/tests, BFF if needed
Forbidden surfaces: backend truth changes, sidecar admin embedding, broker controls, execution controls.
Validation: UI tests, DATA_MISSING rendering, source-label rendering, no-trade controls absent.
Hard stops: UI hides limitations or presents backtest as recommendation.
Done criteria: read-only tab over existing artifacts and review queue.

## Phase 6 - Robustness Engine

Lane: Evaluation
Mode: `safe_extension`
Allowed files: robustness analyzers, report artifacts, tests
Forbidden surfaces: sidecar execution, production data writes, Cockpit live controls.
Validation: overfit/lookahead/sample-size tests, benchmark-required tests.
Hard stops: robustness score used as financial truth or trade signal.
Done criteria: robustness warnings attach to artifacts.

## Phase 7 - Factor Lab

Lane: Evaluation
Mode: `safe_extension`
Allowed files: factor artifact schema/tests, report bundle
Forbidden surfaces: live factor trading, financial truth writes, memory writes.
Validation: factor fixtures, quantile/IC tests, sample-size warnings.
Hard stops: factor results promoted to recommendations without review.
Done criteria: factor test artifacts are reviewable and non-canonical.

## Phase 8 - Risk Reports

Lane: Evaluation
Mode: `safe_extension`
Allowed files: risk artifact schema/generator/tests
Forbidden surfaces: broker actions, portfolio rebalancing, truth writes.
Validation: scenario/drawdown schema tests, limitations required.
Hard stops: risk report produces order instructions.
Done criteria: risk reports visible as research context only.

## Phase 9 - Portfolio Lab

Lane: Evaluation
Mode: `safe_extension`
Allowed files: portfolio experiment artifacts/UI/tests
Forbidden surfaces: broker links, order placement, holdings truth mutation, mixed-currency overclaim.
Validation: local_personal_data label tests, mixed-currency guard, no-order tests.
Hard stops: portfolio experiment can rebalance or execute.
Done criteria: simulated portfolio artifacts with review state and warnings.

## Phase 10 - Autonomous Research Loops

Lane: Evaluation
Mode: `safe_extension`
Allowed files: scheduler/job definitions, loop artifacts, tests
Forbidden surfaces: production data mutation, memory writes, paper/live execution, unattended strategy code execution.
Validation: no-trade tests, review queue tests, loop caps, failure-mode tests.
Hard stops: loop can execute sidecar actions beyond read/backtest or bypass review.
Done criteria: loops create only pending-review artifacts.

## Phase 11 - Paper-Execution Review Only

Lane: Evaluation
Mode: `blocked` until separate explicit approval
Allowed files: paper-execution risk report and approval packet only
Forbidden surfaces: broker keys, paper account setup, execution runtime, live execution.
Validation: threat model, compliance/security review, explicit human approval.
Hard stops: any real broker credential or executable order path.
Done criteria: decision packet only; no setup.

## Phase 12 - Live Execution

Lane: Financial Truth / Query Orchestration / Security, separate project
Mode: `blocked`
Allowed files: none under this framework
Forbidden surfaces: all live execution.
Validation: not applicable.
Hard stops: always.
Done criteria: reject from Strategy Lab integration framework.
