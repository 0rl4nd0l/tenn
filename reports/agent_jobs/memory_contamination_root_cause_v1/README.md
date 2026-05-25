# Memory Contamination Root Cause v1

Generated: 2026-05-25T15:22:26+10:00

## Scope

- GitHub issue: #36.
- Lane: Memory.
- Supporting lanes: Evaluation, Provenance, Query Orchestration.
- Execution mode: AUDIT ONLY.
- Target system layer: memory audit evidence reporting only.
- Contract boundary: no live memory mutation, cleanup, expiry, rewrite, quarantine, alias canonicalization, reindex, DB/Qdrant/news mutation, source-registry mutation, runtime change, service start, chat/context smoke, canonical financial truth change, parser/extraction change, or production data write.

## Preflight Declaration

- Agent: Codex.
- Branch: `audit/repo-hygiene-safe-audits-v1-20260525`.
- Worktree: `/home/l4nd0/tenn-repo-hygiene-audits-v1-20260525`.
- Pre-closeout HEAD: `c6280a56c5ed`.
- Pre-closeout git status: clean against origin before this task card/report was added.
- Recent commits checked: `c6280a56`, `de5545ff`, `439dba6c`, `a423421b`, `24bab3fc`.
- Worktree list checked; many historical/safe worktrees exist, and current shared registry reported no active jobs before claim.
- Intended files: `docs/agent_tasks/memory_contamination_root_cause_v1.md` and this issue-exact report directory only.
- Contested surfaces touched: none.
- Collision risk: LOW for report-only, HIGH for any memory/runtime mutation.
- Decision: proceed report-only.

## Executive Result

Issue #36 is safe to close as audit acceptance met. This closeout does not claim that memory cleanup, quarantine, or current live contamination remediation is complete.

The root-cause audit acceptance criteria are met by existing evidence:

- Historical root cause is confirmed: old memo-level ticker fanout wrote accepted statements once per memo-level ticker into `company_memory`.
- Reader/surfacing risk is confirmed: active contaminated rows can surface in ticker-specific contexts because readers trust the row's company scope.
- No cleanup was performed in the audit or this closeout.
- Root-cause evidence, inferred current risk, speculative claims, and `DATA_MISSING` are separated in the report family.
- The next safe task is explicit: approval-gated review/quarantine or cleanup after source/span review and backup/checksum proof.

Current May 24 evidence updates the live-risk picture without closing remediation: the read-only inventory reports 147 active company-memory rows, 0 active duplicate-statement clusters, and 4 active source-fanout suspicious clusters covering 17 selectable entries. The quarantine-design report recommends no delete/expire/migrate/hide action without operator approval.

## Evidence References

- Root-cause audit: `reports/agent_jobs/memory_contamination_root_cause_audit_v1_20260519/README.md`.
- Memory store inventory: `reports/agent_jobs/memory_contamination_root_cause_audit_v1_20260519/memory_store_inventory.json`.
- Surfacing risk matrix: `reports/agent_jobs/memory_contamination_root_cause_audit_v1_20260519/surfacing_risk_matrix.json`.
- Suspected fanout clusters: `reports/agent_jobs/memory_contamination_root_cause_audit_v1_20260519/suspected_fanout_clusters.json`.
- Writer path trace: `reports/agent_jobs/memory_contamination_root_cause_audit_v1_20260519/writer_path_trace.md`.
- Live read-only inventory: `reports/agent_jobs/memory_live_inventory_readonly_v1_20260524/README.md`.
- Live inventory JSON: `reports/agent_jobs/memory_live_inventory_readonly_v1_20260524/inventory.json`.
- Quarantine design: `reports/agent_jobs/memory_fanout_suppression_quarantine_design_v1_20260524/README.md`.
- Candidate quarantine seed: `reports/agent_jobs/memory_fanout_suppression_quarantine_design_v1_20260524/candidate_quarantine.json`.

## Issue Acceptance Matrix

No production data mutation: met. The original audit used `production_data_access=false`; this closeout did not open or mutate live memory stores.

No cleanup performed: met. No deletion, expiry, rewrite, quarantine, migration, alias canonicalization, Qdrant reindex, or news resync occurred.

Root-cause evidence separated from hypothesis: met. The dated audit explicitly separates Confirmed Facts, Inferred Facts, Speculative Claims, and `DATA_MISSING`.

Writer path / source batch / entity-scope trace: met for the audit boundary. The writer path and historical fanout mechanism are documented; live row source/span review remains follow-up.

Ticker-specific surfacing risk: met. The report documents that active contaminated rows can surface through company-memory readers and Query Orchestrator memory selection.

Likely root cause and blast radius: met. Historical fanout is class-wide across old commentary/news memo routing. Current active blast radius was later refined by read-only inventory to 4 suspicious source-fanout clusters covering 17 selectable entries.

Prevention plan and cleanup prerequisites: met. The report family preserves guard tests, future fixture needs, backup/export, row-ID manifest, operator review, and capped status-only handling as prerequisites.

Implementation risk rating / next step: met. Any mutation remains HIGH risk and approval-gated; report-only closeout is LOW risk.

## DATA_MISSING

- Operator decisions for preserve/suppress/expire on candidate source-fanout rows.
- Full source article/transcript text and source spans for every candidate row.
- Backup/checksum proof for any future mutation.
- Live route proof, intentionally skipped because memory read routes may emit operational artifacts.
- Current full production memo dispatch/candidate-ticker behavior beyond existing guard evidence.

## Boundary Statement

This closeout did not open live production memory stores, run memory cleanup, expire rows, delete rows, rewrite statements, quarantine rows, migrate schemas, canonicalize aliases, reindex Qdrant, resync news, mutate DB/Qdrant/news/memory/source registry, run live chat/context routes, or alter writer/reader/runtime code.

## Validation

- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/memory_contamination_root_cause_v1.md`: passed.
- `python3 scripts/agent_job_registry.py list-active`: passed; no active jobs.
- `python3 scripts/agent_job_registry.py check-overlap docs/agent_tasks/memory_contamination_root_cause_v1.md`: passed.
- `python3 scripts/agent_job_registry.py claim docs/agent_tasks/memory_contamination_root_cause_v1.md`: passed.
- `git worktree list --porcelain`: run for required preflight.
- `git log --oneline -5`: run for recent commit preflight.
- `python3 -m json.tool` on root-cause memory store inventory, surfacing risk matrix, suspected fanout clusters, live inventory, and candidate quarantine JSON: passed.
- `git diff --check`: passed.
- `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/memory_contamination_root_cause_v1.md`: passed.
- `python3 scripts/agent_job_registry.py release memory_contamination_root_cause_v1`: passed.
- `python3 scripts/agent_job_registry.py list-active` after release: passed; no active jobs reported.
