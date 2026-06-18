# Dirty Files

## Original Dirty Worktree

- Path: `/home/l4nd0/tenn-nvme-clean-baseline-reconstruct-v1`
- Branch: `control-plane/dev-flow-agent-task-ledger-v1-20260616`
- HEAD: `137535b81a5b60d1f94ca630605caadccc4e1b99`
- Upstream: `origin/control-plane/dev-flow-agent-task-ledger-v1-20260616`
- Canonical comparison: local branch is `2` commits ahead and `37` commits
  behind `origin/migration/clean-runtime-baseline-reconstruct-v1`.
- Remote branch comparison: local branch is `2` commits ahead and `0` behind
  `origin/control-plane/dev-flow-agent-task-ledger-v1-20260616`.

## Git Status

```text
 M .agents/skills/tenn-fix/SKILL.md
 M .agents/skills/tenn-git-guard/SKILL.md
 M .agents/skills/tenn-worker/SKILL.md
?? docs/agent_tasks/dev_flow_skills_bloat_audit_v1_20260617.md
?? docs/agent_tasks/validation_environment_autonomy_skill_update_v1_20260617.md
```

## Dirty Skill Patch

Relative to the old branch HEAD, the dirty patch adds the same
`Validation Environment Autonomy` section to:

- `.agents/skills/tenn-fix/SKILL.md`
- `.agents/skills/tenn-git-guard/SKILL.md`
- `.agents/skills/tenn-worker/SKILL.md`

Patch size relative to old branch HEAD:

```text
.agents/skills/tenn-fix/SKILL.md       | 25 +++++++++++++++++++++++++
.agents/skills/tenn-git-guard/SKILL.md | 25 +++++++++++++++++++++++++
.agents/skills/tenn-worker/SKILL.md    | 25 +++++++++++++++++++++++++
3 files changed, 75 insertions(+)
```

Against current canonical, the raw working-tree state is not safe to replay.
It would remove PR #368 docs-impact/model-routing content while adding the
validation guidance. That stale removal was rejected.

## Untracked Task Cards

`docs/agent_tasks/dev_flow_skills_bloat_audit_v1_20260617.md`

- Present in canonical.
- Present in PR #368 file list.
- Represented by canonical reports under
  `reports/agent_jobs/dev_flow_skills_bloat_audit_v1_20260617/`.

`docs/agent_tasks/validation_environment_autonomy_skill_update_v1_20260617.md`

- Not present in canonical.
- Not present in #367, #368, #370, or #373.
- Describes the same validation-environment guidance as the dirty skill patch.
- Preserved in the clean sibling worktree as the task card for the narrow
  preservation PR.

## Branch-Divergence Note

The original branch also has two local commits not on canonical. They are not
dirty worktree files, but they affect cleanup safety:

```text
+ 90dda42a735b61f170f008a815bf1c8aafb455d6 Add weather track feature utility packet
+ 137535b81a5b60d1f94ca630605caadccc4e1b99 fix: quote git hygiene skill description
```

The weather-track packet touches artifacts, scripts, tests, reports, and a task
card outside this request's approved control-plane preservation scope. It was
not adopted into this PR.
