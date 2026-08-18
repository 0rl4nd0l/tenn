# Tenn Git Hygiene Skill v1

Date: 2026-06-07
State: `DONE_WITH_RISK`
Task card: `docs/agent_tasks/tenn_git_hygiene_skill_v1_20260607.md`

## Objective

Create a Tenn-native instruction-only Git Hygiene control-plane skill for
safely inspecting, classifying, preserving, integrating, and recommending
cleanup for Tenn Git branches, worktrees, dirty files, stale uncommitted work,
and merge/rebase candidates.

This is development workflow/control-plane infrastructure only. No product,
backend, frontend, runtime, data, extraction, source-PDF, gold-label, prompt,
DB, Qdrant, news, memory, service, production data, model, GPU, or backfill
surface was touched.

## Work Surface

- Worktree: `/home/l4nd0/tenn-git-hygiene-skill-v1-20260607`
- Branch: `safe/tenn-git-hygiene-skill-v1-20260607`
- Base: `origin/migration/clean-runtime-baseline-reconstruct-v1`
- Base/HEAD before edits: `10c162a5162b3e5fc1306cdd908b23bfa6f0a5a8`
- Origin: `https://github.com/0rl4nd0l/tenn.git`

This isolated worktree was created because the cwd greyhound checkout and the
existing Tenn baseline/skill worktrees were already dirty. Existing dirty
worktrees were inspected only enough to select a safe write surface and were not
cleaned or modified.

## Files Changed

- `.agents/skills/tenn-git-hygiene/SKILL.md`
- `docs/agent_tasks/tenn_git_hygiene_skill_v1_20260607.md`
- `reports/agent_jobs/tenn_git_hygiene_skill_v1_20260607/README.md`

No optional cross-reference was added to `tenn-frame-design` or
`tenn-goal-report`.

## Exact Skill Summary

`tenn-git-hygiene` is an instruction-only control-plane skill. It defaults to
report-first Git hygiene inspection and requires approval before preservation,
integration, or cleanup actions. It defines mode gates, safety tiers, Tenn Git
preflight commands, dirty-work age classification, branch/worktree/file
classification, merge/rebase/cherry-pick rules, Integration Plan requirements,
and a report-only Scribe/Watcher pattern.

The skill explicitly states that dirty work older than 24h is not trash. It is
unclassified work requiring preservation, ownership, or disposal decision.

## Safety Tiers

- Tier 0: read-only commands.
- Tier 1: report-local writes.
- Tier 2: preservation actions.
- Tier 3: integration actions.
- Tier 4: destructive actions.

The created files are Tier 1 report-local/control-plane writes under the task
card allowlist. The skill requires explicit approval for Tiers 2-4.

## Scribe Boundaries

The skill allows a Scribe/Watcher to maintain:

- `WORKTREE_LEDGER.md`
- `BRANCH_LEDGER.md`
- `DIRTY_WORK_LEDGER.md`
- `RECOMMENDATIONS.md`

The Scribe/Watcher must not mutate Git state, GitHub, registry, product files,
runtime state, or data. It must not clean, stash, reset, rebase, merge,
cherry-pick, delete, push, force-push, or mutate GitHub.

## Approval Gates

- `AUDIT_ONLY`: read-only inventory and classification.
- `REPORT_LOCAL`: task-card, report, and ledger writes only.
- `PRESERVE_ONLY`: patch bundle, exact allowlisted preservation commit, or
  archival branch only after approval.
- `INTEGRATE_APPROVAL_REQUIRED`: merge, rebase, cherry-pick, PR, or GitHub
  action only after approval.
- `CLEANUP_APPROVAL_REQUIRED`: branch/worktree/delete/clean/stash-drop actions
  only after approval.

## Validation

| Command | Exit | Result |
| --- | ---: | --- |
| `python3 scripts/agent_job_registry.py list-active --read-only --repo-root .` | 0 | Preflight returned `read_only: true`, `lock_acquired: false`, and no active jobs in the isolated worktree. |
| Skill frontmatter parse | 0 | Parsed `.agents/skills/tenn-git-hygiene/SKILL.md`; `name` and `description` present. |
| `python3 scripts/agent_job_contract.py validate docs/agent_tasks/tenn_git_hygiene_skill_v1_20260607.md` | 0 | Task card validates with no issues. |
| `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/tenn_git_hygiene_skill_v1_20260607.md --no-write-report` | 0 | Changed files visible to Git stayed inside the allowlist. The ignored skill/report files are not visible to this checker. |
| `git diff --check` | 0 | No whitespace errors in visible tracked/untracked diff. |
| `git diff --no-index --check /dev/null .agents/skills/tenn-git-hygiene/SKILL.md` | 0 | Explicit whitespace check for ignored new skill file passed. |
| `git diff --no-index --check /dev/null reports/agent_jobs/tenn_git_hygiene_skill_v1_20260607/README.md` | 0 | Explicit whitespace check for ignored new report file passed. |
| `git check-ignore -v .agents/skills/tenn-git-hygiene/SKILL.md reports/agent_jobs/tenn_git_hygiene_skill_v1_20260607/README.md` | 0 | Confirmed `.agents/` is ignored by `.gitignore` and `reports/` by Git info exclude. |
| `git status --short --ignored --untracked-files=all .agents/skills/tenn-git-hygiene/SKILL.md reports/agent_jobs/tenn_git_hygiene_skill_v1_20260607/README.md docs/agent_tasks/tenn_git_hygiene_skill_v1_20260607.md` | 0 | Shows task card as `??` and skill/report as `!!` ignored files. |
| `git status --short --untracked-files=all` | 0 | Final normal status shows only `?? docs/agent_tasks/tenn_git_hygiene_skill_v1_20260607.md` because the skill/report paths are ignored. |

## Unsafe Actions Avoided

- No product/backend/frontend/runtime/data/extraction changes.
- No DB, Qdrant, news, memory, source-PDF, gold-label, prompt, service,
  production data, model, GPU, or backfill mutation.
- No dependency installation.
- No push.
- No GitHub issue or PR creation, edit, comment, close, label, merge, or other
  mutation.
- No `git clean`, `git reset --hard`, stash drop, branch deletion, worktree
  removal, rebase, merge, cherry-pick, force-push, or remote branch deletion.
- No cleanup or modification of existing dirty worktrees.

## DATA_MISSING

- No live GitHub PR/issue read-only commands were run because GitHub state was
  not needed to create this instruction-only skill.
- Dirty-work age classification was defined in the skill but not applied to the
  full Tenn repo graph in this slice.

## Ignored File Note

`.agents/` is ignored by repo `.gitignore`, and `reports/` is ignored by the
shared Git info exclude. The required skill and report files exist on disk but
do not appear in normal `git status --short --untracked-files=all` output and
would require an explicit force-add in a later approved preservation/commit
step.

## Next Recommended Report-only Git Hygiene Audit Prompt

```text
Use the new `tenn-git-hygiene` skill in AUDIT_ONLY mode to inventory Tenn
branches, worktrees, and dirty files against
`origin/migration/clean-runtime-baseline-reconstruct-v1`. Run only the required
preflight plus read-only Git/GitHub inspection. Classify dirty work by age,
owner, intent, risk, and recommended preservation/integration/cleanup action.
Write only a REPORT_LOCAL ledger bundle if approved, and do not clean, stash,
reset, rebase, merge, cherry-pick, delete, push, mutate GitHub, or touch
product/runtime/data/extraction surfaces.
```
