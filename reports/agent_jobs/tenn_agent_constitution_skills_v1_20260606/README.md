# Tenn Agent Constitution Skills V1

Date: 2026-06-06
State: `DONE_WITH_RISK`
Tracker: GitHub issue #78, read-only use only
Task card: `docs/agent_tasks/tenn_agent_constitution_skills_v1_20260606.md`

## Objective

Rewrite Tenn `AGENTS.md` into a lean stable repo constitution and create the
first repo-backed Codex skill skeletons under `.agents/skills`, without touching
product/runtime/data/extraction surfaces.

## Evidence Used

- Audit report:
  `reports/agent_jobs/codex_agent_setup_audit_v1_20260606/README.md`
- Current target repo:
  `/home/l4nd0/tenn-nvme-clean-baseline-reconstruct-v1`
- Branch/HEAD:
  `tmp/sloppy-fix-demo` at `dfa313aaa6c1b34696f4bf9a8bd430636e5792ce`
- Origin:
  `https://github.com/0rl4nd0l/tenn.git`
- Issue #78 read-only metadata: open, `M0 - Control Plane Hardening`, covering
  agent markdown and Codex repo documentation refresh.
- Local evidence that `.agents/` and `.codex/` existed but had no current
  repo-local files in this target before the slice.
- Local validator evidence: accepted primary lanes exclude `Repo Hygiene`; task
  card uses primary `Evaluation` with supporting `Repo Hygiene` and `Reporting`.

## Files Changed

- `AGENTS.md`
- `docs/agent_tasks/tenn_agent_constitution_skills_v1_20260606.md`
- `.agents/skills/tenn-financial-metric-extraction/SKILL.md`
- `.agents/skills/tenn-task-card-registry-safety/SKILL.md`
- `.agents/skills/tenn-goal-report/SKILL.md`
- `reports/agent_jobs/tenn_agent_constitution_skills_v1_20260606/README.md`

The task-card file itself was included in `allowed_files` because local
`check-diff` compares every changed path literally against the allowlist.

## Files Intentionally Not Changed

- `.codex/config.toml`
- `.codex/hooks.json`
- `.codex/skills/*`
- `.gemini/*`
- `scripts/agent_job_contract.py`
- `scripts/agent_job_registry.py`
- `scripts/agent_job_hook.py`
- product/backend/frontend/runtime/data/extraction files
- GitHub issues and PRs

## AGENTS.md Section Summary

`AGENTS.md` is now a 169-line repo constitution with these sections:

1. Repo Map And Target Selection
2. Current Evidence And Truthfulness
3. Source Of Truth Hierarchy
4. Safety Boundaries
5. Financial Truth Priority
6. Multi-Agent Live Repo Control
7. Task Cards, Registry, And Merge Parking
8. Command Output Discipline
9. Blocked, Waiting, And Approval States
10. Risk-Based Validation
11. Done Criteria And Reporting
12. Skill And Subagent Policy
13. GitHub Issue Workflow

Removed stale Cursor Cloud `/workspace` assumptions as defaults, old static
test-failure counts, and host-skill inventory/absolute path patterns. The file
states that repo-backed Codex skills live under `.agents/skills`, while
`.codex/config.toml` and `.codex/hooks.json` are Codex config/hooks surfaces.

## Skills Created

| Skill | Purpose |
| --- | --- |
| `tenn-financial-metric-extraction` | Issue-backed Financial Truth and PDF metric extraction workflow with source-bound, deterministic, auditable, provenance-linked rules. |
| `tenn-task-card-registry-safety` | Task-card validation, dirty-state review, registry safety, collision checks, and allowed-files enforcement. |
| `tenn-goal-report` | `/goal` state machine, report/handoff structure, blocked-state capture, validation tracking, raw-log pointers, and next prompt. |

All three are instruction-only skeletons with `name` and `description`
frontmatter. No scripts, dependencies, references, or assets were added.

## Validation

| Command | Exit | Result |
| --- | ---: | --- |
| `python3 scripts/agent_job_contract.py validate docs/agent_tasks/tenn_agent_constitution_skills_v1_20260606.md` | 0 | Passed; no validation issues. |
| `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/tenn_agent_constitution_skills_v1_20260606.md --no-write-report` | 1 | Failed because pre-existing unrelated dirty/untracked files are outside this task card's allowlist. The new intended files are allowlisted. |
| `git diff --check` | 0 | Passed for tracked diffs. |
| `git diff --no-index --check /dev/null <new-doc>` for each new task/skill file | 0 | Passed via wrapper that accepts diff exit `1` as a clean no-index comparison. |
| Skill frontmatter YAML parse for `.agents/skills/*/SKILL.md` | 0 | Passed; all three skills have `name` and `description`. |
| Manual markdown review | 0 | Reviewed line counts, required AGENTS sections, task card, and skill skeleton content. |

No product/runtime/extraction tests were run because this is a docs/control-plane
slice only.

## Check-Diff Blocker

`check-diff` is not green due to unrelated pre-existing checkout state outside
this slice, including:

- `cockpit-ui/package.json`
- untracked `.gemini/skills/*`
- untracked `.playwright-mcp/*`
- stale `.tenn/*`
- unrelated untracked `docs/agent_tasks/*`
- untracked `scripts/agent_job_contract.py`,
  `scripts/agent_job_registry.py`, and `scripts/agent_job_hook.py`
- other existing artifacts/outputs

The allowlist was not widened and no unrelated files were cleaned.

## Unsafe Actions Avoided

- No DB, Qdrant, news, memory, backfill, source-PDF, gold-label, prompt,
  service, model, GPU, or runtime mutation.
- No dependency install.
- No broad tests.
- No GitHub issue/PR create, edit, comment, close, label, merge, or push.
- No `.codex/config.toml` or `.codex/hooks.json` changes.
- No host-skill migration.
- No reset, stash, clean, rebase, merge, delete, or prune.

## Ignored And Untracked Artifact Note

`reports/` is ignored by repo ignore rules, so this closeout report will appear
only under ignored status unless explicitly force-added later. The new
`.agents/skills/*` files and task card are untracked in the current shared
checkout.

## Remaining Blockers

- `scripts/agent_job_registry.py list-active --read-only` is still missing.
- `Repo Hygiene` is still not an accepted primary lane in the local validator.
- Shared checkout dirt prevents a clean task-card `check-diff` result.
- Existing `.gemini/skills` symlinks and older `.codex/skills` conventions
  remain for future cleanup; this slice did not migrate them.

## Recommended Next Prompt

```text
Proceed with the next bounded Repo Hygiene slice under issue #78: implement
read-only registry inspection by adding
`python3 scripts/agent_job_registry.py list-active --read-only` without creating
locks, owner files, registry roots, status files, or timestamp changes. Start
with focused tests proving current mutation risk and read-only behavior. Do not
touch product/runtime/data/extraction surfaces. Validate with targeted registry
tests, task-card validate/check-diff, `git diff --check`, and final status.
```
