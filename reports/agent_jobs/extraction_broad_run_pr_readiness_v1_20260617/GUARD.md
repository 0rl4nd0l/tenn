# Guard

Decision: `pass_with_data_missing`

## Worktree

- Worktree: `/home/l4nd0/tenn-broad-run-provenance-risk-flags-v1-20260617`
- Branch: `safe/extraction-broad-run-provenance-risk-flags-v1-20260617`
- HEAD before this readiness report: `4f58d1b75c8fe91eec8ddab54428766b2b937005`
- Upstream: `origin/migration/clean-runtime-baseline-reconstruct-v1`
- Merge base: `6eff52404af61b9717bffb5a250e06209713d517`
- Ahead/behind before this readiness report: `0 3`
- Dirty state before this readiness report: clean

## Registry And Ledger

- Registry read-only: `ok: true`, `active_jobs: []`
- Registry root: `/mnt/sdb2/home/l4nd0/tenn/.git/tenn-agent-registry`
- Live ledger: `DATA_MISSING`
- Committed ledger: `DATA_MISSING`

## Duplicate-Work And PR Search

- Exact PR search for branch/topic found only merged adjacent PR #364:
  `[Extraction] Persist metric field provenance for ASX financial rows`.
- Exact issue search for `accepted_output_scale_magnitude_risk` returned `[]`.
- No open PR was found for this branch.

Duplicate-work classification:
`CONTINUE_LOCAL_PR_READINESS`

## Original Checkout Dirt

The original checkout remains dirty with unrelated skill/task-card changes and
was not touched:

- `.agents/skills/tenn-fix/SKILL.md`
- `.agents/skills/tenn-git-guard/SKILL.md`
- `.agents/skills/tenn-worker/SKILL.md`
- `docs/agent_tasks/dev_flow_skills_bloat_audit_v1_20260617.md`
- `docs/agent_tasks/validation_environment_autonomy_skill_update_v1_20260617.md`

## Forbidden Boundaries

Avoided:

- push, PR, and GitHub mutation
- count-24, count-32, random samples, broad extraction, broad backfill, and
  full ticker-universe extraction
- runtime service starts
- DB, Qdrant, Redis, news, memory, source PDF, prompt, gold-label, schema,
  model, GPU, and service mutation
