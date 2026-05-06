# Preflight

Required declaration:

```text
Lane: Reporting
Branch: preserve/dirty-work-20260430T065748Z
Worktree: /mnt/sdb2/home/l4nd0/tenn
Execution mode: SAFE EXTENSION MODE
Intended files:
- docs/agent_tasks/reporting_textual_sources_list_v1.md
- financial-engine_v2/cockpit/core/chat.py
- financial-engine_v2/cockpit/tests/test_slash_commands.py
- financial-engine_v2/cockpit/tests/test_chat_orchestrator_integration.py
- reports/textual_sources_list_envelope_consumption_20260506_172946/**
Contested surfaces touched: none from the contested list
Collision risk: MEDIUM
Decision: proceed after dirty-file non-overlap check; registry claim failure recorded
```

Contract review:

- Target system layer: Client presentation plus Analysis-orchestration evidence display.
- Relevant rules: `SYSTEM_CONTRACT.md` §1.2 Cockpit role, §1.3 retrieval boundary, §2 mandatory flow, §5 backend retrieval authority; `21_cockpit_client_contract.md` §1 and §5.
- Must not change: ingestion, extraction, storage, retrieval/ranking, Qdrant writes, memory writes, canonical financial truth, backend source drawer UI, or legacy `/api/chat`.
- Safety rationale: the change only carries an existing backend-neutral evidence envelope into Textual source display and renders its fields. It does not create evidence labels, retrieve data, rank data, mutate stores, or reinterpret financial truth.
- GPU process check: not required. This task does not spawn, restart, or depend on `llama-server`.

Architecture-check skill note:

- `architecture-check` skill was invoked for backend/retrieval-boundary review.
- DATA_MISSING: referenced `.cursor/rules/00_mandatory_index.md`, `backend_architecture.md`, `embedding_rules.md`, `vector_store_invariants.md`, and `failure_policy.md` were not present in `.cursor/rules/`; contract docs above were used as the authoritative fallback.

Command evidence:

```text
pwd
/home/l4nd0/tenn

git branch --show-current
preserve/dirty-work-20260430T065748Z

git rev-parse HEAD
998d103d26c16ac6e16c58df68d73a5c51787aa3

git merge-base --is-ancestor 998d103d26c1 HEAD && echo query_orchestrator_envelope_present
query_orchestrator_envelope_present
```

`git log --oneline -n 45` started with:

```text
998d103 fix(query): add evidence taxonomy envelope to orchestrator
35593a1 milestone(agent-hooks): add gemini task-card enforcement
902cc18 fix(query): surface no-hit and degraded runtime evidence states
db262f7 milestone(provenance): add f53b052 source-label baseline review
f53b052 fix(provenance): preserve source labels across reload and drawer
```

Required source report presence:

```text
reports/query_orchestrator_evidence_envelope_20260506_170507/README.md
reports/textual_sources_query_orchestrator_envelope_audit_20260506_164051/README.md
reports/source_label_semantics_20260506_144411/README.md
reports/source_label_propagation_drawer_honesty_20260506_154915/README.md
reports/tool_no_hit_runtime_semantics_20260506_162735/README.md
```

Task-card tooling:

```text
financial-engine_v2/.venv/bin/python scripts/agent_job_contract.py validate docs/agent_tasks/reporting_textual_sources_list_v1.md
ok: true

financial-engine_v2/.venv/bin/python scripts/agent_job_registry.py list-active
ok: true
active_jobs: []
registry_scope: shared
```

Claim result:

```text
financial-engine_v2/.venv/bin/python scripts/agent_job_registry.py claim docs/agent_tasks/reporting_textual_sources_list_v1.md
ok: false
reason: pre-existing dirty files outside current task card allowed_files
```

Dirty-file classification:

- Pre-existing or concurrently added unrelated Cockpit web/product files: `cockpit-ui/**`, `tenn_cockpit_home_design_export_20260506/**`, `tenn_prompt_contracts_response_guidelines.zip`, unrelated task cards.
- Task files created/edited by Codex: `docs/agent_tasks/reporting_textual_sources_list_v1.md`, `financial-engine_v2/cockpit/core/chat.py`, `financial-engine_v2/cockpit/tests/test_slash_commands.py`, `financial-engine_v2/cockpit/tests/test_chat_orchestrator_integration.py`, this report directory.
- Overlap verdict: no dirty file overlapped `query_orchestrator.py`, `tenn_chat.py`, `cockpit_api.py`, Textual `chat.py` before this task, `agent_loop.py`, `tool_executor.py`, `response_classification.py`, or the tests changed here.
