# DATA_MISSING

- Current production `company_memory.sqlite` was not opened because `production_data_access=false`.
- The isolated checkout does not contain `financial-engine_v2/data/reports/research_memory/company_memory.sqlite`, `market_memory.sqlite`, `user_thesis_memory.sqlite`, `news_memos.jsonl`, or `source_registry.jsonl`.
- The raw stocktake folder `reports/full_system_stocktake_20260505_152038` is not present in this checkout; only derived root-cause/cleanup reports cite it.
- Current active contaminated-row count in the live DB is DATA_MISSING. The latest accessible artifact says a May 16 read-only audit had zero active duplicate statement clusters and zero active source-fanout clusters, but that was not refreshed against production in this task.
- Current ticker-specific chat surfacing from live data was not tested because live chat/API calls can write session, read-event, or flag artifacts.
- Current `/api/context/company_dump` live response was not sampled because it would require runtime/live backend access and potentially production memory reads.
- Exact originating job ID or batch ID for every contaminated row is not available in the company-memory schema; reports show `source`, `source_id`, timestamps, and metadata, but not a durable writer job ID.
- Evidence spans/source quotes are incomplete in historical company-memory rows according to the prior root-cause reports.
- A complete proof that all production news memo dispatches now pass safe `candidate_tickers` is DATA_MISSING without inspecting live loader artifacts or running a non-mutating replay harness.

## Approval-Gated Query Needed Later

If approved separately, the smallest read-only live DB query would be against:

- `/mnt/hdd-data/home/l4nd0/tenn/financial-engine_v2/data/reports/research_memory/company_memory.sqlite`
- table: `memory_entries`
- fields: `entry_id, company_id, type, statement, normalized_statement, status, source, source_id, first_seen_at, last_seen_at, metadata_json`

Purpose:

- Count active duplicate `normalized_statement + source_id` clusters crossing multiple `company_id` scopes.
- Count active broad `source + source_id` fanout clusters.
- Verify whether known historical manual-review rows remain active.
- Sample only row IDs and short statements needed for operator review, not broad personal data dumps.
