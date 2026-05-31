# Memory System Fitness Audit v1

Issue: #88
Job: `memory_system_fitness_audit_v1_20260526`
Date: 2026-05-31
Agent: Codex

## Preflight

Lane: Memory
Branch: `safe/memory-system-fitness-audit-v1-20260531`
Worktree: `/home/l4nd0/tenn-memory-system-fitness-audit-v1-20260531`
Execution mode: AUDIT MODE
Intended files: task card plus report artifacts under `reports/agent_jobs/memory_system_fitness_audit_v1_20260526/`
Contested surfaces touched: none
Collision risk: LOW
Decision: proceed with audit-only report artifacts

Target system layer: audit/evaluation of Memory-related Analysis and Client surfaces.
Relevant contract rules: backend authority, Cockpit client/orchestration role, no duplicate retrieval or truth store, qualitative memory must not override canonical financial truth.
What must not change: memory stores, production DB, Qdrant, news data, canonical financial truth, parser routing, prompts, gold labels, embeddings/vector collections, runtime/model/GPU/service config.
Why safe: this run writes only the task card and report artifacts; all product/runtime/data-store surfaces were inspected read-only.

## Verdict

Recommendation: KEEP AND EXTEND.

The current memory architecture is broadly the right shape: it separates canonical financial truth from qualitative company memory, market memory, user thesis memory, session memory, operational state, retrieval indexes, and workspace artifacts. The strongest evidence is the ownership map, deterministic memory assembler, write-side financial-metric rejection in company/market memory, and confirmation-gated user thesis flow.

The system is not proven ideal. The gaps are mostly validation, observability, root ownership, UI route parity, preference inventory, and stale/session controls. These should be extended in bounded follow-up work rather than addressed by a broad redesign.

Closeout decision for #88: COMPLETED_AUDIT_ONLY_WITH_DEFERRED_FOLLOWUPS. The audit objective is complete, no product remediation is claimed, and actionable follow-ups are ranked in `followups.md` as issue-ready `DEFER` or `DATA_MISSING` entries per the issue definition of done.

Resolution review hook: PASS_WITH_FOLLOWUPS. This is audit-only, not root-cause remediation. Closure is safe only because #88 explicitly allows proposed implementation follow-ups to be linked or marked `NO_FOLLOWUP`, `DEFER`, or `DATA_MISSING`; this report uses those statuses and does not claim product behavior changed.

## Confirmed

- Active memory classes are documented with separate authority classes: financial truth, company memory, market memory, user thesis memory, OpenViking session store, cockpit state, feedback, marketplace operational state, workspace artifacts, and Qdrant retrieval indexes (`docs/architecture/22_memory_ownership_map.md:5`).
- The intended write boundary is explicit: financial truth is not writable from LLM prose or qualitative memory APIs; company/market memory reject financial metric signal types; user thesis writes are proposal -> confirm -> apply (`docs/architecture/22_memory_ownership_map.md:18`).
- Backend-owned qualitative memory remains authoritative and Cockpit management surfaces are clients over backend APIs, not direct store editors (`docs/architecture/18_cockpit_memory.md:24`, `docs/architecture/18_cockpit_memory.md:178`).
- Memory reads use a deterministic `MemoryAssembler` with explicit providers for financial truth, company memory, market memory, and user thesis memory (`financial-engine_v2/backend/app/services/memory_assembler.py:28`).
- Company and market memory stores reject financial metric signal types before writing (`financial-engine_v2/backend/app/services/company_memory.py:22`, `financial-engine_v2/backend/app/services/company_memory.py:469`, `financial-engine_v2/backend/app/services/market_memory.py:23`, `financial-engine_v2/backend/app/services/market_memory.py:539`).
- User thesis memory creates pending proposals and refuses to apply until the proposal is confirmed (`financial-engine_v2/backend/app/services/user_thesis_memory.py:125`, `financial-engine_v2/backend/app/services/user_thesis_memory.py:214`, `financial-engine_v2/backend/app/services/user_thesis_memory.py:259`).
- Existing integrity audit coverage is real but narrow: it checks market linked-ticker integrity, fallback SQLite presence, and company duplicate/fanout/invalid ID classes (`scripts/audit_memory_integrity.py:38`, `scripts/audit_memory_integrity.py:112`, `scripts/audit_memory_integrity.py:154`).
- Memory read/write event logging exists but is intentionally best-effort and fail-open (`financial-engine_v2/backend/app/services/memory_events.py:36`).

## Inferred

- The architecture should not be collapsed into one generic memory store. The current split maps to different authority, retention, write-gate, and UI needs.
- The largest near-term quality gain is a fixture-based memory fitness harness that proves assembler source plans, filtering, thesis gating, preference separation, event traces, and BFF/UI route parity without touching live memory stores.
- Product work should keep memory mutations explicit and confirmation-gated where user-owned preferences or thesis state can affect future answers.

## Speculative

- A lightweight operator health view for memory read/write traces may reduce debugging time, but the exact UI placement should be decided with the Reporting lane.
- Preference memory could become a distinct documented surface if learned chat preferences become user-visible or answer-affecting beyond routing/retrieval tuning.

## DATA_MISSING

- Live runtime memory root and active DB ownership were not verified. This audit intentionally avoided importing runtime services or opening live memory stores because constructors can create directories/schemas and the task forbids memory-store mutation.
- End-to-end live Cockpit route parity was not proven. Existing frontend evidence is primarily mocked-route test coverage and static BFF inspection.
- The intended final product behavior for learned chat preferences is not fully specified in the memory architecture docs.

## Closeout Boundary

No forbidden surfaces changed. No production memory stores were read or written. No cleanup, expiration, migration, reindex, dedupe, schema migration, runtime probe with write side effects, model/GPU/service change, or product code change was performed.

## Artifact Index

- `memory_surface_inventory.md`: memory class inventory and authority classification.
- `read_write_path_map.md`: current read/write path map.
- `fit_gap_matrix.md`: intended-system fit/gap assessment.
- `followups.md`: ranked issue-ready follow-up roadmap.
- `validation.json`: commands and evidence checks.
- `status.json`: closeout status summary.
- `diff-check.json`: task-card diff gate result.
- `code_review.json`: code-reviewer pass over report-only diff.
