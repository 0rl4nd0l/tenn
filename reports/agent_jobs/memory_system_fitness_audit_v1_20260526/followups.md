# Ranked Follow-Up Roadmap

No new GitHub issues were created by this audit because the task card authorized report artifacts only. Each entry below is issue-ready and explicitly marked `DEFER` or `DATA_MISSING` per #88 definition of done.

## Duplicate Check Summary

Open memory-adjacent issues found: #100, #101, #102, #103, #104, #118. These are YouTube intake, source metadata, memory-candidate queue, cross-route evidence-envelope, or thesis-audit workflow tasks. They do not fully cover the whole-system memory fitness gaps below.

## F1 - Runtime Memory Root Ownership Probe

Status: DATA_MISSING
Suggested title: `[Memory] Add read-only runtime memory-root ownership probe`
Lane: Memory
Priority: P1
Risk: high
Mode: audit

Finding: This audit did not safely verify the live runtime memory root or active DB ownership. `source_registry.py` can select a root from `TENN_RESEARCH_MEMORY_ROOT`, configured data root, project data root, or legacy backend path; store constructors can create paths/schemas, so this audit avoided live imports.

Validation path: add a read-only probe that reports configured/env/root candidates without opening or creating memory stores, then compare the result with `22_memory_ownership_map.md`.

Hard stops: no memory-store writes, no schema creation, no cleanup, no reindex, no production data mutation.

## F2 - Fixture-Based Memory Fitness Harness

Status: DEFER
Suggested title: `[Evaluation] Add fixture-based memory fitness harness`
Lane: Evaluation
Priority: P1
Risk: high
Mode: safe-extension

Finding: Current tests cover important individual stores, and `audit_memory_integrity.py` covers linked-ticker/fanout classes, but no single non-mutating harness proves source-plan selection, read filtering, thesis gating, preference separation, event traces, session degradation, and BFF route contracts together.

Validation path: use temporary SQLite/JSON fixtures only; assert company/market financial metric rejection, active-score/status filtering, thesis proposal lifecycle, event schema, preference separation, and no-live-store access.

Hard stops: no production memory DBs, no Qdrant/Postgres, no runtime config changes.

## F3 - Memory Event Log Health Gate

Status: DEFER
Suggested title: `[Provenance] Add memory read/write event log schema and health gate`
Lane: Provenance
Priority: P1
Risk: medium
Mode: safe-extension

Finding: Read/write memory event logs exist but are best-effort and fail-open. That is appropriate for answer availability, but there is no visible health gate proving event schema, writeability, rotation/retention, or operator visibility.

Validation path: add fixture tests for read/write event payload schema and a read-only operator health check that reports missing/unwritable logs without blocking answers.

Hard stops: do not make observability failure block primary answer paths without explicit design approval.

## F4 - Preference Memory Ownership and Governance

Status: DEFER
Suggested title: `[Memory] Document and validate preference-memory ownership`
Lane: Memory
Priority: P1
Risk: medium
Mode: audit

Finding: `user_preferences`, route-alias preferences, and learned `chat_preferences.json` are separated from company/market/user-thesis memory in code, but learned chat preferences are not fully captured in the memory ownership map or product governance model.

Validation path: inventory all preference writers/readers; classify which are operator settings, route aliases, learned tuning, or user thesis; add tests or docs for confirmation requirements and reset/visibility controls.

Hard stops: do not store route/user intent aliases in user thesis memory; do not let learned preferences create financial truth or unsupported source labels.

## F5 - Live Memory UI/BFF Contract Smoke

Status: DEFER
Suggested title: `[Reporting] Add read-only Memory Workbench BFF contract smoke`
Lane: Reporting
Priority: P2
Risk: medium
Mode: safe-extension

Finding: Web Memory tab and BFF routes exist and mocked tests exercise key flows, but this audit did not prove live no-store route parity between the Next.js BFF and backend memory APIs.

Validation path: add a smoke that uses mocked backend or fixture backend responses to prove request/response shapes for memory index, scoped ticker context, thesis proposals, add, and expire routes without touching live stores.

Hard stops: no direct browser writes to backend memory stores; mutation routes must remain explicit and confirmation-gated where applicable.

## F6 - Session, Archive, and Entity-Observation Controls

Status: DEFER
Suggested title: `[Memory] Audit session-memory cleanup and entity-observation circularity controls`
Lane: Memory
Priority: P2
Risk: medium
Mode: audit

Finding: Docs already identify no automatic session-summary generation, no automatic MemoryStore archive deletion, no alert cleanup, and entity-observation circularity risk. These are controlled enough for current operation but not fully validated as product behavior.

Validation path: audit session summary triggers, compaction, archive retention, alert cleanup expectations, and entity-observation source labeling; decide whether to add operator controls or tests.

Hard stops: no deletion or cleanup of user/workspace memory without explicit approval.

## F7 - Source-Plan Parity Across Agent and Keyword Paths

Status: DEFER
Suggested title: `[Query Orchestration] Audit memory source-plan parity across agent and keyword paths`
Lane: Query Orchestration
Priority: P2
Risk: medium
Mode: audit

Finding: Docs show different memory/context sources reaching LLMs in agent and keyword paths. That may be intentional, but product behavior should specify which memory classes should be available in each path.

Validation path: build a route/source-plan matrix with fixture context; assert visible source labels and answer-input behavior for company, market, thesis, session, dossier, and entity-observation sources.

Hard stops: do not add hidden fallback retrieval or source-backed labels without current evidence.
