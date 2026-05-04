# Project Agent Rules

Use this file as the authoritative Codex context for `financial-engine_v2` tasks.
Read [../CLAUDE.md](../CLAUDE.md) first — all rules there apply to Codex equally.

## Cross-Agent Coordination

This repo can use Gemini, Claude Code, Codex, and other agents in parallel. Before acting on any non-trivial task:
1. Read Claude's memory index: `/home/l4nd0/.claude/projects/-home-l4nd0-tenn/memory/MEMORY.md`
2. Read Codex memories: `~/.codex/memories/`
3. Check specs and plans in `docs/superpowers/specs/` and `docs/superpowers/plans/`

## MULTI-AGENT LIVE REPO CONTROL

For live-repo coordination, follow the canonical shared policy in [../AGENTS.md](../AGENTS.md#multi-agent-live-repo-control). Before implementation, declare lane, branch, worktree, execution mode, intended files, contested surfaces touched, collision risk, and decision. Treat HEAD drift as expected on live branches unless the task is fixed-baseline preservation, cleanup, checkpoint, reset, stash, branch restore, or reproducibility validation.

## Current Sprint (as of 2026-03-21)

**Active:** Extraction pipeline — 4-pass LLM extraction with PyMuPDF `find_tables()` as default PDF backend (docling available via `EXTRACTION_BACKEND=docling`).

| Item | Status | Location |
|------|--------|----------|
| Spec | ✅ Complete | `docs/superpowers/specs/2026-03-21-extraction-redesign.md` |
| Plan | ✅ Complete | `docs/superpowers/plans/2026-03-21-extraction-redesign.md` |
| Implementation (8 tasks) | 🔲 Not started | See plan |
| Guard E fix | 🔲 `git merge main` (commits 710fe968, af7f8e57) | |
| Eval fixtures | 🔲 Not started | `backend/tests/eval_fixtures/` |

## Operating Rules

- Keep edits scoped to the current task; avoid unrelated churn.
- Prefer existing code patterns and config shape in `financial-engine_v2`.
- Do not revert user changes unless explicitly asked.
- Avoid destructive git operations unless explicitly requested.
- Do not run tests unless explicitly requested.
- Preserve existing behavior unless the task is to change it.
- Do not read, echo, or log `.env` files or secrets.

## Milestone Commit Protocol (mandatory)

```
milestone(<subsystem>): <what works now>

Working: <confirmed-working behavior>
Tested: <how verified>
```

WIP state: `wip(<subsystem>): <description>`. Never end a session with uncommitted state.

## Key Files

| Item | Path |
|------|------|
| Capability guards | `backend/tests/test_extraction_capability_guards.py` |
| Current extraction | `backend/app/services/extraction.py` |
| Pipeline | `backend/app/services/pipeline.py` |
| DB models | `backend/app/models/asx_financials.py` |
| Model routing config | `backend/app/config/model_routing.yaml` |

## Canonical Entrypoint

```bash
export PATH="$PWD/.venv/bin:$PATH"
LOCAL_BACKEND_PROFILE=isolated ./scripts/run_local_backend.sh
curl -sS http://127.0.0.1:8000/api/health
```

## Useful Local References

- `backend/app/config/model_routing.yaml`
- `backend/tests/test_model_routing.py`
- `docs/superpowers/specs/2026-03-21-extraction-redesign.md`
- `docs/superpowers/plans/2026-03-21-extraction-redesign.md`

## Runtime and Model

- Model: `gpt-5.4` at `xhigh` reasoning effort
- Use concise, direct outputs and avoid speculative changes
- Prioritize actionable steps and concrete file changes over broad prose
