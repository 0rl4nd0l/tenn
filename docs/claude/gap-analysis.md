# Gap Analysis

As of 2026-03-20 audit. Source: deep inventory of `/home/l4nd0/tenn`.

## Source Trace
- Full repository audit (2026-03-20)
- All files listed in `docs/claude/README.md` Source Trace section

---

## Capability Status Table

| Capability | Status | Evidence | Recommended Action | Priority |
|------------|--------|----------|--------------------|----------|
| Explicit Claude operating instructions (CLAUDE.md) | **Present** | Created at repo root (this migration) | — | — |
| Project overview | **Present** | `docs/claude/project-overview.md` + `docs/architecture/01_system_overview.md` | — | — |
| Current state snapshot | **Present** | `docs/claude/current-state.md` + `docs/current_system.md` | Refresh snapshot when system profile changes | Low |
| Safety constraints | **Present** | `docs/claude/safety.md` + `docs/architecture/13_security_and_secrets.md` | — | — |
| Runbook | **Present** | `docs/claude/runbook.md` + `docs/ops/` (30+ docs) | — | — |
| Decisions/ADR summary | **Present** | `docs/claude/decisions.md` | Formalize remaining inferred decisions (see below) | Low |
| System map | **Present** | `docs/claude/architecture/system-map.md` | — | — |
| Data flow map | **Present** | `docs/claude/architecture/data-flow.md` | — | — |
| Task template/process | **Present** | `docs/claude/tasks/README.md` | — | — |
| Debugging skill | **Present** | `docs/claude/skills/debugging.md` | — | — |
| Performance skill | **Present** | `docs/claude/skills/performance.md` | — | — |
| Implementation discipline skill | **Present** | `docs/claude/skills/implementation-discipline.md` | — | — |
| Domain-specific skill (financial pipeline) | **Present** | `docs/claude/skills/domain-financial-pipeline.md` | — | — |
| Pre-task checks | **Present** | CLAUDE.md + implementation-discipline.md | — | — |
| Pre-write checks | **Present** | CLAUDE.md + implementation-discipline.md | — | — |
| Post-write checks | **Present** | CLAUDE.md + validation_baseline.md | — | — |
| Safety-sensitive area protections | **Present** | `docs/claude/safety.md` | — | — |
| Large-diff gating guidance | **Present** | CLAUDE.md (300 line / 5 file heuristic) | — | — |
| Prompt-injection / secret handling guidance | **Present** | CLAUDE.md + safety.md | — | — |
| Pre-commit hooks | **Present** | `.git/hooks/pre-commit` — ruff on staged Python files | — | — |
| Pre-push hooks | **Present** | `.git/hooks/pre-push` — ruff + pytest + markdown hygiene | — | — |
| Claude Code automation hooks | **Present** | `.claude/settings.json` — SessionStart context, PostToolUse ruff+chmod, Stop diff summary | — | — |
| MCP server configuration | **Present** | `.mcp.json` at repo root; launchers in `scripts/mcp/`; documented in `docs/claude/mcp-servers.md` | Activate GitHub (needs PAT) and Tenn (needs `.venv-autodev`) servers | Medium |
| Automated lint enforcement (CI) | **Partial** | `ruff.toml` + `pytest.ini` exist; no `.github/workflows/` found; pre-push hook covers fast gates | Add CI if GitHub Actions is adopted | Low |
| Explicit failure model doc (Claude-readable) | **Present** | `docs/architecture/10_failure_model.md` read and summarized in `docs/claude/runbook.md` (Failure Model section) | — | — |
| Vector baseline comparison thresholds | **Present** | Gate conditions confirmed from `scripts/validate_financial_metrics_gates.py`: zero duplicates, zero conflicts, zero empty_currency; documented in `domain-financial-pipeline.md` | — | — |
| `commentary_chunks_v2` fallback policy | **Present** | Confirmed: collection is config-driven via `settings.qdrant_collection`; not automatic code fallback; documented in `domain-financial-pipeline.md` | — | — |
| Retry/backoff policy for LLM failures | **Present** | Confirmed from `10_failure_model.md`: fail-fast at startup, retry at request/task time, skip per-item in batch; documented in `runbook.md` | — | — |
| Codex skills registry integration | **Present** | Repo-local Codex skill ports exist under `.codex/skills/`, including `investigation-orchestrator`; `bash scripts/sync_codex_skills.sh` links them into `$CODEX_HOME/skills/` | Re-run sync after adding or updating repo-local skills | Low |
| Domain skill: news substrate | **Present** | Created `docs/claude/skills/domain-news-substrate.md` from `15_news_substrate.md` | — | — |
| Domain skill: model routing | **Present** | Created `docs/claude/skills/domain-model-routing.md` from `model-routing.md` | — | — |
| Domain skill: OpenClaw/llama.cpp ops | **Deferred** | OpenClaw no longer primary workflow; not prioritized | Defer indefinitely unless OpenClaw re-enters active use | Low |
| System analyzer loop (Claude-readable) | **Partial** | `docs/ops/system_analyzer_loop.md` exists | Link from runbook; consider extracting key checks | Low |
| Explicit agent contract in CLAUDE.md | **Present** | `agent_contract.json` + CLAUDE.md reference it | — | — |

---

## Inferred Decisions Not Yet Formalized

These are observed in code/docs but not written as explicit decisions:

1. **Retry/backoff specifics** — failure model exists (`10_failure_model.md`) but details not confirmed
2. **Vector baseline thresholds** — gate scripts define them; not surfaced in readable docs
3. **`commentary_chunks_v2` triggering conditions** — when exactly does fallback activate?
4. **Scrapling integration status** — `docs/ops/scrapling_integration_note.md` exists; integration state unknown
5. **Recovery/reconstruction integration state** — `docs/ops/recovery_reconstruction_integration_manifest.md` exists; status unknown

---

## Not Missing (Excluded Intentionally)

| Item | Reason Not Needed |
|------|------------------|
| Robotics/actuator safety constraints | No robotics runtime in this repo |
| CLAUDE.md for llama.cpp subdir | Already exists at `tools/llama.cpp/CLAUDE.md` (minimal, references AGENTS.md) |
| DB schema migration guidance in Claude docs | Covered by safety prohibition + Alembic docs |
