# State

- status: `LOCAL_FIX_VALIDATED_READY_TO_PUBLISH`
- started_at: `2026-06-26T23:19:58+10:00`
- branch: `safe/issue261-malformed-date-current-base-v2-20260626`
- worktree: `/home/l4nd0/tenn-issue261-malformed-date-current-base-v2-20260626`
- base: `origin/migration/clean-runtime-baseline-reconstruct-v1`
- base_head_at_start: `26e6000ff7b02a4e05ab6a7f31f939b34aa55215`
- supersedes_if_successful: PR #419

## Local Fix

- `financial-engine_v2/backend/app/services/source_weighting.py`
  - Coerces `half_life_days` before the date-parse guard so invalid half-life
    inputs are not mislabeled as malformed dates.
  - Catches malformed `published_at` parse failures, assigns neutral
    `recency_decay = 1.0`, and preserves visible recency metadata.
- `financial-engine_v2/backend/tests/test_tenn_chat_and_weighting.py`
  - Adds direct malformed-date coverage.
  - Adds invalid half-life coverage.
  - Adds chat strategy coverage proving a malformed-date chunk does not drop a
    valid neighbor.
