# Cockpit Agent System — Design Specification

**Date:** 2026-03-25
**Status:** Draft
**Scope:** Redesign cockpit chat into an agent-capable system with tool calling, sub-agents, tiered memory, hybrid model routing, and per-function model selection.

---

## 1. Problem Statement

The cockpit chat is a single-turn RAG system: user message → keyword intent detection → backend RAG → LLM → response. It cannot:

- Call tools autonomously (DB queries, RAG search, price data)
- Spawn background agents for long-running analysis
- Persist research findings across sessions
- Reason about when and how to compose multi-step workflows
- Route different tasks to appropriate models (reasoning vs. coding vs. extraction)
- Fall back to cloud APIs when local models are insufficient

The goal is to transform the cockpit chat into an intelligent financial research agent while preserving the existing extraction pipeline as a controlled, isolated service.

---

## 2. Architecture Overview

```
User (Web UI)
  ↓
Cockpit Agent Orchestrator
  ├── Tool Registry          — declarative tool definitions + JSON schemas
  ├── Tool-Call Loop         — LLM → parse tool calls → execute → loop
  ├── Memory Manager         — tiered markdown + SQLite-vec semantic search
  ├── Sub-Agent Spawner      — asyncio tasks with own LLM clients
  ├── HybridRouter           — routes LLM calls to local or API backends
  │     ├── Task Classifier
  │     ├── Policy Engine
  │     ├── API Executor
  │     ├── Normalizer
  │     └── Cost Tracker
  ├── Extraction Controller  — validation gateway for pipeline jobs
  └── System Prompt          — comprehensive capability description
        ↓
  ┌─────────────────────┐  ┌──────────────┐  ┌─────────────┐
  │ Backend API (RAG)   │  │ Postgres/DB  │  │ Qdrant      │
  │ /api/chat, /rag     │  │ financials   │  │ 5 collections│
  └─────────────────────┘  └──────────────┘  └─────────────┘
```

### Key Principle: Separation of Concerns

```
Agent       = decides WHAT to do
HybridRouter = decides WHERE to execute (local/API)
Controller  = decides WHETHER pipeline jobs run
Extractor   = produces structured data
Agent       = interprets results
```

---

## 3. Components

### 3.1 Agent Orchestrator

**Location:** `cockpit/core/agent/orchestrator.py`

The main loop. Receives user messages, manages the tool-call cycle, delegates to sub-agents, reads/writes memory.

**Tool-Call Loop:**
```
User message
  → Inject: system prompt + relevant memories + conversation history
  → Send to LLM (via HybridRouter)
  → Parse response for tool calls
  → If tool calls found:
      → Execute each tool (confirm if destructive)
      → Append tool results to messages
      → Send back to LLM (loop)
  → If no tool calls (final answer):
      → Return response to user
      → Write findings to memory if significant
  → Max iterations: 10 (safety cap)
```

**The orchestrator is blind to execution backend.** It sends LLM requests to the HybridRouter, which decides local vs. API. The orchestrator never calls APIs directly.

### 3.2 HybridRouter

**Location:** `cockpit/core/agent/hybrid_router.py`

Single insertion point between the orchestrator and LLM execution. Routes every LLM call to either local (llama.cpp via ModelRouter) or cloud API.

**LLM Call Path:**
```
Orchestrator
   ↓
HybridRouter
   ├── local → ModelRouter → llama.cpp (router mode)
   └── api   → API Executor → Anthropic / OpenAI
   ↓
Normalizer → Validator → Response
```

**Sub-components:**

| Component | Purpose |
|-----------|---------|
| Task Classifier | Categorize request: simple/complex/deep-reasoning/tool-heavy |
| Policy Engine | Rules for when to use API vs. local (configurable) |
| API Executor | Handles cloud API calls with auth, retry, timeout |
| Normalizer | Converts all outputs (local + API) to a common response format |
| Validator | Schema-checks outputs before returning to orchestrator |
| Cost Tracker | Logs source, latency, cost per request |

**Response metadata (always attached):**
```json
{
  "source": "local | api",
  "model": "Qwen3.5-27B",
  "confidence": 0.92,
  "cost_usd": 0.00,
  "latency_ms": 3400
}
```

**Policy defaults:**
- Local-first for all requests
- API fallback when: context exceeds local model capacity, explicit user override, or local model fails
- API required for: none (fully local by default)
- User can configure policy in preboot UI or `~/.tenn/config/hybrid-router.yaml`

### 3.3 Tool Registry

**Location:** `cockpit/core/agent/tools/`

