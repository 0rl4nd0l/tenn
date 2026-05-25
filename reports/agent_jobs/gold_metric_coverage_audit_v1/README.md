# Gold Metric Coverage Audit v1

Generated: 2026-05-25T15:10:37+10:00

## Scope

- GitHub issue: #37.
- Lane: Evaluation.
- Supporting lanes: Financial Truth, Provenance.
- Execution mode: AUDIT ONLY.
- Target system layer: evaluation/reporting evidence only.
- Contract boundary: no parser routing, extraction prompts, scorecard code, fixture labels, gold labels, canonical financial truth, production DB, Qdrant, source PDFs, news, memory, ingestion, extraction, generated payload, runtime, service, or GPU mutation.

## Preflight Declaration

- Agent: Codex.
- Branch: `audit/repo-hygiene-safe-audits-v1-20260525`.
- Worktree: `/home/l4nd0/tenn-repo-hygiene-audits-v1-20260525`.
- Intended files: `docs/agent_tasks/gold_metric_coverage_audit_v1.md` and this issue-exact report directory only.
- Contested surfaces touched: none.
- Collision risk: LOW.
- Decision: proceed report-only.

## Executive Result

Issue #37 is satisfied by the existing dated Gold Metric Coverage Audit artifact family plus the current May 25 Eval Spine and confirmed metric scoring evidence.

The current evidence separates the three profiles:

- `canonical_core`: 10 real-gold documents and 24 required checks over `revenue`, `operating_cash_flow`, and `net_debt`; this is a strict no-regression anchor only.
- `expanded_required`: 15 real-gold documents and 39 required checks over the same three metric families; this is current required-subset stability only.
- `confirmed_metric_coverage`: 15 backend eval fixtures, 146 expectations, 73 eligible scored-ready rows, 70 candidate rows, and 3 ambiguous or derived rows; this is breadth inventory, and the current extracted-payload score remains `DATA_MISSING`.

No broad production extraction coverage claim is supported by current artifacts. No extraction run was performed for this closeout.

## Evidence References

- Dated #37 audit bundle: `reports/agent_jobs/gold_metric_coverage_audit_v1_20260519/README.md`.
- Corpus inventory: `reports/agent_jobs/gold_metric_coverage_audit_v1_20260519/corpus_inventory.json`.
- Metric inventory: `reports/agent_jobs/gold_metric_coverage_audit_v1_20260519/metric_inventory.json`.
- Scorecard proposal: `reports/agent_jobs/gold_metric_coverage_audit_v1_20260519/scorecard_proposal.json`.
- Current evidence manifest: `reports/agent_jobs/eval_spine_current_evidence_manifest_audit_v1_20260525/evidence_manifest.json`.
- Current confirmed metric payload scoring audit: `reports/agent_jobs/confirmed_metric_extracted_payload_scoring_audit_v1_20260525/scoring_availability.json`.

## Required Issue Sections

Corpus inventory: present in the dated audit bundle. The current issue-exact closeout does not duplicate the full inventory JSON; it references the parsed, validation-checked artifact.

All labelled metrics by document: present in the dated audit README and metric inventory.

Required/scored metrics: `revenue`, `operating_cash_flow`, and `net_debt` are the only current real-gold required-scored metric families for `canonical_core` and `expanded_required`.

Confirmed-unscored metrics: present in `confirmed_metric_coverage` and separated from required scoring. They must not be silently merged into canonical no-regression scoring.

Ambiguous/derived metrics: 3 rows are currently excluded from confirmed metric extracted-payload scoring; they were not promoted.

Schema/evaluator support matrix: represented by the dated metric inventory and scorecard proposal. The proposal requires profile names and separate eligible, candidate, ambiguous, unsupported, and `DATA_MISSING` counts.

Scorecard proposal: `canonical_core`, `expanded_required`, and `confirmed_metric_coverage` remain separate output profiles with different acceptance language.

Blast-radius analysis: the main risk is overclaiming. Existing canonical and expanded scorecards prove no-regression or required-subset stability only, not production extraction breadth. Current confirmed coverage can define the denominator, but cannot emit an extracted-payload accuracy score without current generated payload artifacts.

Safe next step: use the #63 result as the next evaluation gate. Build or locate a non-production generated extracted-payload artifact set for the 73 eligible confirmed metric rows, then score only those eligible rows without promoting candidate or ambiguous rows.

## DATA_MISSING

- Current generated extracted payloads for the 73 eligible confirmed metric coverage rows.
- Current confirmed metric coverage extracted-payload accuracy score.
- Broad production extraction accuracy proof.
- Source URL completeness for all current real-gold fixtures.
- Approved Tier 2 and Tier 3 metric acceptance criteria beyond the current supported set.

## Boundary Statement

This closeout did not run production extraction, ingestion, backfill, reindexing, live Docling, parser routing, source route smoke, service start/stop/restart, GPU work, or scorecard writes. It did not mutate canonical truth, source PDFs, fixture labels, prompts, code, DB, Qdrant, memory, or runtime state.

## Validation

- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/gold_metric_coverage_audit_v1.md`: passed.
- `python3 scripts/agent_job_registry.py list-active`: passed; one non-overlapping Strategy Lab job active.
- `python3 scripts/agent_job_registry.py check-overlap docs/agent_tasks/gold_metric_coverage_audit_v1.md`: passed.
- `python3 scripts/agent_job_registry.py claim docs/agent_tasks/gold_metric_coverage_audit_v1.md`: passed.
- `python3 -m json.tool` on dated corpus inventory, metric inventory, scorecard proposal, #63 scoring availability, and #62 evidence manifest: passed.
- `git diff --check`: passed.
- `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/gold_metric_coverage_audit_v1.md`: passed.
- `python3 scripts/agent_job_registry.py release gold_metric_coverage_audit_v1`: passed.
- `python3 scripts/agent_job_registry.py list-active` after release: passed; no active jobs reported.
