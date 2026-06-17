# Git Guard

## Result

- Decision: `pass_with_data_missing`
- Duplicate-work classification: `PROCEED_AS_NEW_WORK_WITH_REUSE`
- Worktree: `/home/l4nd0/tenn-broad-run-provenance-risk-flags-v1-20260617`
- Branch: `safe/extraction-broad-run-provenance-risk-flags-v1-20260617`
- HEAD: `6eff52404af61b9717bffb5a250e06209713d517`
- Upstream: `origin/migration/clean-runtime-baseline-reconstruct-v1`
- Selected base: `origin/migration/clean-runtime-baseline-reconstruct-v1`
- Merge-base: `6eff52404af61b9717bffb5a250e06209713d517`
- Ahead/behind at start: `0 0`

## Evidence Checked

- `pwd`
- `git branch --show-current`
- `git rev-parse HEAD`
- `git remote -v`
- `git rev-parse --abbrev-ref --symbolic-full-name @{u}`
- `git status --short --untracked-files=all`
- `python3 scripts/agent_job_registry.py list-active --read-only --repo-root .`
- live and committed task-ledger file checks
- `git merge-base HEAD origin/migration/clean-runtime-baseline-reconstruct-v1`
- `git rev-list --left-right --count origin/migration/clean-runtime-baseline-reconstruct-v1...HEAD`
- task-card/report/branch/worktree/GitHub fallback searches for accepted-output, row-level provenance, scale, broad extraction, WHC, HCW, EDU, and LBL

## Registry And Ledger

- Registry read-only: `ok: true`, `active_jobs: []`, `read_only: true`
- Registry root: `/mnt/sdb2/home/l4nd0/tenn/.git/tenn-agent-registry`
- Live Task Ledger: `DATA_MISSING`
- Committed Task Ledger: `DATA_MISSING`
- Ledger update result: `DATA_MISSING`; no ledger file existed to append to. The fallback duplicate-work search was clean enough for the narrow allowed-files implementation.

## Matching Candidates

- Merged provenance and extraction guard work exists and is reused as context: PR #301, #319, #322, #350, #351, #362, #364, #365, and #366.
- Open PR search for this exact broad-run output contract returned no covering PR.
- Issue #96 remains related but broader than this bounded evidence-surfacing slice.
- Local historical worktrees exist for adjacent provenance/scale tasks; none owned this exact post-PR365 broad-run row-level provenance plus risk-flag surface.

## Boundaries Preserved

- No DB, Qdrant, Redis, news, memory, source PDF, prompt, gold-label, schema, model, GPU, service, or production-data mutation.
- No count-24, count-32, broad backfill, full ticker-universe extraction, runtime service start, PR #318 patch use, push, or PR.
