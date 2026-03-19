# Rebuild and recovery

This document describes backup expectations, RAG index rebuild and verification tooling, how to interpret Qdrant inspection output, and recovery procedures for common failure scenarios.

---

## Backup expectations

Before running destructive operations (e.g. full Qdrant rebuild, schema changes, or model migrations), ensure backups are in place.

### Postgres

- **Logical dump**: Use `pg_dump` against the running Postgres instance. The app uses database name and user from env (defaults: `POSTGRES_DB=fe`, `POSTGRES_USER=fe`). Example from the host (with `fe_postgres` and port 5432):

  ```bash
  pg_dump -h localhost -U fe -d fe -F c -f fe_backup_$(date +%Y%m%d).dump
  ```

- **Volume backup**: The Compose stack uses the logical volume key `fe_pgdata` for Postgres data (`/var/lib/postgresql/data` in the container). The actual Docker volume name may be Compose-project-prefixed (for example `financial-engine_v2_fe_pgdata` on this host). To back up the volume, stop the stack, resolve the real Docker volume name with `docker volume ls` or `docker inspect fe_postgres`, copy or snapshot that volume, then restart. Restore by replacing the volume contents and starting Postgres.

### Qdrant

- **Volume backup**: Qdrant data is stored in the logical volume key `fe_qdrant` (container path `/qdrant/storage`). The actual Docker volume name may be Compose-project-prefixed (for example `financial-engine_v2_fe_qdrant` on this host). There is no built-in “export collection” step in the runbooks; backup is at the volume level. Before a full rebuild or risky change:
  1. Stop the backend and worker (so nothing is writing to Qdrant).
  2. Resolve the real Docker volume name with `docker volume ls` or `docker inspect fe_qdrant`, then copy or snapshot that volume (or use your platform’s volume snapshot).
  3. Optionally run `inspect_qdrant_collection.py` and keep the output as a pre-recovery baseline (point count, ticker distribution).

Restoring Qdrant from backup: replace the volume data with the backup and restart the `qdrant` service; the collection will be as of the snapshot. No separate “re-import” is needed if you restore the whole volume.

---

## Rebuild Qdrant index: `rebuild_rag_qdrant_index.py`

The script **wipes** the existing RAG collection and rebuilds it from documents in Postgres (re-chunking and re-embedding via the pipeline). Use it after a corrupted index, after an intentional model/schema change, or when you need a full RAG re-index.

**Location:** `financial-engine_v2/scripts/rebuild_rag_qdrant_index.py`

**Run from:** Repo root. The script adds `financial-engine_v2/backend` to `PYTHONPATH`; ensure the backend env (e.g. `.env` with `QDRANT_URL`, `QDRANT_COLLECTION`, DB, Ollama, etc.) is set so the script can connect to Postgres, Qdrant, and the embedding service.

**Usage:**

```bash
# Full rebuild (all documents)
python financial-engine_v2/scripts/rebuild_rag_qdrant_index.py

# Rebuild only one ticker
python financial-engine_v2/scripts/rebuild_rag_qdrant_index.py --ticker BHP

# Rebuild only documents published on or after a date
python financial-engine_v2/scripts/rebuild_rag_qdrant_index.py --since 2024-01-01

# Limit number of documents (e.g. for a quick test)
python financial-engine_v2/scripts/rebuild_rag_qdrant_index.py --limit 100

# Dry run: print plan and exit without writing to Qdrant or DB
python financial-engine_v2/scripts/rebuild_rag_qdrant_index.py --dry-run
```

**Options:**

| Option     | Default | Description |
|-----------|--------|--------------|
| `--ticker` | (all) | Restrict to one ticker symbol (e.g. `BHP`). |
| `--since`  | (none) | Only documents with `published_at >=` this ISO date. |
| `--limit`  | 0      | Max documents to process (0 = no limit). |
| `--report` | `financial-engine_v2/reports/rebuild_rag_qdrant_index_report.json` | Output report path. |
| `--dry-run` | false | Print plan/estimates and exit; no Qdrant or DB writes. |

**Behavior:**

- Enables embeddings and Qdrant in config and disables extraction for a RAG-only rebuild.
- Deletes the existing collection (if present), then for each selected document calls the pipeline to chunk and embed and upsert into Qdrant.
- Writes a JSON report with `selected_count`, `processed_count`, `error_count`, `total_chunks`, `qdrant_count`, and per-document items.
- On success, writes **vector baseline** to `financial-engine_v2/reports/vector_baseline.json` (used by `verify_vector_baseline.py`).
- Exit code 1 if any document failed (`status != "success"`).

