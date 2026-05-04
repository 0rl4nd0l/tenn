# Tenn Full System Map (Backend + Frontend)

**Interactive Dashboard:** `docs/tenn-system-map.html` (Recommended for viewing)
**Bundled PDF:** `docs/architecture/tenn_diagrams_booklet.pdf` (Static export)

This map documents Tenn as it exists in `financial-engine_v2` and `cockpit-ui`.

## 1) End-to-End System Topology

```mermaid
flowchart LR
  classDef fe fill:#131d37,stroke:#5a79bf,stroke-width:2px,color:#fff
  classDef be fill:#121a30,stroke:#35508a,stroke-width:2px,color:#fff
  classDef agent fill:#0f1730,stroke:#5fc8a5,stroke-width:2px,color:#fff
  classDef data fill:#0a1021,stroke:#2d3b66,stroke-width:1px,color:#a9b7dc
  classDef user fill:#1c2a52,stroke:#7ee0ff,stroke-width:2px,color:#fff

  U[Operator / User]:::user

  subgraph FE["Frontend (cockpit-ui)"]
    direction TB
    UI_SCREENS["Chat / Ops / News / Intel"]:::fe
    API_CLIENT["api-client.ts (SSE/REST)"]:::fe
    STORE["Zustand Store"]:::fe
  end

  subgraph BE["Backend (FastAPI)"]
    direction TB
    API_SURFACE["/api/cockpit/* /context/* /rag/*"]:::be
    AUTH_API["Authority / Validation"]:::be
  end

  subgraph AGENT["Agent Runtime"]
    direction TB
    LOOP["AgentLoop / Parser"]:::agent
    EXEC["ToolExecutor / Router"]:::agent
  end

  subgraph INFRA["Infrastructure & Data"]
    direction TB
    PG[(Postgres)]:::data
    QDR[(Qdrant)]:::data
    REDIS[(Redis / Celery)]:::data
    LLM["llama.cpp / Ollama"]:::data
    WEB["Web / Social API"]:::data
  end

  U --> UI_SCREENS
  UI_SCREENS --> API_CLIENT
  API_CLIENT --> STORE
  API_CLIENT --> API_SURFACE
  
  API_SURFACE --> LOOP
  LOOP --> EXEC
  
  EXEC --> AUTH_API
  EXEC --> QDR
  EXEC --> WEB
  EXEC --> LLM
  
  AUTH_API --> PG
  EXEC --> REDIS
  REDIS --> PG
  REDIS --> QDR
```

## 2) LLM Tool-Call Lifecycle

```mermaid
sequenceDiagram
  autonumber
  participant User
  participant UI as cockpit-ui
  participant API as FastAPI
  participant Loop as AgentLoop
  participant Exec as ToolExecutor
  participant Data as Data/Inference

  User->>UI: Request Action
  UI->>API: POST /chat (SSE)
  API->>Loop: Run Cycle
  Loop->>Loop: Parse Response

  alt is Read-Only
    Loop->>Exec: execute(read_only_tool)
    Exec->>Data: Fetch Context
    Data-->>Exec: Raw Results
    Exec-->>Loop: Structured Data
    Loop-->>API: Stream Answer
    API-->>UI: Display Response
  else is Mutating
    Loop->>Exec: propose(mutating_tool)
    Exec-->>Loop: action_proposal (Preview)
    Loop-->>API: Stream Proposal
    API-->>UI: Show Confirmation UI
    User->>UI: Confirm
    UI->>API: POST /action/execute
    API->>Data: Run Celery Job
    Data-->>UI: Job Status (Polling)
  end
```


## 3) LLM-Accessible Tool Surface (Current)

### Read-only tools
- `query_ticker_data`
- `get_company_dump`
- `get_price`
- `get_price_on_date`
- `get_price_range`
- `get_financials`
- `search_news`
- `search_announcements`
- `search_files`
- `list_recent_reports`
- `get_data_quality`
- `run_analysis`
- `fetch_url`
- `get_strategy`
- `search_web`
- `search_social`
- `recall_dossier`
- `deep_research`
- `get_watchlist_alerts`
- `scan_watchlist`
- `score_ticker`
- `screen_tickers`
- `get_valuation`
- `get_thesis`
- `check_decision_outcome`
- `review_open_decisions`

