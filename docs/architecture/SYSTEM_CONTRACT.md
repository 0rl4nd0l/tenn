# SYSTEM CONTRACT — FINANCIAL ENGINE (TENn)

Version: v2.0
Status: ACTIVE — ENFORCED
Authority: Backend (financial-engine_v2/backend)

---

# 0. PURPOSE

This contract defines **non-negotiable system rules** governing:

* data integrity
* pipeline behavior
* retrieval architecture
* model usage
* agent behavior (Claude / Codex)
* system topology
* system observability

The goal is to:

* eliminate architectural drift
* prevent fallback masking
* enforce a single source of truth
* ensure deterministic, testable outputs
* guarantee consistent system evolution

---

# 1. SYSTEM AUTHORITY

## 1.1 Source of Truth

**Backend is the sole authority.**

The backend exclusively owns:

* ingestion pipelines
* extraction logic
* structured financial data (Postgres)
* vector data (Qdrant)
* retrieval logic
* data correctness

No other component may override or duplicate this authority.

---

## 1.2 Cockpit Role (STRICT — ENFORCED)

Cockpit is a **client + orchestration layer only**.

Cockpit MUST:

* call backend APIs for all authoritative data reads
* orchestrate workflows
* perform reasoning/synthesis using provided context

Cockpit MUST NOT:

* access Qdrant directly (write path enforced via backend commentary API)
* access Postgres directly for authoritative reads (enforced: `BackendApiClient` is sole data source when configured)
* implement retrieval pipelines
* perform data ingestion
* maintain independent data stores of truth
* create alternate financial interpretations outside backend

### Enforcement Status (2026-03-31)

**RESOLVED.** All cockpit authoritative reads now flow through `BackendApiClient`:

| Data | Backend Endpoint | Cockpit Consumer |
|------|-----------------|------------------|
| Documents, financials, announcements | `GET /api/context/ticker` | `_load_ticker_context`, tool executor, deep research |
| Extraction failures, low-confidence | `GET /api/context/verification` | verification, data quality tools |
| Transcript approve/reject/purge | `POST /api/commentary/transcripts/*` | `/review` command handler |
| Pending transcripts | `GET /api/commentary/transcripts/pending` | `/review list` |

**DbReader** is retained only for:
* Diagnostic queries (`run_diagnostic_query()`)
* Legacy fallback when `backend_api_client` is `None` (environments without the backend running)

When `backend_api_client` is configured, backend failure returns empty data with error signal — no silent DbReader fallback.

**See also:** [21_cockpit_client_contract.md](21_cockpit_client_contract.md) — Cockpit addendum (HTTP surfaces, liveness vs `/api/cockpit/health`, consumer patterns, conformance matrix).

---

## 1.3 Retrieval Boundary (CRITICAL)

Cockpit MAY:

* request retrieval via backend APIs

Cockpit MUST NOT:

* perform retrieval logic
* rank/search independently
* merge datasets itself

---

# 2. SYSTEM ARCHITECTURE (MANDATORY FLOW)

The system MUST follow:

INGESTION → EXTRACTION → STORAGE → RETRIEVAL → ANALYSIS → CLIENT

---

## 2.1 Layer Responsibilities

| Layer      | Responsibility                   |
| ---------- | -------------------------------- |
| Ingestion  | Acquire raw data                 |
| Extraction | Structure raw data               |
| Storage    | Persist structured + vector data |
| Retrieval  | Query and rank relevant data     |
| Analysis   | Interpret and derive insights    |
| Client     | Present and orchestrate          |

---

## 2.2 Forbidden Patterns

* skipping layers
* cross-layer access (e.g. cockpit → Qdrant)
* mixing extraction and analysis
* embedding logic in incorrect layers
* duplicate pipelines

---

# 3. PIPELINE CONTRACT

## 3.1 Ingestion

* no transformation
* no filtering
* idempotent inserts only

---

## 3.2 Extraction (STRUCTURAL)

Responsibilities:

* PDF → text
* text → chunks

Rules:

* MUST preserve all data
* MUST NOT drop rows heuristically
* NO semantic interpretation

---

## 3.3 Metric Extraction (LLM)

Rules:

* extract ONLY explicit values
* DO NOT infer
* DO NOT substitute

Failure:

```
return null
```

---

## 3.4 Allowed Exception

ONLY allowed derivation:

* Appendix 5B capex = sum of explicit sub-items

No other derivations permitted.

---

## 3.5 Normalization

* unit conversion allowed
* sign normalization allowed
* NO fabrication
* NO gap filling

---

# 4. DATA INVARIANTS

## 4.1 Data Preservation

NO layer may reduce fidelity.

Forbidden:

* dropping valid rows
* skipping valid tables

---

## 4.2 Deterministic Logical Vector IDs

```
{document_id}:{chunk_index}
```

This is the canonical logical vector/chunk ID and must be preserved in Qdrant
payloads as `logical_vector_id`.

Physical Qdrant point IDs may be a deterministic UUIDv5 mapping of the logical
ID when required by the Qdrant adapter/storage boundary. That UUIDv5 value is a
storage address, not the canonical vector/chunk identity.

