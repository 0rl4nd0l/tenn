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

## 1.2 Cockpit Role (STRICT)

Cockpit is a **client + orchestration layer only**.

Cockpit MUST:

* call backend APIs
* orchestrate workflows
* perform reasoning/synthesis using provided context

Cockpit MUST NOT:

* access Qdrant directly
* access Postgres directly
* implement retrieval pipelines
* perform data ingestion
* maintain independent data stores of truth
* create alternate financial interpretations outside backend

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

## 4.2 Deterministic Vector IDs

```
{document_id}:{chunk_index}
```

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

## 5.3 Current Exception (TRANSITIONAL)

The following exists temporarily:

```
GET /api/rag/query → news_chunks
```

Rules:

* MUST remain read-only
* MUST be marked deprecated
* MUST NOT be expanded
* MUST be removed after migration

---

## 5.4 Forbidden Retrieval Patterns

* direct Qdrant queries outside backend
* cockpit-side retrieval logic
* multiple RAG implementations

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

* introduce fallbacks
* modify multiple layers
* bypass backend
* create parallel systems
* approximate results

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
