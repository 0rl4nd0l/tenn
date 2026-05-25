# Eval Spine Normalizer Surfacing v1

Generated: 2026-05-25T15:27:03+10:00

## Scope

- GitHub issue: #50.
- Lane: Evaluation.
- Supporting lanes: Reporting, Provenance.
- Execution mode: AUDIT ONLY closeout for existing safe-extension evidence.
- Target system layer: evaluation/reporting artifacts only.
- Contract boundary: no extraction logic, parser routing, prompts, gold labels, canonical truth, source PDFs, DB/Qdrant/news/memory stores, production data, Cockpit runtime display, service start, model/runtime config, or extracted-payload accuracy generation.

## Preflight Declaration

- Agent: Codex.
- Branch: `audit/repo-hygiene-safe-audits-v1-20260525`.
- Worktree: `/home/l4nd0/tenn-repo-hygiene-audits-v1-20260525`.
- Pre-closeout HEAD: `2bb96b0bd2fd`.
- Pre-closeout git status: clean against origin before this task card/report was added.
- Registry before claim: `active_jobs: []`.
- Intended files: `docs/agent_tasks/eval_spine_normalizer_surfacing_v1_20260524.md` and this issue-exact report directory only.
- Contested surfaces touched: none.
- Collision risk: LOW.
- Decision: proceed report-only.

## Executive Result

Issue #50 is safe to close as acceptance met for the bounded audit/safe-extension scope. This closeout does not claim Cockpit runtime display integration.

Existing evidence shows the normalizer is no longer buried only in implementation code:

- `scripts/reporting/README.md` documents the operator/agent invocation and interpretation guardrails.
- `reports/agent_jobs/eval_spine_normalizer_usage_followup_v1_20260524/normalized_manifest.json` surfaces profile-separated output.
- `scorecards.csv` surfaces one row per profile, with explicit overclaim guards.
- `metric_expectations.csv` surfaces per-metric expectation classes.
- The current artifact preserves `canonical_core`, `expanded_required`, and `confirmed_metric_coverage` as separate profiles and explicitly marks confirmed metric coverage as inventory-only, not current accuracy.

The remaining display gap is runtime/UI surfacing. That requires a separate child card if needed because this issue's bounded safe extension stayed offline/report-local.

## Evidence References

- Base normalizer report: `reports/agent_jobs/gold_metric_coverage_eval_spine_normalizer_v1_20260524/README.md`.
- Usage follow-up report: `reports/agent_jobs/eval_spine_normalizer_usage_followup_v1_20260524/README.md`.
- Normalized manifest: `reports/agent_jobs/eval_spine_normalizer_usage_followup_v1_20260524/normalized_manifest.json`.
- Scorecard CSV: `reports/agent_jobs/eval_spine_normalizer_usage_followup_v1_20260524/scorecards.csv`.
- Metric expectations CSV: `reports/agent_jobs/eval_spine_normalizer_usage_followup_v1_20260524/metric_expectations.csv`.
- Operator/agent documentation: `scripts/reporting/README.md`.
- Existing implementation commit in current branch history: `d00110b3`.

## Surfacing Map

Current surfacing:

- Script/API surface: `scripts/reporting/gold_metric_coverage_eval_spine_normalizer.py`.
- Agent/operator docs: `scripts/reporting/README.md`.
- Report-local status/evidence: `reports/agent_jobs/eval_spine_normalizer_usage_followup_v1_20260524/README.md` and `status.json`.
- Machine-readable manifest: `normalized_manifest.json`.
- Spreadsheet-friendly summaries: `scorecards.csv` and `metric_expectations.csv`.

Still separate or intentionally out of scope:

- Cockpit runtime/status UI display: not implemented by this issue.
- Current confirmed metric extracted-payload accuracy: `DATA_MISSING`.
- Production eval store ingestion: not required for this issue's bounded safe-extension closeout.

## Issue Acceptance Matrix

Current surfacing gaps are proven: met. The report family identifies report-local/offline visibility as implemented and Cockpit/runtime display as out of scope.

Profile labels remain separate: met. `canonical_core`, `expanded_required`, and `confirmed_metric_coverage` are preserved in the generated sample artifacts.

No broad accuracy claim is made: met. Confirmed metric coverage remains breadth inventory, not current accuracy.

Any implementation is separately bounded and validated: met. Existing implementation is limited to offline reporting docs/script/tests/sample artifacts; no runtime or extraction surfaces were changed by this closeout.

## DATA_MISSING

- `confirmed_metric_coverage_current_accuracy`, because no current extracted-payload scoring artifact was supplied.
- Cockpit runtime/status display of normalized profile data.
- Production eval-store ingestion or automation beyond report-local artifacts.

## Boundary Statement

This closeout did not modify extraction logic, parser routing, prompts, gold labels, canonical truth, source PDFs, DB/Qdrant/news/memory stores, production data, Cockpit runtime surfaces, or services. It did not generate or claim new extraction accuracy.

## Validation

- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/eval_spine_normalizer_surfacing_v1_20260524.md`: passed.
- `python3 scripts/agent_job_registry.py list-active`: passed; no active jobs.
- `python3 scripts/agent_job_registry.py check-overlap docs/agent_tasks/eval_spine_normalizer_surfacing_v1_20260524.md`: passed.
- `python3 scripts/agent_job_registry.py claim docs/agent_tasks/eval_spine_normalizer_surfacing_v1_20260524.md`: passed.
- `python3 -m json.tool reports/agent_jobs/eval_spine_normalizer_usage_followup_v1_20260524/normalized_manifest.json`: passed.
- Presence checks for `scorecards.csv`, `metric_expectations.csv`, and `scripts/reporting/README.md`: passed.
- `git merge-base --is-ancestor d00110b3 HEAD`: passed.
- `git diff --check`: passed.
- `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/eval_spine_normalizer_surfacing_v1_20260524.md`: passed.
- `python3 scripts/agent_job_registry.py release eval_spine_normalizer_surfacing_v1_20260524`: passed.
- `python3 scripts/agent_job_registry.py list-active` after release: passed; no active jobs reported.
