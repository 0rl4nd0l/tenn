# AGENTS.md instructions for /home/l4nd0/tenn

<INSTRUCTIONS>
## Skills
A skill is a set of local instructions to follow that is stored in a `SKILL.md` file. Below is the list of skills that can be used. Each entry includes a name, description, and file path so you can open the source for full instructions when using a specific skill.
### Available skills
- architecture-check: Validate proposed backend, RAG, vector store, and embedding changes against mandatory architecture rules before implementation. Use for architecture compliance checks or before editing sensitive retrieval surfaces. (file: /home/l4nd0/tenn/.codex/skills/architecture-check/SKILL.md)
- architecture-cleanup-steward: Audit unused architecture, stale docs, or dead components and apply conservative cleanup while enforcing .cursor rule files. Use for architecture reduction, doc sync, or cleanup reviews. (file: /home/l4nd0/tenn/.codex/skills/architecture-cleanup-steward/SKILL.md)
- code-fixer: Apply findings from code-reviewer or function-quality with minimal targeted edits, fixing critical issues first and adding tests when required. (file: /home/l4nd0/tenn/.codex/skills/code-fixer/SKILL.md)
- code-reviewer: Review the current git diff or modified files for bugs, risks, regressions, maintainability issues, and missing tests. Use when the user asks for a review or wants findings before fixing code. (file: /home/l4nd0/tenn/.codex/skills/code-reviewer/SKILL.md)
- embedding-change-checklist: Verify RAG and embedding invariants before merging changes to embeddings.py, EMBED_MODEL config, Alembic versions, or vector collection settings. (file: /home/l4nd0/tenn/.codex/skills/embedding-change-checklist/SKILL.md)
- function-quality: Perform a deep read-only feature analysis across code, tests, config, and docs, then return structured findings compatible with code-fixer. Use for named feature audits or completeness reviews. (file: /home/l4nd0/tenn/.codex/skills/function-quality/SKILL.md)
- ingest-ticker: Run full history ticker sync for one or more ASX tickers with argument validation, venv setup, and prerequisite checks. Use when the user asks to ingest one or more ASX tickers. (file: /home/l4nd0/tenn/.codex/skills/ingest-ticker/SKILL.md)
- intelligence-pack-review: Analyze the latest reports/weekly JSON intelligence pack and produce a four-section executive brief without modifying any data stores. (file: /home/l4nd0/tenn/.codex/skills/intelligence-pack-review/SKILL.md)
- investigation-orchestrator: Rigorous investigation and redesign workflow for larger or more difficult fixes, debugging, diagnosis, refactors, and system improvements. Use when the task is complex, cross-file, high-risk, or the root cause is unclear and needs structured exploration before implementation. (file: /home/l4nd0/tenn/.codex/skills/investigation-orchestrator/SKILL.md)
- migration-reviewer: Review Alembic migrations against SQLAlchemy model changes for completeness, safety, downgrade coverage, and chain integrity. (file: /home/l4nd0/tenn/.codex/skills/migration-reviewer/SKILL.md)
- performance-check: Perform a read-only performance health check for embeddings, retrieval, request latency, and optional GPU status using logs and gpu_runtime_status.py. (file: /home/l4nd0/tenn/.codex/skills/performance-check/SKILL.md)
- prompt-crafter: Turn a task outline into structured SYSTEM/CONTEXT/TASK/INPUTS/REQUIREMENTS/OUTPUT FORMAT/VALIDATION prompts, optionally as EXTRACT/ANALYZE/IMPLEMENT or a ready-to-use agent markdown file. (file: /home/l4nd0/tenn/.codex/skills/prompt-crafter/SKILL.md)
- prompt-structure-reference: Reference the structured prompt schema and chaining pattern used in this repo. Use when creating or validating prompts, agents, or staged EXTRACT/ANALYZE/IMPLEMENT workflows. (file: /home/l4nd0/tenn/.codex/skills/prompt-structure-reference/SKILL.md)
- rag-stability-eval: Run the RAG stability harness, parse the latest summary, and report STABLE, MINOR DRIFT, or MAJOR DRIFT without modifying Qdrant or the database. (file: /home/l4nd0/tenn/.codex/skills/rag-stability-eval/SKILL.md)
- repository-audit: Runs the repository audit workflow for this repo. Use when the user asks for a repository audit, branch inventory or reduction analysis, environment preflight before validation, or an evidence-based completeness review. (file: /home/l4nd0/tenn/.codex/skills/repository-audit/SKILL.md)
- textual-developer: Specialized guidance for building and debugging Textual (Python TUI) applications within the Tenn/Cockpit architecture. Use when modifying the Cockpit UI or TUI-related screens. (file: /home/l4nd0/tenn/.codex/skills/textual-developer/SKILL.md)
- vanilla-web-steward: Guidance for building "Framework-less" (Vanilla HTML/JS/CSS) dashboards for OpenClaw/Tenn. Use when modifying dashboards or building new web UIs without a heavy framework. (file: /home/l4nd0/tenn/.codex/skills/vanilla-web-steward/SKILL.md)
- skill-creator: Guide for creating effective skills. This skill should be used when users want to create a new skill (or update an existing skill) that extends Codex's capabilities with specialized knowledge, workflows, or tool integrations. (file: /home/l4nd0/snap/codex/34/skills/.system/skill-creator/SKILL.md)
- skill-installer: Install Codex skills into $CODEX_HOME/skills from a curated list or a GitHub repo path. Use when a user asks to list installable skills, install a curated skill, or install a skill from another repo (including private repos). (file: /home/l4nd0/snap/codex/34/skills/.system/skill-installer/SKILL.md)
### How to use skills
- Discovery: The list above is the skills available in this session (name + description + file path). Skill bodies live on disk at the listed paths.
- Trigger rules: If the user names a skill (with `$SkillName` or plain text) OR the task clearly matches a skill's description shown above, you must use that skill for that turn. Multiple mentions mean use them all. Do not carry skills across turns unless re-mentioned.
- Missing/blocked: If a named skill isn't in the list or the path can't be read, say so briefly and continue with the best fallback.
- How to use a skill (progressive disclosure):
  1) After deciding to use a skill, open its `SKILL.md`. Read only enough to follow the workflow.
  2) When `SKILL.md` references relative paths (e.g., `scripts/foo.py`), resolve them relative to the skill directory listed above first, and only consider other paths if needed.
  3) If `SKILL.md` points to extra folders such as `references/`, load only the specific files needed for the request; don't bulk-load everything.
  4) If `scripts/` exist, prefer running or patching them instead of retyping large code blocks.
  5) If `assets/` or templates exist, reuse them instead of recreating from scratch.
