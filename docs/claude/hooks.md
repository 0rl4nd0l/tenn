# Hooks

All automation hooks active in this repo. Agents should read this before triggering file writes, commits, or pushes.

## Source Trace
- `.claude/settings.json` (Confirmed)
- `.codex/config.toml` (Confirmed)
- `.codex/hooks.json` (Confirmed)
- `.gemini/settings.json` (Confirmed)
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
| `Stop` | When Claude finishes a task | Runs `scripts/agent_job_hook.py` and enforces the Tenn task-card contract only when `TENN_AGENT_TASK_CARD` or worktree-local `.tenn/active_agent_task` is set |
| `Stop` | When Claude finishes a task | Runs `git diff --stat HEAD` — shows all files changed since last commit |
| `Stop` | When Claude finishes a task | Checks if infrastructure/config files changed without corresponding `docs/claude/` updates — prints WARNING if so |

**Ruff binary / pytest binary:** `financial-engine_v2/.venv/bin/ruff` and `.../pytest`
Legacy hygiene hooks are non-blocking (`|| true`); they warn without interrupting Claude if they fail. The Tenn task-card hook is intentionally blocking when an active task card fails validation or `check-diff`.

**Note for agents:** The `SessionStart` and `Stop` hooks output context to the transcript. Use `Stop` output to verify what changed before concluding a task.

**Sensitive path warning:** The `PreToolUse` hook prints a `WARNING:` line but does not block the edit. Claude should read the warning and confirm scope before proceeding when it appears.

**Graphify reminder:** The `PreToolUse` search hook must emit a top-level `systemMessage`. Do not use `hookSpecificOutput.additionalContext` for this hook; recent Claude Code runtimes reject that field for `PreToolUse`.

**Doc coverage warning:** The doc-coverage `Stop` hook detects when infrastructure files (`.mcp.json`, `settings.json`, `scripts/mcp/`, `.claude/commands/`, etc.) were modified but no `docs/claude/` files were updated. This is a non-blocking JSON `systemMessage` warning — the agent must act on it before concluding the task. See CLAUDE.md "Post-Write Documentation" for the mapping of changed surfaces to required doc updates.

**Tenn task-card hook:** `scripts/agent_job_hook.py` reads hook stdin JSON, resolves the repo root, finds the current session task card from `TENN_AGENT_TASK_CARD` or worktree-local `.tenn/active_agent_task`, then runs `scripts/agent_job_contract.py validate`, registry `list-active`, registry `check-overlap`, and contract `check-diff`. With no active task card it returns valid empty JSON (`{}`) and must not block exploratory sessions. With an active task card it emits valid JSON for pass or block results.

**Task cards:** A task card is the explicit scope file for an implementation-capable agent job. It declares the `job_id`, `lane`, `owner`, `allowed_files`, `output_dir`, `mutation_mode`, timeout, approval flag, and `production_data_access: false`. The contract validator checks that metadata before work starts, and `check-diff` checks that the current git diff stays inside the card's `allowed_files`. The task card selected by `TENN_AGENT_TASK_CARD` or `.tenn/active_agent_task` is session-local; the registry claim created from that card is the shared visibility record.

**Agent job registry:** `scripts/agent_job_registry.py` is the shared dev-agent source of truth for active Codex/Claude/Gemini task-card claims. The registry root is resolved in this order:

1. `TENN_AGENT_REGISTRY_ROOT`
2. `git config tenn.agentRegistryRoot`
3. `git rev-parse --git-common-dir` plus `tenn-agent-registry`
4. repo-local `.tenn/agent_jobs` fallback with a warning when git metadata is unavailable

Active records live under `<registry_root>/active/<job_id>.json`. The worktree-local markers `TENN_AGENT_TASK_CARD` and `.tenn/active_agent_task` only select the current session task card; they are not the registry source of truth. `list-active` includes `registry_root`, `registry_scope`, `repo_root`, and `git_common_dir` so agents can confirm whether a session is using shared or fallback visibility.

**List / claim / release workflow:**

```bash
python scripts/agent_job_contract.py validate <task_card>
python scripts/agent_job_registry.py list-active
python scripts/agent_job_registry.py claim <task_card>
export TENN_AGENT_TASK_CARD=<task_card>
# work inside the task card scope
python scripts/agent_job_contract.py check-diff <task_card>
python scripts/agent_job_registry.py release <job_id>
```

- `list-active` is the first visibility check. Confirm `registry_root`, `registry_scope`, and current active jobs before claiming work.
- `claim` validates the task card, checks active lane/file/output overlap, writes `<registry_root>/active/<job_id>.json`, and writes `reports/agent_jobs/<job_id>/status.json`.
- `heartbeat <job_id>` refreshes `last_seen_at` for a long-running claimed job.
- `release <job_id>` removes the active registry record and updates the status report to `released`; run it when the job is complete or abandoned.
- The Stop hook still runs `check-overlap` and `check-diff` for the selected card. A manual `claim` is what makes the job visible to other agents before Stop.

**Linked worktrees:** Linked worktrees from the same clone normally share one `git-common-dir`, so the default `<git-common-dir>/tenn-agent-registry` fallback gives Codex, Claude, and Gemini shared active-job visibility even when each agent is launched from a different linked worktree. The active record stores the physical `worktree`, `branch`, `git_common_dir`, and repo-relative `allowed_files`, so overlap checks compare the same logical paths across worktrees.

