# Hooks

All automation hooks active in this repo. Agents should read this before triggering file writes, commits, or pushes.

## Source Trace
- `.claude/settings.json` (Confirmed)
- `.codex/config.toml` (Confirmed)
- `.codex/hooks.json` (Confirmed)
- `.git/hooks/pre-commit` (Confirmed)
- `.git/hooks/pre-push` (Confirmed)

---

## Claude Code Hooks (`.claude/settings.json`)

These fire automatically during Claude Code sessions.

| Event | Trigger | What It Does |
|-------|---------|--------------|
| `SessionStart` | Every session start | Prints current branch and `git status --short` (first 20 lines) |
| `PreToolUse` / `Edit\|Write` | Before editing any file | Warns if path is embedding-sensitive (`embeddings.py`, `alembic/versions/`) or secret-bearing (`.env`) |
| `PreToolUse` / `Glob\|Grep` | Before broad search tools | Emits a graphify reminder via `systemMessage` when `graphify-out/graph.json` exists |
| `PostToolUse` / `Write\|Edit` | After Claude writes/edits a `.py` file | Runs `ruff check --fix` on the file; silent on non-Python files |
| `PostToolUse` / `Write\|Edit` | After Claude writes/edits a `.sh` file | Runs `chmod +x` on the file |
| `PostToolUse` / `Write\|Edit` | After Claude edits a file under `backend/app/` | Runs `pytest backend/tests/ -x -q --tb=short`; silent if venv not found |
| `Stop` | When Claude finishes a task | Runs `scripts/agent_job_hook.py` and enforces the Tenn task-card contract only when `TENN_AGENT_TASK_CARD` or `.tenn/active_agent_task` is set |
| `Stop` | When Claude finishes a task | Runs `git diff --stat HEAD` — shows all files changed since last commit |
| `Stop` | When Claude finishes a task | Checks if infrastructure/config files changed without corresponding `docs/claude/` updates — prints WARNING if so |

**Ruff binary / pytest binary:** `financial-engine_v2/.venv/bin/ruff` and `.../pytest`
Legacy hygiene hooks are non-blocking (`|| true`); they warn without interrupting Claude if they fail. The Tenn task-card hook is intentionally blocking when an active task card fails validation or `check-diff`.

**Note for agents:** The `SessionStart` and `Stop` hooks output context to the transcript. Use `Stop` output to verify what changed before concluding a task.

**Sensitive path warning:** The `PreToolUse` hook prints a `WARNING:` line but does not block the edit. Claude should read the warning and confirm scope before proceeding when it appears.

**Graphify reminder:** The `PreToolUse` search hook must emit a top-level `systemMessage`. Do not use `hookSpecificOutput.additionalContext` for this hook; recent Claude Code runtimes reject that field for `PreToolUse`.

**Doc coverage warning:** The doc-coverage `Stop` hook detects when infrastructure files (`.mcp.json`, `settings.json`, `scripts/mcp/`, `.claude/commands/`, etc.) were modified but no `docs/claude/` files were updated. This is a non-blocking JSON `systemMessage` warning — the agent must act on it before concluding the task. See CLAUDE.md "Post-Write Documentation" for the mapping of changed surfaces to required doc updates.

**Tenn task-card hook:** `scripts/agent_job_hook.py` reads hook stdin JSON, resolves the repo root, finds an active task card from `TENN_AGENT_TASK_CARD` or `.tenn/active_agent_task`, then runs `scripts/agent_job_contract.py validate` and `check-diff`. With no active task card it returns valid empty JSON and does not block exploratory sessions. With an active task card it emits valid JSON for pass or block results.

**Stop hook JSON:** Claude Stop hooks that produce output now emit JSON objects such as `{"systemMessage": "..."}`. The previous raw `git diff --stat` and plain text doc-coverage output were replaced to avoid invalid Stop hook JSON output.

---

## Codex Hooks (`.codex/config.toml`, `.codex/hooks.json`)

Repo-local Codex hooks are enabled with `codex_hooks = true`.

| Event | Trigger | What It Does |
|-------|---------|--------------|
| `PreToolUse` / `Bash` | Before shell commands | Emits a graphify reminder via `systemMessage` when `graphify-out/graph.json` exists |
| `Stop` | When Codex finishes a task | Runs `scripts/agent_job_hook.py` and enforces the Tenn task-card contract only when `TENN_AGENT_TASK_CARD` or `.tenn/active_agent_task` is set |

---

## Git Hooks

### `pre-commit` (`.git/hooks/pre-commit`)

Fires on every `git commit`. Blocks the commit if lint fails.

- Collects staged `.py` files only
- Runs `ruff check` (no auto-fix; fix manually then re-stage)
- Exits 0 (skip) if no Python files staged or ruff not found

**Fix a failed commit:**
```bash
financial-engine_v2/.venv/bin/ruff check --fix <file>
git add <file>
git commit
```

### `pre-push` (`.git/hooks/pre-push`)

Fires on every `git push`. Blocks the push if any gate fails.

Runs in order:
1. `ruff check autodev financial-engine_v2/backend scripts`
2. `pytest autodev/tests financial-engine_v2/backend/tests scripts -q --tb=short`
3. `bash scripts/check_markdown_hygiene.sh`

**Does NOT run:** canonical dataset checks, financial metrics gates, financial coverage gates — these require fixtures not always present. Run them manually before merge: see [runbook.md](runbook.md#full-validation-sequence-2026-03-19-baseline).

**Fix a failed push:**
```bash
# Lint
financial-engine_v2/.venv/bin/ruff check --fix autodev financial-engine_v2/backend scripts

# Tests — read the failure output, fix the issue

# Markdown hygiene — fix broken links reported by check_markdown_hygiene.sh
```

---

## Hook Locations

| Hook | File | Scope |
|------|------|-------|
| Session start context | `.claude/settings.json` | Claude Code only |
| Sensitive path warning (PreToolUse) | `.claude/settings.json` | Claude Code only |
| Graphify search reminder (PreToolUse) | `.claude/settings.json` / `.codex/hooks.json` | Claude Code + Codex |
| Tenn task-card contract (Stop) | `.claude/settings.json` / `.codex/hooks.json` | Claude Code + Codex |
| Auto ruff on Python writes | `.claude/settings.json` | Claude Code only |
| Auto chmod on shell writes | `.claude/settings.json` | Claude Code only |
| Auto pytest on backend edits | `.claude/settings.json` | Claude Code only |
| End-of-task diff summary | `.claude/settings.json` | Claude Code only |
| Doc coverage check | `.claude/settings.json` | Claude Code only |
| Pre-commit lint | `.git/hooks/pre-commit` | All git clients |
| Pre-push fast gates | `.git/hooks/pre-push` | All git clients |

---

## What Is NOT Automated

- Full 10-step validation sequence — run manually; see [runbook.md](runbook.md)
- Canonical dataset checks — require baseline fixtures in `reports/`
- Financial metrics / coverage gates — require generated report fixtures
- CI pipeline — no GitHub Actions configured

---

## Modifying Hooks

**Claude Code hooks:** edit `.claude/settings.json`. Reload via `/hooks` in the UI or restart the session.

**Git hooks:** edit `.git/hooks/pre-commit` or `.git/hooks/pre-push` directly. Not version-controlled (`.git/` is excluded from git). To share with collaborators, document required hooks here and have them install manually.

**Ruff path:** if the venv moves, update the hardcoded path `/home/l4nd0/tenn/financial-engine_v2/.venv/bin/ruff` in:
- `.claude/settings.json` (PostToolUse ruff hook)
- `.git/hooks/pre-commit`
- `.git/hooks/pre-push`
