# Proposed DuckDB Schema

This schema is for an offline report warehouse under `reports/`, not for backend runtime code. It should ingest task cards, status files, scorecards, validation artifacts, and report sidecars. It must not become a dependency of FastAPI, Cockpit, extraction, parser routing, Qdrant, news loaders, memory stores, or production DBs.

## Design Principles

- Keep run metadata separate from scored results.
- Preserve branch, HEAD, worktree, mode, and task-card provenance for every row.
- Treat scorecard profile names as first-class dimensions.
- Keep `canonical_core` strict and narrow; never join broader coverage into canonical KPI rows.
- Represent `DATA_MISSING`, expected empty states, expected 404 routes, no-hit, and degraded runtime explicitly.
- Prefer JSON sidecars and status files over scraping Markdown prose.
- Preserve source artifact paths so every row can be traced back to the report that created it.

## Table Map

### `artifact_runs`

Primary key: `run_id`.

Links a report/eval job to branch, HEAD, worktree, output directory, task card, start/end time, verdict, and source manifest. Example sources: `reports/agent_jobs/*/status.json`, future `manifest.json`, task-card frontmatter.

### `task_cards`

Primary key: `task_card_id`.

Stores normalized task-card frontmatter, including lane, owner, mutation mode, production data access, allowed files, and validation result. Example sources: `docs/agent_tasks/*.md`, `diff-check.json.validation`.

### `validation_commands`

Primary key: `validation_command_id`.

Stores commands run, cwd, command class, result status, exit code, and notes. This is intentionally broad enough for pytest, Vitest, curl smoke, jq checks, registry commands, and `git diff --check`.

### `artifact_files`

Primary key: `artifact_file_id`.

Records files belonging to each run, including type, parser status, byte size, and whether a future manifest referenced the file. This is the bridge from report directory contents to typed fact tables.

### `scorecard_results`

Primary key: `scorecard_result_id`.

Stores one row per scorecard profile and run. Important dimensions: `scorecard_profile`, `is_canonical`, `kpi_eligible`, document count, metric check count, candidate count, ambiguous count, unsupported count, `DATA_MISSING` count, accuracy fields, pass/fail status, and overclaim guard.

Example sources: `scorecard_proposal.json`, future `extraction_real_eval_results_canonical_scorecard.json`, future confirmed metric coverage artifacts.

### `metric_expectations`

Primary key: `metric_expectation_id`.

Stores source-evidenced expected metric labels. Important fields include document, ticker, period, metric name, expected value, currency, scale, tolerance, evidence status, support status, source PDF hash, page number, and `canonical_write`.

Example sources: real-gold fixtures, confirmed coverage scorecard expectations, Appendix 5B approval packets.

### `metric_results`

Primary key: `metric_result_id`.

Stores observed evaluation results for a metric expectation. It links to `metric_expectations` where possible and records actual value, status, reason, trust outcome, and context correctness.

Example sources: `extraction_real_eval_results_metrics.csv`, future confirmed coverage scoring output.

### `runtime_smokes`

Primary key: `runtime_smoke_id`.

Stores runtime/model/GPU smoke evidence. It distinguishes direct local llama.cpp tiny prompts from Cockpit route behavior. Important fields include runtime surface, endpoint, model, GPU, request counts, latency, token counts, degraded status, verdict, and missing evidence.

Example sources: APEX/M40 direct soak audit, runtime stability audit, NVMe runtime reports.

### `route_smokes`

Primary key: `route_smoke_id`.

Stores route ownership and smoke outcomes. It preserves `route_expected_404` and `expected_empty_state` as classifications rather than failures.

Example sources: route parity audit, Cockpit Home missing producer audit, route validation matrices.

### `source_label_checks`

Primary key: `source_label_check_id`.

Stores source-label and guard behavior. This table keeps `missing_required_evidence`, `no_hit`, `context_only`, `claim_verified`, and guard actions separate.

Example sources: A2M trace reports, Cockpit chat/source guard reports, future route/source-label tests.

### `memory_audit_results`

Primary key: `memory_audit_result_id`.

Stores memory contamination audit facts without loading the memory database itself. It captures row counts, active counts, duplicate/fanout clusters, review counts, surfacing risk, cleanup readiness, and `untrusted_memory`.

Example sources: memory live inventory JSON and memory root-cause audit artifacts.

### `news_trace_results`

Primary key: `news_trace_result_id`.

Stores A2M/news trace state across ingestion, entity linking, SQLite, Qdrant, `/rag/query`, backend chat, and source labels. This table must distinguish static analysis from read-only live trace, and it must preserve `DATA_MISSING` when production data access is not approved.

### `dirty_worktree_events`

Primary key: `dirty_worktree_event_id`.

Stores worktree dirt and allowlist evidence. This avoids losing the reason a `check-diff` failed or why an isolated worktree was chosen.

### `registry_events`

Primary key: `registry_event_id`.

Stores registry list/claim/heartbeat/release events and overlap checks. Current live registry state remains authoritative, but this table makes historical job coordination queryable.

### `data_missing_items`

Primary key: `data_missing_id`.

Stores missing evidence as first-class rows. Fields separate policy blocks, environment blocks, and expected empty states.

### `decisions_and_verdicts`

Primary key: `decision_id`.

Stores final verdicts, recommendations, confidence, and labelled confirmed/inferred/speculative facts. This keeps report conclusions queryable without scraping Markdown headings.

## Immediate Seed Set

The first curated ingestion should load only:

- `reports/agent_jobs/gold_metric_coverage_audit_v1_20260519/*.json`
- `reports/agent_jobs/appendix5b_fifth_doc_approval_packet_v1_20260517/*.json`
- `reports/agent_jobs/memory_contamination_live_inventory_readonly_v1_20260519/*.json`
- `reports/agent_jobs/memory_contamination_root_cause_audit_v1_20260519/*.json`
- `reports/agent_jobs/a2m_news_trace_entity_linking_blast_radius_audit_v1_20260519/*.json`
- `reports/agent_jobs/*/status.json`
- `reports/agent_jobs/*/diff-check.json`

Markdown-only runtime and route reports should wait for manifest sidecars or hand-authored manifests. Do not scrape metric tables from prose as the first implementation.
