# Novel Diffs

## Preserved

The clean preservation patch adds one section to each of three canonical skill
files:

```text
## Validation Environment Autonomy

If a requested validation command fails because a standard validation tool is
missing, try safe existing or ephemeral validation environments before blocking.
```

The section then defines a bounded resolution order:

1. existing repo venv
2. documented repo test command
3. available dependency runner such as `uv`
4. ephemeral venv under `/tmp` or another throwaway path
5. `unittest` or stdlib fallback when equivalent
6. `WAITING_ON_USER` only after safe paths fail

It explicitly prohibits project dependency, CI, system package, runtime service,
and host-global config mutation without approval.

## Rejected From Raw Dirty Patch

The dirty working-tree patch was not replayed as-is because the old branch is
behind canonical. On canonical, those same files already contain PR #368's
docs-impact and model-routing guidance. Replaying the raw dirty worktree state
would remove that merged content.

## Clean Preservation Diff

Expected clean diff before reports:

```text
.agents/skills/tenn-fix/SKILL.md       | 25 +++++++++++++++++++++++++
.agents/skills/tenn-git-guard/SKILL.md | 25 +++++++++++++++++++++++++
.agents/skills/tenn-worker/SKILL.md    | 25 +++++++++++++++++++++++++
3 files changed, 75 insertions(+)
```

The preserved task card is:

```text
docs/agent_tasks/validation_environment_autonomy_skill_update_v1_20260617.md
```

The already-merged task card intentionally not preserved from dirty state is:

```text
docs/agent_tasks/dev_flow_skills_bloat_audit_v1_20260617.md
```
