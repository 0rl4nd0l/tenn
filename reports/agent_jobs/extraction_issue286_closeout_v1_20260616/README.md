# Extraction Issue 286 Closeout

## Decision

`KEEP_OPEN_BOUNDARY_EXPLICIT`.

Issue #286 should remain open. Three extraction-only child slices are now merged
on `origin/migration/clean-runtime-baseline-reconstruct-v1`, but the remaining
persistence/schema portion of the issue is outside the current no-DB/no-schema
boundary.

## Live Evidence

- Issue: #286, open, `priority:p1`, `state:ready`.
- Issue comment: https://github.com/0rl4nd0l/tenn/issues/286#issuecomment-4715842193
- Closeout PR: https://github.com/0rl4nd0l/tenn/pull/354
- Current baseline: `9a61c20cf0db988d06948861644d79698f37138c`.
- Registry read-only: `ok=true`, `read_only=true`, `active_jobs=[]`.

## Completed Child Slices

- PR #349: accounting-number parsing.
  - URL: https://github.com/0rl4nd0l/tenn/pull/349
  - Merge commit: `4b2b9e4c769617e21e94bbc90ec0fc420f170df9`
  - Fixed deterministic parsing for common accounting metric strings.
- PR #350: payload-level field provenance.
  - URL: https://github.com/0rl4nd0l/tenn/pull/350
  - Merge commit: `227e1ce0d4e99c4a13ece8012a44adeba4585cdf`
  - Added structured `field_provenance` to extraction payloads.
- PR #351: field provenance consumer wiring.
  - URL: https://github.com/0rl4nd0l/tenn/pull/351
  - Merge commit: `9a61c20cf0db988d06948861644d79698f37138c`
  - Updated provenance/eval/review consumers to prefer structured
    `field_provenance` with legacy fallback.

## Remaining Boundary

#286 acceptance says each persisted metric can be traced to a document/run and
source excerpt/page when available. The remaining work is persistence/schema
wiring for field-level provenance. That is not authorized in this closeout
because it may touch DB schema, persistence models, migrations, or stored rows.

## Commands Run

- `git fetch origin --prune`: exit 0.
- `pwd && date -Iseconds && git rev-parse --show-toplevel && git branch --show-current && git rev-parse HEAD && git status --short --untracked-files=all && git remote -v`: exit 0.
- `python3 scripts/agent_job_registry.py list-active --read-only --repo-root .`: exit 0.
- `gh issue view 286 --json number,title,state,labels,updatedAt,url,body,comments`: exit 0.
- `gh pr view 349 --json number,title,state,url,mergedAt,mergeCommit,headRefName,baseRefName,commits,files`: exit 0.
- `gh pr view 350 --json number,title,state,url,mergedAt,mergeCommit,headRefName,baseRefName,commits,files`: exit 0.
- `gh pr view 351 --json number,title,state,url,mergedAt,mergeCommit,headRefName,baseRefName,commits,files`: exit 0.
- `gh pr create --base migration/clean-runtime-baseline-reconstruct-v1 --head safe/extraction-issue286-closeout-v1-20260616 ...`: exit 0, PR #354 opened.
- `gh issue comment 286 --body ...`: exit 0, posted status comment.

## Unsafe Actions Avoided

- No issue closure.
- No code change.
- No DB, schema, migration, Qdrant, Redis, news, memory, source PDF, prompt,
  gold-label, runtime, model, GPU, service, backfill, broad extraction, count-24,
  or count-32 action.

## Next Safe Action

Either leave #286 open with this status, or authorize a new persistence/schema
task card for the remaining persisted field-provenance boundary.
