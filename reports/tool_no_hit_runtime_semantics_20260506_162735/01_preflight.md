# Preflight

Required declaration:

```text
Lane: Query Orchestration
Branch: preserve/dirty-work-20260430T065748Z
Worktree: /mnt/sdb2/home/l4nd0/tenn
Execution mode: SAFE EXTENSION MODE
Intended files: cockpit_api.py; tool_executor.py; agent_loop.py; chat.py; focused backend/cockpit tests; report folder
Contested surfaces touched: financial-engine_v2/backend/app/routes/cockpit_api.py; financial-engine_v2/cockpit/core/agent_loop.py
Collision risk: MEDIUM
Decision: proceed
```

Commands recorded:

- `pwd` -> `/home/l4nd0/tenn` (same worktree, resolved path)
- `git branch --show-current` -> `preserve/dirty-work-20260430T065748Z`
- `git rev-parse HEAD` -> `f53b0526a6a483c350f8ee74434b95ed3f0dc06a`
- `git status --short` at preflight -> `?? tenn_prompt_contracts_response_guidelines.zip`
- `financial-engine_v2/.venv/bin/python scripts/agent_job_registry.py list-active` -> `active_jobs: []`

Live branch drift:

- Before commit, HEAD moved to
  `db262f7489b3fa3b08b8410f56c8f6d9fd27e3da`
  (`milestone(provenance): add f53b052 source-label baseline review`).
- Active jobs remained empty.
- Required commits remained reachable.
- Drift did not overlap the files changed for this task.

Required commits:

- `3c147f74b1c6` reachable: yes
- `f53b0526a6a4` reachable: yes
- `b9ace36e5e02` reachable: yes

Required report folder:

- `reports/source_label_propagation_drawer_honesty_20260506_154915/` present: yes

Contract check:

- Target layer: Cockpit query orchestration and provenance/source metadata.
- Relevant contract rules: backend remains authoritative; Cockpit client/runtime
  is orchestration only; no hidden degradation; no parallel provenance system;
  no storage, vector, ingestion, extraction, or memory mutation.
- Must not change: ingestion, extraction, Qdrant, `news.sqlite`, memory stores,
  financial truth extraction, retrieval ranking, source-label taxonomy, raw
  thinking exposure.
- Safety: additive metadata using existing labels only.

DATA_MISSING:

- `.cursor/rules/00_mandatory_index.md`
- `.cursor/rules/backend_architecture.md`
- `.cursor/rules/embedding_rules.md`
- `.cursor/rules/vector_store_invariants.md`
- `.cursor/rules/failure_policy.md`

The branch contains `.cursor/rules/graphify.mdc`; absent rule files were treated
as missing evidence and `SYSTEM_CONTRACT.md` plus the Cockpit client contract
were used as the enforceable architecture surface.
