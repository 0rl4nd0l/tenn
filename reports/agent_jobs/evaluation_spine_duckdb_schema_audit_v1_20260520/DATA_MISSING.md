# DATA_MISSING

This audit stayed report-only and did not access production data, Qdrant, news stores, memory stores, live extraction, runtime smokes, or Cockpit producers.

## Missing Report Directories Or Artifacts

- Current `reports/extraction_real_eval_results.json` is missing in this checkout.
- Current `reports/extraction_real_eval_results_summary.json` is missing in this checkout.
- Current `reports/extraction_real_eval_results_documents.csv` is missing in this checkout.
- Current `reports/extraction_real_eval_results_metrics.csv` is missing in this checkout.
- Current `reports/extraction_real_eval_summary.md` is missing in this checkout.
- Current `reports/news_eval_report.json` is missing in this checkout.
- Current `reports/company_eval_report_v2.json` is missing in this checkout.
- Current `reports/eval_queries_report.json` is missing in this checkout.
- Current `reports/baselines/canonical_eval_baseline_latest.json` is missing in this checkout.
- `reports/rag_stability/*.json` was documented but not present in the inspected report inventory.

## Missing Scorecards

- No current generated real-gold extraction result artifact was found under the expected `reports/extraction_real_eval_*` paths.
- No current generated confirmed metric coverage scoring output was found that evaluates extracted payloads against the broader confirmed profile.
- Historical canonical10 artifacts referenced in older docs/memory live outside this current checkout path and were not used as current evidence.

## Missing Commit And Branch Metadata

- Many Markdown-only reports include branch/HEAD in prose, but not a normalized machine-readable manifest.
- Some status files can contain historical or stale registry status; current registry state must come from live `agent_job_registry.py list-active`.
- Older baseline docs and report references do not always include current branch, HEAD, worktree, runtime profile, parser backend, model label, or artifact SHA.

## Missing Runtime Metadata

- Direct APEX/M40 soak data is in Markdown tables, not normalized JSON.
- Cockpit route prompt/token amplification and auto-diagnostic side effects are described in Markdown and code inspection, not a normalized runtime-smoke artifact.
- Parser backend, strict method, prompt hash, model label, endpoint URL, and GPU UUID are not consistently present across historical eval outputs.

## Missing Source-label State

- A2M static trace did not query live news SQLite or Qdrant because production data access was false.
- The active A2M live trace job exists but was not read or imported by this audit because it is a separate active job.
- Several source-label reports describe behavior in Markdown; future ingestion needs source-label check rows or a manifest sidecar.

## Missing Artifact Schema Fields

- Markdown-only route/runtime/Home reports need manifest fields for `artifact_family`, `verdict`, `truth_status`, `DATA_MISSING`, `runtime_surface`, `route_owner`, and `expected_empty_state`.
- Feedback/auto-diagnostic artifacts need a contract distinguishing operator feedback, auto-diagnostic flags, and true evaluation labels.
- Memory artifacts lack durable writer job IDs and source spans for historical contaminated rows; those are missing in the underlying report evidence, not just the eval spine.

## Policy-Bound Missing Evidence

- Production DBs, Qdrant, news stores, memory stores, extraction jobs, chat smokes, Home producers, and runtime probes were intentionally not accessed.
- No DuckDB database was created.
- No MLflow run was created.
