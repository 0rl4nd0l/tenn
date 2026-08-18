# Confirmed Metric Source PDF Resolution Audit v1

Lane: Evaluation  
Supporting lane: Provenance  
Branch: `migration/clean-runtime-baseline-reconstruct-v1`  
HEAD at audit: `6e6dcdbdb03c37cecc731a30c090050813ba4368`  
Worktree: `/home/l4nd0/tenn-nvme-clean-baseline-reconstruct-v1`  
Canonical path checked: `/home/l4nd0/tenn` resolves to this worktree  
Execution mode: AUDIT ONLY  
Intended files: this task card and this report directory only  
Contested surfaces touched: none  
Collision risk: LOW for task card/report artifacts; HIGH paths were not touched  
Decision: proceed report-only

## Executive Result

The confirmed metric coverage source-PDF blocker is not a true missing-file blocker in the current operator environment.

All 15 confirmed metric coverage fixture source groups, covering all 146 fixture rows, resolve to readable PDF files through the existing allowlisted `/data/asx/docs` root. On this host `/data/asx/docs` resolves to `/mnt/tenn-nvme2/tenn/financial-engine_v2/data/asx/docs`.

The earlier missing-PDF signal comes from a different check: `extraction_gold_eval_scorecard._source_pdf_exists()` tests only `PROJECT_ROOT / pdf_path` for relative fixture paths. That project-root candidate is empty for these fixture PDFs, so the review packet reports `missing_source_pdf_count=146` even though the source-route resolver can open all 146 row sources through the `/data` allowlist.

Scoring decision: source-PDF resolution no longer blocks the 73 scorecard-scored-ready rows. Candidate and ambiguous rows remain excluded. This audit does not score extracted payloads and does not claim broad metric extraction accuracy.

## Confirmed

- Task card `docs/agent_tasks/confirmed_metric_source_pdf_resolution_audit_v1_20260524.md` validates.
- Registry `list-active` initially returned no active jobs; `check-overlap` passed; the job was claimed safely.
- Source route roots are `financial-engine_v2/data/asx/docs` and `/data/asx/docs`.
- `/data` is a symlink to `/mnt/tenn-nvme2/tenn/financial-engine_v2/data`.
- All 15 fixture `pdf_path` values are local relative `data/asx/docs/...pdf` references, not external URLs.
- All 15 source PDFs resolve through the existing source-route resolver and have readable `%PDF-` headers.
- No fixture source group is allowlist-blocked, external-only, ambiguous, source-unopenable, or genuinely missing through the route resolver.
- No current `reports/extraction_eval` or `financial-engine_v2/reports/extraction_eval` artifact exists in this checkout.
- `graphify-out/GRAPH_REPORT.md` and `graphify-out/wiki/index.md` were not present.
- No source PDFs were copied, moved, renamed, downloaded, imported, regenerated, or normalized.

## Source-PDF Status Summary

By row:

- `openable_local_source`: 146
- `missing_local_source`: 0
- `path_mismatch`: 0 for the source route, but the scorecard project-root existence probe has 146 false missing rows
- `allowlist_blocked`: 0
- `external_only`: 0
- `ambiguous_source_reference`: 0
- `source_unopenable`: 0
- `DATA_MISSING`: 0 for fixture source PDF resolution

By fixture source group:

- 15/15 source groups openable through `/data/asx/docs`.
- 15/15 project-root candidates under this checkout are absent.
- 15/15 resolved files are readable PDFs.

## Row / Status Counts

- Total confirmed metric coverage rows: 146
- `CONFIRMED_SOURCE_EVIDENCED`: 73
- `CANDIDATE_REVIEW_REQUIRED`: 70
- `AMBIGUOUS_OR_DERIVED`: 3
- Source-openable rows: 146
- Rows eligible for the next source-PDF-unblocked scoring task: 73
- Rows excluded as candidate review required: 70
- Rows excluded as ambiguous/derived: 3

Review precision flags remain conservative:

