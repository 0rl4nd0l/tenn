# Confirmed Metric Scoring Gap Safe Extension v1

Lane: Evaluation
Supporting lanes: Financial Truth, Provenance
Branch: `safe/confirmed_metric_scoring_gap_safe_extension_v1_20260524`
HEAD at validation: `84a17f10dc1e6a491fd1fb70088c84502494bd39`
Worktree: `/home/l4nd0/tenn-confirmed-metric-scoring-gap-safe-extension-v1-20260524`
Execution mode: SAFE EXTENSION
Contested surfaces touched: none
Collision risk: MEDIUM bounded evaluation/report artifacts; no HIGH overlap found
Decision: proceed

## Executive Result

A confirmed metric coverage scoring-gap artifact was produced for the current fixture scorecard denominator.

The current `confirmed_metric_coverage` profile has 146 fixture expectations across 15 fixtures. The exact scoring denominator for future extracted-payload scoring is 73 eligible `CONFIRMED_SOURCE_EVIDENCED` / scorecard-scored-ready rows. The 70 `CANDIDATE_REVIEW_REQUIRED` rows and 3 `AMBIGUOUS_OR_DERIVED` rows remain excluded.

No broad metric extraction accuracy score was claimed. The generated artifact reports the gap: source-route openability is proven through the existing allowlisted `/data/asx/docs` resolver, while extracted-payload scoring remains DATA_MISSING.

## Confirmed

- Task card `docs/agent_tasks/confirmed_metric_scoring_gap_safe_extension_v1_20260524.md` validates under current repo tooling.
- Registry overlap check returned no HIGH overlap; the initially active Strategy Lab job was Reporting-only and did not touch this task's allowed files.
- The isolated worktree starts from `84a17f10dc1e6a491fd1fb70088c84502494bd39` and avoids the unrelated dirty `cockpit-ui/next-env.d.ts` in the canonical checkout.
- Source-route resolver openability is current-turn proven for 15/15 fixture source groups and 146/146 fixture rows.
- Project-root fixture-file existence remains a path-scope mismatch: 146/146 rows are missing under `financial_engine_root / pdf_path`, but this is distinct from source-route openability.
- Profile labels remain separate: `canonical_core`, `expanded_required`, and `confirmed_metric_coverage` are not combined.
- No canonical financial truth, fixture labels, parser routing, extraction routing, source PDFs, DB, Qdrant, memory store, or production data were mutated.

## Inferred

- The next safe scoring step is to feed existing, non-production extracted payload artifacts into the confirmed metric coverage scorer, if such artifacts are produced by a separate bounded task.
- The principal remaining gap is extracted-payload availability and scoring, not source-PDF route resolution.

## Speculative

- Live Cockpit HTTP source serving should work if the backend runtime uses the same `/data/asx/docs` source root and auth path, but this task did not start or authenticate against the backend.

## DATA_MISSING

- Current extracted-payload scoring for confirmed metric coverage.
- Current generated `reports/extraction_eval` latest artifact.
- `graphify-out/GRAPH_REPORT.md` and `graphify-out/wiki/index.md`.
- Live authenticated HTTP source-route proof.
- Broad metric extraction accuracy score.

## Scoring Denominator

- Profile: `confirmed_metric_coverage`
- Denominator source: current fixture scorecard inventory from `build_confirmed_metric_coverage_scorecard()`.
- Eligible scored-ready rows: 73
- Excluded candidate rows: 70
- Excluded ambiguous/derived rows: 3
- Total fixture expectations: 146
- Denominators combined: no

## Produced Artifact

`confirmed_metric_scoring_gap_report.json` was produced. It is a scoring-gap artifact, not an accuracy score. It records the eligible denominator, excluded rows, source-PDF route status, extracted-payload DATA_MISSING status, and per-metric-family gaps.

## What This Proves

- Source-PDF route resolution no longer blocks the 73 eligible confirmed metric coverage rows.
- Candidate and ambiguous exclusions are preserved.
- The confirmed metric coverage denominator is explicit and separate from `canonical_core` and `expanded_required`.

## What This Does Not Prove

- It does not prove extracted-payload correctness.
- It does not prove broad metric extraction accuracy.
- It does not prove live authenticated HTTP source serving.
- It does not promote any candidate or ambiguous labels.

## Validation Results

- Task-card validation: pass.
- Registry list/check-overlap/claim/release: pass.
- Focused review tests: 5 passed.
- Focused API tests: 15 passed, with existing pydantic/FastAPI warnings.
- JSON validation for generated artifacts: pass.
- `git diff --check`: pass.
- Task-card `check-diff`: pass, disallowed files empty.
- Final registry `list-active`: active jobs empty.

## Changed Files

- `docs/agent_tasks/confirmed_metric_scoring_gap_safe_extension_v1_20260524.md`
- `reports/agent_jobs/confirmed_metric_scoring_gap_safe_extension_v1_20260524/README.md`
- `reports/agent_jobs/confirmed_metric_scoring_gap_safe_extension_v1_20260524/status.json`
- `reports/agent_jobs/confirmed_metric_scoring_gap_safe_extension_v1_20260524/confirmed_metric_scoring_gap_report.json`
- `reports/agent_jobs/confirmed_metric_scoring_gap_safe_extension_v1_20260524/validation.json`
- `reports/agent_jobs/confirmed_metric_scoring_gap_safe_extension_v1_20260524/diff-check.json`

## Final Worktree Status

Expected final state after commit: clean. `reports/` is ignored by the shared git info exclude, so the allowed report artifacts are intentionally force-added for commit.

## Project Memory Save Recommendation

SAVE_RECOMMENDED: source-route openability is no longer the scoring blocker; the confirmed metric coverage scoring gap is now normalized around denominator 73, with extracted-payload scoring still DATA_MISSING.
