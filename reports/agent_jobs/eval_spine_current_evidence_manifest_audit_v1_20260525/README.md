# Eval Spine Current Evidence Manifest Audit

Generated: 2026-05-25T14:29:56+10:00

## Scope

- GitHub issue: #62.
- Lane: Evaluation.
- Execution mode: AUDIT MODE.
- Target system layer: report-bundle inventory and current evidence normalization only.
- Contract boundary: no production DB, Qdrant, news, memory, ingestion, extraction, reindexing, migration, restart, package install, parser, source-label, UI, runtime, or service changes.

## Executive Result

This audit consolidates the current May 25 report evidence into one manifest. It deliberately does not treat closed audit tasks as product completion.

Confirmed current state:

- Confirmed metric source-PDF route openability is resolved for 146/146 fixture rows and the scoring denominator is explicit at 73 eligible rows.
- Confirmed metric extracted-payload scoring remains DATA_MISSING.
- Source-label sufficiency now requires deterministic `recent_news_event` evidence for recent-news/update claims, and a positive fixture exists.
- A2M is present in Qdrant news chunks, but SQLite/projection parity remains DATA_MISSING.
- Memory fanout risk is bounded by inventory/design reports, not fixed in runtime: 4 suspicious source-fanout clusters covering 17 active selectable entries remain pending operator-approved handling.
- Strategy Lab can display verified read-only sandbox proof, but current sidecar availability, paper/live trading, store writes, and canonical financial truth remain explicitly unavailable.
- Production hardening is not closed. Worker provenance, merge parking/report visibility, Graphify instruction wording, worktree hygiene, Redis health semantics, and CI suite health remain open control-plane gaps.
- PR #39 currently fails `CI / lint-and-test` at backend+cockpit pytest on head `9940a9a78bad0694ce9066528a8f40067128eb2f`; Sloppy Scan passes.

## Current Report Families

- Financial truth / confirmed metrics:
  - `confirmed_metric_source_pdf_resolution_audit_v1_20260524`
  - `confirmed_metric_scoring_gap_safe_extension_v1_20260524`
  - `gold_metric_coverage_audit_v1_20260519`
  - `gold_metric_coverage_eval_spine_normalizer_v1_20260524`
  - `eval_spine_normalizer_usage_followup_v1_20260524`
- Query/provenance trust:
  - `source_label_semantic_sufficiency_guard_v1_20260524`
  - `source_label_semantic_sufficiency_live_failure_fix_v1_20260524`
  - `recent_news_positive_claim_verified_fixture_v1_20260524`
  - `a2m_news_projection_path_discovery_v1_20260524`
  - `a2m_news_live_trace_readonly_v1_20260524`
- Memory:
  - `memory_live_inventory_readonly_v1_20260524`
  - `memory_fanout_suppression_quarantine_design_v1_20260524`
- Strategy Lab:
  - `strategy_lab_quantdinger_verified_readonly_status_v1_20260525`
- Control plane / hardening:
  - `pr39_ci_failure_root_cause_audit_v1_20260525`
  - `production_hardening_gate_audit_v1_20260525`
  - `worker_gpu_worker_provenance_env_parity_audit_v1_20260525`
  - `redis_role_audit_v1_20260525`
  - `worktree_taskcard_hygiene_audit_v1_20260525`
  - `merge_parking_registry_surface_audit_design_v1_20260525`
  - `graphify_artifact_contract_audit_v1_20260525`

## PR / CI Snapshot

- PR #39 is open and draft. It is `UNSTABLE`.
- PR #39 failing check: `lint-and-test`, run `26379324415`, job `77645418602`.
- PR #39 passing check on same head: `scan`, run `26379324430`.
- Current root cause classification from #66: broad backend+cockpit suite-readiness/product-contract failure, not dependency install or Ruff.

## Open Issue Snapshot

Current open issues at evidence time included #63, #62, #61, #57, #56, #55, #54, #53, #51, #50, #49, #46, #42, #41, #40, #38, #37, and #36.

Safe immediate continuation recommended by this manifest:

1. Create the merge parking registry safe extension from the #65 design.
2. Update stale Graphify contract wording from #67.
3. Run #63 confirmed metric extracted-payload scoring audit.

## DATA_MISSING Summary

- Current extracted-payload scoring for confirmed metric coverage.
- Current generated `reports/extraction_eval` latest artifact.
- Live authenticated HTTP source-route proof for confirmed metric PDFs.
- SQLite-to-Qdrant parity for A2M/news because checked source SQLite files are absent.
- Nightly fallback refresh success/failure evidence for materializing `news.sqlite`.
- Operator decisions for memory fanout candidate preserve/suppress/expire.
- Live worker/gpu_worker runtime provenance truth.
- Live production hardening smoke and full validation run.
- `graphify-out/GRAPH_REPORT.md` and `graphify-out/wiki/index.md`.
- Committed merge parking registry implementation.

## Validation

- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/eval_spine_current_evidence_manifest_audit_v1_20260525.md`: passed.
- `python3 scripts/agent_job_registry.py list-active`: passed.
- `python3 scripts/agent_job_registry.py check-overlap docs/agent_tasks/eval_spine_current_evidence_manifest_audit_v1_20260525.md`: passed.
- `python3 scripts/agent_job_registry.py claim docs/agent_tasks/eval_spine_current_evidence_manifest_audit_v1_20260525.md`: passed.
- Report bundle inventory commands: passed.
- GitHub issue and PR snapshot commands: passed.
- JSON validation, `git diff --check`, task-card check-diff, and registry release: passed.
