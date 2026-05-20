# Tenn Strategy Lab / QuantDinger Framework v1

Job: `strategy_lab_quantdinger_framework_v1_20260520`
Primary lane: Evaluation
Supporting lanes: Query Orchestration, Reporting, Provenance, Financial Truth, Memory
Mode: `AUDIT + DESIGN FRAMEWORK + REPORT ONLY`
Production data access: false
Implementation status: not implemented

## Decision

Implementation should defer. The next safe phase is Phase 0 fit audit, followed by an isolated sandbox only if Phase 0 proves a bounded read/backtest path. Do not integrate QuantDinger into Tenn runtime, Cockpit UI, MCP, memory, financial truth, DB, Qdrant, broker, paper trading, or live trading from this task.

QuantDinger is a plausible external sidecar/comparator for Strategy Lab research because public materials confirm read, market, regime, backtest, parameter tuning, and MCP surfaces that do not inherently require live trading. It is also high risk because the same platform includes credentials, broker/exchange adapters, bots, paper/live execution, and a full Docker application stack.

## Current Repo State

- Worktree: `/home/l4nd0/tenn-runtime` -> `/home/l4nd0/tenn-nvme-clean-baseline-reconstruct-v1`
- Branch at report write: `migration/clean-runtime-baseline-reconstruct-v1`
- HEAD at report write: `e006bf86a79604b4473b8f8edf2998c4f0426243`
- Task card: `docs/agent_tasks/strategy_lab_quantdinger_framework_v1_20260520.md`
- Registry status at claim: active job claimed by Codex for this job.
- Registry status after release: `active_jobs=[]`.
- Active marker: `.tenn` absent; no `.tenn/active_agent_task` marker found.
- Final visible git status:
  - `?? docs/agent_tasks/asx_document_type_fixture_contract_integration_v1_20260520.md`
  - `?? docs/agent_tasks/strategy_lab_quantdinger_framework_v1_20260520.md`
- Product/runtime code changed: no.
- Production data touched: no.

The ASX task card is an unrelated untracked file outside this job's allowed
paths. It was not touched by this job, but it causes registry `check-overlap`
and task-card `check-diff` to fail cleanly on outside-allowed dirt.

## Files Written

- `docs/agent_tasks/strategy_lab_quantdinger_framework_v1_20260520.md`
- `reports/agent_jobs/strategy_lab_quantdinger_framework_v1_20260520/README.md`
- `reports/agent_jobs/strategy_lab_quantdinger_framework_v1_20260520/artifact_schema_v1.md`
- `reports/agent_jobs/strategy_lab_quantdinger_framework_v1_20260520/task_card_outlines.md`
- `reports/agent_jobs/strategy_lab_quantdinger_framework_v1_20260520/strategy_lab_quantdinger_framework_v1_20260520_reports.zip`
- `reports/agent_jobs/strategy_lab_quantdinger_framework_v1_20260520/checkpoints/checkpoint_00_preflight.md`
- `reports/agent_jobs/strategy_lab_quantdinger_framework_v1_20260520/checkpoints/checkpoint_01_tenn_surface_map.md`
- `reports/agent_jobs/strategy_lab_quantdinger_framework_v1_20260520/checkpoints/checkpoint_02_quantdinger_fit.md`
- `reports/agent_jobs/strategy_lab_quantdinger_framework_v1_20260520/checkpoints/checkpoint_03_artifact_contract.md`
- `reports/agent_jobs/strategy_lab_quantdinger_framework_v1_20260520/checkpoints/checkpoint_04_mcp_runtime_policy.md`
- `reports/agent_jobs/strategy_lab_quantdinger_framework_v1_20260520/checkpoints/checkpoint_05_strategy_lab_ux.md`
- `reports/agent_jobs/strategy_lab_quantdinger_framework_v1_20260520/checkpoints/checkpoint_06_autonomous_value_loops.md`
- `reports/agent_jobs/strategy_lab_quantdinger_framework_v1_20260520/checkpoints/checkpoint_07_runtime_compatibility.md`
- `reports/agent_jobs/strategy_lab_quantdinger_framework_v1_20260520/checkpoints/checkpoint_08_implementation_backlog.md`
- `reports/agent_jobs/strategy_lab_quantdinger_framework_v1_20260520/status.json` from registry claim/heartbeat/release.
- `reports/agent_jobs/strategy_lab_quantdinger_framework_v1_20260520/diff-check.json` from final check-diff.

