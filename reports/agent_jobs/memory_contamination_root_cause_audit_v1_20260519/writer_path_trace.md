# Writer Path Trace

## Company Memory Store

- Module: `financial-engine_v2/backend/app/services/company_memory.py`
- Store path: `DEFAULT_COMPANY_MEMORY_PATH = RESEARCH_MEMORY_ROOT / "company_memory.sqlite"`.
- Schema: `company_memory`, `memory_entries`, and `change_log`.
- Primary writer: `CompanyMemoryStore.update_company_memory(company_id, signal)`.
- Scope key: `company_id` from the caller, normalized uppercase.
- Statement identity: `type + normalized_statement`, deduped only inside the same `company_id` and only for active rows.
- Provenance: `source`, `source_id`, timestamps, and `metadata_json`; report artifacts show source title/evidence spans were historically incomplete.
- Fanout risk: the store itself does not fan out, but it also does not reject the same `source_id + statement` appearing under many company IDs.

## Memo Signal Router

- Module: `financial-engine_v2/backend/app/services/memory_signal_router.py`.
- Inputs: memo-level `tickers`, per-family statement lists (`claims`, `catalysts`, `risks`, `key_events`), source/source_id, published metadata.
- Current guard: `_company_targets_for_statement()` only returns:
  - one explicit statement-level target ticker if exactly one valid target is present;
  - the single memo ticker if the memo has exactly one ticker;
  - exactly one ticker if the statement text explicitly mentions exactly one ticker from a multi-ticker memo;
  - otherwise no company target.
- Historical root cause: old `_signals_for_statement()` looped every accepted statement over every memo-level ticker. That is confirmed by `reports/memory_contamination_root_cause_20260505_161634`.
- Current test status: `financial-engine_v2/backend/tests/test_memory_signal_router.py` contains passing tests for multi-topic no-fanout, ambiguous multi-ticker no-write, and statement-level target-ticker routing.

## Commentary Memos

- Module: `financial-engine_v2/backend/app/services/commentary_memo_extractor.py`.
- Writer path: `extract_and_store(..., route_signals=True)` stores a memo and calls `signals_from_commentary_memo(stored)` then `route_signals(...)` by default.
- Input object: LLM-produced memo with `claims`, `catalysts`, `risks`, `sentiment`, `time_horizon`, `tickers`, `source_id`, `source_type`, and `published_at`.
- Root-cause contribution: historical commentary memos carried one memo-level `tickers` list; without statement-level targets, the old router treated every listed ticker as a target for every statement.

## News Memos

- Module: `financial-engine_v2/backend/app/services/news_memo_extractor.py`.
- Writer path: `extract_and_store(..., route_signals=True)` stores a memo and calls `signals_from_news_memo(stored)` then `route_signals(...)` by default.
- Input object: LLM-produced memo with `key_events`, `claims`, `risks`, `tickers`, `provider`, `source_id`, and `published_at`.
- Current guard: prompt restricts tickers to `CANDIDATE_TICKERS`; normalizer drops tickers outside the allowlist; router guard still controls statement-to-company targeting.
- Remaining gap: code inspection did not prove that every production dispatch supplies high-quality `candidate_tickers`; this is DATA_MISSING without tracing the live loader path and memo diagnostics.

## Manual API Writers

- Routes: `/api/context/memory/company/add`, `/api/context/memory/company/expire`, `/api/context/memory/market/add`, `/api/context/memory/market/expire`.
- Manual company add writes one explicit ticker scope via `add_manual_company_memory_entry`.
- Manual expiry is status-only through `expire_company_memory_entry`; it mutates `status`, `closed_at`, `last_seen_at`, and writes change-log/audit events.
- Fanout risk: low for manual company add because request has one `ticker`; cleanup risk high if used without row-id manifest, backup, approval, and max-row-count gate.
