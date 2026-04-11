---
date: 2026-04-11
topic: open-ideation
focus: Entire Tenn project (financial-engine_v2 + Cockpit + ops/tooling)
---

# Ideation: Tenn — whole-project improvement directions

## Codebase Context

### Codebase (observed)

- **Shape:** Dual product — (1) `financial-engine_v2`: FastAPI backend, Celery workers, Postgres, Qdrant, multipass financial extraction (Docling/PyMuPDF paths), RAG, analysis modules, portfolio orchestration; (2) Cockpit: Textual TUI and Next.js web UI with shared backend APIs, routing, GPU/llama contention logic; (3) supporting scripts, eval harnesses, CI, and extensive `docs/architecture/` + `docs/claude/` governance.
- **Conventions:** `SYSTEM_CONTRACT.md` is authoritative; canonical backend boot via `financial-engine_v2/scripts/run_local_backend.sh`; ruff (not black/isort); milestone commits with `Working:` / `Tested:`; embedding/RAG changes gated by checklist skills and stability harnesses.
- **Pain points / gaps (from `docs/claude/STATE.md` and lessons):** Extraction redesign spec/plan vs implementation lag; FX conversion not built; known real-gold eval failures (`net_debt`, RIO currency); AZJ/font class of issues; Cockpit “contract/code mismatch” still open under docs-governance; long-lived branch `cloud/session-20260319`; parallel skill surfaces (`.claude/`, `.codex/`, `.cursor/`) increase onboarding cost; operator must juggle GPU guard, mutex, Ollama vs llama.cpp, and multiple validation docs.
- **Leverage points:** Already-strong eval/fixture/lesson infrastructure; memory orchestration and query orchestrator recently wired; newspaper4k news path; CI baseline exists; lessons file encodes repeatable failure modes.

### Past learnings

- **`docs/claude/lessons.md`:** Large, high-signal catalog (margins vs `_pct_change`, `temperature=0` on all extraction LLM calls, `prompt_hash` from `PROMPT_HASH`, Qdrant payloads must include chunk `text`, primary ticker from `article_relevance` not `sorted()[0]`, etc.). Institutional knowledge is **documented** but not uniformly **enforced** by automated guards beyond scattered tests.
- **`docs/solutions/`:** Not present in this workspace; no separate solutions index to mine.

### Issue intelligence

- Not run (no issue-tracker intent in focus). Optional follow-up: cluster GitHub issues for user-reported themes.

---

## Ranked Ideas

### 1. Execute the approved extraction redesign plan end-to-end

**Description:** `AGENTS.md` still lists the 2026-03-21 extraction redesign spec/plan as complete while the eight implementation tasks are not started. Deliver the docling multipass pipeline as the single canonical path per plan, with tests and capability guards updated so the spec stops drifting from reality.

**Rationale:** Unlocks the main architectural bet for accuracy and maintainability; everything downstream (eval %, RAG chunks, analysis modules) compounds on extraction quality.

**Downsides:** Large, multi-PR effort; high regression risk without strict eval gates; must stay inside `SYSTEM_CONTRACT` (no shadow pipelines).

**Confidence:** 82%

**Complexity:** High

**Status:** Unexplored

---

### 2. Close Cockpit contract vs implementation (single authoritative doc + API audit)

**Description:** Resolve the open “Cockpit contract/code mismatch” from docs-governance: produce one short contract doc (routes, streaming events, action execution, auth assumptions) and a tracked checklist of code paths that must conform; fix or explicitly deprecate divergent behavior.

**Rationale:** Reduces wrong-surface fixes (see L065), stabilizes web vs TUI parity work, and cuts support load for hybrid routing and GPU handoff.

**Downsides:** Requires disciplined API/UI inventory; may surface breaking changes for ad-hoc clients.

**Confidence:** 78%

**Complexity:** Medium

**Status:** Unexplored

---

### 3. Real-gold eval as a scheduled quality gate (target known failure classes)

**Description:** Automate (e.g. weekly CI or manual workflow) a bounded real-gold run over `data/extraction_gold_real` with thresholds and artifact upload; prioritize fixes for `net_debt`, RIO currency, and other recurring classes called out in STATE.

**Rationale:** Connects extraction-quality workstream to measurable regression signal beyond synthetic fixtures; aligns with existing real-gold HTTP route and verification UI.

**Downsides:** Needs stable LLM backend in CI or a “record replay” strategy; runtime cost; flaky if external models move.

**Confidence:** 75%

**Complexity:** Medium

**Status:** Unexplored

---

### 4. Unified operator observability (one checklist or small dashboard)

