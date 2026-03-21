---
name: embedding-change-checklist
description: Verify RAG/embedding invariants before committing changes that touch the vector pipeline. Run automatically before any PR that touches embeddings.py, config.py (EMBED_MODEL), or alembic/versions/.
user-invocable: false
---

# Embedding Change Safety Checklist

Run this before committing any change that touches:
- `financial-engine_v2/backend/app/services/embeddings.py`
- `financial-engine_v2/backend/app/core/config.py` (specifically `EMBED_MODEL`)
- `financial-engine_v2/backend/app/alembic/versions/`
- Any file that sets `EMBED_MODEL`, `DISTANCE_METRIC`, or vector collection names

## Steps

### 1. Verify stored embedding model matches intent
```bash
cat financial-engine_v2/reports/runtime_embedding_model.txt 2>/dev/null || echo "No baseline file — first-time setup"
```
The stored model must match the `EMBED_MODEL` value in `.env` / `config.py`. If it differs and Qdrant has live vectors, startup will abort. This is intentional — do not suppress the check.

### 2. Confirm critical invariants are unchanged
- **Vector ID format**: must remain `document_id:chunk_index` — do not change without rebuilding the collection
- **Distance metric**: must remain `COSINE` — changing requires a full collection rebuild
- **Collection names**: `asx_docs`, `commentary_chunks`, `commentary_chunks_v2` — renaming breaks the retrieval stack

### 3. Run backend tests
```bash
financial-engine_v2/.venv/bin/pytest financial-engine_v2/backend/tests/ -x -q --tb=short
```
All tests must pass before proceeding.

### 4. Run RAG stability check
Invoke `/rag-stability` — must return **STABLE** or explain **MINOR DRIFT** with root cause.
If MAJOR DRIFT is reported, stop and surface to user.

### 5. Confirm startup check would pass (isolated profile)
```bash
LOCAL_BACKEND_PROFILE=isolated bash financial-engine_v2/scripts/run_local_backend.sh &
sleep 5
curl -sS http://127.0.0.1:8000/api/health
```
Health endpoint must return 200. Kill the process after verification.

## Output Format

Report result as one of:
- **SAFE TO MERGE** — all steps passed, invariants confirmed unchanged
- **NEEDS REVIEW** — minor drift or test gap; describe what was found
- **BLOCKED** — invariant violated or test failure; do not merge until resolved
