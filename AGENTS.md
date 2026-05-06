# AGENTS.md instructions for /home/l4nd0/tenn
<!-- Last updated: 2026-05-04 -->

> **Note for Claude Code:** The skills listed in this file use `.codex/skills/` paths that are only accessible to the Codex agent. If you are Claude Code, ignore the skills block and use your own skills in `.claude/skills/` instead. All other repo context below applies to both agents equally.

<INSTRUCTIONS>
## Skills (Codex-only — paths under `.codex/skills/`)
A skill is a set of local instructions to follow that is stored in a `SKILL.md` file. Below is the list of skills that can be used. Each entry includes a name, description, and file path so you can open the source for full instructions when using a specific skill.
### Available skills
- architecture-check: Validate proposed backend, RAG, vector store, and embedding changes against mandatory architecture rules before implementation. Use for architecture compliance checks or before editing sensitive retrieval surfaces. (file: /home/l4nd0/tenn/.codex/skills/architecture-check/SKILL.md)
- architecture-cleanup-steward: Audit unused architecture, stale docs, or dead components and apply conservative cleanup while enforcing .cursor rule files. Use for architecture reduction, doc sync, or cleanup reviews. (file: /home/l4nd0/tenn/.codex/skills/architecture-cleanup-steward/SKILL.md)
- code-fixer: Apply findings from code-reviewer or function-quality with minimal targeted edits, fixing critical issues first and adding tests when required. (file: /home/l4nd0/tenn/.codex/skills/code-fixer/SKILL.md)
- code-reviewer: Review the current git diff or modified files for bugs, risks, regressions, maintainability issues, and missing tests. Use when the user asks for a review or wants findings before fixing code. (file: /home/l4nd0/tenn/.codex/skills/code-reviewer/SKILL.md)
- cockpit-flag-orchestrator: Investigate and fix outstanding Cockpit feedback artifacts, including auto diagnostics, manually flagged chats, and captured UI screenshots. Use when Codex is asked to triage unresolved Cockpit flags, coordinate subagents to inspect evidence and debate fixes, implement the chosen fix, verify it, commit it, and resolve backend flag records. (file: /home/l4nd0/tenn/.codex/skills/cockpit-flag-orchestrator/SKILL.md)
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

## Truthfulness and Sources (MANDATORY)

For Tenn/Cockpit user-facing answers:
1. Every substantive factual claim must be grounded in current-turn evidence.
2. Prior session context is background only and must never be treated as proof.
3. If the current turn cannot surface supporting sources to the user, the answer must explicitly say it cannot verify the claim yet rather than stating it as fact.

## SYSTEM CONTRACT ENFORCEMENT (MANDATORY)

**[docs/architecture/SYSTEM_CONTRACT.md](docs/architecture/SYSTEM_CONTRACT.md) is the authoritative system specification.**

Before any change, Codex agents MUST:
1. Read and comply with SYSTEM_CONTRACT.md
2. State the target system layer, relevant contract rules, what must NOT change, and why the change is safe
3. STOP immediately if any planned action conflicts with contract invariants
4. NOT introduce fallbacks, substitutions, parallel implementations, or approximations that violate the contract

## Parallel Agent Architecture

This repo can use multiple agent systems in parallel:
- **Claude Code** (primary) — claude-sonnet-4-6, skills in `.claude/skills/`
- **Codex** — skills in `.codex/skills/`
- **Gemini CLI** — agent-specific rules in `GEMINI.md`

They share the same codebase. To see Claude's current progress, decisions, and feedback:
- **Claude's memory index:** `/home/l4nd0/.claude/projects/-mnt-sdb2-home-l4nd0-tenn/memory/MEMORY.md`
- **Codex's memory:** `~/.codex/memories/` (Codex reads and writes here)
- **Specs:** `docs/superpowers/specs/`
- **Plans:** `docs/superpowers/plans/`

**Before acting on any task:** Read Claude's memory index to avoid duplicating completed work.

## MULTI-AGENT LIVE REPO CONTROL

Tenn is in hardening/consolidation mode. The shared repo branch may be LIVE, with Gemini, Codex, Claude, or other agent sessions actively editing the repo at the same time. Other agent sessions working on the same repo is expected and allowed.

### 1. Live Repo Rule

- The shared branch may be LIVE.
- Do not treat HEAD drift as inherently bad.
- HEAD drift is expected when the branch is live.
- A fixed HEAD is only required when a task explicitly says it is doing preservation, cleanup, checkpointing, reset, stash, branch restore, or reproducibility validation.
- Do not repeat frozen-HEAD audits endlessly when the branch is intentionally live.

### 2. Session Declaration Rule

Every agent session must declare before implementation:

- agent name: Gemini / Codex / Claude / other
- branch
- worktree path
- lane
- execution mode
- files intended to touch
- files actually touched, in final report
- whether it touches contested surfaces
- collision risk: LOW / MEDIUM / HIGH

### 3. Lane Model

Every task must be classified into exactly one lane:

- Financial Truth — extraction, metric truth, parser/runtime extraction logic, normalization, canonical financial facts
- Evaluation — tests, scorecards, audits, browser regression, eval scripts, failure analysis, benchmark artifacts
- Provenance — evidence traceability, source attribution, citation/evidence chains, source maps, provenance validators
- Query Orchestration — routing, chat control path, agent loop, tool selection, answer composition, continuity, intent handling
- Memory — company memory, market memory, user thesis memory, preference memory, memory signal routing, thesis watchdog
- Reporting — Next.js Cockpit UI, analyst shell, source drawer, route parity UI, marketplace UI, docs/report output surfaces

### 4. Execution Modes

- AUDIT MODE: inspect, map, report; no modifications
- SAFE EXTENSION MODE: minimal additive edits to existing systems only
- BLOCKED MODE: no implementation; output blockers and next safe step only

### 5. Collision Rules

- LOW: isolated docs/tests/reports or non-overlapping lane files
- MEDIUM: additive work in existing subsystem but touches active product files
- HIGH: touches shared runtime/control paths, memory writes, financial truth, source/evidence labels, or files already owned by another active session

Hard stop:

- If HIGH overlap risk remains unresolved, do not implement.
- Output report only.

### 6. Contested Surfaces

Treat this list as collision-critical:

- `financial-engine_v2/backend/app/routes/cockpit_api.py`
- `financial-engine_v2/cockpit/core/tool_definitions.py`
- `financial-engine_v2/cockpit/core/chat.py`
- `financial-engine_v2/cockpit/core/agent_loop.py`
- `financial-engine_v2/cockpit/core/command_router.py`
- `financial-engine_v2/cockpit/core/turn_continuity.py`
- `financial-engine_v2/cockpit/core/response_classification.py`
- `financial-engine_v2/backend/app/services/tenn_chat.py`
- `financial-engine_v2/backend/app/services/cockpit_service.py`
- `financial-engine_v2/backend/app/services/query_orchestrator.py`
- `financial-engine_v2/backend/app/services/company_memory.py`
- `financial-engine_v2/backend/app/services/market_memory.py`
- `financial-engine_v2/backend/app/services/memory_signal_router.py`
- `financial-engine_v2/backend/app/services/user_thesis_memory.py`
- `financial-engine_v2/backend/app/services/thesis_watchdog.py`
- `cockpit-ui/lib/api-client.ts`
- `cockpit-ui/lib/cockpit-types.ts`
- `cockpit-ui/components/cockpit/chat/`
- `cockpit-ui/components/cockpit/holdings/`
- `cockpit-ui/components/cockpit/watchlist/`
- `cockpit-ui/components/cockpit/thesis/`
- `cockpit-ui/components/cockpit/marketplace/`

### 7. Shared Branch Rule

- Do not edit a shared live branch unless the task explicitly assigns that branch/session ownership.
- Product implementation should use an isolated branch/worktree when other agents are active.
- Do not run cleanup, stash, reset, preservation, branch restore, or checkpoint prompts on a shared live branch.
- If cleanup/checkpoint is required, first require a user-approved freeze or a dedicated checkpoint branch.
- If another session is actively modifying the same files, classify as HIGH risk and stop.

### 8. Fixed-HEAD Rule

- Do not keep rerunning fixed-HEAD audits against a branch that is intentionally live.
- If a prompt expects HEAD X but HEAD has moved:
  - for preservation/checkpoint/restore tasks: stop and report drift
  - for ordinary implementation tasks: treat the branch as live, re-scope to isolated worktree/branch, and continue only if collision risk is LOW/MEDIUM
- Never "update the expected HEAD" silently.

### 9. Frontend Boundary

- Cockpit frontend/product work targets the Next.js web UI under `cockpit-ui/`.
- Do not implement new frontend behavior in `financial-engine_v2/cockpit/ui/app.py` or local TUI unless explicitly requested.
- Treat local TUI changes as non-target work by default.

### 10. Memory and Financial Truth Boundaries

- Heavy, mutating, or long-running jobs and memory writes require confirmation gates.
- Financial truth must remain deterministic, auditable, and provenance-bound.
- Do not store route/user intent aliases in `user_thesis_memory.py`.
- User thesis memory is for confirmation-gated investment thesis/evidence notes.
- Preference memory must be separate from company memory, market memory, user thesis memory, and financial truth.
- Do not let LLM outputs define canonical numbers or conflate narrative/reporting claims with canonical financial metrics.

### 11. Source/Evidence Label Safety

- Never label an answer source-backed using irrelevant no-row or wrong-tool evidence.
- Holdings/personal portfolio answers must not be backed by TradingView screener or `screen_tickers` no-row evidence.
- If evidence is missing or irrelevant, label as DATA_MISSING / unsupported rather than source-backed.
- Web/search context is source discovery, not canonical financial truth.
- Feedback/flags are review/evaluation artifacts, not truth or automatic training data.

### 12. Subagent Policy

- Subagents may be used only for parallel repo inspection, documentation gathering, or evidence collection.
- Do not use subagents to create competing Tenn architecture proposals.
- Do not assign subagents ownership of contested runtime surfaces.
- Parent agent must reconcile all subagent findings into one final report.
- If subagent findings conflict, resolve the conflict and explain which conclusion is accepted and why.

