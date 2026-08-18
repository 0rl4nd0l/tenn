# Memory Fanout Suppression / Quarantine Design

Generated: 2026-05-24T13:19:55Z

## Verdict

`DESIGN_COMPLETE_NO_LIVE_MUTATION`.

The current read path can select active source-fanout suspicious company-memory rows, but source-fanout alone is not deterministic enough for automatic deletion or production read-path hiding. The smallest safe next step is an approval-gated quarantine manifest plus a future read-path suppression/downgrade guard that is exact-entry scoped, reportable, and reversible.

## Current Evidence Used

- `reports/agent_jobs/memory_live_inventory_readonly_v1_20260524/inventory.json`
- `reports/agent_jobs/memory_live_inventory_readonly_v1_20260524/README.md`
- `reports/agent_jobs/memory_contamination_root_cause_audit_v1_20260519/surfacing_risk_matrix.json`
- `reports/agent_jobs/memory_remaining_review_packet_v1_20260520/review_summary.json`
- `reports/agent_jobs/memory_remaining_review_packet_v1_20260520/operator_review_rows.csv`
- Current code inspection of:
  - `financial-engine_v2/backend/app/services/company_memory.py`
  - `financial-engine_v2/backend/app/services/memory_assembler.py`
  - `financial-engine_v2/backend/app/services/query_orchestrator.py`
  - `financial-engine_v2/backend/app/services/memory_signal_router.py`
  - `scripts/audit_memory_integrity.py`

No memory DB, route, Qdrant, news SQLite, Postgres, migration, cleanup, expiry, reindex, or chat smoke was run by this child task.

## Confirmed Read / Selection Path

1. `CompanyMemoryStore.retrieve()` reads `entities["primary_ticker"]`, then calls `list_entries(company_id, status="active")`.
2. `_rank_active_entries()` annotates active rows with `active_score` and keeps rows above the promotion threshold.
3. `MemoryAssembler._filter_payload()` keeps `company_memory` items with `status=active` and `active_score >= 0.55`.
4. `QueryOrchestrator._select_memory_items()` again filters `active_score >= 0.55` before adding selected memory statements into answer context.
5. Evidence labeling keeps memory as `memory_context` / `context_only`; it is not canonical financial truth or claim verification.

The live inventory artifact reports 17 suspicious active entries selectable in offline dry-run scoring.

## Candidate Strategies

| Strategy | Recommendation | Reason |
|---|---|---|
| Quarantine table/list artifact | `YES_NEXT` | Exact entry/source scoped, reviewable, reversible, and does not mutate stores. |
| Read-path filter | `YES_AFTER_APPROVAL` | Safest production behavior is to suppress exact approved entry IDs before assembly, with explicit selected/filtered counts. |
| Source-fanout score penalty | `NOT_FIRST` | Penalty can still surface contaminated rows and is harder to explain than exact suppression. |
| Migration cleanup | `NO_FOR_THIS_GOAL` | Store mutation requires backup, checksum, operator review, and a separate approved mutation task. |
| Evidence-role reclassification | `PARTIAL` | Already context-only; reclassification alone does not stop surfacing as ticker/company context. |
| Alias/entity write-path prevention | `KEEP_EXISTING_GUARD` | Current `_company_targets_for_statement()` guard prevents ambiguous multi-ticker fanout on new writes; alias work is separate risk. |
| Combination | `BEST` | Review manifest now, exact read-path suppression later, cleanup only after explicit approval. |

## Deterministic Detection Limits

Deterministic enough for report-local candidate selection:

- Active row status.
- Same `(source, source_id)` attached to more than the configured company threshold.
- Existing source-fanout audit logic in `scripts/audit_memory_integrity.py`.
- Exact entry IDs from the immutable read-only inventory.

Not deterministic enough for automatic production suppression or deletion:

- A multi-company article can legitimately contain distinct company-specific statements.
- The current row schema lacks source spans, writer job IDs, batch IDs, and durable target-attribution reasons.
- Source-fanout clusters require source/article review to determine whether every row is contamination.
- Some known historical rows in the review packet appear likely legitimate under their scoped company.

## Proposed Future Read-Path Guard

Future task card, after operator approval:

1. Add a static quarantine manifest artifact with exact `entry_id`, `company_id`, `source`, `source_id`, `reason`, `review_status`, and `approved_by`.
2. Load the manifest in a non-store helper, not from the live SQLite DB.
3. Apply the helper at the company-memory read boundary after `list_entries(..., status="active")` and before ranking/assembly.
4. Suppress only exact approved entry IDs, or downgrade them to an explicit `memory_context_quarantined`/`DATA_MISSING` diagnostic if display is required.
5. Include `quarantined_count`, `quarantine_manifest_id`, and `filtered_entry_ids` in memory read telemetry/report metadata.
6. Add synthetic tests proving:
   - approved suspicious rows are not selected;
   - non-quarantined rows from the same source are preserved;
   - memory context remains `context_only`, never `claim_verified`;
   - no store mutation occurs.

## User Review Requirements Before Suppression

For each candidate cluster or row:

- Full source article/transcript text or source URL.
- Row statement and scoped company ID.
- Evidence that the statement belongs to the scoped company, not merely the article-level ticker list.
- Active score and reason the row is selectable.
- Operator decision: preserve, suppress from read path, or later expire by explicit mutation task.
- Backup/checksum proof before any status change task.

## Next Safe Implementation Prompt

Create `memory_fanout_read_path_quarantine_guard_v1_<date>` with:

- Primary lane: Memory.
- Mode: SAFE EXTENSION with synthetic fixtures only unless operator-approved manifest is supplied.
- Allowed files: a new non-live quarantine helper, focused tests, report-local approved manifest sample, task/report files.
- Forbidden: live memory update/delete/rewrite, migration, alias canonicalisation, Qdrant/news/Postgres writes, chat smoke that writes memory events.
- Required tests: synthetic `CompanyMemoryStore.retrieve`/`MemoryAssembler` suppression, selected/filtered count telemetry, and no claim-verified memory labels.