- Coordination and sequencing:
  - If multiple skills apply, choose the minimal set that covers the request and state the order you'll use them.
  - Announce which skill(s) you're using and why (one short line). If you skip an obvious skill, say why.
- User-facing responses:
  - Use the skill workflow and collect any required structured artifacts internally, but default to normal prose responses to the user.
  - Only return raw JSON or schema-shaped output when the user explicitly asks for it or when a downstream tool invocation requires it in-band.
- Context hygiene:
  - Keep context small: summarize long sections instead of pasting them; only load extra files when needed.
  - Avoid deep reference-chasing: prefer opening only files directly linked from `SKILL.md` unless you're blocked.
  - When variants exist (frameworks, providers, domains), pick only the relevant reference file(s) and note that choice.
- Safety and fallback: If a skill can't be applied cleanly (missing files, unclear instructions), state the issue, pick the next-best approach, and continue.
</INSTRUCTIONS>

---

# Project Context — Tenn / financial-engine_v2

**Shared operating rules:** Read [CLAUDE.md](CLAUDE.md) first — all rules there apply to Codex equally.

## SYSTEM CONTRACT ENFORCEMENT (MANDATORY)

**[docs/architecture/SYSTEM_CONTRACT.md](docs/architecture/SYSTEM_CONTRACT.md) is the authoritative system specification.**

Before any change, Codex agents MUST:
1. Read and comply with SYSTEM_CONTRACT.md
2. State the target system layer, relevant contract rules, what must NOT change, and why the change is safe
3. STOP immediately if any planned action conflicts with contract invariants
4. NOT introduce fallbacks, substitutions, parallel implementations, or approximations that violate the contract

## Parallel Agent Architecture

This repo uses two agent systems in parallel:
- **Claude Code** (primary) — claude-sonnet-4-6, skills in `.claude/skills/`
- **Codex** (this agent) — gpt-5.4, skills in `.codex/skills/`

They share the same codebase. To see Claude's current progress, decisions, and feedback:
- **Claude's memory index:** `/home/l4nd0/.claude/projects/-home-l4nd0-tenn/memory/MEMORY.md`
- **Codex's memory:** `~/.codex/memories/` (Codex reads and writes here)
- **Specs:** `docs/superpowers/specs/`
- **Plans:** `docs/superpowers/plans/`

**Before acting on any task:** Read Claude's memory index to avoid duplicating completed work.

## Current Sprint State (as of 2026-03-21)

| Item | Status | Location |
|------|--------|----------|
| Extraction redesign spec | ✅ Complete, reviewer-approved | `docs/superpowers/specs/2026-03-21-extraction-redesign.md` |
| Extraction redesign plan | ✅ Complete, reviewer-approved | `docs/superpowers/plans/2026-03-21-extraction-redesign.md` |
| Implementation (8 tasks) | 🔲 Not started | See plan |
| Guard E fix (cashflow layout modules) | 🔲 Blocked on `git merge main` | See project memory |
| Eval ground truth fixtures | 🔲 Not started | `backend/tests/eval_fixtures/` |

**Sprint goal:** Replace single-pass LLM extraction (PyMuPDF flat text → `build_prompt()` → `generate_json()`) with 4-pass docling multi-pass pipeline (`docling_extract.py` → `multipass_extraction.py` → `_upsert_financial_rows()`).

## Key File Locations

| Item | Path |
|------|------|
| Extraction spec | `docs/superpowers/specs/2026-03-21-extraction-redesign.md` |
| Extraction plan | `docs/superpowers/plans/2026-03-21-extraction-redesign.md` |
| Claude memory index | `/home/l4nd0/.claude/projects/-home-l4nd0-tenn/memory/MEMORY.md` |
| Capability guards | `financial-engine_v2/backend/tests/test_extraction_capability_guards.py` |
| Current extraction | `financial-engine_v2/backend/app/services/extraction.py` |
| Pipeline | `financial-engine_v2/backend/app/services/pipeline.py` |
| DB models | `financial-engine_v2/backend/app/models/asx_financials.py` |

## Canonical Entrypoint

```bash
export PATH="$PWD/financial-engine_v2/.venv/bin:$PATH"
LOCAL_BACKEND_PROFILE=isolated financial-engine_v2/scripts/run_local_backend.sh
curl -sS http://127.0.0.1:8000/api/health
```

## Milestone Commit Protocol (mandatory)

```
milestone(<subsystem>): <what works now>

Working: <confirmed-working behavior>
Tested: <how verified>
```

WIP: `wip(<subsystem>): <description>`. Never end a session with uncommitted state.