### 13. Required Preflight Template

Each implementation-capable agent prompt should begin its report with:

```text
Lane:
Branch:
Worktree:
Execution mode:
Intended files:
Contested surfaces touched:
Collision risk:
Decision:
- proceed
- audit only
- blocked
```

### 14. Required Final Report Template

Each implementation-capable agent should end with:

```text
Files changed:
Files inspected:
Lane:
Execution mode:
Collision risk:
Validation run:
Validation result:
Files intentionally not touched:
Remaining blockers:
Next safe step:
```

### 15. DATA_MISSING Rule

- If repo state, branch ownership, instruction surface, storage schema, or validation evidence is missing, write DATA_MISSING and list the exact missing evidence.
- Do not fabricate repo state, file paths, commits, validation results, or current agent ownership.

## Tenn Dev-Agent Task-Card Contract

This contract applies to Codex, Claude Code, Gemini, and any other implementation-capable dev agent working in this repo.

- Every implementation task must declare exactly one lane before work begins.
- When a task card is provided, validate it before implementation with `python scripts/agent_job_contract.py validate <task_card>`.
- Task cards must use `production_data_access: false`; dev-agent jobs must not request or use production data access.
- Before claiming work, inspect active jobs with `python scripts/agent_job_registry.py list-active`; before implementation on a task-card job, claim it with `python scripts/agent_job_registry.py claim <task_card>` so Codex/Claude sessions can see the lane/file lock.
- Before the final report for any task-card job, run `python scripts/agent_job_contract.py check-diff <task_card>` and resolve or report any blocked diff.
- Release completed or abandoned claims with `python scripts/agent_job_registry.py release <job_id>`.
- The shared registry root resolves by `TENN_AGENT_REGISTRY_ROOT`, then `git config tenn.agentRegistryRoot`, then `<git-common-dir>/tenn-agent-registry`, and only then repo-local `.tenn/agent_jobs` fallback with reduced visibility. Separate clones and Tenn web UI Codex launches must use the same env/config root to share active-job visibility.
- Stop on unresolved HIGH collision risk. Do not implement while HIGH overlap risk remains unresolved.
- Hook activation uses `TENN_AGENT_TASK_CARD=<path>` or `.tenn/active_agent_task` to identify the active task card. Exploratory sessions without either marker must not be blocked by the task-card hook.

## Current Sprint State

> **This section is a snapshot.** Always cross-reference `docs/claude/STATE.md` for current workstream status before acting.

Active workstreams as of 2026-04-14:

| Workstream | Status | Notes |
|------------|--------|-------|
| extraction-quality | `[ in-progress ]` | 88.64% excl. AZJ; MIN/TLS shares_outstanding open; Docling default |
| extraction-truth | `[ in-progress ]` | Backend real-gold eval + UI review session handoff shipped |
| cockpit-routing | `[ in-progress ]` | Shared-router mutex, API fallback, follow-up/intent routing |
| docs-governance | `[ in-progress ]` | Contract addendum shipped; conformance matrix ongoing |
| extraction-hardening | `[ in-progress ]` | FX conversion not yet built; AZJ unsolvable (threshold=0.0) |

Completed sprint goals (multipass extraction pipeline is **live** — Docling default, 4-pass LLM extraction, `multipass_extraction.py` → `_upsert_financial_rows()`). See `docs/claude/STATE.md` for full history.

## Key File Locations

| Item | Path |
|------|------|
| Extraction spec | `docs/superpowers/specs/2026-03-21-extraction-redesign.md` |
| Extraction plan | `docs/superpowers/plans/2026-03-21-extraction-redesign.md` |
| Claude memory index | `/home/l4nd0/.claude/projects/-mnt-sdb2-home-l4nd0-tenn/memory/MEMORY.md` |
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

## Flagged Report Resolution Protocol (mandatory, Claude + Codex)

If a task fixes a Cockpit flagged report (`report_id` under `/api/cockpit/feedback/flags/{report_id}`), the responsible agent MUST mark that report resolved after the fix commit lands.

Required resolution payload:
- `commit_sha`: fix commit hash
- `note`: exact commit subject line (first line of the fix commit message)

Required closeout command:

```bash
COMMIT_SHA="$(git rev-parse --short=12 HEAD)"
COMMIT_MSG="$(git log -1 --pretty=%s)"
curl -sS -X POST "http://127.0.0.1:8000/api/cockpit/feedback/flags/<REPORT_ID>/resolve" \
  -H "Content-Type: application/json" \
  -d "{\"commit_sha\":\"${COMMIT_SHA}\",\"resolved_by\":\"<claude|codex>\",\"note\":\"${COMMIT_MSG}\"}"
```

A flagged bug-fix is not complete until this call succeeds.

## graphify

This project has a graphify knowledge graph at graphify-out/.

Rules:
- Before answering architecture or codebase questions, read graphify-out/GRAPH_REPORT.md for god nodes and community structure
- If graphify-out/wiki/index.md exists, navigate it instead of reading raw files
- Do not run `graphify update .` after every milestone or code change
- Run `graphify update .` at most once per day, or when the user explicitly requests a graph refresh
