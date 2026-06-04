# Claude Code Commands

Custom slash commands available in this repo via `.claude/commands/`. Invoke with `/command-name`.

Most commands now have matching repo-local Codex skill ports under `.codex/skills/`, synced into the active Codex registry with `bash scripts/sync_codex_skills.sh`.

## Source Trace
- `.codex/skills/*/SKILL.md` (Confirmed — repo-local Codex skill ports)
- `.claude/commands/*.md` (Confirmed — created 2026-03-20)

---

## Command Reference

### Slash Commands (`.claude/commands/`)

| Command | Invoke | Purpose |
|---------|--------|---------|
| Architecture Check | `/architecture-check` | Validates proposed changes against mandatory architecture invariants. Analysis only; refuses VIOLATES RULE changes. |
| Architecture Cleanup | `/architecture-cleanup` | Audits and prunes unused architecture; syncs docs with reality; enforces `docs/architecture/SYSTEM_CONTRACT.md`. |
| Code Review | `/code-review` | Runs `git diff` and reviews for quality, security, maintainability. Outputs critical/warnings/suggestions with fix examples. |
| Code Fix | `/code-fix` | Applies findings from `/code-review` or `/function-quality`. Critical first, then warnings, then suggestions. |
| Function Quality | `/function-quality` | Deep feature analysis (EXTRACT → ANALYZE). Pass a feature name; output is `/code-fix`-compatible. |
| Intelligence Pack | `/intelligence-pack` | Analyzes latest `reports/weekly/*.json`; produces 4-section executive brief. Read-only. |
| Investigation Orchestrator | `/investigation-orchestrator` | Structured investigation workflow for larger or harder bugs, diagnoses, refactors, and redesigns. Maps code first, writes a spec, then implements. |
| Performance Check | `/performance-check` | Checks GPU memory, embedding throughput, batch efficiency, and search latency. Read-only diagnostics. |
| Prompt Crafter | `/prompt-crafter` | Turns a task outline into structured EXTRACT/ANALYZE/IMPLEMENT prompts; can create `.cursor/agents/` files. |
| Prompt Structure | `/prompt-structure` | Reference for the structured prompt schema and chaining patterns used across agents. |
| RAG Stability | `/rag-stability` | Runs `evaluate_rag_stability.py`, interprets drift metrics, outputs STABLE/MINOR DRIFT/MAJOR DRIFT report. |
| Repo Audit | `/repo-audit` | Full repository audit: preflight, branch inventory, docs completeness, CONFIRMED/INFERRED/UNVERIFIED claims. |
| Ingest Ticker | `/ingest-ticker <TICKER>` | Runs `full_history_ticker_sync.py` for one or more ASX tickers. Validates args, activates venv, reports per-ticker result. |
| Save | `/save` | Exports the current Claude session as a copyable text block; falls back to Cockpit's latest `reports/cockpit/exports/claude_context.json` when the live transcript is unavailable. |

### Skills (`.claude/skills/`)

These are invoked by Claude automatically (not user-facing slash commands).

| Skill | Invocation | Purpose |
|-------|-----------|---------|
| `embedding-change-checklist` | Claude-only | Runs the 5-step RAG/embedding safety checklist before any PR touching `embeddings.py`, `config.py` (EMBED_MODEL), or `alembic/versions/`. |
| `investigation-orchestrator` | Claude-only and Codex ported | Process skill for larger or harder investigations and redesigns that require mapping, spec-before-edit discipline, and evidence-based implementation. |

---

## Typical Workflows

**Review and fix code:**
```
/code-review  →  /code-fix
```

**Deep feature analysis then fix:**
```
/function-quality  →  /code-fix
```

**Investigate before fixing a non-trivial issue:**
```
/investigation-orchestrator
```

**Check system health:**
```
/performance-check
/rag-stability
```

**Before touching embeddings/RAG/vector store:**
```
/architecture-check
```

**Create a new agent or prompt:**
```
/prompt-crafter
```

---

### Subagents (`.claude/agents/`)

Subagents are invoked by Claude during complex tasks requiring specialized review.

| Agent | File | Purpose |
|-------|------|---------|
| `migration-reviewer` | `.claude/agents/migration-reviewer.md` | Reviews Alembic migration files when SQLAlchemy models change. Checks upgrade/downgrade completeness, flags destructive ops, verifies chain integrity. |

---

## Skill Parity Table

| Codex Skill | Claude Command | Status |
|-------------|---------------|--------|
| `architecture-check` | `/architecture-check` | Ported |
| `architecture-cleanup-steward` | `/architecture-cleanup` | Ported |
| `code-reviewer` | `/code-review` | Ported |
| `code-fixer` | `/code-fix` | Ported |
| `function-quality` | `/function-quality` | Ported |
| `intelligence-pack-review` | `/intelligence-pack` | Ported |
| `investigation-orchestrator` | `/investigation-orchestrator` | Ported |
| `performance-check` | `/performance-check` | Ported |
| `prompt-crafter` | `/prompt-crafter` | Ported |
| `prompt-structure-reference` | `/prompt-structure` | Ported |
| `rag-stability-eval` | `/rag-stability` | Ported |
| `repository-audit` | `/repo-audit` | Ported |
| `ingest-ticker` | `/ingest-ticker` | New (repo-native) |
| `embedding-change-checklist` | Claude-invocable skill | New (repo-native) |
| `migration-reviewer` | Claude subagent | New (repo-native) |
| `news-pipeline-remaining-fixes` | — | Not ported (one-time fix, not a general skill) |

Repo-local Codex ports now present for:

- `architecture-check`
- `architecture-cleanup-steward`
- `code-reviewer`
- `code-fixer`
- `function-quality`
- `intelligence-pack-review`
- `investigation-orchestrator`
- `performance-check`
- `prompt-crafter`
- `prompt-structure-reference`
- `rag-stability-eval`
- `repository-audit`
- `ingest-ticker`
- `embedding-change-checklist`
- `migration-reviewer`

---

## Notes for Agents

- Commands are defined in `.claude/commands/*.md` — edit those files to update behavior.
- `/code-fix` expects input structured as `{critical: [], warnings: [], suggestions: []}` with `file`, `location`, `issue`, `fix_example` per item — exactly what `/code-review` and `/function-quality` produce.
- `/rag-stability` and `/performance-check` are **read-only** — they never modify Qdrant, the database, or config.
- `/architecture-check` will **refuse** implementation if a VIOLATES RULE finding exists — this is intentional.
