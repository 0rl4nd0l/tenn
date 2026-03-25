# SYSTEM CONTRACT — Architectural Invariants

> This document codifies the architectural invariants that all agents and contributors
> must enforce. Violations require stopping and flagging, never silent continuation.
>
> Established: 2026-03-25
> Authority: Full-system audit (cross-validated by 4 independent subagents)

---

## 1. Vector ID Determinism (CRITICAL)

**All Qdrant point IDs MUST be deterministic.**

- ASX documents: `"{document_id}:{chunk_index}"` (pipeline.py)
- Commentary: `uuid5(NAMESPACE_URL, "commentary_chunks:{chunk_id}")` (commentary_ingest.py)
- News chunks: writer is `sync_news_qdrant` task (worker_app/news_tasks.py)

**Prohibited:** `uuid.uuid4()` for vector point IDs. Non-deterministic IDs break
idempotent re-processing, corrupt the index on re-ingestion, and defeat `git bisect`
for vector regressions.

**Enforcement:** The legacy worker (`worker/app/tasks.py`) used `uuid4()` and has been
deprecated. No active code path uses non-deterministic vector IDs.

---

## 2. Single Worker Authority

**The backend Celery app (`backend/app/celery_app.py`) is the sole authority for
document processing tasks.**

Registered task modules: `app.worker_tasks`, `app.tasks.commentary_tasks`

The `worker/worker_app/celery_app.py` exists **only** for Beat scheduling of news
pipeline tasks. It does NOT register or execute document processing tasks.

**Task name collisions are prohibited.** No two modules may register the same Celery
task name. The deprecated worker's `backfill_ticker`, `download_pdf`, and
`process_document` tasks have been prefixed with `deprecated_` to eliminate collisions.

---

## 3. RAG Endpoint Authority

| Endpoint | Collection | Purpose | Authority |
|----------|-----------|---------|-----------|
| `POST /rag/query` (main.py) | `asx_docs` | ASX document search | CANONICAL |
| `GET /api/rag/query` (routes.py) | `news_chunks` | News search | ACTIVE (cockpit consumer) |
| `POST /chat` (routes/chat.py) | `commentary_chunks` | Conversational RAG | CANONICAL |

**Dead endpoints must be removed, not left as reachable code.**
The unmounted `routes/rag.py` has been deleted as it duplicated `POST /rag/query`.

---

## 4. Embedding Model Consistency

- Embedding model changes require a full collection rebuild.
- Startup enforces consistency via `reports/runtime_embedding_model.txt`.
- Distance metric is `COSINE` — changing requires collection rebuild.
- Vector ID format is `document_id:chunk_index` — changing requires collection rebuild.

---

## 5. Backend Is Source of Truth

- The FastAPI backend is the authoritative system for retrieval, extraction, and data persistence.
- Cockpit is a client; it does not write to Qdrant or Postgres directly.
- All vector writes flow through backend services (`pipeline.py`, `commentary_ingest.py`)
  or the news sync task (`worker_app/news_tasks.py`).

---

## 6. No Silent Degradation

- Error handling and fallbacks are secondary to fixing root causes.
- A function that returns `None` or `{}` where it previously raised must be investigated.
- Tests that pass by simplifying assertions rather than restoring behavior are not fixes.
- See `CLAUDE.md` bug-resolution rules and `~/.claude/rules/bug-resolution.md`.

---

## Enforcement

This contract is enforced by:
1. Code review (pre-merge checklist in CLAUDE.md)
2. Startup validation (embedding model guard, Qdrant dimension check)
3. Architecture docs cross-reference (this file + docs/architecture/*.md)
4. Agent operating instructions (CLAUDE.md behavioral rules)

**Any proposed change that would violate this contract must be flagged before implementation.**
