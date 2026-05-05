# Next Cleanup Prompt

Use this only after an operator explicitly approves a cleanup lane. Do not run it as part of the fanout guard work.

```text
You are Codex working on Tenn.

TASK
Design a historical company-memory cleanup plan for contamination caused by pre-guard memo ticker fanout.

LANE
Memory

EXECUTION MODE
AUDIT MODE only unless explicitly promoted by the user.

READ FIRST
- docs/architecture/SYSTEM_CONTRACT.md
- reports/memory_contamination_root_cause_20260505_161634/*
- reports/memory_signal_router_fanout_guard_20260505_164348/*
- financial-engine_v2/backend/app/services/company_memory.py
- financial-engine_v2/backend/app/services/market_memory.py
- financial-engine_v2/backend/app/services/memory_signal_router.py

DO NOT
- mutate live memory rows
- expire rows
- rewrite rows
- normalize aliases in live storage
- migrate DBs
- reindex Qdrant
- run ingestion or reprocessing

OUTPUT
Produce an evidence-based cleanup design that lists candidate contaminated clusters, exact review gates, rollback requirements, and the minimal safe mutation plan. Stop before any write.
```

