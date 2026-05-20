# Evaluation Spine DuckDB Schema Audit v1

Job: `evaluation_spine_duckdb_schema_audit_v1_20260520`
Mode: `AUDIT ONLY / DESIGN ONLY`
Primary lane: Evaluation
Supporting lanes: Provenance, Reporting, Financial Truth
Worktree: `/home/l4nd0/tenn-evaluation-spine-duckdb-audit-v1-20260520`
Branch: `audit/evaluation-spine-duckdb-schema-v1-20260520`
HEAD: `669bff1c7e4f`

## 1. Executive Verdict

- Evaluation spine status: `EVALUATION_SPINE_READY_FOR_DESIGN`
- DuckDB status: `DUCKDB_SAFE_OFFLINE`
- MLflow status: `DEFERRED`
- Recommended next task: add a future-report `manifest.json` generator and tests, then a report-local DuckDB prototype that ingests only a curated JSON set.

Tenn has enough structured report/eval artifacts to design the local evaluation spine now. The safe first implementation is not a backend integration. It is an offline report warehouse under `reports/`, seeded from task cards, `status.json`, `diff-check.json`, scorecard JSON, inventory JSON, approval packets, memory audit JSON, and A2M trace JSON.

The current blocker to immediate broad ingestion is not DuckDB. It is inconsistent artifact normalization. Several important reports are Markdown-first and contain key facts only in prose or tables. Those families need a normalized manifest sidecar before Tenn should compare them across branch, HEAD, runtime/model/parser, scorecard profile, pass/fail status, and `DATA_MISSING`.

## 2. Confirmed Facts

Files and report families inspected:

- `reports/agent_jobs/`
- `reports/extraction*`
- `reports/*eval*`
- `docs/validation_baseline.md`
- `docs/architecture/12_evaluation_and_drift_monitoring.md`
- `docs/architecture/`
- `financial-engine_v2/backend/tests/`
- `scripts/*eval*`
- `scripts/*gold*`
- `scripts/*extraction*`
- `scripts/*appendix*`
- representative JSON scorecards, approval packets, inventories, `status.json`, `diff-check.json`, validation artifacts, and README reports

High-signal reports inspected:

- `reports/agent_jobs/gold_metric_coverage_audit_v1_20260519/`
- `reports/agent_jobs/asx_deterministic_extraction_extension_audit_v1_20260519/`
- `reports/agent_jobs/appendix5b_fifth_doc_approval_packet_v1_20260517/`
- `reports/agent_jobs/a2m_news_trace_entity_linking_blast_radius_audit_v1_20260519/`
- `reports/agent_jobs/memory_contamination_root_cause_audit_v1_20260519/`
- `reports/agent_jobs/memory_contamination_live_inventory_readonly_v1_20260519/`
- `reports/agent_jobs/nvme_runtime_audit_artifact_checkpoint_v1_20260519/`
- `reports/agent_jobs/apex_m40_runtime_stability_audit_v1_20260519/`
- `reports/agent_jobs/apex_m40_direct_runtime_soak_audit_v1_20260519/`
- `reports/agent_jobs/route_parity_home_news_status_audit_v1_20260519/`
- `reports/agent_jobs/cockpit_home_missing_producers_audit_v1_20260519/`
- `reports/agent_jobs/cockpit_chat_orchestration_side_effect_audit_v1_20260519/`

Structured JSON artifacts found:

- `status.json` and `diff-check.json` across many `reports/agent_jobs/*` directories.
- Gold Metric Coverage: `corpus_inventory.json`, `metric_inventory.json`, `scorecard_proposal.json`.
- ASX deterministic extraction design: `extension_point_inventory.json`, `document_type_classifier_plan.json`, `no_regression_gate_map.json`.
- Appendix 5B: `approval_packet.json`, `candidate_inventory.json`, `status.json`.
- A2M trace: `a2m_trace_map.json`, `blast_radius_candidates.json`, `source_label_risk_matrix.json`, `validation_commands.json`.
- Memory contamination: `memory_store_inventory.json`, `surfacing_risk_matrix.json`, `suspected_fanout_clusters.json`, `active_contamination_summary.json`, `schema_inventory.json`, path/status/check JSON files.
- NVMe/data binding: `binding_changes.json`, `target_visibility.json`, `post_binding_validation.json`, `copy_gap_final_check.json`, and related JSON.

Report-only Markdown artifacts found:

- APEX/M40 direct runtime soak and runtime-stability reports.
- Route parity and Cockpit Home producer classification reports.
- Cockpit chat/source-guard side-effect report.
- Many older Home/news/runtime/reporting artifacts.

