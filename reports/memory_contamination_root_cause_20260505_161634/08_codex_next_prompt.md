# Codex Next Prompt

You are Codex working on Tenn.

LANE: Memory

EXECUTION MODE: SAFE EXTENSION MODE only. Do not clean live memory.

MISSION: Fix the confirmed company-memory fanout bug in `financial-engine_v2/backend/app/services/memory_signal_router.py` without changing retrieval ranking, answer synthesis, production routing, Qdrant, migrations, or live memory rows.

READ FIRST:

- docs/architecture/SYSTEM_CONTRACT.md
- CLAUDE.md
- /home/l4nd0/.claude/projects/-mnt-sdb2-home-l4nd0-tenn/memory/MEMORY.md
- graphify-out/wiki/index.md
- reports/memory_contamination_root_cause_20260505_161634/00_summary.md
- reports/memory_contamination_root_cause_20260505_161634/01_write_path_trace.md
- reports/memory_contamination_root_cause_20260505_161634/02_fanout_root_cause.md
- financial-engine_v2/backend/app/services/memory_signal_router.py
- financial-engine_v2/backend/tests/test_memory_signal_router.py

CONSTRAINTS:

- Do not delete, expire, rewrite, or normalize live memory rows.
- Do not run ingestion, reprocess news/transcripts, upsert Qdrant, or migrate DBs.
- Do not change `CompanyMemoryStore.retrieve()`, memory ranking, or answer synthesis for this fix.
- Keep the fix in the router boundary unless tests prove a minimal extractor contract adjustment is required.

TARGET BEHAVIOR:

- A statement is written to company memory only for a company it specifically targets.
- A memo-level list of mentioned tickers must not be treated as targets for every statement.
- Macro/sector/market recap content goes to market memory only.
- Transcript summaries are not fanned out as company-specific truth.
- Source/source_id/published_at metadata remains attached.

STARTING TEST:

- Convert `test_multi_topic_commentary_does_not_fanout_primary_company_signal` from xfail to passing as part of the fix.

VALIDATION:

```bash
financial-engine_v2/.venv/bin/python -m pytest financial-engine_v2/backend/tests/test_memory_signal_router.py financial-engine_v2/backend/tests/test_memo_extractors_signal_routing.py -q
```

FINAL REPORT MUST INCLUDE:

- exact functions changed
- tests run
- confirmation that no live memory rows were changed
- cleanup still blocked pending separate approval