### Mutating tools (confirmation-gated)
- `run_backfill`
- `run_metric_extraction`
- `run_news_ingest`
- `run_announcement_ingest`
- `update_financials`
- `rebuild_financials`
- `audit_financials`
- `save_research_finding`
- `generate_chart`
- `create_thesis`
- `add_thesis_evidence`
- `reflect_on_decision`
- `adjust_signal_weights`

## 4) Information Sources by Subsystem

```mermaid
flowchart LR
  classDef tool fill:#0f1730,stroke:#5fc8a5,stroke-width:1px,color:#fff
  classDef source fill:#0a1021,stroke:#2d3b66,stroke-width:1px,color:#a9b7dc
  classDef store fill:#121a30,stroke:#35508a,stroke-width:2px,color:#fff

  subgraph LLM_TOOLS["ToolExecutor Dispatch"]
    T1["Ticker/Financial"]:::tool
    T2["News/Web/Social"]:::tool
    T3["Research/Strategy"]:::tool
    T4["File/Report"]:::tool
  end

  subgraph API["Service APIs"]
    S1["/api/context/ticker"]:::source
    S2["/rag/query"]:::source
    S5["llama.cpp / Router"]:::source
    S8["OpenBB (optional)"]:::source
  end

  subgraph STORES["Persistence"]
    S3[(Postgres)]:::store
    S4[(Qdrant)]:::store
    S7[(Filesystem)]:::store
  end

  T1 --> S1 --> S3
  T1 --> S5
  T1 -.-> S8
  
  T2 --> S2 --> S4
  T2 --> S5
  
  T3 --> S1
  T3 --> S3
  
  T4 --> S7
```

## 5) Frontend Subsystem Map

```mermaid
flowchart LR
  classDef route fill:#131d37,stroke:#5a79bf,stroke-width:1px,color:#fff
  classDef core fill:#121a30,stroke:#35508a,stroke-width:2px,color:#fff
  classDef client fill:#0f1730,stroke:#5fc8a5,stroke-width:1px,color:#fff
  classDef bridge fill:#1c2a52,stroke:#7ee0ff,stroke-width:1px,color:#fff

  subgraph ROUTES["Next.js Routes"]
    R["Chat/Ops/News/Intel"]:::route
  end

  subgraph UI_CORE["UI Components"]
    LAYOUT["CockpitLayout"]:::core
    STATUS["Status/Offline"]:::core
  end

  subgraph CLIENT_LAYER["Data Layer"]
    API["api-client.ts"]:::client
    STORE["Zustand Store"]:::client
    JOBS["use-job-stream.ts"]:::client
  end

  subgraph BACKEND["financial-engine_v2"]
    B["FastAPI Surface"]:::bridge
  end

  R --> LAYOUT
  LAYOUT --> STATUS
  LAYOUT --> API
  API --> STORE
  API --> B
  JOBS --> B
```


## 6) Delegation-Oriented Subsystem Inventory

- **Frontend UX shell**: layout, sidebar, status/offline, route navigation.
- **Frontend feature modules**: chat, operations, verification, intel pulse, news, history/settings/updater.
- **Frontend client integration**: REST + SSE wrappers, persistent stores, job stream hooks.
- **Backend API layer**: cockpit routes, context routes, extraction-review routes, process routes, RAG/commentary routes.
- **Agent runtime**: `AgentLoop`, `ResponseParser`, `ToolExecutor`, `ToolRouter`, `ActionRegistry`, tool schemas.
- **Execution layer**: action previews, confirmation gates, async job launch/tracking, Celery tasks.
- **Data layer**: Postgres (structured truth), Qdrant (vector/commentary retrieval), Redis (queue broker), file artifacts.
- **Inference/model layer**: llama.cpp primary runtime, optional Ollama compatibility path, model routing policy.
- **External intel/data sources**: ASX/news ingestion providers, web/social search clients, optional OpenBB market data sidecar.