**Description:** One place (markdown runbook + optional minimal HTML/CLI) that answers: Is API healthy? Is extraction mutex clear? GPU guard status? Last RAG stability summary? Last embed model / collection dim? Tie together existing scripts (`gpu_process_guard.sh`, rag-stability harness, health endpoints) instead of scattered docs.

**Rationale:** Lowers mean time to diagnose routing/GPU/embed issues repeatedly touched in STATE and lessons.

**Downsides:** Risk of duplicating docs unless it links out; must stay maintained when ports/scripts change.

**Confidence:** 70%

**Complexity:** Low–Medium

**Status:** Unexplored

---

### 5. Lessons-to-guards pipeline (encode top lessons as tests or static checks)

**Description:** For the highest-frequency lesson classes (payload `text`, temperature, prompt hash, margin helpers, ticker ordering), add or extend targeted tests and small lint/check scripts so new code cannot reintroduce the same bug without failing CI.

**Rationale:** `lessons.md` is already the spec; automation compounds its value and reduces reliance on human memory.

**Downsides:** Diminishing returns if over-applied; some checks need AST/context and are awkward in ruff alone.

**Confidence:** 72%

**Complexity:** Medium

**Status:** Unexplored

---

### 6. Contributor map for agent/skill duplication (.claude / .codex / .cursor)

**Description:** Publish a single index: which skills are authoritative for this repo, which are legacy/experimental, and when to use Codex vs Claude vs Cursor paths. Optionally trim or symlink obvious duplicates after review.

**Rationale:** Reduces wrong-skill selection and conflicting guidance; speeds onboarding for multi-harness workflows mentioned in AGENTS.md.

**Downsides:** Political/maintenance overhead; plugins may reintroduce drift without hook updates.

**Confidence:** 68%

**Complexity:** Low–Medium

**Status:** Unexplored

---

### 7. Finish extraction-hardening FX and fixture diversity (complements #1 and #3)

**Description:** Implement FX conversion where the contract requires consistent reporting currency; expand fixtures beyond the current set toward more sectors and report formats called out in CLAUDE.md (4D/4E/5B, full IFRS), tied to eval thresholds.

**Rationale:** Directly addresses STATE open items and “don’t overfit to six fixtures” guidance.

**Downsides:** Needs clear business rules for FX sources and failure modes; more fixtures increase CI time.

**Confidence:** 74%

**Complexity:** Medium–High

**Status:** Unexplored

---

## Rejection Summary

| # | Idea | Reason rejected |
|---|------|-----------------|
| 1 | “Rewrite backend in another language” | Far too expensive; violates minimal-change norm; no grounding in current pain. |
| 2 | “Generic AI assistant for all investing” | Product vague; not grounded in repo scope. |
| 3 | “Replace Postgres with X” | No evidenced pain; schema migrations are explicitly high-friction per project rules. |
| 4 | “Merge every long-lived branch immediately” | Process advice without repo-specific merge plan; risk of bundling unrelated work. |
| 5 | “Add a second parallel extraction pipeline for experiments” | Conflicts with SYSTEM_CONTRACT single canonical pipeline / no shadow implementations. |
| 6 | “Microservices split for each analysis module” | Over-engineering relative to current scale and ops surface. |
| 7 | “Buy a hosted vector DB and drop Qdrant” | High migration cost; not motivated by cited STATE issues. |
| 8 | “More dashboards without linking to existing health/RAG scripts” | Duplicates docs; lower leverage than unified observability (#4). |
| 9 | “Automate all of OpenClaw ops” | STATE defers OpenClaw skill; low active priority unless OpenClaw returns. |
| 10 | “100% extraction accuracy guarantee” | Not actionable; conflates goal with mechanism. |

---

## Session Log

- 2026-04-11: Initial ideation — focus “entire project”; ~28 internal candidates after multi-frame generation and dedupe; 7 survivors ranked; `docs/solutions/` absent; issue intelligence skipped; artifact written.
- 2026-04-11: Two read-only explore subagents ran independently on synthesized combinations — **A (#1+#3+#7)** extraction backbone + real-gold gate + FX/fixtures; **B (#2+#4)** Cockpit contract + operator observability. Orchestrator review recorded in chat; both programs cite `SYSTEM_CONTRACT.md` and concrete repo paths.

---

## Synthesized combinations (orchestrator)

- **#1 + #3 + #7:** Treat “extraction redesign delivery” as the backbone, with expanded fixtures and scheduled real-gold as the proof loop — one program of work with three milestones rather than three disconnected initiatives.
- **#2 + #4:** Cockpit contract clarity plus operator observability reduces time lost to “which surface / which process owns GPU and streaming.”
