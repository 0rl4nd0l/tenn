# Preflight

Required commands:

```text
pwd
```

Result: `/home/l4nd0/tenn` (same checkout as `/mnt/sdb2/home/l4nd0/tenn`).

```text
git branch --show-current
```

Result: `preserve/dirty-work-20260430T065748Z`

```text
git rev-parse HEAD
```

Initial observed HEAD during preflight: `3e7187e4aad8343ad722d1f9313cfbe573e185f6`

Current HEAD after live-branch drift: `8d3d58811cf16100a6540cf4f5eae727497b18d4`

```text
git status --short
```

Current unrelated dirty item before implementation: `?? tenn_prompt_contracts_response_guidelines.zip`

No dirty overlap existed on the files changed by this task.

```text
git log --oneline -n 20
```

Top entries observed after drift:

```text
8d3d588 milestone(reporting): add ebay sync bff route parity
3e7187e milestone(news): align nightly memo diagnostics path
dd05503 milestone(marketplace): checkpoint requirement-driven match payloads
93e91cc milestone(agent-jobs): activate dev-agent task-card hooks
518c363 ops(memory): remove tracked cleanup backup artifact
```

Contract notes:

- Target layer: Query Orchestration / retrieval selection.
- Relevant invariants: no financial truth changes, no memory mutation, no Qdrant mutation, no ingestion/reindexing, no source-label changes.
- Contested surfaces touched: `financial-engine_v2/cockpit/core/agent_loop.py`.
- Collision risk: MEDIUM per task card; no dirty overlap on touched files.
- DATA_MISSING: the local `architecture-check` skill referenced missing `.cursor/rules/*` files in this checkout, so the implementation used `SYSTEM_CONTRACT.md` and architecture docs as fallback evidence.