**Separate clones:** Separate clones do not share a `git-common-dir`. If Codex, Claude, and Gemini are launched from separate clones, set the same absolute shared registry root in each session or clone:

```bash
export TENN_AGENT_REGISTRY_ROOT=/path/to/shared/tenn-agent-registry
# or persist per clone:
git config tenn.agentRegistryRoot /path/to/shared/tenn-agent-registry
```

Without that shared env/config, each clone will use its own git-common-dir registry and active jobs from the other clone will not be visible. If git metadata is unavailable, the repo-local `.tenn/agent_jobs` fallback is only local to that checkout and `list-active` reports a fallback warning.

**Codex launched from the Tenn web UI:** Any Tenn web UI launcher that spawns Codex must pass the same `TENN_AGENT_REGISTRY_ROOT` used by local Codex/Claude/Gemini sessions, or launch from a clone/worktree whose `git config tenn.agentRegistryRoot` points at that root. Do not rely on the web process current directory for registry discovery; verify with `python scripts/agent_job_registry.py list-active` from the launched environment.

### Agent Job Registry Troubleshooting

| Symptom | Check | Fix |
|---------|-------|-----|
| Active job not visible | Run `python scripts/agent_job_registry.py list-active` in both sessions and compare `registry_root`, `registry_scope`, and `git_common_dir`. | Point both sessions at the same root with `TENN_AGENT_REGISTRY_ROOT` or `git config tenn.agentRegistryRoot`, then re-run `claim`. |
| Wrong registry root | `list-active` shows an unexpected root or `repo_local_fallback`. | Set an absolute shared root via env/config. For linked worktrees, confirm `git rev-parse --git-common-dir` is the expected common directory. |
| Stale active job | `list-active` reports a stale active job warning or an owner is known to be done. | If the owner is still working, run `heartbeat <job_id>`. If the work is abandoned or complete, run `release <job_id>` from a session using the same registry root. |
| Stale registry lock | Registry commands fail with a timeout waiting for `<registry_root>/.lock`. | Inspect `<registry_root>/.lock/owner.json`; only remove the `.lock` directory after confirming that owner process is gone. |
| Unrelated dirty files blocked | Hook or `check-overlap` reports dirty paths outside the current card. | Commit, clean, move to a separate worktree, or update the task card scope before continuing. Do not hide unrelated work inside the current card. |
| Overlapping `allowed_files` blocked | `claim` or Stop reports an active job overlap by lane, `allowed_files`, or `output_dir`. | Coordinate with the active job owner, wait for `release`, or narrow one task card so the repo-relative paths no longer overlap. |

**Stop hook JSON:** Claude Stop hooks that produce output now emit JSON objects such as `{"systemMessage": "..."}`. The previous raw `git diff --stat` and plain text doc-coverage output were replaced to avoid invalid Stop hook JSON output.

---

## Codex Hooks (`.codex/config.toml`, `.codex/hooks.json`)

Repo-local Codex hooks are enabled with `codex_hooks = true`.

| Event | Trigger | What It Does |
|-------|---------|--------------|
| `PreToolUse` / `Bash` | Before shell commands | Emits a graphify reminder via `systemMessage` when `graphify-out/graph.json` exists |
| `Stop` | When Codex finishes a task | Runs `scripts/agent_job_hook.py` and enforces the Tenn task-card contract only when `TENN_AGENT_TASK_CARD` or worktree-local `.tenn/active_agent_task` is set |

---

## Gemini Hooks (`.gemini/settings.json`)

Repo-local Gemini hooks use Gemini-compatible JSON decisions (`allow` / `block`).

| Event | Trigger | What It Does |
|-------|---------|--------------|
| `BeforeTool` / `read_file\|list_directory` | Before Gemini broad file reads | Emits a graphify reminder via `additionalContext` when `graphify-out/graph.json` exists |
| `BeforeTool` / `write_file\|replace\|run_shell_command` | Before Gemini file mutations or shell commands | Runs `scripts/agent_job_hook.py --platform gemini --event BeforeTool` and enforces the Tenn task-card contract only when `TENN_AGENT_TASK_CARD` or worktree-local `.tenn/active_agent_task` is set |

The Gemini task-card hook runs the same validator, shared registry visibility check, overlap check, and diff-scope check as the Codex/Claude Stop hook. Because this hook runs before mutating/shell tool calls, it passes `--no-write-report` to `check-diff`; this prevents repeated per-tool checks from creating their own `reports/agent_jobs/<job_id>/diff-check.json` dirty artifact. Task-card jobs should still run the normal final `python scripts/agent_job_contract.py check-diff <task_card>` before release/final report.

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
| Graphify search reminder (PreToolUse/BeforeTool) | `.claude/settings.json` / `.codex/hooks.json` / `.gemini/settings.json` | Claude Code + Codex + Gemini |
| Tenn task-card contract (Stop/BeforeTool) | `.claude/settings.json` / `.codex/hooks.json` / `.gemini/settings.json` | Claude Code + Codex + Gemini |
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
