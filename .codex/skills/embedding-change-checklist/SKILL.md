---
name: embedding-change-checklist
description: Verify RAG and embedding invariants before merging changes to embeddings.py, EMBED_MODEL config, Alembic versions, or vector collection settings.
---

# Embedding Change Checklist

Use this skill before merge when vector or embedding surfaces changed.

## Trigger Surfaces

- `financial-engine_v2/backend/app/services/embeddings.py`
- `financial-engine_v2/backend/app/core/config.py`
- `financial-engine_v2/backend/app/alembic/versions/`
- Any file changing `EMBED_MODEL`, `DISTANCE_METRIC`, or collection names

## Checklist

1. Verify stored embedding model baseline:

```bash
cat financial-engine_v2/reports/runtime_embedding_model.txt 2>/dev/null || echo "No baseline file"
```

2. Confirm invariants remain unchanged:
   - vector ID format `document_id:chunk_index`
   - distance metric `COSINE`
   - collection names `asx_docs`, `commentary_chunks`, `commentary_chunks_v2`
3. Run backend tests:

```bash
financial-engine_v2/.venv/bin/pytest financial-engine_v2/backend/tests/ -x -q --tb=short
```

4. Run `rag-stability-eval`.
5. Confirm isolated startup health:

```bash
LOCAL_BACKEND_PROFILE=isolated bash financial-engine_v2/scripts/run_local_backend.sh &
sleep 5
curl -sS http://127.0.0.1:8000/api/health
```

## Result Labels

- `SAFE TO MERGE`
- `NEEDS REVIEW`
- `BLOCKED`