## Confirmed Facts

- Tenn's system contract makes backend the sole authority for ingestion, extraction, structured financial data, vector data, retrieval, and data correctness.
- Cockpit is a client/orchestration layer and must not become a second financial truth or retrieval authority.
- Tenn has explicit source/evidence labels including `financial_truth`, `memory_context`, `local_personal_data`, `external_web_context`, `missing_required_evidence`, and `unknown_unclassified`.
- Tenn memory classes are separated: financial truth, company memory, market memory, user thesis memory, session memory, and operational/workspace state.
- Tenn has task-card, registry, status, and diff-check conventions for safe agent work.
- Tenn has Evaluation Spine report-manifest conventions that fit Strategy Lab artifact normalization.
- Public QuantDinger materials confirm a self-hosted stack, Agent Gateway, MCP package, read/backtest tools, token scopes, audit logs, paper-only defaults, and live-trading controls.
- Public QuantDinger materials also confirm live-trading, broker/exchange, bot, credential, and Docker/runtime surfaces.
- PyPI lists `quantdinger-mcp` version `0.1.0`, released May 2, 2026.

## Inferred Facts

- The safe Tenn integration pattern is sidecar-as-comparator, not sidecar-as-brain.
- A Strategy Lab should start as report artifacts and review queue, then only later expose read-only summaries in Cockpit.
- QuantDinger's MCP read/backtest surface can likely support useful research without live trading.
- Sidecar results should be mapped to Tenn evidence labels such as `external_tool_context`, `backtest_result`, `regime_context`, and `missing_required_evidence`.
- Current Tenn portfolio/watchlist/analysis modules provide enough native context to define autonomous research loops without trading.

## Speculative Ideas

- A future Strategy Lab tab could show Ideas, Backtests, Sweeps, Factors, Regimes, Risk, Portfolio Lab, Review Queue, Evidence, and Admin Debug.
- A future generic sidecar interface could allow QuantDinger, vectorbt, qlib, Lean, or a Tenn-native runner to share the same artifact contract.
- A future robustness engine could score overfit, lookahead, survivorship, sample size, benchmark gaps, and regime fragility before any review approval.

## DATA_MISSING

- No local QuantDinger install inspected.
- No QuantDinger Docker Compose startup.
- No MCP server startup.
- No token issuance.
- No broker/exchange/paper/live execution check.
- No real QuantDinger backtest result payload.
- No resource benchmark.
- No live Tenn Cockpit/runtime probe.
- No production DB/Qdrant/news/memory/financial-truth data inspection.
- No Strategy Lab code or UI exists in current repo.

## Collision Risks

- `docs/agent_tasks/asx_document_type_fixture_contract_integration_v1_20260520.md`
  appeared as an unrelated untracked file outside this job's allowed files.
- Registry showed no active overlapping job after this job was released.
- The outside ASX task-card dirt does not overlap the Strategy Lab report
  bundle, but it prevents a clean `check-overlap` / `check-diff` result until
  that file is either claimed by its own task card, preserved, or removed by
  its owner.
- No product/runtime code, production data, database, Qdrant, memory,
  financial-truth, parser, extraction, gold-label, broker, Docker, MCP, or UI
  surface was changed by this job.

## Top 5 Value Opportunities

1. Backtest comparator: convert external backtest outputs into Tenn reviewable, non-canonical artifacts.
2. Thesis-to-test loop: turn human/Tenn thesis notes into bounded historical tests with explicit assumptions.
3. Factor/regime research: evaluate candidate signals by factor, regime, and robustness without touching financial truth.
4. Portfolio risk lab: simulate exposure and risk using `local_personal_data` labels and no execution.
5. Autonomous research backlog: generate task-card outlines from repeated DATA_MISSING, rejected artifacts, and robustness warnings.

## Top 5 Risks

1. Live/paper trading creep through QuantDinger's broker and bot surfaces.
2. Financial-truth contamination if backtest or sidecar market data is treated as canonical.
3. Memory contamination if machine-generated strategy notes bypass proposal/review gates.
4. Runtime collision from Docker, Postgres, Redis, Nginx, MCP ports, or local LLM usage.
5. Overfit and false precision from backtests without benchmark, data-source, fees/slippage, and limitation metadata.

## Hard Boundaries

