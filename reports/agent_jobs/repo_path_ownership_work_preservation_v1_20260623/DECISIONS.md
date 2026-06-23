# Decisions

## Use A Fresh Sibling Worktree

Decision: `CONTINUE` in a fresh task worktree.

Reason: `/home/l4nd0/tenn` was a valid git worktree, but it was dirty with
board-validator control-plane work at initial inspection and later rechecked as
clean but not based on current canonical. This task touches overlapping
control-plane docs, so implementing there would risk stale-path decisions.

Chosen worktree:

```text
/home/l4nd0/tenn-repo-path-ownership-work-preservation-v1-20260623
```

## No New Visible Skill

Decision: no new visible repo-backed skill.

Reason: `tenn-git-guard` already owns branch, worktree, ledger, registry, and
duplicate-work preflight. The smallest useful control-plane change is a guard
mode/field extension plus a doc source of truth.

Visible skill count remains expected at 10.

## Prior Work Classification

Relevant prior work was adopted or superseded:

- `ADOPT`: PR #397 portable guard first guidance.
- `ADOPT`: `dev_flow_agent_task_ledger_v1_20260616` duplicate-work ledger
  policy.
- `ADOPT`: `dev_flow_ledger_runtime_handoff_replay_v1_20260618` latest-ledger
  classification behavior.
- `SUPERSEDE`: `canonical_path_mountpoint_audit_v1_20260522` report-only path
  rule, because it did not leave a current active control-plane source of
  truth and predated the current portable guard.

No open PR or active registry job was found for this exact lane.

## Docs Impact

docs_impact: `DOCS_UPDATED`

docs_checked:

- `AGENTS.md`
- `docs/README.md`
- `docs/dev_flow/CODEX_OPERATOR_GUIDE.md`
- `docs/dev_flow/CONTROL_PLANE_STATUS.md`
- `docs/dev_flow/CONTROL_PLANE_OPEN_WORK.md`
- `docs/dev_flow/SKILLS_SURFACE.md`
- `.agents/skills/tenn-git-guard/SKILL.md`
- `.agents/skills/tenn-fix/SKILL.md`

docs_changed:

- `AGENTS.md`
- `docs/dev_flow/CODEX_OPERATOR_GUIDE.md`
- `docs/dev_flow/CONTROL_PLANE_STATUS.md`
- `docs/dev_flow/CONTROL_PLANE_OPEN_WORK.md`
- `docs/dev_flow/REPO_PATH_OWNERSHIP_AND_WORK_PRESERVATION.md`
- `docs/dev_flow/SKILLS_SURFACE.md`
- `.agents/skills/tenn-git-guard/SKILL.md`
- `.agents/skills/tenn-fix/SKILL.md`

docs_followup: none.

reason: the task changes operator flow, guard output, path classification, and
duplicate-work stop behavior.

## Model And Worker Routing

task_tier: medium

recommended_model: standard coding model with high attention to repo evidence

actual_model: Codex

why_this_model: control-plane docs plus a focused guard/test change; no product
runtime or financial-truth mutation.

worker_model_allowed: false

worker_decision_limit: not_applicable

escalation_needed: false
