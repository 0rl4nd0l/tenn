# Preservation Decision

Date: 2026-06-06
State: `WAITING_ON_USER`

## Branch / HEAD / Origin

- CWD: `/home/l4nd0/tenn-nvme-clean-baseline-reconstruct-v1`
- Branch: `tmp/sloppy-fix-demo`
- HEAD: `dfa313aaa6c1b34696f4bf9a8bd430636e5792ce`
- HEAD subject: `chore(repo-hygiene): update extraction merge parking decisions`
- Origin: `https://github.com/0rl4nd0l/tenn.git`
- Remote refs checked:
  - `origin/main`: `c260942969309d7be00bafdd35dc4e6f769ffcbc`
  - `origin/migration/clean-runtime-baseline-reconstruct-v1`: `9436d1d32de0da5423b8edcfc7efc883ccac3fd6`
  - `origin/tmp/sloppy-fix-demo`: `1938535ae8f2c91543477a6220fee63f0bf551a2`

## Decision

No commit was created.

The current branch is not clearly approved for issue #78 preservation:

- The branch name is `tmp/sloppy-fix-demo`, not an issue #78 or agent-docs
  preservation branch.
- Local `tmp/sloppy-fix-demo` is at `dfa313a`, while the remote branch of the
  same name is at `1938535`.
- Issue #78 is the right tracker, but branch placement needs an explicit
  decision before committing.

## Files Present For Preservation

These completed-slice files exist locally:

- `AGENTS.md`
- `.agents/skills/tenn-financial-metric-extraction/SKILL.md`
- `.agents/skills/tenn-task-card-registry-safety/SKILL.md`
- `.agents/skills/tenn-goal-report/SKILL.md`
- `docs/agent_tasks/tenn_agent_constitution_skills_v1_20260606.md`
- `reports/agent_jobs/tenn_agent_constitution_skills_v1_20260606/README.md`
- `reports/agent_jobs/codex_agent_setup_audit_v1_20260606/README.md`

No other files were identified as required for this preservation slice.

## Reports Force-Added

No files were staged or force-added. The report directories remain ignored:

- `reports/agent_jobs/codex_agent_setup_audit_v1_20260606/`
- `reports/agent_jobs/tenn_agent_constitution_skills_v1_20260606/`

## Validation Commands

No commit-validation commands were run because the branch decision blocked
staging and committing. Preflight inspection was read-only:

- `pwd`
- `git branch --show-current`
- `git rev-parse HEAD`
- `git log -1 --oneline --decorate`
- `git remote -v`
- `git status --short --untracked-files=all`
- exact file existence and line-count checks for the allowlisted files
- `git status --short --ignored=matching -- <allowlisted paths>`
- `git branch -vv --no-abbrev`
- `git ls-remote --heads origin tmp/sloppy-fix-demo main migration/clean-runtime-baseline-reconstruct-v1`

## Staged / Committed Files

None.

## Remaining Unrelated Dirt

The shared checkout still contains unrelated dirty/untracked files, including:

- `cockpit-ui/package.json`
- `.gemini/skills/*`
- `.playwright-mcp/*`
- `.tenn/*`
- unrelated `docs/agent_tasks/*`
- `cockpit-ui/package-lock.json`
- `financial-engine_v2/backend/shared/tenn_extraction_active.lock`
- `outputs/*`
- `scripts/agent_job_contract.py`
- `scripts/agent_job_hook.py`
- `scripts/agent_job_registry.py`

These were not cleaned, staged, or modified.

## Wait State

```text
WAITING_ON_USER
Needed: branch/commit decision for the completed issue #78 agent constitution slice
Why: the new AGENTS.md, skills, task card, and reports are currently untracked/ignored and could be lost
Current safe state: content exists locally; no unrelated files staged
Options:
A. Commit exact allowlisted files on the current branch
B. Create a patch bundle only
C. Move/recreate the slice in a clean sibling worktree
Recommended: C. Move/recreate the slice in a clean sibling worktree or approve an explicit issue #78 preservation branch, because the current branch is tmp/sloppy-fix-demo and diverges from its remote ref.
```

## Next Recommended Prompt

```text
Use option C: preserve the issue #78 agent constitution slice in a clean sibling
worktree or explicit issue #78 preservation branch. Include only AGENTS.md, the
three .agents/skills SKILL.md files, the task card, and the two report README
files. Do not include unrelated shared-checkout dirt. Do not start registry
list-active --read-only until the preservation commit or patch is complete.
```
