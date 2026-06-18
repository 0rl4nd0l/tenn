# Classification

## Summary

| Path | Classification | Decision |
| --- | --- | --- |
| `.agents/skills/tenn-fix/SKILL.md` | `STALE_PRESERVE` | Preserve only the novel validation-environment guidance as an additive canonical patch. Reject raw stale hunks that would remove PR #368 content. |
| `.agents/skills/tenn-git-guard/SKILL.md` | `STALE_PRESERVE` | Preserve only the novel validation-environment guidance as an additive canonical patch. Reject raw stale hunks that would replace PR #368's docs-impact guard. |
| `.agents/skills/tenn-worker/SKILL.md` | `STALE_PRESERVE` | Preserve only the novel validation-environment guidance as an additive canonical patch. Reject raw stale hunks that would remove PR #368 model-routing fields. |
| `docs/agent_tasks/dev_flow_skills_bloat_audit_v1_20260617.md` | `MERGED_USE_CANONICAL` | Already represented by PR #368 and canonical task/report artifacts. Do not recommit from dirty checkout. |
| `docs/agent_tasks/validation_environment_autonomy_skill_update_v1_20260617.md` | `STALE_PRESERVE` | Not present in canonical or recent PRs. Preserve in clean PR with the narrow additive skill patch. |

## Required Questions

Is the dirty `tenn-fix` work already covered by PR #368?

`No`. PR #368 covers docs impact and model/worker routing in `tenn-fix`. The
dirty validation-environment guidance is not present in canonical. The raw dirty
file is stale because it would delete PR #368 content; only the additive
validation section is novel.

Is the dirty `tenn-git-guard` work already covered by PR #367 or #368?

`No`. PR #367 covers task-ledger preflight behavior, and PR #368 covers docs
impact guard behavior. The validation-environment guidance is not present in
either PR or current canonical.

Is the dirty `tenn-worker` work already covered by PR #368 or #370/#373?

`No`. PR #368 covers worker model-routing and decision-limit guidance. PR #370
and #373 are OpenCode bridge work and do not touch `tenn-worker`. The dirty
validation-environment guidance is novel.

Are the untracked task cards already represented by canonical task cards or
reports?

`Partly`.

- `dev_flow_skills_bloat_audit_v1_20260617.md` is represented by canonical
  task/report artifacts from PR #368.
- `validation_environment_autonomy_skill_update_v1_20260617.md` is absent from
  canonical and recent PRs, and is preserved.

Is any remaining diff genuinely novel and useful?

`Yes`. The validation-environment guidance is a narrow control-plane skill
improvement: when a standard validation tool is missing, agents should try safe
repo, `uv`, `/tmp` ephemeral, or stdlib-equivalent validation paths before
blocking, without mutating project dependencies or host-global/runtime config.

## Owner-Boundary Items

The old branch's two unmerged local commits are outside this dirty-file
classification and outside the approved preservation PR scope. They should not
be discarded by a broad reset or branch cleanup without a separate owner
decision.
