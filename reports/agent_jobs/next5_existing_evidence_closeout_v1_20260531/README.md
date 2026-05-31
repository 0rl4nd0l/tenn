# Next Five Existing Evidence Closeout v1

## Summary

This report handles the closeable existing-evidence slice from the next-five
issue set after #74.

Closed-scope issues:

- #112: nightly-news final-status observability.
- #114: missing nightly-news ticker universe input.
- #115: report-only Codex nightly lock-up audit.

Remaining next issues:

- #71 remains open because it still needs a committed source-label fixture matrix
  task/test artifact.
- #88 remains open because it still needs the memory-system fitness audit report.

## Preflight

| Field | Value |
|---|---|
| Agent | Codex |
| Lane | Reporting |
| Worktree | `/home/l4nd0/tenn-next5-existing-evidence-closeout-v1-20260531` |
| Branch | `safe/next5-existing-evidence-closeout-v1-20260531` |
| Base HEAD | `7ee06fbdad5f954056981769eef3ba25bee86480` |
| Execution mode | `audit_only` |
| Collision risk | LOW |
| Contested surfaces touched | none |

Active registry jobs during claim:

- Active Financial Truth safe-extension job:
  `extraction_clv_tableless_metric_fix_v1_20260531`, different lane/files.
- Stale Query Orchestration audit job:
  `query_orchestration_inference_engine_phase1_audit_v1_20260529`, different
  report directory.

Task-card overlap check passed with no issues.

## Evidence

The fix/report commit for #112, #114, and #115 is GitHub-visible:

- Commit:
  `3725591cf76ec1a56428a476e23dbd1ebc4050fc`
- URL:
  https://github.com/0rl4nd0l/tenn/commit/3725591cf76ec1a56428a476e23dbd1ebc4050fc
- Subject:
  `milestone(runtime): repair nightly news ingest observability`

## Issue #112

Close gate: `COMPLETED_WITH_EVIDENCE`.

Evidence:

- `financial-engine_v2/scripts/nightly_news.sh` writes
  `nightly_news_<stamp>.status.json` on success or failure.
- It records phase states for initializing, fetch, sync, memo, memo_backfill,
  and finish.
- It supports no-write smoke validation with `NIGHTLY_NEWS_DRY_RUN=1`.
- Current shell syntax check passed:
  `bash -n financial-engine_v2/scripts/nightly_news.sh`.
- Report artifact:
  `reports/agent_jobs/nightly_news_observability_followup_v1_20260526/README.md`
- Status artifact parsed:
  `reports/agent_jobs/nightly_news_observability_followup_v1_20260526/status.json`

## Issue #114

Close gate: `COMPLETED_WITH_EVIDENCE`.

Evidence:

- `financial-engine_v2/data/raw/asx_ticker_universe.txt` exists.
- Current SHA-256:
  `042b6b799c24ecbcf0c94f73ac94753e90d35f8282cd10205c17a2f7f8479cf9`
- Current line count: `376`.
- `nightly_news.sh` passes `--tickers-file` explicitly to
  `fetch_daily_news.py`.
- Prior no-write dry-run evidence in the committed report recorded
  `tickers_count=375`.
- Report artifact:
  `reports/agent_jobs/nightly_news_ticker_universe_input_repair_v1_20260526/README.md`
- Status artifact parsed:
  `reports/agent_jobs/nightly_news_ticker_universe_input_repair_v1_20260526/status.json`

## Issue #115

Close gate: `COMPLETED_AUDIT_ONLY_WITH_FOLLOWUPS`.

Evidence:

- Report-only lock-up artifacts exist under
  `reports/agent_jobs/codex_nightly_lockup_report_v1_20260526/`.
- The lock-up report states no branches were merged, cleaned, rebased, reset,
  stashed, deleted, pruned, or archived.
- It records no memory file or Tenn memory-store writes.
- It produced `README.md`, `status.json`, `branch_matrix.json`,
  `github_activity.json`, `memory_candidates.md`, and `next_day_handoff.md`.
- JSON artifacts parsed successfully.

Follow-up handling:

- Branch/worktree reduction is explicitly not performed here and remains a
  separate operator-approved hygiene pass if desired.
- Runner integration is not required to close the first report-only audit
  objective; it can be a later task if the operator wants automation wiring.

## Boundaries

- No production DB/Qdrant/news/memory mutation.
- No canonical financial truth mutation.
- No parser routing / extraction prompt / gold-label mutation.
- No runtime/model/GPU/service config mutation.
- No installed cron/systemd mutation.
- No product/backend/frontend/runtime source changes in this closeout task.
- No unrelated dirty work touched.

## DATA_MISSING

- `graphify-out/wiki/index.md` and `graphify-out/GRAPH_REPORT.md` are absent in
  this checkout.
- No GitHub Actions run was found for this closeout branch at report time; this
  report did not create a PR.