Declarative tool definitions. Each tool is a Python function with a JSON Schema for parameters.

```
cockpit/core/agent/tools/
├── __init__.py              # ToolRegistry class
├── db_tools.py              # get_financials, get_documents, get_extraction_failures, get_low_confidence
├── rag_tools.py             # search_asx_docs, search_commentary, search_news, search_methodology
├── price_tools.py           # get_price_history, get_price_snapshot
├── pipeline_tools.py        # metric_extraction, run_news_ingest, run_backfill, run_announcement_ingest
├── web_tools.py             # fetch_url
└── agent_tools.py           # spawn_researcher, spawn_auditor, spawn_comparator, spawn_pipeline_runner
```

**Tool interface:**
```python
@dataclass
class ToolSpec:
    name: str                          # e.g. "get_financials"
    description: str                   # injected into system prompt
    parameters: dict                   # JSON Schema
    requires_confirmation: bool        # True for pipeline actions
    execute: Callable[[dict], Any]     # runs the tool
```

**Confirmation rules:**
- Read-only tools (DB, RAG, price, web): auto-execute
- Pipeline tools (extraction, ingest, backfill): require user `/confirm`
- Agent tools (spawn): auto-execute but user sees status

**Tool calling format:**
- Native function calling via `--jinja` flag for Qwen3.5 and Ministral models
- Fallback text-extraction parsing for models without native support (DeepSeek-R1, older Qwen)
- Cloud APIs use native tool-use (Anthropic/OpenAI format)
- HybridRouter's Normalizer ensures consistent tool-call format regardless of backend

### 3.4 Memory System

**Location:** `cockpit/core/agent/memory/`
**Storage root:** `~/.tenn/memory/`

#### Storage Layout

```
~/.tenn/memory/
├── MEMORY.md              # Long-term durable (user prefs, key findings, system state)
├── sessions/
│   ├── current.md          # Active conversation (full recent messages)
│   └── YYYY-MM-DD-HH.md   # Archived session logs (auto-rotated)
├── research/
│   ├── BHP.md              # Per-ticker research findings
│   ├── CSL.md              # Accumulated across sessions
│   └── sector-mining.md    # Cross-ticker thematic notes
├── daily/
│   └── YYYY-MM-DD.md       # Daily session summary (compacted at session end)
└── memory.db               # SQLite-vec for semantic search
```

#### Three Tiers

| Tier | Storage | Scope | Written By | Persistence |
|------|---------|-------|-----------|-------------|
| **Conversation** | `sessions/current.md` | Active chat | Orchestrator | Compacted at context limit |
| **Research** | `research/<ticker>.md` | Per-ticker findings | Agent (after interpreting structured data) | Durable |
| **Durable** | `MEMORY.md` | User prefs, system state | Explicit instruction or pattern detection | Never compacted |

#### Storage Boundary (Critical)

```
Extraction output → Postgres (structured data) + Qdrant (embeddings)
                     ↓
Agent reads via get_financials() → interprets → writes to research/<ticker>.md
```

**Raw extraction output NEVER goes directly into research memory.** This prevents hallucinated "facts" from polluting the research store.

#### Semantic Search

- All `.md` files chunked and embedded into `memory.db` (SQLite-vec)
- Embedding model: `nomic-embed-text` via Ollama (port 11434)
- On each user message: embed query → search memory.db → inject top-k relevant memories into system prompt
- On write: re-embed affected files

#### Compaction

When conversation approaches context limit:
1. Summarize oldest messages into a paragraph
2. Write full detail to `daily/YYYY-MM-DD.md`
3. Extract durable findings → write to `research/<ticker>.md`
4. Replace detailed messages with summary in active context
5. Re-embed new daily/research files into `memory.db`

### 3.5 Sub-Agent System

**Location:** `cockpit/core/agent/subagents.py`

#### Agent Types

| Type | Role | Default Model | Spawned When |
|------|------|--------------|-------------|
| researcher | Deep-dive analysis | Qwen3.5-27B | "Deep dive on CSL" |
| auditor | QA on extraction quality | Ministral-3-14B-Reasoning | "Check confidence for MIN" |
| comparator | Multi-ticker comparison | Ministral-3-14B-Reasoning | "Compare BHP, RIO, FMG" |
| pipeline-runner | Execute pipeline jobs | No model (pure code) | "Ingest today's news" |

#### Lifecycle