Scorecards found:

- `canonical_core`: current strict 10-document, 24-check no-regression anchor over `revenue`, `operating_cash_flow`, and `net_debt`.
- `expanded_required`: current 15-document, 39-check required subset over the same three metric families.
- `confirmed_metric_coverage`: broader read-only coverage profile with 15 fixtures, 146 expectations, 73 scorable rows, 70 candidate rows, 3 ambiguous rows, and 0 unsupported rows in the Gold Metric Coverage report.

Validation artifacts found:

- Task-card `validation` structures inside `diff-check.json`.
- `status.json` registry records.
- Dedicated validation command lists in A2M and README reports.
- Tests and documented validation baselines in `docs/validation_baseline.md`.

Missing artifact classes:

- Current generated `reports/extraction_real_eval_results*.json/csv/md` artifacts.
- Current `reports/news_eval_report.json`, `reports/company_eval_report_v2.json`, `reports/eval_queries_report.json`.
- Current `reports/baselines/canonical_eval_baseline_latest.json`.
- Current `reports/rag_stability/*.json` in this checkout.
- Normalized manifests for Markdown-first runtime, route, Home, and chat/source-guard reports.

## 3. Inferred Facts

Artifacts immediately ingestible into DuckDB:

- `status.json` and `diff-check.json`.
- Gold Metric Coverage JSON.
- Appendix 5B approval packet JSON.
- Memory contamination live/root-cause JSON.
- A2M trace JSON.
- Selected NVMe binding/readiness JSON.

Artifacts needing manifest normalization first:

- APEX/M40 runtime reports, because per-request metrics are in Markdown tables.
- Route parity and Cockpit Home reports, because route ownership and expected empty states are prose/table facts.
- Cockpit chat/source-guard reports, because guard/source-label state is prose and code-path classification.
- Feedback/auto-diagnostic artifacts, because there is no stable feedback-quality schema yet.

Scorecard naming is mostly consistent in code, but inconsistent in reports and UI surfaces. The DuckDB spine must enforce `scorecard_profile` on every score row so `canonical_core`, `expanded_required`, `confirmed_metric_coverage`, runtime smoke, route parity, memory integrity, news trace, UI honesty, and feedback quality cannot be collapsed into one unnamed pass rate.

Overclaim risk is highest when:

- `canonical_core` is presented as production extraction coverage.
- direct APEX/M40 runtime stability is treated as Cockpit chat stability.
- `DATA_MISSING` or expected empty Home states are treated as failures.
- memory context is treated as financial truth.
- static A2M code trace is treated as live news/Qdrant proof.

## 4. Speculative Claims

- A future manifest generator may be enough to avoid Markdown scraping for new reports.
- Existing JSON artifacts likely cover 60-70 percent of the first useful dashboard without touching historical Markdown-only reports.

These are implementation estimates, not proven runtime facts.

## 5. DATA_MISSING

Detailed gap list: `DATA_MISSING.md`.

Highest-impact gaps:

- Missing current extraction real-eval result artifacts.
- Missing current canonical regression/news/company/eval report JSON.
- Missing normalized branch/HEAD/runtime metadata in older artifacts.
- Missing normalized runtime/parser/model metadata across eval outputs.
- Missing normalized source-label rows for chat/source-guard reports.
- Missing feedback-quality schema.
- Missing live A2M trace output because a separate A2M live trace job is active and this audit did not touch it.

## 6. Artifact Family Inventory

Full structured inventory: `artifact_family_inventory.json`.