Forbidden:

* uuid4()
* random IDs

---

## 4.3 Embedding Consistency

* embedding model must remain consistent
* dimension must not change without rebuild

---

## 4.4 No Silent Corruption

Any vector-impacting change requires:

* rebuild OR
* explicit validation

---

# 5. RETRIEVAL (RAG) CONTRACT

## 5.1 Single Retrieval Authority

ALL retrieval is owned by backend.

---

## 5.2 Unified Interface (TARGET STATE)

```
POST /rag/query
```

Input:

```
{
  query: string,
  source: "asx_docs" | "news" | "commentary" | "hybrid",
  ticker?: string,
  top_k?: number
}
```

---

## 5.3 Legacy Exception (REMOVED)

The former transitional route has been removed:

```
GET /api/rag/query
```

Rules:

* MUST NOT be reintroduced
* All retrieval callers MUST use `POST /rag/query`
* News retrieval MUST use `POST /rag/query` with `source="news"`

---

## 5.4 Forbidden Retrieval Patterns

* direct Qdrant queries outside backend
* cockpit-side retrieval logic
* multiple RAG implementations

---

## 5.5 Context API (AUTHORITATIVE)

Backend provides cockpit with all authoritative data reads via:

```
GET /api/context/ticker?ticker=XYZ
```

Returns a single bundle: `docs`, `financials`, `latest_financial_snapshot`, `announcement_context`, `extraction_failures`, `low_confidence_financials`. Query params control limits and thresholds. Partial failure populates `errors[]` without aborting the response.

```
GET /api/context/verification?ticker=XYZ
```

Returns `extraction_failures` and `low_confidence_financials` for data quality checks. Ticker is optional — omit for cross-ticker view.

Rules:
* SQL matches the original DbReader queries exactly (field name parity)
* `low_confidence_threshold` default is `0.4` (matching DbReader)
* Valid ticker with no data returns HTTP 200 with empty lists — never 404

---

## 5.6 Commentary API (AUTHORITATIVE)