```
Orchestrator decides to spawn sub-agent
  → Create context brief (task + relevant memory + tool list)
  → HybridRouter decides: local or API execution
     ├── local: asyncio task + own LlamaCppClient, model swap via router
     └── api: asyncio task + API client, no model swap needed (GPU stays free)
  → Sub-agent executes: tool calls, RAG queries, DB reads
  → Sub-agent writes findings to research/<ticker>.md
  → Sub-agent returns structured result to orchestrator via asyncio.Queue
  → Orchestrator synthesizes and presents to user
```

#### Constraints

- **Max concurrent (local):** 1 (single GPU, `--models-max 1`)
- **Max concurrent (API):** configurable (default 2)
- **Max spawn depth:** 1 (no recursive spawning)
- **Timeout:** 300 seconds (configurable)
- **Tool access:** same as orchestrator minus `spawn_agent`

#### Model Swapping (Local Sub-Agents)

1. Orchestrator (27B) → spawn researcher on different model (14B)
2. Router loads 14B → 27B auto-evicted
3. Researcher runs
4. Researcher completes → router loads 27B back
5. Orchestrator resumes

If orchestrator and sub-agent use the same model, no swap needed.

#### API Sub-Agents (Parallel Unlock)

When HybridRouter routes a sub-agent to an API:
- GPU stays free for the orchestrator
- Sub-agent runs in parallel via cloud API
- Output normalized and validated before returning
- Enables pseudo-parallel execution on single GPU

#### User Visibility

- Status line: `[Agent: researcher] Analyzing CSL cash flow trends...`
- Progress updates streamed (not in main chat)
- Result attributed: "Based on deep analysis (researcher agent)..."
- Cancel: `/cancel-agent`

### 3.6 Extraction Controller

**Location:** `cockpit/core/agent/extraction_controller.py`

Validation gateway between the agent's tool call and the extraction pipeline.

**The agent cannot send raw prompts into extraction.**

#### Tool Contract

```python
metric_extraction(document_id: str, ticker: str) -> job_id: str
```

No prompt. No instructions. No free text.

#### Responsibilities

| Responsibility | Implementation |
|---------------|---------------|
| Input validation | Document exists (PDF, size OK), ticker valid, reject free-form |
| Deduplication | Same doc hash → skip |
| Rate limiting | Max N concurrent extraction jobs |
| Job queuing | Celery or lightweight async queue |
| Model routing | Uses `EXTRACTION_LLAMACPP_URL` / `EXTRACT_MODEL` (independent of agent) |
| Schema validation | JSON schema check on output, retry on failure (max 3) |
| Output contract | Returns `{doc_id, metrics, confidence, extraction_version, errors}` |

#### API Fallback (Optional)

If local extraction fails or is unavailable, the controller can route to a cloud API for extraction — but output validation is identical. The HybridRouter's normalizer handles format differences.

### 3.7 Per-Function Model Routing

**Configured in:** Preboot UI (per-function model selectors with suggested defaults)

| Function | Default Model | VRAM (Q4_K_M) | Speed (M40) | Native Tool Calling |
|----------|--------------|---------------|-------------|-------------------|
| Orchestrator | Qwen3.5-27B | ~17 GB | ~12 tok/s | Yes |
| Analyst | Qwen3.5-27B | (shared) | ~12 tok/s | Yes |
| Sub-agent worker | Ministral-3-14B-Reasoning | ~9 GB | ~22 tok/s | Yes (Mistral format) |
| Deep reasoning | DeepSeek-R1-Distill-Qwen-14B | ~8 GB | ~9 tok/s | No (text-based) |
| Coder | Qwen2.5-Coder-14B | ~8 GB | fast | Text-based |
| Extraction | Qwen2.5-14B-Instruct | ~8 GB | ~9 tok/s | N/A (structured output) |

**Preboot UI additions:**
- Per-function model dropdown with suggested defaults noted
- "Advanced" section for model routing configuration
- HybridRouter policy toggle: "Local only" / "Local + API fallback" / "API preferred"

### 3.8 System Prompt

**Location:** `cockpit/core/agent/prompts/system.md`

The system prompt is the LLM's operating manual. It must tell the model:

1. **Identity:** "You are Tenn, a financial research agent for ASX-listed companies."
2. **Tools:** Full registry with descriptions, parameter schemas, and usage guidelines
3. **Decision framework:** When to use each tool, when to spawn sub-agents vs. handle inline
4. **Memory access:** How to read prior research, when to write findings
5. **Confidence calibration:** How to express uncertainty, when to flag low-confidence data
6. **Boundaries:** No raw prompts to extraction, no hallucinated financials, no direct DB writes
7. **Composition patterns:** Multi-step workflow examples (e.g., "to compare companies: get_financials for each → search_commentary → synthesize")

