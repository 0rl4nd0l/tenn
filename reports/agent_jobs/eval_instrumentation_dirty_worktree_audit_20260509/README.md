# Eval Dirty Worktree Audit: 2026-05-09

## Executive summary
The dirty worktree `/mnt/sdb2/home/l4nd0/tenn-eval-instrumentation-20260421` is on branch `audit/eval-instrumentation-bounded-20260421` at `49a5d34a49b1`, which is an ancestor of the current main preserve head (`dabbc456...`). It has 8 modified tracked files across backend extraction/eval code and tests. The diff is mostly additive evaluation instrumentation (runtime provenance fields, runtime timeout/cache metadata, report rollup columns) and is not yet represented in main preserve state.

## Confirmed facts
- Main preflight command set executed and captured:
  - `date -Iseconds`: `2026-05-09T13:00:09+10:00`
  - `git rev-parse --show-toplevel`: `/mnt/sdb2/home/l4nd0/tenn`
  - `git rev-parse --abbrev-ref HEAD`: `preserve/dirty-work-20260430T065748Z`
  - `git rev-parse HEAD`: `dabbc456e42f737d12e6a1d979e6189e0936e865`
  - `git status --short --untracked-files=all` (main): `?? docs/agent_tasks/cockpit_upgrade_integration_readiness_20260509.md` and `?? docs/agent_tasks/eval_instrumentation_dirty_worktree_audit_20260509.md`
  - `python3 scripts/agent_job_registry.py list-active`: `active_jobs: []`
  - `python3 scripts/agent_job_registry.py check-overlap docs/agent_tasks/eval_instrumentation_dirty_worktree_audit_20260509.md`: no issues
  - `python3 scripts/agent_job_contract.py validate ...`: `ok: true`
  - `python3 scripts/agent_job_contract.py check-diff ...`: failed due external untracked `docs/agent_tasks/cockpit_upgrade_integration_readiness_20260509.md` outside allowed files
- Dirty worktree preflight command set executed:
  - branch: `audit/eval-instrumentation-bounded-20260421`
  - `HEAD`: `49a5d34a49b105bdba28ac5ed42649d57b4f4976`
  - `status --short --untracked-files=all`: only 8 tracked modified files
  - `diff --name-status`: 8 modified tracked files
  - `diff --stat`: 248 insertions, 13 deletions
  - `log --oneline --decorate -15`: branch tip is `milestone(extraction-eval): enforce auditable real-gold KPI provenance`
- Branch ancestry checks:
  - `git -C ... rev-list --count 49a5d34..dabbc456`: `263`
  - `git -C ... show preserve/dirty-work-20260430T065748Z:financial-engine_v2/backend/app/main.py` does not contain new fields (`doc_elapsed_ms`, `timeout_budget_sec`, `cache_hit`, `cache_source`), so these changes are not present in preserve tip.

## Inferred facts
- `49a5d34...` is a strict ancestor of preserve head; the dirty branch is an older branch point with local file edits layered on top.
- The working-dir branch appears to contain high-value, additive extraction-eval instrumentation that was partially reviewed in prior hygiene audits but remains undecided for integration.
- No commit on this dirty branch directly includes the exact current eight-file local diff; these are local unstaged edits relative to the dirty branch tip.

## DATA_MISSING
- `docs/agent_tasks/eval_instrumentation_dirty_worktree_audit_20260509.md` was missing before creation and now exists.
- `python3 scripts/agent_job_contract.py check-diff` currently reports `docs/agent_tasks/cockpit_upgrade_integration_readiness_20260509.md` as modified outside allowed files, indicating pre-existing workspace state not scoped to this task.

## Main preserve worktree state
- Branch: `preserve/dirty-work-20260430T065748Z`
- HEAD: `dabbc456e42f737d12e6a1d979e6189e0936e865`
- Current mode: audit-only, no runtime jobs active
- Current dirty state: two untracked docs files only

## Dirty eval worktree state
- Path: `/mnt/sdb2/home/l4nd0/tenn-eval-instrumentation-20260421`
- Branch: `audit/eval-instrumentation-bounded-20260421`
- HEAD: `49a5d34a49b105bdba28ac5ed42649d57b4f4976`
- Diff payload: 8 tracked modified files (backend extraction/eval runtime paths and tests)

## Dirty file matrix
See `dirty_file_matrix.md`.

## Value/risk assessment
- Primary value: evaluation instrumentation for real-gold extraction runtime observability (timing, timeout budget used, cache path provenance).
- Primary risk: production code contract changes are additive but touch extraction runtime and API response shape.
- No deletions, no runtime data stores touched, no DB/Qdrant/Postgres mutations.
- Risk concentration: API payload extension in `financial-engine_v2/backend/app/main.py` and metadata persistence changes in `financial-engine_v2/backend/app/services/docling_extract.py`.

## Decision (preserve/integrate/archive/idle)
This worktree should be treated as **high-value candidate for preservation**, not archival. It is best preserved as an isolated audit + patch set and integrated through a gated follow-up task card because the branch is behind preserve and lacks direct merge provenance.

## Exact recommended next task
Create a new safe integration task card that cherry-picks or replays these 8 files after preserve-rebase validation:
- Task: `docs/agent_tasks/eval_instrumentation_dirty_worktree_audit_20260509_followup.md` (or equivalent naming)
- Scope: add runtime provenance fields (`doc_elapsed_ms`, `timeout_budget_sec`, `cache_hit`, `cache_source`) across extraction, API response, and eval output tables.

## Hard stops
- Do not run cleanup/archive while this audit task is unclosed and contract checks are incomplete.
- Do not mutate this dirty worktree.
- Do not merge or stage these files directly without revalidating against preserve tip and confirming API consumers of eval-response shape.
- Investigate/resolve `cockpit_upgrade_integration_readiness_20260509.md` untracked file if strict task-card check is required.

## Project Memory save recommendation
`SAVE_RECOMMENDED`

## Final git status (main preserve)
```text
?? docs/agent_tasks/cockpit_upgrade_integration_readiness_20260509.md
?? docs/agent_tasks/eval_instrumentation_dirty_worktree_audit_20260509.md
```

## Final git status (dirty worktree)
```text
 M financial-engine_v2/backend/app/main.py
 M financial-engine_v2/backend/app/services/docling_extract.py
 M financial-engine_v2/backend/app/services/method_isolated_extraction.py
 M financial-engine_v2/backend/app/services/multipass_extraction.py
 M financial-engine_v2/backend/tests/test_docling_extract.py
 M financial-engine_v2/backend/tests/test_extraction_gold_eval.py
 M scripts/run_real_extraction_eval.py
 M scripts/test_run_real_extraction_eval.py
```