Backend owns all Qdrant writes for commentary/transcript data:

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/commentary/transcripts/pending` | GET | List staged transcripts |
| `/api/commentary/transcripts/{source_id}/approve` | POST | Read staged JSONL, upsert to Qdrant, clean staging |
| `/api/commentary/transcripts/{source_id}/reject` | POST | Delete staged transcript |
| `/api/commentary/transcripts/purge-expired` | POST | Remove expired staged transcripts |

Rules:
* Write endpoints require API key (`X-API-Key` header)
* `source_id` validated against `^[a-zA-Z0-9_\-]{1,128}$`
* Staged files live at `~/.tenn/memory/staged_chunks/`
* `collection_name` is read from the staging index, not from the request body
* Qdrant unavailable returns HTTP 503

---

# 6. WORKER CONTRACT

## 6.1 Canonical Worker

```
backend/app/worker_tasks.py
```

---

## 6.2 Legacy Worker

```
worker/app/tasks.py
```

Status:

* DEPRECATED
* MUST NOT RUN

---

## 6.3 Scheduling

* all jobs use same Celery app
* all jobs use canonical pipeline

---

# 7. NO PARALLEL SYSTEMS RULE

The system MUST NOT contain:

* multiple sources of truth
* duplicated pipelines
* competing implementations

If found:

* STOP
* consolidate
* remove duplication

---

# 8. FAIL-FAST PRINCIPLE

On failure or ambiguity:

* STOP
* surface issue
* DO NOT degrade

---

## Forbidden:

* silent fallbacks
* hidden retries changing logic
* masking errors

---

# 9. MODEL USAGE CONTRACT

## 9.1 Extraction Models

* MUST be instruct-style
* MUST be deterministic

---

## 9.2 Embeddings

* MUST be consistent
* MUST match vector dimension

---

## 9.3 Routing

* MUST NOT change output semantics
* fallback must preserve task type

---

## 9.4 GPU Process Topology

The GPU (Tesla M40, 24GB) has a fixed process budget.

**Authorised processes:**

| Role | Port | VRAM Budget | Startup Owner |
|------|------|-------------|---------------|
| Chat/Router | `:8001` | 10 GB | `systemd --user llama-cpp-router.service` via `scripts/run_llama_server.sh` |
| Extraction | `:8002` | 10 GB | `scripts/run_extraction_server.sh` |

**Total allocated:** 20 GB. **Headroom:** 4 GB (Ollama embeddings + OS + CUDA context).

**Rogue definition:** Any top-level or independently spawned `llama-server` process whose `--port` is not in `{8001, 8002}`.

**Router-mode exception:** In router mode, the canonical service on `:8001` may spawn per-model child worker processes on ephemeral localhost ports. Those children are part of the authorised router runtime, not independent instances, and must not be classified as rogue solely by child port.

Invariants:
* Agents and scripts MUST NOT spawn additional llama-server instances on non-canonical ports.
* If an independent third instance is found running, it MUST be terminated before proceeding.
* Verification: `scripts/gpu_process_guard.sh --check` (exit 0=clean, 1=rogues, 2=VRAM critical).

---

## 9.5 Agent Spawn Protocol

Before spawning or restarting any llama-server instance, agents MUST:

1. Query `GET /health` on the target port.
2. If healthy and correct model loaded → **REUSE** — do not spawn.
3. If healthy but wrong model → use router API (`POST /models/load`) or `restart_with_model`.
4. If dead → check VRAM via `nvidia-smi`.
5. If VRAM insufficient → run `gpu_process_guard.sh --kill-rogues`, then recheck.
6. Only spawn after VRAM gate passes.

Agents MUST NOT:
* Spawn llama-server on any port other than 8001 or 8002.
* Spawn without checking the health of the target port first.
* Ignore VRAM constraints.

## 9.6 Shared-Router Mutual Exclusion

When chat and registered GPU-exclusive work share the canonical router on `:8001`, they MUST NOT contend for the same local GPU runtime at the same time.

Invariants:
* GPU-exclusive activity MUST be registered in a process-safe shared state for the full duration of the protected work.
* Extraction activity MUST register as GPU-exclusive activity for the full duration of each multipass extraction run.
* Cockpit/local chat MUST route to the configured API backend while GPU-exclusive activity is active on the shared router.
* If no API backend is configured, chat MUST fail fast or remain blocked until the GPU-exclusive activity finishes; it MUST NOT silently continue on the local router during protected work.
* Launchers MUST NOT start or restart the shared local chat/router runtime while GPU-exclusive activity is active unless the owning GPU task explicitly overrides the guard.
* Any caller that uses `POST /models/load` MUST resolve stale alias IDs to a usable router registry entry before requesting the load.

---

# 10. AGENT (CLAUDE / CODEX) RULES

## 10.1 Contract Authority

Agents MUST:

* read SYSTEM_CONTRACT.md
* comply with all rules

---

## 10.2 Pre-Flight Check (MANDATORY)

Agents MUST state:

1. Target layer
2. Relevant invariants
3. What must NOT change
4. Why change is safe

---

## 10.3 Forbidden Agent Behavior

Agents MUST NOT:

* introduce fallbacks that mask backend failures (see §1.2 enforcement)
* modify multiple layers
* bypass backend (all reads via §5.5/§5.6 APIs, all writes via backend)
* create parallel systems
* approximate results
* re-introduce direct Postgres or Qdrant access in cockpit

---

## 10.4 Contract Enforcer (REQUIRED)

All complex tasks MUST include:

SUBAGENT — CONTRACT ENFORCER

Responsibilities:

* validate changes
* detect violations
* STOP execution if needed

---

# 11. ANALYSIS LAYER (RESERVED)

## 11.1 Responsibility

Analysis layer will:

* perform ALL derivations
* generate financial insights

---

## 11.2 Separation Rule

Extraction:

* raw data only

Analysis:

* interpretation + derived metrics

---

# 12. EVALUATION CONTRACT

## 12.1 Extraction

* MUST run live eval
* MUST track accuracy

---

## 12.2 RAG

* MUST track stability
* MUST detect drift

---

## 12.3 Blocking Rule

NO pipeline change without:

* evaluation
* regression check

---

# 13. CHANGE MANAGEMENT

## 13.1 Allowed

* prompt improvements
* bug fixes
* contract-compliant enhancements

---

## 13.2 Restricted

Require explicit approval:

* schema changes
* vector format changes
* pipeline restructuring
* API changes

---

## 13.3 Migration Rule

* mark deprecated
* verify unused
* remove safely

---

# 14. FAILURE DEFINITION

| Condition     | Output           |
| ------------- | ---------------- |
| Missing data  | null             |
| Ambiguous     | best valid match |
| No valid data | null             |

Incorrect:

* substitution
* guessing
* hidden fallback

---

# 15. ENFORCEMENT

If any rule is violated:

1. STOP
2. identify violation
3. report clearly
4. DO NOT proceed

---

# 16. SYSTEM OBSERVABILITY (MANDATORY)

## 16.1 Observability Mandate

**Transparency is a core system invariant.** 

All long-running or resource-intensive tasks MUST be observable in the global system state (Cockpit/Verification Workstation) regardless of their trigger source.

## 16.2 Registration Requirements

Every job (Extraction, Evaluation, Backfill, or Maintenance) MUST:

1.  **Register Start:** Use the backend-authoritative activity monitor (e.g., `extraction_activity` context manager) to announce its existence and metadata (Ticker, Document ID, Method).
2.  **Heartbeat:** Maintain liveness in the shared state for the full duration of the execution.
3.  **Register Completion:** Explicitly clear its activity token upon success, failure, or cancellation.

## 16.3 Origin Agnostic

The observability mandate applies strictly to ALL job origins:
*   Frontend (Web UI/Cockpit)
*   Agents (Codex/Claude via tools)
*   CLI (Local scripts)
*   Systemd Services (Background workers)

**Bypassing the activity monitor is a contract violation.**

---

# FINAL PRINCIPLE

The system prioritizes:

1. correctness
2. determinism
3. traceability

Over:

* completeness
* convenience
* always returning an answer

---

# END OF CONTRACT
