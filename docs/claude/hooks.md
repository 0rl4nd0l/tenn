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
| `Stop` | When Claude finishes a task | Runs `scripts/agent_job_hook.py`; default enforcement follows the selected task card, while V2-required repos also check no-card terminal state |
| `Stop` | When Claude finishes a task | Runs `git diff --stat HEAD` — shows all files changed since last commit |
| `Stop` | When Claude finishes a task | Checks if infrastructure/config files changed without corresponding `docs/claude/` updates — prints WARNING if so |

**Ruff binary / pytest binary:** `financial-engine_v2/.venv/bin/ruff` and `.../pytest`
Legacy hygiene hooks are non-blocking (`|| true`); they warn without interrupting Claude if they fail. The Tenn task-card hook is intentionally blocking when an active task card fails validation or `check-diff`.

**Note for agents:** The `SessionStart` and `Stop` hooks output context to the transcript. Use `Stop` output to verify what changed before concluding a task.

**Sensitive path warning:** The `PreToolUse` hook prints a `WARNING:` line but does not block the edit. Claude should read the warning and confirm scope before proceeding when it appears.

**Graphify reminder:** The `PreToolUse` search hook must emit a top-level `systemMessage`. Do not use `hookSpecificOutput.additionalContext` for this hook; recent Claude Code runtimes reject that field for `PreToolUse`.

**Doc coverage warning:** The doc-coverage `Stop` hook detects when infrastructure files (`.mcp.json`, `settings.json`, `scripts/mcp/`, `.claude/commands/`, etc.) were modified but no `docs/claude/` files were updated. This is a non-blocking JSON `systemMessage` warning — the agent must act on it before concluding the task. See CLAUDE.md "Post-Write Documentation" for the mapping of changed surfaces to required doc updates.

**Tenn task-card hook:** `scripts/agent_job_hook.py` reads hook stdin JSON, resolves the repo root, and finds the current session task card from `TENN_AGENT_TASK_CARD` or worktree-local `.tenn/active_agent_task`. `BeforeTool` validates the card and active-registry selector, classifies the proposed tool/capability/path, and runs `check-diff`; registry `claim` performs the atomic lane/file/output overlap check. `Stop` runs `check-closeout` plus decision-ledger matching for a claim, or verifies a semantic no-run state/release receipt for an explicitly selected unclaimed V2 card. By default, no-card sessions and V1 terminal failures retain warning-compatible legacy behavior; selected V1 `BeforeTool` violations can still block. A pilot repository may set `TENN_V2_REQUIRED=1`; its pre-tool hook admits only a narrow task-card/ledger-initialization/claim bootstrap and conservative read-only commands before a V2 claim. With a claim, proposed file paths must be exact `allowed_files`, shell admission is fail-closed, and every classified capability must be declared. A no-card terminal event only confirms that no active target-worktree V2 claim remains and relies on configured pre-tool coverage; it does not independently prove that prior work was trivial or read-only. An explicitly selected unclaimed V2 card must instead prove a report-free semantic stop such as `REUSED_COMPLETE` or present a validated release receipt.

V2 Python/pytest admission trusts repo-local executable code; it classifies
command intent and explicit outputs but is not an OS sandbox. Pytest must disable
bytecode writes, plugin autoload, and its cache provider; `uv run` must use
`--no-sync --frozen`. V2 publication suppresses repository Git hooks and signing
with the exact admitted commit/push forms, so run required lint and tests
explicitly before publishing. See the semantic-control document for the command
constraints and trust boundary.

**Task cards:** A task card is the explicit scope file for an implementation-capable agent job. It declares the `job_id`, `lane`, `owner`, `allowed_files`, `output_dir`, `mutation_mode`, timeout, approval flag, and `production_data_access: false`. The contract validator checks that metadata before work starts, and `check-diff` checks that the current git diff stays inside the card's `allowed_files`. The task card selected by `TENN_AGENT_TASK_CARD` or `.tenn/active_agent_task` is session-local; the registry claim created from that card is the shared visibility record.

**V2 semantic control:** A card with `control_contract_version: 2` also declares
the proof question, track, phase transition, evidence identity, capabilities,
and reopen condition described in
`docs/dev_flow/SEMANTIC_ANTI_LOOP_CONTROL_V2.md`. Run portable preflight with
`--task-card` before substantive work. Its fingerprint is computed, persisted
in active V2 claims, and checked against the shared
`decision-ledger.jsonl`. Invalid V2 contracts and closeouts hard-block the
repo hook; legacy V1 terminal failures retain warning-compatible behavior,
while a selected V1 card's `BeforeTool` contract or diff violation may still
block the proposed tool. For the same track, evidence hash, and hypothesis,
classification applies the two-outcome no-delta loop guard before considering
`does_not_block`; outcome status and task/run/report references remain
provenance rather than decision delta.

