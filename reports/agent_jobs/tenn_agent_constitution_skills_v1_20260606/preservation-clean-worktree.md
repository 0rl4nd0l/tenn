# Issue #78 Clean Worktree Preservation

Date: 2026-06-06

## Objective

Preserve the completed issue #78 Tenn agent constitution and repo-backed skill
slice in a clean sibling worktree without carrying over unrelated dirty files
from the shared source checkout.

This is Repo Hygiene / Control Plane documentation work only. It does not
modify Tenn product, backend, frontend, runtime, data, extraction, prompt,
gold-label, service config, database, Qdrant, news, memory, or backfill state.

## Source Worktree

- Path: `/home/l4nd0/tenn-nvme-clean-baseline-reconstruct-v1`
- Branch: `tmp/sloppy-fix-demo`
- HEAD: `dfa313aaa6c1b34696f4bf9a8bd430636e5792ce`
- Origin: `https://github.com/0rl4nd0l/tenn.git`
- Source status: dirty before preservation.
- Source mutation: none. The source worktree was read from only.

## Target Worktree

- Path: `/home/l4nd0/tenn-issue-78-agent-constitution-skills-v1-20260606`
- Branch: `repo-hygiene/issue-78-agent-constitution-skills-v1-20260606`
- Base: `origin/migration/clean-runtime-baseline-reconstruct-v1`
- Base HEAD: `9436d1d32de0da5423b8edcfc7efc883ccac3fd6`
- Origin: `https://github.com/0rl4nd0l/tenn.git`

## Copied Files

- `AGENTS.md`
- `.agents/skills/tenn-financial-metric-extraction/SKILL.md`
- `.agents/skills/tenn-task-card-registry-safety/SKILL.md`
- `.agents/skills/tenn-goal-report/SKILL.md`
- `docs/agent_tasks/tenn_agent_constitution_skills_v1_20260606.md`
- `reports/agent_jobs/tenn_agent_constitution_skills_v1_20260606/README.md`
- `reports/agent_jobs/tenn_agent_constitution_skills_v1_20260606/preservation.md`
- `reports/agent_jobs/codex_agent_setup_audit_v1_20260606/README.md`

## Closeout File Added

- `reports/agent_jobs/tenn_agent_constitution_skills_v1_20260606/preservation-clean-worktree.md`

## Force-Add Notes

Reports are ignored by `.git/info/exclude`, so the report README, preservation
note, audit README, and this clean-worktree closeout note must be force-added
if committed.

The clean base also ignores `.agents/` through `.gitignore:47`. The three
allowlisted repo skill files must therefore be force-added to preserve the
completed issue #78 skill skeletons in the clean worktree. No broad `.agents`
migration or host-skill copy was performed.

## Validation

| Command | Exit | Notes |
| --- | ---: | --- |
| `git diff --check` | 0 | No whitespace errors in tracked diff before staging. |
| `python3 scripts/agent_job_contract.py validate docs/agent_tasks/tenn_agent_constitution_skills_v1_20260606.md` | 0 | Task-card validator returned `ok: true`. |
| Skill frontmatter parse for the three `.agents/skills/*/SKILL.md` files | 0 | All three files have `name` and `description` frontmatter. |
| Manual markdown review | 0 | Confirmed AGENTS sections, task-card header, and skill headers. |

Final staged diff checks are run after staging so ignored force-added files are
included in the commit validation surface.

## Product / Runtime / Extraction Safety Check

After copying the allowlisted files, the changed-path scan returned no paths
under product, runtime, extraction, backend, frontend, data, tests, outputs,
prompt, gold-label, Qdrant, news, memory, `.gemini`, `.playwright-mcp`, or
`.tenn` surfaces.

## Committed Files

Pending staging and commit in the clean target worktree.

## Commit SHA

Pending. The exact commit SHA is assigned after the commit object is created
and will be reported in the final Codex closeout. A committed file cannot
truthfully contain its own final object ID without changing that object ID.

## Original Source Dirty State Left Untouched

The original source worktree remains dirty and was not cleaned, reset, stashed,
rebased, merged, pruned, deleted, or otherwise modified. Observed unrelated
dirty surfaces include:

- `cockpit-ui/package.json`
- `.gemini/skills/*`
- `.playwright-mcp/*`
- `.tenn/*`
- multiple unrelated `docs/agent_tasks/*`
- `financial-engine_v2/backend/shared/tenn_extraction_active.lock`
- `outputs/*`
- untracked registry/control-plane scripts

## Unsafe Actions Avoided

- No product, backend, frontend, runtime, data, extraction, prompt, gold-label,
  service config, DB, Qdrant, news, memory, source PDF, or backfill mutation.
- No dependency installation.
- No broad tests.
- No GitHub issue or PR mutation.
- No push.
- No registry `list-active --read-only` implementation.
- No cleanup or mutation of the dirty source worktree.

## Next Recommended Prompt

Implement `python3 scripts/agent_job_registry.py list-active --read-only` with
tests proving it does not create locks, owner files, registry roots, status
files, or timestamp changes.