**When to use:** After confirming backups (Postgres + Qdrant volume), when you need a clean index (e.g. corrupted collection, model change, or schema change). Prefer `--dry-run` first to confirm document selection.

---

## Verify vector baseline: `verify_vector_baseline.py`

Read-only check that the current Qdrant point count is within tolerance of the baseline written by `rebuild_rag_qdrant_index.py`. Used in CI/ops to detect partial wipes or unexpected drift.

**Location:** `financial-engine_v2/scripts/verify_vector_baseline.py`

**Baseline file:** `financial-engine_v2/reports/vector_baseline.json` (must exist; created by a successful full rebuild).

**Usage:**

```bash
# From repo root, with backend env and Qdrant reachable
python financial-engine_v2/scripts/verify_vector_baseline.py
```

**Behavior:**

- Reads `vector_count` from the baseline file.
- Connects to Qdrant and performs an exact count of the RAG collection.
- Compares current count to baseline; allowed tolerance is **5%** (configurable in script as `TOLERANCE_FRACTION`).
- Prints baseline count, current count, difference, and tolerance.
- **Exit 0**: within tolerance (or baseline is 0 and current is 0).
- **Exit 1**: baseline missing/invalid, Qdrant unreachable, or difference exceeds 5%.

**When to use:** After restores, after partial rebuilds, or in CI to ensure the index was not accidentally truncated. If it fails, inspect with `inspect_qdrant_collection.py` and consider a full rebuild if the index is inconsistent.

---

## Interpreting Qdrant inspector output: `inspect_qdrant_collection.py`

Read-only inspection of the RAG Qdrant collection. No writes or deletes.

**Location:** `financial-engine_v2/scripts/inspect_qdrant_collection.py`

**Usage:**

```bash
python financial-engine_v2/scripts/inspect_qdrant_collection.py
```

**Output sections and how to interpret them:**

1. **Collection metadata**  
   - Name, vector dimension, distance metric, total point count.  
   - **Interpretation:** Dimension must match the embedding model (e.g. 768 for `nomic-embed-text`). Distance should be COSINE. A zero count means the collection is empty or was wiped.

2. **Count by ticker**  
   - Number of points per `ticker` payload (and `<no ticker>` if any).  
   - **Interpretation:** Use to see distribution and spot missing tickers or one ticker dominating due to misconfiguration.

3. **Duplicate point IDs**  
   - Point IDs that appear more than once.  
   - **Interpretation:** Duplicates indicate a bug (e.g. double upsert). Ideally zero; non-zero suggests inconsistent indexing and possible rebuild.

4. **Missing chunk_index sequences (per document)**  
   - For each document, which chunk indices are missing from the expected contiguous 0..N-1.  
   - **Interpretation:** Gaps suggest failed or partial upserts for some chunks. Consider re-processing those documents or a full rebuild.

5. **document_id not canonical UUID**  
   - Points whose payload `document_id` is not a canonical UUID string.  
   - **Interpretation:** Schema/ingestion bug; such points may break joins or deduplication. Fix ingestion and consider rebuilding.

6. **point.id prefix mismatch**  
   - Points whose ID does not start with `document_id + ":"`.  
   - **Interpretation:** Invariant violation; can affect retrieval and updates. Fix pipeline and consider rebuild.

7. **Summary**  
   - Totals: unique IDs, duplicate count, documents with gaps, payload/id violations, number of tickers.  
   - **Interpretation:** Use as a single-page health check. Any non-zero duplicates or violations warrant investigation and possibly rebuild.

---

## Recovery scenarios

### Corrupted collection

**Symptoms:** Retrieval errors, missing or wrong results, or Qdrant returning errors; inspector shows duplicates, many gaps, or id/payload violations.

**Steps:**

1. **Back up** Postgres (pg_dump) and Qdrant volume (`fe_qdrant`).
2. **Inspect** with `inspect_qdrant_collection.py` and keep the output for comparison.
3. **Rebuild** the index:
   ```bash
   python financial-engine_v2/scripts/rebuild_rag_qdrant_index.py
   ```
