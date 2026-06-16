# Agent Flow Cleanup Execution Report - 2026-06-16

Status: `DONE_WITH_RISK`

## Summary

Implemented the requested cleanup wave using read-only subagents and main-agent
review. This pass addressed all four requested follow-ups:

1. Added a read-only Git hook status checker.
2. Normalized skill authority around `.agents/skills`.
3. Collapsed tool identity docs back to `AGENTS.md` as the constitution.
4. Added report-bundle artifact validation to task-card tooling.

No host hooks, host `$CODEX_HOME`, Git config, runtime services, data stores,
GitHub state, commits, branch operations, or dependency installs were mutated.

## What Changed

### Hook Status Checker

Added:

- `scripts/check_agent_hooks.py`
- `scripts/test_check_agent_hooks.py`

Behavior:

- Reads Git config and Git plumbing only.
- Reports `core.hooksPath`, git common dir, effective hook dir, hook existence,
  executable bits, and optional fingerprints.
- Defaults to exit `0` even when hooks are missing, with `"ok": false` in JSON.
- Exits nonzero only with `--strict`.

Original cleanup-pass live result before the separate hook install:

- `ok: false`
- configured hook path: `/home/l4nd0/tenn/.git/hooks`
- effective hook dir reported missing
- `pre-commit` and `pre-push` missing at the effective path

That closed the false-confidence gap without installing or changing hooks in
this cleanup pass. The follow-up hook execution package now installs
worktree-local `.githooks` and scopes `core.hooksPath=.githooks` to this
worktree's `config.worktree`.

### Hook Behavior Reduction

Retained the previous hook essentialization:

- `Stop` and `SessionEnd` validate the active card and inspect registry with
  `list-active --read-only`.
- `Stop` and `SessionEnd` do not run `check-overlap`.
- `Stop` and `SessionEnd` do not run `check-diff` or write diff reports.
- `BeforeTool` still runs `check-diff --no-write-report` and can block unsafe
  diffs.
- `.claude/settings.json` is repo-relative and low-side-effect.

### Report-Bundle Validation

Updated:

- `scripts/agent_job_contract.py`
- `scripts/test_agent_job_contract.py`

Added:

```bash
python3 scripts/agent_job_contract.py check-report-artifacts <task-card> --repo-root .
```

The command verifies that report artifacts listed in `allowed_files` under the
task `output_dir` exist, are files, are non-empty, and resolve inside the output
directory. `check-artifacts` remains as an alias.

### Skill Authority

Added:

- `docs/agents/skill-registry.md`

Updated:

- `AGENTS.md` points to the skill registry.
- `scripts/sync_codex_skills.sh` now reads `.agents/skills`, not
  `.codex/skills`, and is dry-run by default. Host `$CODEX_HOME/skills` mutation
  requires `--apply`.
- `GEMINI.md`, `CODEX.md`, `docs/claude/commands.md`, and
  `docs/claude/gap-analysis.md` now identify `.agents/skills` as the active
  repo-backed skill root.
- `docs/process/codex_skill_sources/github_issue_system/README.md` now labels
  mirrored issue skills as reference-only.
- `docs/process/codex_skill_sources/github_issue_system/tenn-issue-closeout/SKILL.md`
  uses `list-active --read-only`.
- `.agents/skills/tenn-financial-metric-extraction/SKILL.md` now uses the
  current read-only registry command.
- `.agents/skills/tenn-auto-progress/SKILL.md` now has frontmatter.
- `.agents/skills/tenn-git-hygiene/SKILL.md` now allows H1-first skills and
  optional frontmatter.

### Instruction Collapse

Replaced large conflicting identity docs with concise tool notes:

- `CLAUDE.md`
- `CODEX.md`
- `GEMINI.md`
- `financial-engine_v2/PROJECT_AGENT_RULES.md`

They now defer to `AGENTS.md`, remove unconditional commit/clean-tree mandates,
and make runtime startup task-specific instead of default.

Updated `docs/entrypoints.md` to state it is for runtime tasks only.

## Files Touched

- `.agents/skills/tenn-auto-progress/SKILL.md`
- `.agents/skills/tenn-financial-metric-extraction/SKILL.md`
- `.agents/skills/tenn-git-hygiene/SKILL.md`
- `.claude/settings.json`
- `AGENTS.md`
- `CLAUDE.md`
- `CODEX.md`
- `GEMINI.md`
- `docs/agent_tasks/agent_flow_cleanup_execution_v1_20260616.md`
- `docs/agents/skill-registry.md`
- `docs/claude/commands.md`
- `docs/claude/gap-analysis.md`
- `docs/entrypoints.md`
- `docs/process/codex_skill_sources/github_issue_system/README.md`
- `docs/process/codex_skill_sources/github_issue_system/tenn-issue-closeout/SKILL.md`
- `financial-engine_v2/PROJECT_AGENT_RULES.md`
- `scripts/agent_job_contract.py`
- `scripts/agent_job_hook.py`
- `scripts/check_agent_hooks.py`
- `scripts/sync_codex_skills.sh`
- `scripts/test_agent_job_contract.py`
- `scripts/test_agent_job_hook.py`
- `scripts/test_check_agent_hooks.py`
- this report bundle

## Intentionally Not Touched

- `.codex/hooks.json`
- `.gemini/settings.json`
- actual Git hook installation or Git config in the cleanup pass; the combined
  commit-ready package includes the separate worktree-local `.githooks`
  execution report
- host `$CODEX_HOME`
- `.codex/skills/cockpit-flag-orchestrator`
- `.claude/skills/**`
- `.kilocode/skills/**`
- runtime/product/extraction/data/GitHub surfaces

## Validation

Passed:

- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/agent_flow_cleanup_execution_v1_20260616.md`
- `python3 scripts/agent_job_registry.py list-active --read-only`
- `PYTHONDONTWRITEBYTECODE=1 python3 -m py_compile scripts/agent_job_hook.py scripts/check_agent_hooks.py scripts/agent_job_contract.py`
- `PYTHONDONTWRITEBYTECODE=1 python3 -m json.tool .claude/settings.json`
- `bash -n scripts/sync_codex_skills.sh`
- `PYTHONDONTWRITEBYTECODE=1 financial-engine_v2/.venv/bin/pytest -q -p no:cacheprovider scripts/test_agent_job_hook.py scripts/test_check_agent_hooks.py scripts/test_agent_job_contract.py`
  - result: `51 passed`
- `bash scripts/sync_codex_skills.sh`
  - result: dry-run only, `linked=0`, `would_link=6`, `skipped=0`
- stale-reference scan found no remaining target conflicts except intentionally
  allowed references in `AGENTS.md`, `docs/agents/skill-registry.md`, and
  legacy/custom labels.

Expected non-passing/diagnostic:

- `python3 scripts/check_agent_hooks.py --repo-root .` exits `0` by default and
  reports `"ok": false` because Git hooks are missing at the effective configured
  path.
- `check-diff` for this task is expected to fail because unrelated pre-existing
  untracked task cards remain outside this card's allowlist.

## Residual Risk

- Git hooks were not installed in this cleanup pass. They are now covered by
  the separate `git_hook_install_execution_v1_20260616` package.
- `.codex/skills/cockpit-flag-orchestrator` remains in place as legacy/custom.
  It is now documented as non-canonical, but it has not been ported or moved.
- `docs/claude/hooks.md` may still contain stale descriptive detail. It was not
  in this task-card allowlist and should be refreshed in a narrow follow-up if
  needed.
- Existing unrelated untracked task cards still block strict same-worktree
  `check-diff`.