- source page present: 103 rows
- source row present: 107 rows
- source table present: 12 rows
- precise source evidence flag: 0 rows
- human review required flag: 146 rows

Those precision flags should not be erased or relaxed. They are distinct from the source-PDF path-resolution blocker.

## Can Scoring Proceed?

Yes, but only as a separate child task and only for the 73 scorecard-scored-ready rows.

The next task may proceed from a source-PDF-resolution perspective because every scored-ready row's fixture source group is openable through the existing allowlist. It must still preserve:

- candidate rows excluded unless human review promotes them later;
- ambiguous rows excluded until ambiguity is resolved;
- profile-specific reporting;
- no canonical truth writes;
- no parser/routing changes;
- no broad metric extraction accuracy claim until extracted payload scorecards prove it.

## Inferred

- The review packet's `missing_source_pdf_count=146` is a stale/path-scope artifact rather than a real source-route failure.
- Operator PDF openability can be restored without copying PDFs by relying on the existing `/data/asx/docs` allowlist path.
- A future report/UI improvement should distinguish project-root fixture-file existence from source-route openability.

## Speculative

- If the runtime backend is configured with the same `/data` symlink and auth, Cockpit source-page opening should work for these 15 fixture PDFs. This audit did not start the backend or make authenticated HTTP calls.
- A later safe-extension could add explicit `source_route_status` or similar report metadata so operators do not confuse project-root missing with source-route missing.

## DATA_MISSING

- Current extracted-payload scoring for confirmed metric coverage remains DATA_MISSING.
- Current generated `reports/extraction_eval` latest artifact remains DATA_MISSING.
- Graphify report/wiki remain DATA_MISSING.
- HTTP serving through a live backend was not verified because this audit did not start runtime services.

## Next Safe Task Recommendation

Recommend exactly one next task: `confirmed_metric_scoring_gap_safe_extension_v1_20260524`.

Rationale: source-PDF path resolution is now resolved for all 146 rows, including all 73 scorecard-scored-ready rows. The next bounded task should produce or normalize the confirmed metric scoring artifact while preserving exclusions for 70 candidate rows and 3 ambiguous rows.

## Validation

Validation results are also recorded in `status.json` after final checks.

Planned validation set:

- task-card validation
- registry `list-active`
- registry `check-overlap`
- registry claim and release
- JSON validation for generated JSON artifacts
- `git diff --check`
- task-card `check-diff`
- final git status
- final registry `list-active`

## Registry Status

The job was claimed in the shared registry under `/mnt/sdb2/home/l4nd0/tenn/.git/tenn-agent-registry`. Final release status is recorded in `status.json`.

## Changed Files

- `docs/agent_tasks/confirmed_metric_source_pdf_resolution_audit_v1_20260524.md`
- `reports/agent_jobs/confirmed_metric_source_pdf_resolution_audit_v1_20260524/README.md`
- `reports/agent_jobs/confirmed_metric_source_pdf_resolution_audit_v1_20260524/status.json`
- `reports/agent_jobs/confirmed_metric_source_pdf_resolution_audit_v1_20260524/source_pdf_resolution_matrix.json`
- `reports/agent_jobs/confirmed_metric_source_pdf_resolution_audit_v1_20260524/source_path_gap_register.json`
- `reports/agent_jobs/confirmed_metric_source_pdf_resolution_audit_v1_20260524/next_task_recommendation.md`
- `reports/agent_jobs/confirmed_metric_source_pdf_resolution_audit_v1_20260524/recommended_child_task_card.md`
- `reports/agent_jobs/confirmed_metric_source_pdf_resolution_audit_v1_20260524/validation.json`
- `reports/agent_jobs/confirmed_metric_source_pdf_resolution_audit_v1_20260524/diff-check.json`

## Project Memory Save Recommendation

`SAVE_RECOMMENDED`: this audit corrects the prior "all PDFs missing" interpretation by separating project-root existence from source-route openability, and it establishes the safe next scoring task boundary.