4. **Verify** baseline:
   ```bash
   python financial-engine_v2/scripts/verify_vector_baseline.py
   ```
5. **Re-run** RAG stability if you use it:
   ```bash
   python financial-engine_v2/scripts/evaluate_rag_stability.py
   ```
   (First run after rebuild has no previous run to compare; CI may pass. Next run will establish a new baseline for drift.)

**Alternative:** If you have a recent Qdrant volume backup and no intentional model/schema change, restore the volume and restart Qdrant instead of rebuilding.

---

### Model change attempt

**Symptoms:** You want to switch embedding model (e.g. env or config change). The backend may refuse to start due to the **model guard**: `reports/runtime_embedding_model.txt` is compared to `settings.embed_model`; mismatch causes startup failure.

**Steps:**

1. **Back up** Postgres and Qdrant volume.
2. **Plan** for a full rebuild: vectors from the old model are incompatible with the new one; the index must be rebuilt.
3. **Update** config/env to the new model, then either:
   - Remove or update `reports/runtime_embedding_model.txt` so the backend can start (follow your guard policy), or
   - Run the rebuild in an environment where the new model is active and the guard is satisfied.
4. **Run** full rebuild (no `--limit`):
   ```bash
   python financial-engine_v2/scripts/rebuild_rag_qdrant_index.py
   ```
5. **Confirm** the backend writes the new model name to `runtime_embedding_model.txt` and that `vector_baseline.json` is updated.
6. **Verify** baseline and run `evaluate_rag_stability.py`; the first run after rebuild has no previous comparison; subsequent runs will track drift for the new model.

---

### Drift fails CI

**Symptoms:** The `rag-stability-check` job in `.github/workflows/backend-ci.yml` fails. It runs `financial-engine_v2/scripts/evaluate_rag_stability.py` (from `financial-engine_v2/backend`). CI fails if: any of the 15 test queries returns 0 hits, or `avg_rank_drift` > 2, or `avg_score_drift` > 0.15.

**Steps:**

1. **Reproduce locally** (backend + Qdrant + Ollama up, same env as CI):
   ```bash
   cd financial-engine_v2/backend && python ../scripts/evaluate_rag_stability.py
   ```
2. **Inspect** `financial-engine_v2/reports/rag_stability/latest_summary.json`: check `avg_rank_drift`, `avg_score_drift`, `drift_percentage`, and whether the run had a previous run to compare.
3. **Verify** index consistency:
   ```bash
   python financial-engine_v2/scripts/verify_vector_baseline.py
   ```
   If this fails, the index may have been partially wiped or changed; run `inspect_qdrant_collection.py` and consider a full rebuild.
4. **Check** embedding model consistency: ensure `reports/runtime_embedding_model.txt` matches the running backend’s `embed_model` and that no model/config change was introduced without a rebuild.
5. **If** the index and model are correct but drift is still high (e.g. upstream model or data changed), decide whether to:
   - **Accept** the new state: remove or rotate the previous run in `reports/rag_stability/` so the next CI run has no comparison (exit 0), establishing a new baseline, or
   - **Rebuild** from a known-good state and re-establish baseline and stability runs.

Do **not** auto-run the rebuild in CI; use it only after human approval and backups.

---

## Script and artifact reference

| Item | Path |
|------|------|
| Rebuild script | `financial-engine_v2/scripts/rebuild_rag_qdrant_index.py` |
| Verify baseline script | `financial-engine_v2/scripts/verify_vector_baseline.py` |
| Qdrant inspector | `financial-engine_v2/scripts/inspect_qdrant_collection.py` |
| RAG stability harness | `financial-engine_v2/scripts/evaluate_rag_stability.py` |
| Rebuild report | `financial-engine_v2/reports/rebuild_rag_qdrant_index_report.json` |
| Vector baseline | `financial-engine_v2/reports/vector_baseline.json` |
| RAG stability summary | `financial-engine_v2/reports/rag_stability/latest_summary.json` |
| Model guard file | `financial-engine_v2/reports/runtime_embedding_model.txt` |
| Postgres volume | Compose key `fe_pgdata` (actual Docker name may be project-prefixed, for example `financial-engine_v2_fe_pgdata`) |
| Qdrant volume | Compose key `fe_qdrant` (actual Docker name may be project-prefixed, for example `financial-engine_v2_fe_qdrant`) |