- No live trading.
- No paper trading setup.
- No broker keys.
- No credential scope.
- No trading scope.
- No Docker or service startup from this task.
- No MCP server startup from this task.
- No Tenn runtime code changes.
- No Cockpit UI/backend code changes.
- No Postgres, Qdrant, news, memory, parser, extraction, gold-label, or financial-truth writes.
- No QuantDinger output may become canonical financial truth.
- No Strategy Lab artifact may affect memory or watchlist priority without human review and a later task card.

## Recommended Next Safe Phase

Phase 0 fit audit:

- inspect QuantDinger source/API docs more deeply;
- inventory exact Agent Gateway and MCP tool schemas;
- classify every tool by Tenn permission ladder;
- design sidecar isolation without starting it;
- produce a go/no-go packet for Phase 1 sandbox.

## Project Memory Save Recommendation

`SAVE_RECOMMENDED`: save the Strategy Lab boundary pattern:

- external quant sidecars are comparator engines, not Tenn's brain;
- Strategy Lab starts as Evaluation artifacts and review queue;
- read/backtest tools can be considered later;
- credentials, paper execution, live execution, financial-truth writes, DB/Qdrant/memory writes, and UI/runtime code are blocked until separate task cards.

## Commands And Checks Run

```bash
sed -n '1,220p' /mnt/hdd-data/home/l4nd0/tenn/.codex/skills/repository-audit/SKILL.md
pwd
readlink -f /home/l4nd0/tenn-runtime
git -C /home/l4nd0/tenn-runtime rev-parse --show-toplevel
git -C /home/l4nd0/tenn-runtime branch --show-current
git -C /home/l4nd0/tenn-runtime rev-parse --short HEAD
git -C /home/l4nd0/tenn-runtime status --short --untracked-files=all
git -C /home/l4nd0/tenn-runtime worktree list
git -C /home/l4nd0/tenn-runtime log -8 --oneline --decorate
python3 scripts/agent_job_contract.py validate docs/agent_tasks/strategy_lab_quantdinger_framework_v1_20260520.md
python3 scripts/agent_job_registry.py list-active --repo-root /home/l4nd0/tenn-runtime
python3 scripts/agent_job_registry.py check-overlap docs/agent_tasks/strategy_lab_quantdinger_framework_v1_20260520.md --repo-root /home/l4nd0/tenn-runtime
python3 scripts/agent_job_registry.py claim docs/agent_tasks/strategy_lab_quantdinger_framework_v1_20260520.md --repo-root /home/l4nd0/tenn-runtime
python3 scripts/agent_job_registry.py heartbeat strategy_lab_quantdinger_framework_v1_20260520 --repo-root /home/l4nd0/tenn-runtime
python3 scripts/agent_job_registry.py release strategy_lab_quantdinger_framework_v1_20260520 --repo-root /home/l4nd0/tenn-runtime
python3 scripts/agent_job_registry.py list-active --repo-root /home/l4nd0/tenn-runtime
git diff --check
python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/strategy_lab_quantdinger_framework_v1_20260520.md --repo-root /home/l4nd0/tenn-runtime
find reports/agent_jobs/strategy_lab_quantdinger_framework_v1_20260520 -type f | sort
rm -f /tmp/strategy_lab_quantdinger_framework_v1_20260520_reports.zip
zip -r /tmp/strategy_lab_quantdinger_framework_v1_20260520_reports.zip docs/agent_tasks/strategy_lab_quantdinger_framework_v1_20260520.md reports/agent_jobs/strategy_lab_quantdinger_framework_v1_20260520 -x reports/agent_jobs/strategy_lab_quantdinger_framework_v1_20260520/strategy_lab_quantdinger_framework_v1_20260520_reports.zip
mv /tmp/strategy_lab_quantdinger_framework_v1_20260520_reports.zip reports/agent_jobs/strategy_lab_quantdinger_framework_v1_20260520/strategy_lab_quantdinger_framework_v1_20260520_reports.zip
unzip -t reports/agent_jobs/strategy_lab_quantdinger_framework_v1_20260520/strategy_lab_quantdinger_framework_v1_20260520_reports.zip
unzip -l reports/agent_jobs/strategy_lab_quantdinger_framework_v1_20260520/strategy_lab_quantdinger_framework_v1_20260520_reports.zip
git status --short --untracked-files=all
git status --short --ignored reports/agent_jobs/strategy_lab_quantdinger_framework_v1_20260520
du -h reports/agent_jobs/strategy_lab_quantdinger_framework_v1_20260520/strategy_lab_quantdinger_framework_v1_20260520_reports.zip
find .tenn -maxdepth 2 -type f -print
sed -n '1,260p' docs/architecture/SYSTEM_CONTRACT.md
sed -n '1,180p' docs/entrypoints.md
sed -n '1,220p' docs/architecture/13_security_and_secrets.md
sed -n '1,260p' docs/architecture/21_cockpit_client_contract.md
sed -n '1,240p' docs/architecture/18_cockpit_memory.md
sed -n '1,260p' docs/architecture/22_memory_ownership_map.md
sed -n '1,260p' docs/evaluation_spine_manifest_contract.md
sed -n '1,220p' docs/architecture/12_evaluation_and_drift_monitoring.md
sed -n '1,260p' financial-engine_v2/backend/app/services/query_orchestrator.py
sed -n '1348,1605p' financial-engine_v2/backend/app/routes/cockpit_api.py
sed -n '1,260p' financial-engine_v2/backend/app/services/provenance.py
sed -n '1,240p' financial-engine_v2/backend/app/services/analysis_report_schema.py
sed -n '1,240p' financial-engine_v2/cockpit/core/tool_definitions.py
sed -n '1,260p' financial-engine_v2/cockpit/core/tool_executor.py
sed -n '1,240p' financial-engine_v2/cockpit/core/actions.py
sed -n '1,260p' financial-engine_v2/cockpit/core/agent_loop.py
find cockpit-ui/app -maxdepth 4 -type f
find cockpit-ui/app/api/cockpit -maxdepth 5 -type f -name 'route.ts'
find cockpit-ui/components/cockpit -maxdepth 3 -type f
rg -n "Strategy Lab|strategy lab|QuantDinger|factor|backtest|portfolio|risk report|evidence|provenance|source_label|QueryOrchestrator|tool policy|MCP|financial truth|DATA_MISSING" docs cockpit-ui financial-engine_v2/backend scripts
```