| Family | Lane | Examples | Machine-readable | Branch/HEAD | Validation commands | Pass/fail metrics | DATA_MISSING | DuckDB readiness | Notes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Extraction canonical / real-gold eval | Evaluation | `scripts/run_real_extraction_eval.py`, `scripts/analyze_real_extraction_eval_duckdb.py` | no | no | yes | yes | yes | needs manifest | Code can emit strong artifacts, but current expected outputs are missing. |
| Gold Metric Coverage | Evaluation | `scorecard_proposal.json`, `metric_inventory.json` | yes | yes | yes | yes | yes | ready | Best immediate seed and clearest scorecard separation. |
| Appendix 5B approval packets | Financial Truth | `approval_packet.json` | yes | yes | yes | yes | yes | ready | Strong source/page/metric/value evidence with `canonical_write=false`. |
| ASX deterministic extraction design | Financial Truth | classifier/gate plan JSON | yes | yes | yes | no | yes | needs manifest | Design artifacts, not scored metric results. |
| NVMe/runtime validation | Evaluation | NVMe binding/readiness JSON plus logs | no | yes | yes | yes | yes | needs manifest | Some JSON ready; large functionality reports need classification. |
| APEX/M40 runtime | Query Orchestration | direct soak and stability Markdown | no | yes | yes | yes | yes | needs manifest | Runtime metrics need typed runtime-smoke rows. |
| Cockpit route/Home | Reporting | route parity and Home producer reports | no | yes | yes | yes | yes | needs manifest | Expected 404 and empty states must be typed. |
| Cockpit chat/source guard | Query Orchestration | side-effect and guard reports | no | yes | yes | yes | yes | needs manifest | Source guard state must not be counted as runtime failure. |
| Memory contamination | Memory | live inventory/root-cause JSON | yes | yes | yes | yes | yes | ready | Strong immediate `memory_audit_results` seed. |
| A2M/news trace | Query Orchestration | A2M trace JSON | yes | yes | yes | yes | yes | ready | Static trace ready; active live trace remains untouched. |
| Registry/diff checks | Reporting | task cards, `status.json`, `diff-check.json` | yes | yes | yes | yes | yes | ready | Primary run-envelope source. |
| RAG stability/canonical regression | Evaluation | architecture docs, baseline report refs | no | no | yes | yes | yes | needs manifest | Expected artifacts are documented but missing here. |
| Future feedback | Reporting | `reports/cockpit/*`, chat side-effect report | no | no | no | no | yes | needs manifest | Do not auto-score sparse feedback. |

## 7. Proposed DuckDB Schema

Full SQL: `proposed_duckdb_schema.sql`.
Readable table map: `proposed_duckdb_schema.md`.

| Table | Primary key | Links | Example source artifacts | Notes |
| --- | --- | --- | --- | --- |
| `artifact_runs` | `run_id` | root table | manifests, `status.json` | Branch, HEAD, worktree, verdict, mode, output dir. |
| `task_cards` | `task_card_id` | `artifact_runs.run_id` | `docs/agent_tasks/*.md`, `diff-check.json` | Normalized task-card frontmatter and validation. |
| `validation_commands` | `validation_command_id` | `artifact_runs.run_id` | README validation sections, `validation_commands.json` | Exact commands, cwd, result, exit code. |
| `artifact_files` | `artifact_file_id` | `artifact_runs.run_id` | report directories | File inventory and schema/parse status. |
| `scorecard_results` | `scorecard_result_id` | `artifact_runs.run_id` | scorecard JSON | Profile-scoped result rows. |
| `metric_expectations` | `metric_expectation_id` | `scorecard_results` | real-gold labels, approval packets | Expected metric/source evidence. |
| `metric_results` | `metric_result_id` | expectations and scorecards | real-eval metrics CSV/JSON | Actual value/status/trust/context result. |
| `runtime_smokes` | `runtime_smoke_id` | `artifact_runs.run_id` | APEX/M40 reports | Direct runtime and Cockpit route scopes stay separate. |
| `route_smokes` | `route_smoke_id` | `artifact_runs.run_id` | route parity/Home reports | Expected 404 and expected empty states are typed. |
| `source_label_checks` | `source_label_check_id` | `artifact_runs.run_id` | A2M/source-guard reports | `missing_required_evidence`, `no_hit`, `claim_verified`. |
| `memory_audit_results` | `memory_audit_result_id` | `artifact_runs.run_id` | memory inventory JSON | Counts and surfacing risk without loading memory DBs. |
| `news_trace_results` | `news_trace_result_id` | `artifact_runs.run_id` | A2M trace JSON | Stage-by-stage news retrieval trace. |
| `dirty_worktree_events` | `dirty_worktree_event_id` | `artifact_runs.run_id` | `git status`, `diff-check.json` | Worktree dirt and allowlist evidence. |
| `registry_events` | `registry_event_id` | `artifact_runs.run_id` | registry list/claim/release output | Historical coordination events. |
| `data_missing_items` | `data_missing_id` | `artifact_runs.run_id` | `DATA_MISSING.md`, manifests | Missing evidence as rows. |
| `decisions_and_verdicts` | `decision_id` | `artifact_runs.run_id` | README verdicts, manifests | Report conclusion facts. |

## 8. Ingestion Manifest Contract

Full contract: `ingestion_manifest_contract.json`.

Required future manifest fields:

- `job_id`
- `lane`
- `mode`
- `production_data_access`
- `branch`
- `head`
- `worktree`
- `task_card`
- `output_dir`
- `started_at`
- `completed_at`
- `validation_commands`
- `changed_files`
- `result_verdicts`
- `data_missing`
- `save_recommendation`
- `source_artifact_references`

