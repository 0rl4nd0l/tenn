# Confirmed Metric Extracted-Payload Scoring Audit v1

## Scope

- GitHub issue: #63.
- Lane: Evaluation.
- Supporting lanes: Financial Truth, Provenance.
- Execution mode: AUDIT ONLY.
- Target system layer: evaluation/reporting evidence only.
- Contract boundary: no parser routing, extraction prompts, scorecard code, fixture labels, gold labels, canonical financial truth, production DB, Qdrant, source PDFs, news, memory, ingestion, extraction, or generated payload mutation.

## Preflight Declaration

- Agent: Codex.
- Branch: `audit/repo-hygiene-safe-audits-v1-20260525`.
- Worktree: `/home/l4nd0/tenn-repo-hygiene-audits-v1-20260525`.
- Intended files: this task card and report directory only.
- Contested surfaces touched: none.
- Collision risk: LOW.
- Decision: proceed report-only.

## Executive Result

Current confirmed metric coverage cannot be scored against extracted payloads in this checkout because no current generated extracted-payload artifact set is present.

The confirmed metric coverage denominator remains explicit:

- Profile: `confirmed_metric_coverage`.
- Eligible scored-ready rows: 73.
- Excluded candidate rows: 70.
- Excluded ambiguous or derived rows: 3.

The extracted-payload score remains `DATA_MISSING`. Source-PDF openability is resolved, but source-route openability is not extraction correctness.

## Evidence References

- Source-PDF resolution: `reports/agent_jobs/confirmed_metric_source_pdf_resolution_audit_v1_20260524/README.md`.
- Scoring-gap artifact: `reports/agent_jobs/confirmed_metric_scoring_gap_safe_extension_v1_20260524/confirmed_metric_scoring_gap_report.json`.
- Evidence manifest: `reports/agent_jobs/eval_spine_current_evidence_manifest_audit_v1_20260525/evidence_manifest.json`.

## Extracted Payload Inventory

Generated extraction-eval artifact directories checked:

- `reports/extraction_eval`: absent.
- `financial-engine_v2/reports/extraction_eval`: absent.
- `financial-engine_v2/backend/reports/extraction_eval`: absent.

Synthetic unit-test fixtures exist under `financial-engine_v2/backend/tests/fixtures/extraction_eval/`, but they are not generated current extracted payloads for the confirmed metric coverage fixtures. Their fixture IDs have zero overlap with the 15 confirmed metric fixture IDs.

## Scoring Availability

- `confirmed_metric_coverage`: denominator known, extracted-payload score unavailable, status `DATA_MISSING`.
- `canonical_core`: outside this audit denominator; not combined.
- `expanded_required`: outside this audit denominator; not combined.

No candidate rows were promoted. No ambiguous or derived rows were promoted. No broad extraction accuracy claim is made.

## Boundary Statement

This audit did not run production extraction, ingestion, backfill, reindex, source PDF regeneration, parser routing, or scorecard writes. It did not mutate canonical truth or any data store.

## DATA_MISSING

- Current generated extracted payloads for the 73 eligible confirmed metric coverage rows.
- Current confirmed metric coverage extracted-payload accuracy score.
- Broad extraction accuracy proof.
- Live HTTP/source serving proof, which remains separate from payload scoring.

## Validation

- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/confirmed_metric_extracted_payload_scoring_audit_v1_20260525.md`: passed after correcting `mutation_mode` to `audit_only`.
- `python3 scripts/agent_job_registry.py list-active`: passed, no active jobs before claim.
- `python3 scripts/agent_job_registry.py check-overlap docs/agent_tasks/confirmed_metric_extracted_payload_scoring_audit_v1_20260525.md`: passed.
- `python3 scripts/agent_job_registry.py claim docs/agent_tasks/confirmed_metric_extracted_payload_scoring_audit_v1_20260525.md`: passed.
- Artifact inventory command: passed.
- Backend scorecard import through system Python: failed due missing `pydantic_settings`; not used for the audit conclusion.
- `python3 -m json.tool` on all JSON report artifacts: passed.
- `git diff --check`: passed.
- `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/confirmed_metric_extracted_payload_scoring_audit_v1_20260525.md`: passed.
- `python3 scripts/agent_job_registry.py release confirmed_metric_extracted_payload_scoring_audit_v1_20260525`: passed.