Public web checks:

```text
Search: QuantDinger GitHub QuantDinger MCP backtesting trading bot Docker
Search: quantdinger-mcp GitHub
Open: https://www.quantdinger.com/
Open: https://www.quantdinger.com/docs.html
Open: https://github.com/brokermr810/QuantDinger
Open: https://pypi.org/project/quantdinger-mcp/
Open: https://raw.githubusercontent.com/brokermr810/QuantDinger/main/docs/agent/MCP_SETUP.md
Open: https://raw.githubusercontent.com/brokermr810/QuantDinger/main/mcp_server/README.md
```

## Milestone Artifacts

| Milestone | Artifact |
| --- | --- |
| M0 | `checkpoints/checkpoint_00_preflight.md` |
| M1 | `checkpoints/checkpoint_01_tenn_surface_map.md` |
| M2 | `checkpoints/checkpoint_02_quantdinger_fit.md` |
| M3 | `checkpoints/checkpoint_03_artifact_contract.md`, `artifact_schema_v1.md` |
| M4 | `checkpoints/checkpoint_04_mcp_runtime_policy.md` |
| M5 | `checkpoints/checkpoint_05_strategy_lab_ux.md` |
| M6 | `checkpoints/checkpoint_06_autonomous_value_loops.md` |
| M7 | `checkpoints/checkpoint_07_runtime_compatibility.md` |
| M8 | `checkpoints/checkpoint_08_implementation_backlog.md`, `task_card_outlines.md` |
| M9 | `README.md` |

## Final Validation

- Task-card validation: PASS.
- Registry claim/list-active: PASS; no active overlapping job was present when
  claimed.
- Registry release: PASS; final `list-active` returned `active_jobs=[]`.
- `git diff --check`: PASS; no whitespace errors reported.
- `check-overlap`: FAIL because
  `docs/agent_tasks/asx_document_type_fixture_contract_integration_v1_20260520.md`
  is dirty outside this job's allowed files.
- Task-card `check-diff`: FAIL for the same outside ASX task-card dirt; report
  written to `diff-check.json`.
- Final write boundary: Strategy Lab writes are limited to the requested task
  card and `reports/agent_jobs/strategy_lab_quantdinger_framework_v1_20260520/**`.
- Export bundle:
  `reports/agent_jobs/strategy_lab_quantdinger_framework_v1_20260520/strategy_lab_quantdinger_framework_v1_20260520_reports.zip`.
- Export bundle integrity: PASS; `unzip -t` reported no errors.
