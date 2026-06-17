# Guard

Decision: `pass_with_data_missing`

## Worktree

- Worktree: `/home/l4nd0/tenn-broad-run-provenance-risk-flags-v1-20260617`
- Branch: `safe/extraction-broad-run-provenance-risk-flags-v1-20260617`
- HEAD before this slice: `a0b54e668ebb0d103704bda03cc58b089f0e8301`
- Upstream: `origin/migration/clean-runtime-baseline-reconstruct-v1`
- Merge base: `6eff52404af61b9717bffb5a250e06209713d517`
- Ahead/behind before this slice: `0 2`
- Dirty state before task-card creation: clean

## Registry And Ledger

- Registry read-only command: `python3 scripts/agent_job_registry.py list-active --read-only --repo-root .`
- Registry result: `ok: true`, `active_jobs: []`
- Registry root: `/mnt/sdb2/home/l4nd0/tenn/.git/tenn-agent-registry`
- Live ledger: `DATA_MISSING`
- Committed ledger: `DATA_MISSING`

## Duplicate-Work Search

Checked:

- task cards and reports for `accepted_output_scale_magnitude_risk`
- exact GitHub PR search for `"accepted_output_scale_magnitude_risk"`
- exact GitHub issue search for `"accepted_output_scale_magnitude_risk"`
- related local and remote branch names for risk/provenance/scale work

Findings:

- No exact GitHub PR or issue matched `accepted_output_scale_magnitude_risk`.
- Prior local artifacts cover the parent implementation and the first saved
  LBL no-risk replay.
- Merged PR #364 covers persisted metric field provenance, not this positive
  risk fixture slice.

Duplicate-work classification:
`CONTINUE_VALIDATION_OF_LOCAL_BRANCH`

## Original Checkout Dirt

The original checkout at
`/home/l4nd0/tenn-nvme-clean-baseline-reconstruct-v1` remains dirty with
unrelated skill and task-card changes. This slice uses the clean sibling
worktree and does not touch the original checkout.

## Forbidden Boundaries

Avoided:

- count-24, count-32, random samples, broad extraction, broad backfill, and
  full ticker-universe extraction
- `run_multipass_extraction`
- runtime service starts
- DB, Qdrant, Redis, news, memory, source PDF, prompt, gold-label, schema,
  model, GPU, and service mutation
- GitHub mutation, push, and PR
