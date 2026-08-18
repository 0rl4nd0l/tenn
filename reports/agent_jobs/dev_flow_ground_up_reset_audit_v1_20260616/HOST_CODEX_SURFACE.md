# Host Codex Surface

Read-only host inspection found:

- `~/.codex/config.toml`
- `~/.codex/hooks/*.py`
- `~/.codex/rules/default.rules`
- `~/.codex/skills/**`
- `~/.codex/goals_1.sqlite`

No host-global file was mutated.

## Config

Host config enables hooks, memories, goals, multi-agent, remote control,
Playwright, Jam, Chorus, GitHub, Google Drive, OpenAI developer, security, web,
iOS, macOS, data visualization, and fiscal plugins. Multiple Tenn project paths
are trusted.

Classification: `OWNER_BOUNDARY`.

Recommendation: Tenn repo workflows may read this as environment context, but
must not rely on host plugin availability for repo safety. Repo skills and
scripts should remain the Tenn source of truth.

## Goals DB

`~/.codex/goals_1.sqlite` exists. Schema includes `thread_goals` with `active`,
`paused`, `blocked`, `usage_limited`, `budget_limited`, and `complete` status.

Classification: `CORE_KEEP`.

Recommendation: Use for goal-state reporting and burn warnings only. Do not use
as a substitute for report-local `STATE.md`.

## Host Skills

Relevant day-to-day host skills should be routed through Tenn wrappers:

- keep `diagnose`;
- keep `code-reviewer`;
- keep `improve-codebase-architecture`;
- merge issue/triage/closeout pieces into `/issue` and `/fix`;
- do not expose generic `triage` directly to Tenn labels.

## Host Hooks

Host hooks are valuable, but not all are Tenn-native. In particular,
`post_apply_patch.py` can run format/test commands after patches. It did not
change this report bundle, but the future Git guard should explicitly mark
whether the current run is report-only and whether post-patch side effects are
acceptable.
