# Subagent Review Summary

Four read-only reviewer agents were used. No subagent edited files.

## Hook Status Reviewer

Findings:

- Codex, Claude, and Gemini hook configs parse and invoke repo hook wrappers.
- Git `core.hooksPath` points at `/home/l4nd0/tenn/.git/hooks`.
- In this worktree, that effective hook path does not expose executable
  `pre-commit` or `pre-push` hooks.
- Recommended a read-only JSON status script with default report-only behavior
  and strict nonzero mode.

Implemented:

- Added `scripts/check_agent_hooks.py`.
- Added `scripts/test_check_agent_hooks.py`.
- Default mode exits `0` with `"ok": false`; `--strict` exits nonzero on
  missing/invalid hooks.

## Skill Authority Reviewer

Findings:

- `.agents/skills` is constitutional authority, but older docs pointed to
  `.codex/skills`.
- `scripts/sync_codex_skills.sh` synced from `.codex/skills`.
- `tenn-financial-metric-extraction` had stale `list-active --read-only`
  guidance.
- `tenn-auto-progress` lacked frontmatter while `tenn-git-hygiene` expected
  frontmatter.

Implemented:

- Added `docs/agents/skill-registry.md`.
- Updated stale docs/scripts to `.agents/skills`.
- Made skill sync dry-run by default and `.agents/skills` based.
- Fixed read-only registry guidance and skill metadata/frontmatter rules.

## Instruction Collapse Reviewer

Findings:

- `CLAUDE.md`, `CODEX.md`, `GEMINI.md`, and
  `financial-engine_v2/PROJECT_AGENT_RULES.md` preserved independent authority,
  commit mandates, clean-tree expectations, broad runtime reads, and stale skill
  references.
- `docs/entrypoints.md` used broad "all agents" language despite AGENTS limiting
  entrypoint context to runtime tasks.

Implemented:

- Replaced the identity docs with concise tool notes that defer to `AGENTS.md`.
- Removed unconditional commit/clean-tree/runtime startup mandates.
- Marked entrypoints as runtime-task-only.

## Report-Bundle Validation Reviewer

Findings:

- Task-card validation checked `allowed_files` shape and `output_dir` shape, but
  not whether ignored report artifacts existed.
- `check-diff` is not a report-bundle verifier and can write `diff-check.json`.
- Recommended a new dedicated subcommand.

Implemented:

- Added `check-report-artifacts`.
- Kept `check-artifacts` as an alias.
- Added tests for non-empty artifacts, missing output dir, missing artifacts,
  empty artifacts, CLI output, alias behavior, and symlink escape.