---

## 4. File Structure

```
cockpit/core/agent/
├── __init__.py
├── orchestrator.py          # Main agent loop
├── hybrid_router.py         # Local/API routing + normalization + validation
├── model_router.py          # Per-function model mapping
├── subagents.py             # Sub-agent spawner and lifecycle
├── extraction_controller.py # Pipeline validation gateway
├── tools/
│   ├── __init__.py          # ToolRegistry
│   ├── db_tools.py
│   ├── rag_tools.py
│   ├── price_tools.py
│   ├── pipeline_tools.py
│   ├── web_tools.py
│   └── agent_tools.py
├── memory/
│   ├── __init__.py          # MemoryManager
│   ├── store.py             # Markdown read/write
│   ├── search.py            # SQLite-vec semantic search
│   └── compaction.py        # Summarization + flush
└── prompts/
    └── system.md            # System prompt template
```

---

## 5. Hardware Constraints

- **GPU:** Tesla M40 24GB (288 GB/s GDDR5, compute 5.2, no Flash Attention)
- **RAM:** 32 GB
- **CPU:** Intel i3-9100F (4 cores)
- **Models:** Hot-swapped via llama.cpp router mode (`--models-dir`, `--models-max 1`)
- **Concurrent local models:** 1 (single GPU)
- **Concurrent API calls:** configurable (default 2)

---

## 6. What Does NOT Change

These existing systems remain untouched:

| System | Why |
|--------|-----|
| Backend `/api/chat` endpoint | Still serves RAG queries; agent calls it as a tool |
| Multipass extraction pipeline | Controlled exclusively via ExtractionController |
| Qdrant collections (5) | Agent queries via tools, doesn't manage collections |
| Postgres schema | Agent reads via DbReader, doesn't write |
| llama.cpp router mode | Already implemented; agent leverages it for model swapping |
| Preboot UI | Extended with per-function model selectors, not replaced |

---

## 7. Implementation Phases

| Phase | Scope | Dependencies |
|-------|-------|-------------|
| **1. Tool Registry + Tool-Call Loop** | Core agent capability — tools, schemas, execution loop, native function calling | None |
| **2. HybridRouter** | Local/API routing, normalization, validation, cost tracking | Phase 1 |
| **3. Memory System** | Markdown storage, SQLite-vec indexing, compaction, semantic search | Phase 1 |
| **4. Sub-Agent Spawner** | Background agents, lifecycle, model swapping, result queue | Phases 1-3 |
| **5. Extraction Controller** | Validation gateway, schema enforcement, retry logic | Phase 1 |
| **6. Preboot UI — Model Routing** | Per-function model selectors with suggested defaults | Phase 2 |
| **7. System Prompt Engineering** | Comprehensive prompt with tool docs, decision framework, examples | Phases 1-5 |
| **8. Integration Testing** | End-to-end: user message → tool calls → sub-agent → memory → response | All |

---

## 8. Risks

| Risk | Severity | Mitigation |
|------|----------|------------|
| Local models fail at multi-step tool composition | High | HybridRouter falls back to API for complex orchestration |
| Model swap latency during sub-agent work (cold cache) | Medium | Page cache warming, prefer same-model sub-agents when possible |
| Memory contamination from hallucinated findings | High | Storage boundary: extraction → Postgres only; agent interprets before writing to research |
| Context window exhaustion with tools + memory + history | Medium | Compaction system; careful token budgeting in system prompt |
| API cost runaway | Medium | Cost tracker with configurable budget caps in HybridRouter |
| Sub-agent timeout/hang | Low | 300s timeout, `/cancel-agent`, asyncio task cancellation |

---

## 9. Success Criteria

- [ ] LLM can autonomously call DB, RAG, price, web tools to answer financial questions
- [ ] Multi-step tool composition works (e.g., get financials → search commentary → synthesize)
- [ ] Sub-agents complete background research and write findings to memory
- [ ] Memory persists across sessions — prior research retrieved semantically
- [ ] Compaction keeps conversations within context limits without losing critical context
- [ ] Per-function model selection works from preboot UI
- [ ] HybridRouter falls back to API when local is insufficient
- [ ] Extraction pipeline remains isolated — no raw prompts, schema-validated output
- [ ] All outputs (local + API) normalized and validated before reaching orchestrator
- [ ] System prompt enables the LLM to make good tool-use decisions
