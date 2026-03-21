# Introduction Plan

Staged rollout for introducing missing capabilities identified in `gap-analysis.md`.

As of 2026-03-20. All stages are additive and reversible.

---

## Stage 1 — Zero-Risk Documentation Normalization

**Objective:** Surface existing knowledge in Claude-readable form. No code changes. No automation.

**Status:** Complete (executed as part of 2026-03-20 migration)

### Changes Made
- Created `CLAUDE.md` at repo root — top-level operating instructions
- Created `docs/claude/README.md` — index
- Created `docs/claude/project-overview.md` — system overview
- Created `docs/claude/current-state.md` — active runtime status
- Created `docs/claude/safety.md` — consolidated safety constraints
- Created `docs/claude/runbook.md` — consolidated operational runbook
- Created `docs/claude/decisions.md` — key decisions table
- Created `docs/claude/architecture/system-map.md` — component map
- Created `docs/claude/architecture/data-flow.md` — pipeline and query flows
- Created `docs/claude/skills/debugging.md`
- Created `docs/claude/skills/performance.md`
- Created `docs/claude/skills/implementation-discipline.md`
- Created `docs/claude/skills/domain-financial-pipeline.md`
- Created `docs/claude/tasks/README.md` — task template and process
- Created `docs/claude/gap-analysis.md`
- Created `docs/claude/introduction-plan.md` (this file)

### Validation
- `bash scripts/check_markdown_hygiene.sh` — confirm no broken links introduced
- Spot-check: CLAUDE.md loads and cross-links resolve

### Risk Level: Zero
- No source files modified
- No code changed
- All new files are documentation only
- Rollback: delete `CLAUDE.md` and `docs/claude/`

---

## Stage 2 — Lightweight Process Additions

**Objective:** Fill partial gaps with minimal, targeted doc additions. Still no executable automation.

**Risk Level: Very Low** — documentation only

### 2a — Failure Model Summary
**Status: Complete** — `10_failure_model.md` read in full; fail-fast/retry/skip matrix added to `docs/claude/runbook.md`.

### 2b — Vector Baseline Threshold Documentation
**Status: Complete** — `validate_financial_metrics_gates.py` read; gate conditions confirmed (zero duplicates, zero conflicts, zero empty_currency); documented in `domain-financial-pipeline.md`.

### 2c — Domain Skill: OpenClaw / llama.cpp Ops
**Status: Deferred** — OpenClaw is no longer an active workflow. Skip unless it re-enters use.

### 2d — Domain Skill: News Substrate
**Status: Complete** — `docs/claude/skills/domain-news-substrate.md` created from `15_news_substrate.md`.

### 2e — Domain Skill: Model Routing
**Status: Complete** — `docs/claude/skills/domain-model-routing.md` created from `model-routing.md`.

### 2f — `commentary_chunks_v2` Fallback Policy
**Status: Complete** — Confirmed from `rag.py`: collection is config-driven via `settings.qdrant_collection`, not automatic code fallback. Documented in `domain-financial-pipeline.md`.

---

## Stage 3 — Optional Enforcement Hooks / Automation

**Objective:** Add lightweight executable enforcement where a clear existing pattern exists. Zero new infrastructure.

**Risk Level: Low–Medium** — requires testing before enabling

### 3a — Markdown Hygiene in Pre-Push
**Status: Complete** — `check_markdown_hygiene.sh` runs as part of `.git/hooks/pre-push`.

### 3b — Ruff and Pytest Enforcement
**Status: Complete** — `.git/hooks/pre-commit` (ruff on staged files), `.git/hooks/pre-push` (ruff + pytest fast subset).

### 3c — Claude Code Session Hooks
**Status: Complete** — `.claude/settings.json` implements:
- `SessionStart`: branch + git status context
- `PostToolUse` / `Write|Edit`: ruff --fix on Python files; chmod +x on shell scripts
- `Stop`: git diff --stat summary

### 3d — CI Gate for Tests
**Gap:** No `.github/workflows/` found. Pre-push hook covers fast gates locally.

- Add `.github/workflows/ci.yml` only if GitHub Actions is adopted.
- Scope: ruff + pytest on `autodev/tests`, `financial-engine_v2/backend/tests`, `scripts`.
- Do not include canonical dataset checks in CI (require fixtures not in repo).
- Rollback: delete workflow file.

---

## Deferral Log

| Item | Reason Deferred |
|------|----------------|
| Scrapling integration status | Requires reading `docs/ops/scrapling_integration_note.md` in detail; low priority |
| Recovery/reconstruction manifest status | Requires reading the manifest; low priority |
| Codex skills registry sync | Operational, not documentation; run manually when needed |
| Pre-commit hook automation | Requires confirming team tooling; Stage 3 only |
| CI workflow | Requires confirming GitHub Actions setup; Stage 3 only |
