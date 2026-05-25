# Repo-Native Goals

Goal files are parent orchestration contracts for multi-step Tenn work. They
record the objective, lane ownership, task-card link, report output directory,
validation expectations, hard stops, merge-parking status, and save
recommendation for a larger goal.

Goal files do not replace task cards. A task card remains the implementation
contract for a dev-agent job, including `allowed_files`, registry claim, overlap
check, and `check-diff` enforcement. A goal may point to one current task card
or to a sequence of task cards, but each implementation slice still needs its
own validated task card before mutation.

## Files

- `_template.md` is the starting point for a new goal file.
- `goal_schema_v1.json` validates only the YAML frontmatter shape for
  `docs/goals/*.md` files. It does not validate prose body sections.

## Validation Scope

Use `scripts/agent_goal_contract.py` with explicit paths or `--changed`.

Examples:

```bash
python3 scripts/agent_goal_contract.py validate docs/goals/_template.md
python3 scripts/agent_goal_contract.py validate --changed
```

The helper intentionally does not scan every historical goal, task-card, or
status artifact by default. Existing artifacts are only checked when named
directly or when they are part of the current changed-file set.

## Boundary

Goals may document later merge parking, but this first control-plane slice does
not implement merge parking, Git-ref claims, auto-merge, broad CI enforcement,
or cleanup automation. Those require separate task cards and explicit approval.
