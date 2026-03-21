---
name: migration-reviewer
description: Review Alembic migrations against SQLAlchemy model changes for completeness, safety, downgrade coverage, and chain integrity.
---

# Migration Reviewer

Use this skill whenever backend models or Alembic revisions change.

## Trigger Surfaces

- `financial-engine_v2/backend/app/models/`
- `financial-engine_v2/backend/app/alembic/versions/`

## Workflow

1. Read the changed model files.
2. Read the corresponding latest migration file.
3. Verify model changes are covered by migration operations.
4. Check:
   - `upgrade()` implemented
   - `downgrade()` implemented
   - `revision`, `down_revision`, `branch_labels` valid
5. Flag destructive or risky operations:
   - `drop_column`
   - `drop_table`
   - `nullable=False` without safe backfill/default
   - suspicious rename patterns
6. Verify chain integrity with:

```bash
financial-engine_v2/.venv/bin/alembic -c financial-engine_v2/backend/alembic.ini history --verbose 2>/dev/null | head -30
```

## Output

Return:

- detected model changes
- migration coverage checklist
- destructive operation assessment
- verdict: `SAFE TO APPLY`, `NEEDS REVIEW`, or `BLOCKED`
