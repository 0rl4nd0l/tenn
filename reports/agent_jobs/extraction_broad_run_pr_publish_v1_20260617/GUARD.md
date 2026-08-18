# Guard

Decision: `pass_with_data_missing`

## Worktree

- Worktree: `/home/l4nd0/tenn-broad-run-provenance-risk-flags-v1-20260617`
- Branch: `safe/extraction-broad-run-provenance-risk-flags-v1-20260617`
- HEAD before publish scaffold: `f0d48118`
- Upstream before push: `origin/migration/clean-runtime-baseline-reconstruct-v1`
- Ahead/behind before publish scaffold: `0 4`
- Dirty state before publish scaffold: clean

## GitHub Preflight

- `gh --version`: available
- `gh auth status`: authenticated as `0rl4nd0l`
- Remote: `https://github.com/0rl4nd0l/tenn.git`
- Repository: `0rl4nd0l/tenn`
- Existing PR for head branch before publish: none
- PR base selected by task: `migration/clean-runtime-baseline-reconstruct-v1`

## Registry And Ledger

- Registry read-only result before publish: `ok: true`, `active_jobs: []`
- Live ledger: `DATA_MISSING`
- Committed ledger: `DATA_MISSING`

## Duplicate Work

Exact PR/issue searches found no existing PR for
`safe/extraction-broad-run-provenance-risk-flags-v1-20260617` and no exact issue
for `accepted_output_scale_magnitude_risk`.

Merged adjacent PR #364 covers persisted metric field provenance, not this
branch's broad-run reporting and fixture evidence.

## Forbidden Boundaries

Avoided so far:

- merge
- PR #318 use
- count-24, count-32, random samples, broad extraction, broad backfill, and full
  ticker-universe extraction
- runtime service starts
- DB, Qdrant, Redis, news, memory, source PDF, prompt, gold-label, schema,
  model, GPU, service, and production data mutation
