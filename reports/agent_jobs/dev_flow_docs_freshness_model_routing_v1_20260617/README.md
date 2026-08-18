# Dev Flow Docs Freshness And Model Routing V1

## Objective

Implement the docs freshness and model/subagent routing rules recommended by the
skills-bloat audit, preserving the audit task/report artifacts because they were
local-only on canonical at preflight.

## State

DONE_WITH_RISK

## Preflight Evidence

- Original checkout:
  `/home/l4nd0/tenn-nvme-clean-baseline-reconstruct-v1`
- Implementation worktree:
  `/home/l4nd0/tenn-docs-freshness-model-routing-v1-20260617`
- Branch: `control-plane/docs-freshness-model-routing-v1-20260617`
- Base/upstream: `origin/migration/clean-runtime-baseline-reconstruct-v1`
- HEAD at worktree creation:
  `6eff52404af61b9717bffb5a250e06209713d517`
- Registry read-only: `ok=true`, `active_jobs=[]`
- Live task ledger: `DATA_MISSING`
- Committed task ledger: `DATA_MISSING`
- Selected base and merge-base:
  `origin/migration/clean-runtime-baseline-reconstruct-v1` /
  `6eff52404af61b9717bffb5a250e06209713d517`

## Duplicate-Work Classification

- Classification: `warning`
- Related open PR: #367,
  `[Control Plane] Add task ledger runtime and handoff workflow`
- Decision: proceed narrowly because #367 implements ledger runtime and
  repo-native handoff, while this task implements docs-impact and model-routing
  gates. The files overlap on some control-plane skills/templates, so merge
  order may require a small rebase after #367 lands.
- `tenn-handoff` skill status on canonical: absent; not edited here.
- `docs/dev_flow/templates/HANDOFF.md` status on canonical: absent; created
  here only as a generic handoff template carrying docs/model routing fields.

## Files Touched

- `.agents/skills/tenn-fix/SKILL.md`
- `.agents/skills/tenn-worker/SKILL.md`
- `.agents/skills/tenn-review-board/SKILL.md`
- `.agents/skills/tenn-code-reviewer/SKILL.md`
- `.agents/skills/tenn-git-guard/SKILL.md`
- `docs/dev_flow/templates/WORKER_RESULT.md`
- `docs/dev_flow/templates/PR_REVIEW.md`
- `docs/dev_flow/templates/HANDOFF.md`
- `docs/dev_flow/templates/DOCS_IMPACT.md`
- `docs/dev_flow/templates/MODEL_ROUTING.md`
- `docs/agent_tasks/dev_flow_skills_bloat_audit_v1_20260617.md`
- `docs/agent_tasks/dev_flow_docs_freshness_model_routing_v1_20260617.md`
- `reports/agent_jobs/dev_flow_skills_bloat_audit_v1_20260617/**`
- `reports/agent_jobs/dev_flow_docs_freshness_model_routing_v1_20260617/**`

## Files Intentionally Not Touched

- Product/runtime/data/extraction/count-24 paths.
- Host-global files under `/home/l4nd0/.codex` or `/home/l4nd0/.agents`.
- `.agents/skills/tenn-handoff/SKILL.md`, because it is absent on canonical and
  owned by open PR #367.
- `.agents/skills/tenn-explain/SKILL.md`, because this slice did not need it.
- `scripts/docs_impact.py`, because the task explicitly forbids implementing a
  complex docs-impact script in this run.
- The unrelated validation-environment-autonomy edits in the original checkout.

## Docs Impact

- docs_impact: `DOCS_UPDATED`
- docs_checked:
  - `reports/agent_jobs/dev_flow_skills_bloat_audit_v1_20260617/DOCS_FRESHNESS_DESIGN.md`
  - `reports/agent_jobs/dev_flow_skills_bloat_audit_v1_20260617/MODEL_ROUTING_DESIGN.md`
  - `reports/agent_jobs/dev_flow_skills_bloat_audit_v1_20260617/SUBAGENT_DELEGATION_DESIGN.md`
  - `.agents/skills/tenn-fix/SKILL.md`
  - `.agents/skills/tenn-code-reviewer/SKILL.md`
  - `.agents/skills/tenn-git-guard/SKILL.md`
  - `docs/dev_flow/templates/PR_REVIEW.md`
  - `docs/dev_flow/templates/WORKER_RESULT.md`
- docs_changed:
  - `.agents/skills/tenn-fix/SKILL.md`
  - `.agents/skills/tenn-worker/SKILL.md`
  - `.agents/skills/tenn-review-board/SKILL.md`
  - `.agents/skills/tenn-code-reviewer/SKILL.md`
  - `.agents/skills/tenn-git-guard/SKILL.md`
  - `docs/dev_flow/templates/DOCS_IMPACT.md`
  - `docs/dev_flow/templates/MODEL_ROUTING.md`
  - `docs/dev_flow/templates/HANDOFF.md`
  - `docs/dev_flow/templates/WORKER_RESULT.md`
  - `docs/dev_flow/templates/PR_REVIEW.md`
- docs_followup:
  - Reconcile `docs/dev_flow/templates/HANDOFF.md` and
    `.agents/skills/tenn-handoff/SKILL.md` after PR #367 is merged or parked.
- reason: This change updates Codex control-plane skills/templates to require
  docs-impact and model/subagent routing evidence.

## Model And Subagent Routing

- task_tier: `large`
- recommended_model: `high reasoning`
- actual_model: `high reasoning Codex session`
- why_this_model: multi-file control-plane workflow policy affects future agent
  closeout and delegation behavior.
- worker_model_allowed: `mini/low-cost for evidence_only`
- worker_decision_limit: `evidence_only`
- escalation_needed: `no`; PR #367 is related but not equivalent.
- subagents_used: none.

## Commands Run

See `VALIDATION.md` for command results. Local validation passed before commit,
push, and PR creation.

## Unsafe Actions Avoided

- No product/runtime/data/extraction/count-24 mutation.
- No host-global mutation.
- No cleanup, branch deletion, reset, stash, merge, rebase, or prune.
- No GitHub mutation before local validation.
- No dependency, runtime, or model-provider configuration changes.

## Remaining Risk

- Open PR #367 touches some of the same control-plane skills and creates the
  repo-native handoff skill/template. This PR may need a small rebase or manual
  reconciliation after #367 lands.

## Next Recommended Prompt

```text
/goal Reconcile docs freshness/model routing PR with PR #367 after one of the
branches merges or is parked. Preserve Codex-control-plane wording, keep Tenn
specificity only for task-card/registry/owner-boundary/extraction safety, and
do not touch product/runtime/data/extraction/count-24 paths.
```