Recommended optional fields:

- `supporting_lanes`
- `base_head`
- `runtime_worktree`
- `artifact_family`
- `runtime_metadata`
- `scorecards`
- `do_not_do`

Normalization rules:

- Missing evidence must be `data_missing[]`, not omitted.
- Scorecard profile names are required for every score.
- Expected 404 and expected empty states are not failures.
- Live-data probes must set `production_data_access=true`.
- Status files are historical evidence, but live registry state remains authoritative.

## 9. Scorecard Dimension Model

Full model: `scorecard_dimension_model.json`.

First-class profiles:

- `canonical_core`
- `expanded_required`
- `confirmed_metric_coverage`
- `runtime_smoke`
- `route_parity`
- `source_label_semantics`
- `memory_integrity`
- `news_retrieval_trace`
- `UI_feature_honesty`
- `feedback_quality`

Core rule: every score or verdict must state which profile it belongs to and what it does not prove. `canonical_core` remains the strict no-regression profile only.

## 10. DATA_MISSING And Degraded State Model

Full model: `data_missing_and_degraded_state_model.md`.

States to encode:

- `DATA_MISSING`
- `degraded_runtime`
- `no_hit`
- `context_only`
- `missing_required_evidence`
- `production_data_access_blocked`
- `untrusted_memory`
- `stale_artifact`
- `test_blocked_environment`
- `route_expected_404`
- `expected_empty_state`

Reporting rule: failures, blocked tests, missing evidence, expected empty state, and degraded runtime must be counted separately.

## 11. MLflow Position

MLflow should be `DEFERRED`.

Rationale:

- Tenn already has a local file-backed MLflow wrapper for real-gold extraction eval.
- That wrapper is useful later for model/profile/run tracking.
- The current cross-system gap is not experiment tracking; it is manifest normalization and offline artifact comparison.
- Adding MLflow now would add another metadata surface before run identity, scorecard profiles, and `DATA_MISSING` semantics are stable.

Policy: do not add MLflow now. Do not add MLflow to backend dependencies. Revisit only after DuckDB/report manifests are stable.

## 12. Safe Implementation Roadmap

Full roadmap: `implementation_roadmap.md`.

Smallest next sequence:

1. Add manifest contract generator for future reports only.
2. Add offline DuckDB schema SQL under a report/prototype path.
3. Add one ingestion script that reads a tiny curated set of existing report JSON files into a DuckDB file under `reports`, not backend.
4. Add read-only CLI to query artifact runs.
5. Keep no production dependency.

## 13. Do Not Do

- Do not integrate DuckDB into backend request paths.
- Do not integrate DuckDB into Cockpit runtime paths.
- Do not add DuckDB to backend dependencies.
- Do not add MLflow to backend dependencies.
- Do not add MLflow now.
- Do not create a DuckDB database in a production path.
- Do not auto-import production data.
- Do not run live extraction.
- Do not run Qdrant queries.
- Do not run news loaders.
- Do not run chat/runtime smokes.
- Do not run Home producers.
- Do not replace existing eval reports.
- Do not modify canonical scorecards.
- Do not score from sparse feedback.
- Do not mix memory truth with financial truth.
- Do not infer live A2M/news/Qdrant state from static-only artifacts.

## 14. Validation Commands Run

Preflight:

- `pwd` -> `/home/l4nd0`
- `readlink -f /home/l4nd0/tenn-runtime` -> `/home/l4nd0/tenn-nvme-clean-baseline-reconstruct-v1`
- `git branch --show-current` in `/home/l4nd0/tenn-runtime` -> `migration/clean-runtime-baseline-reconstruct-v1`
- `git rev-parse --short=12 HEAD` in `/home/l4nd0/tenn-runtime` -> `669bff1c7e4f`
- `git status --short` in `/home/l4nd0/tenn-runtime` -> clean
- `git worktree list` -> many worktrees; active A2M live trace worktree present; isolated audit worktree created
- `git show --stat --oneline --no-renames HEAD` -> `669bff1c milestone(evaluation): checkpoint asx extraction audit artifacts`

Task card and registry:

- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/evaluation_spine_duckdb_schema_audit_v1_20260520.md` -> `ok: true`
- `python3 scripts/agent_job_registry.py list-active` -> active A2M news retrieval parity job present
- `python3 scripts/agent_job_registry.py check-overlap docs/agent_tasks/evaluation_spine_duckdb_schema_audit_v1_20260520.md` -> `ok: true`
- `python3 scripts/agent_job_registry.py claim docs/agent_tasks/evaluation_spine_duckdb_schema_audit_v1_20260520.md` -> `ok: true`
- `python3 scripts/agent_job_registry.py heartbeat evaluation_spine_duckdb_schema_audit_v1_20260520` -> `ok: true`

Inspection:

- `find`, `rg`, `sed`, `jq`, and read-only shell inventory commands over the allowed inspection targets.
- Counted current inventory: 218 JSON files under `reports` maxdepth 3, 201 JSON files under `reports/agent_jobs` maxdepth 2, 82 README files, 70 status files, and 80 diff-check files.
- Confirmed expected extraction/canonical report artifacts listed in `DATA_MISSING.md` are absent in this checkout.

Artifact validation:

- `jq empty` over current JSON artifacts in this report directory -> passed for `artifact_family_inventory.json`, `ingestion_manifest_contract.json`, `scorecard_dimension_model.json`, and `status.json`.
- In-memory DuckDB parse attempt for `proposed_duckdb_schema.sql` -> `DUCKDB_MODULE_MISSING`; SQL was left as static-review design artifact.

Final validation:

- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/evaluation_spine_duckdb_schema_audit_v1_20260520.md --write-report` -> `ok: true`; wrote `validation.json`.
- `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/evaluation_spine_duckdb_schema_audit_v1_20260520.md` -> `ok: true`; wrote `diff-check.json`.
- `git diff --check` -> passed with no output.
- `for f in reports/agent_jobs/evaluation_spine_duckdb_schema_audit_v1_20260520/*.json; do jq empty "$f"; done` -> `JSON_OK`.
- DuckDB executable/module status: `command -v duckdb` returned no path and Python `import duckdb` returned `DUCKDB_MODULE_MISSING`; SQL was not executed and remains a static design artifact.
- `python3 scripts/agent_job_registry.py release evaluation_spine_duckdb_schema_audit_v1_20260520` -> `ok: true`.
- Final `python3 scripts/agent_job_registry.py list-active` -> this job absent; separate active job remains: `news_retrieval_parity_a2m_live_trace_v1_20260520`.

## 15. Final Git Status

Final scoped status:

```text
?? docs/agent_tasks/evaluation_spine_duckdb_schema_audit_v1_20260520.md
!! reports/agent_jobs/evaluation_spine_duckdb_schema_audit_v1_20260520/DATA_MISSING.md
!! reports/agent_jobs/evaluation_spine_duckdb_schema_audit_v1_20260520/README.md
!! reports/agent_jobs/evaluation_spine_duckdb_schema_audit_v1_20260520/artifact_family_inventory.json
!! reports/agent_jobs/evaluation_spine_duckdb_schema_audit_v1_20260520/data_missing_and_degraded_state_model.md
!! reports/agent_jobs/evaluation_spine_duckdb_schema_audit_v1_20260520/diff-check.json
!! reports/agent_jobs/evaluation_spine_duckdb_schema_audit_v1_20260520/implementation_roadmap.md
!! reports/agent_jobs/evaluation_spine_duckdb_schema_audit_v1_20260520/ingestion_manifest_contract.json
!! reports/agent_jobs/evaluation_spine_duckdb_schema_audit_v1_20260520/proposed_duckdb_schema.md
!! reports/agent_jobs/evaluation_spine_duckdb_schema_audit_v1_20260520/proposed_duckdb_schema.sql
!! reports/agent_jobs/evaluation_spine_duckdb_schema_audit_v1_20260520/scorecard_dimension_model.json
!! reports/agent_jobs/evaluation_spine_duckdb_schema_audit_v1_20260520/status.json
!! reports/agent_jobs/evaluation_spine_duckdb_schema_audit_v1_20260520/validation.json
```

`reports/` is ignored in this checkout, so report artifacts are visible with `--ignored`. `check-diff` passed because the only non-ignored changed file is the task card and it is allowed.

## 16. Registry Release Status

Released.

- `release` returned `ok: true`.
- `status.json` now has `status: released` and `released_at: 2026-05-20T03:22:14.046444Z`.
- Final `list-active` shows no active record for this evaluation spine job.
- The separate active A2M live trace job remains active and was not touched.

## 17. Project Memory Save Recommendation

SAVE_RECOMMENDED: save that Tenn's local evaluation spine should start as a DuckDB-first offline report warehouse over manifest-normalized artifacts, with scorecard profile separation mandatory and MLflow deferred until manifests/DuckDB tables stabilize. Also save the first safe implementation sequence: manifest generator, report-local schema prototype, curated JSON ingestion, read-only CLI, no production dependency.