Every claimed V2 run admitted to substantive work must close with
`RUN_OUTCOME.json` and exactly one `<output_dir>/DECISION_ENTRY.json` candidate.
Normal registry release validates both and appends the candidate under the
shared registry lock. Pre-claim semantic stops such as `REUSED_COMPLETE` create
no new outcome/report. Claimed terminal/no-progress outcomes must not create
`NEXT_GOAL.md`; they name the evidence already reused and the exact
`resume_only_if` condition.

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
# write <output_dir>/RUN_OUTCOME.json and <output_dir>/DECISION_ENTRY.json
python scripts/agent_job_registry.py release <job_id>
# Administrative recovery only (stale/corrupt claim or task-card/identity drift):
python scripts/agent_job_registry.py release <job_id> --abandon-reason "<reason>"
```

- `list-active` is the first visibility check. Confirm `registry_root`, `registry_scope`, and current active jobs before claiming work.
- V1 `claim` validates the task card and active lane/file/output overlap. V2 `claim` additionally requires a readable decision ledger and runs semantic scope classification under the registry lock; exact resolved scopes, active fingerprints, decision blocks, and the third unchanged no-delta continuation stop before an active record is written.
- `heartbeat <job_id>` refreshes `last_seen_at` for a long-running claimed job.
- V1 `release <job_id>` preserves the legacy removal behavior. V2 normal release validates the claimed card, `RUN_OUTCOME.json`, and exactly one current-run `DECISION_ENTRY.json` candidate; under the registry lock it validates the live ledger, appends the candidate, writes a receipt, and then removes the active record. A failure leaves the claim active.
- Claimed runs never call standalone decision-ledger `append`. That command is reserved for `--authorize-unclaimed-seed` and refuses a seed matching an active run or semantic scope.
- `release <job_id> --abandon-reason "<reason>"` is limited to administrative recovery for a stale/corrupt V2 claim or task-card/semantic-identity drift. Unreadable active records are quarantined with an abandonment receipt instead of being silently discarded. `DATA_MISSING`, `BLOCKED_NO_NEW_INPUT`, and other valid terminal outcomes are not abandonment: they require `RUN_OUTCOME.json`, a decision candidate, and normal release so no-delta history counts toward the loop guard.
- `BeforeTool` runs card validation, active-registry selection, capability/proposed-path admission, and `check-diff`. Lane/file/output overlap is enforced atomically by `claim`. `Stop` runs closeout and decision-ledger matching for a claimed card, or semantic no-run/release-receipt validation for an explicitly selected unclaimed V2 card.

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
| Stale active job | `list-active` reports a stale active job warning. | If the owner is still working, run `heartbeat <job_id>`. Otherwise, V2 permits `release <job_id> --abandon-reason "<reason>"` only for stale/corrupt or card/semantic-identity-drift recovery; a valid terminal result uses normal release with its outcome and decision candidate. |
| Stale registry lock | Registry commands fail with a timeout waiting for `<registry_root>/.lock`. | Inspect `<registry_root>/.lock/owner.json`; only remove the `.lock` directory after confirming that owner process is gone. |
| Unrelated dirty files blocked | Hook or `check-overlap` reports dirty paths outside the current card. | Commit, clean, move to a separate worktree, or update the task card scope before continuing. Do not hide unrelated work inside the current card. |
| Overlapping `allowed_files` blocked | `claim` reports an active job overlap by lane, `allowed_files`, or `output_dir`. | Coordinate with the active job owner, wait for `release`, or narrow one task card so the repo-relative paths no longer overlap. Overlap is an atomic claim-time check, not a Stop-time check. |

**Stop hook JSON:** Claude Stop hooks that produce output now emit JSON objects such as `{"systemMessage": "..."}`. The previous raw `git diff --stat` and plain text doc-coverage output were replaced to avoid invalid Stop hook JSON output.

---

## Codex Hooks (`.codex/config.toml`, `.codex/hooks.json`)

Repo-local Codex hooks are enabled with `codex_hooks = true`.

| Event | Trigger | What It Does |
|-------|---------|--------------|
| `PreToolUse` / `Bash\|apply_patch\|Edit\|Write` | Before shell/file mutation tools | Runs V2 task admission and capability checks; Tenn does not set the repository-wide V2-required flag, so V1 remains compatible |
| `PreToolUse` / `Bash` | Before shell commands | Emits a graphify reminder via `systemMessage` when `graphify-out/graph.json` exists |
| `Stop` | When Codex finishes a task | Runs `scripts/agent_job_hook.py`; default enforcement follows the selected task card, while V2-required repos also check no-card terminal state |

---

## Gemini Hooks (`.gemini/settings.json`)

Repo-local Gemini hooks use Gemini-compatible JSON decisions (`allow` / `block`).

| Event | Trigger | What It Does |
|-------|---------|--------------|
| `BeforeTool` / `read_file\|list_directory` | Before Gemini broad file reads | Emits a graphify reminder via `additionalContext` when `graphify-out/graph.json` exists |
| `BeforeTool` / `write_file\|replace\|run_shell_command` | Before Gemini file mutations or shell commands | Runs `scripts/agent_job_hook.py --platform gemini --event BeforeTool`; selected cards are enforced by default and V2-required repos also gate pre-claim substantive tools |

The Gemini task-card hook uses the same `BeforeTool` admission flow as the other configured agent surfaces: it resolves and validates the selected card and active claim, classifies the proposed tool/capability/path, and runs `check-diff --no-write-report`. This prevents repeated pre-tool checks from creating their own `reports/agent_jobs/<job_id>/diff-check.json` dirty artifact. Lane/file/output overlap is checked atomically by registry `claim`, not by `BeforeTool` or `Stop`. Task-card jobs still run the normal final `python scripts/agent_job_contract.py check-diff <task_card>` before writing closeout artifacts and using normal release.

---

## Git Hooks

### `pre-commit` (`.git/hooks/pre-commit`)

Fires on ordinary `git commit` commands. Blocks the commit if lint fails. A V2
admitted publication deliberately sets `core.hooksPath=/dev/null`; its explicit
validation must already be green before that commit.

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

Fires on ordinary `git push` commands. Blocks the push if any gate fails. V2
admitted pushes use `--no-verify` after the same gates have run explicitly.

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
