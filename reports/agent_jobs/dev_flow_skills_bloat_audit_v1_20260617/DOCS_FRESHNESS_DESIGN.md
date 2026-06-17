# Docs Freshness Design

## Goal

Make documentation freshness a closeout gate without turning every task into a
docs rewrite.

## Required Workflow Addition

Every `/fix`, `tenn-code-reviewer`, and handoff run must include a Docs Impact
Check.

If behavior, schema, command usage, workflow, validation, operator steps,
artifact shape, API, data model, skill trigger, or safety boundary changed, then
affected docs/templates/skills must be updated in the same task or a
`DOCS_FOLLOWUP` must be created.

If no docs update is required, record `DOCS_NOT_REQUIRED` with a reason.

## Template Fields

Add these fields to task cards, `STATE.md`, `PR_REVIEW.md`, and handoff
templates:

```yaml
docs_impact: DOCS_NOT_REQUIRED | DOCS_UPDATED | DOCS_FOLLOWUP | DATA_MISSING
docs_checked:
  - <path>
docs_changed:
  - <path or none>
docs_followup:
  - <issue/report/task path or none>
reason: <short reason>
```

## Docs Freshness Metadata

For durable docs, templates, and skills, add optional metadata:

```yaml
last_verified_commit: <sha>
last_verified_pr: <number or none>
source_of_truth_files:
  - <path>
stale_if_files:
  - <path>
owner: <role or lane>
evidence_grade: VERIFIED | USER_REPORTED | INFERRED | UNKNOWN | CONFLICT
```

## Docs Impact Decision Table

| Change type | Required outcome |
| --- | --- |
| User-visible behavior changes | Update user/operator docs or create `DOCS_FOLLOWUP`. |
| CLI command or validation command changes | Update task cards/templates/README or create `DOCS_FOLLOWUP`. |
| Report artifact shape changes | Update `docs/dev_flow/templates/**` or report template docs. |
| Skill trigger or safety boundary changes | Update the skill and skill registry docs. |
| Schema/API/data model changes | Update schema/API docs and affected tests or create follow-up. |
| No behavior/operator/doc contract change | Record `DOCS_NOT_REQUIRED` with reason. |

## Future `scripts/docs_impact.py`

Recommendation: implement a future `scripts/docs_impact.py` after the active
ledger/handoff work is resolved.

Suggested behavior:

- read changed files from git diff
- map code/config/template/skill paths to likely docs
- emit JSON with `docs_impact`, `docs_checked`, `docs_changed`,
  `docs_followup`, and `reason`
- fail closed only when a high-confidence docs surface is stale and no
  follow-up is recorded
- never mutate docs automatically

Initial command:

```bash
python3 scripts/docs_impact.py --task-card <task_card> --repo-root . --json
```

## Where To Wire It Later

- `tenn-fix`: after implementation and before code review.
- `tenn-code-reviewer`: review whether docs impact was honestly handled.
- `tenn-goal-report`: include docs impact in closeout.
- `docs/dev_flow/templates/STATE.md`
- `docs/dev_flow/templates/PR_REVIEW.md`
- future `docs/dev_flow/templates/HANDOFF.md`
- task-card validator only after report-only behavior is proven stable.
