# Post-PR301 Broad Accuracy Push Closeout

Generated: 2026-06-07T05:00:57Z

Worktree:
`/home/l4nd0/tenn-post-pr301-broad-accuracy-push-v1-20260607`

Branch:
`safe/extraction-post-pr301-broad-accuracy-push-v1-20260607`

Canonical starting HEAD:
`10c162a5162b3e5fc1306cdd908b23bfa6f0a5a8`

Final HEAD:
`42ffac6031562d7fbed206d1a180650f0c1312a9`

Final decision: `READY_FOR_COUNT24_APPROVAL_PACKET`.

Count-24/count-32, broad extraction, broad backfill, and full ticker-universe
extraction were not run.

## Commits Created

- `e28a2ca1` task-card scaffold.
- `61a624c4` DXC/LBL containment no-op proof.
- `31413271` candidate-exclusion taxonomy hardening.
- `7be3d3af` bounded count-16 validation.
- `6c86b5d4` failure and accepted-output taxonomy.
- `42ffac60` half-year announcement-date accepted-output guard.

## Milestones

1. DXC/LBL containment: completed as no-op proof. No exact matching DB rows or
   Qdrant points were found in inspected state; no DB/Qdrant/news/memory
   mutation was performed.
2. Candidate exclusions: completed. Existing noncandidate classes were
   preserved; meeting/proxy coverage was tightened and `director_interest_notice`
   was added with tests and docs.
3. Count-16 validation: completed exactly once with seed `20260602`.
   Candidate pool count `28633`; ordered hash
   `3d99f44885fd056ac3f112d56abe95d14dd1ac9affdcd7315f860f690cdeb63f`.
   Result: 7 ok, 0 ok_low_confidence, 9 failed, 0 exceptions.
4. Failure/accepted-output taxonomy: completed. Five failures were true
   noncandidates, two were scale-related fail-closed cases, DXC failed closed
   on `net_operating_income` as EBIT, CTN failed closed on period/source
   mismatch, and HUB/LBL were suspicious accepted half-year rows.
5. Narrow repair: completed. Added a fail-closed guard for half-year outputs
   whose `period_end` equals a leading ASX announcement date in the source
   title/filename.
6. Final decision: count-24 approval packet is reasonable for operator review,
   but no count-24 execution is authorized by this report.

## Validation Summary

- Focused classifier/scorecard tests from Milestone 2 passed.
- Count-16 runner completed with exit 0.
- Focused repair tests: 3 passed, 181 deselected.
- Full touched multipass test file: 184 passed.
- py_compile passed for touched Python files.
- ruff passed for touched Python files.
- Saved HUB/LBL payloads now fail `_validate_gate` with
  `validation_gate:announcement_date_period_end`.
- JSON validation, `git diff --check`, `git diff --cached --check`, task-card
  `check-diff`, no-source-PDF-staged checks, and direct registry active-record
  inspection passed.

## Side Effects

No DB files, Qdrant collections, news stores, memory, source PDFs, prompts,
gold labels, schemas, runtime/model/GPU config, or queues were mutated by the
bounded sample or repair. Redis queue checks were clean after the count-16 run.

## Remaining DATA_MISSING

- Reliable GPU memory telemetry: `nvidia-smi` failed during the count-16 phase.
- PR #301 accepted-output artifact omitted accepted-row refs/provenance and
  extraction_run_id values.
- Route-level exposure checks were not run for DXC/LBL because exact DB/Qdrant
  matches were absent.
- `pdfplumber`/`pypdf` were unavailable; Poppler text extraction and one
  rendered visual check were used.
- WHC 2022 scale root cause remains not narrow enough for this milestone's one
  allowed repair.

## Project Memory Recommendation

Save a memory note that post-PR301 bounded count-16 found HUB/LBL accepted
half-year announcement-date period risks, and that `42ffac60` added the
fail-closed `validation_gate:announcement_date_period_end` guard.

## Next Recommended Prompt

```text
Using worktree /home/l4nd0/tenn-post-pr301-broad-accuracy-push-v1-20260607 at or after 42ffac6031562d7fbed206d1a180650f0c1312a9, prepare a count-24 approval packet for Tenn extraction after post-PR301 containment and the half-year announcement-date guard. Do not run count-24 yet. Re-check branch/HEAD/status/registry/runtime readiness, summarize the exact guard evidence, list remaining DATA_MISSING, and ask for explicit approval before any count-24/count-32/broad extraction/backfill/full ticker-universe execution.
```

## Integration Review Addendum - 2026-06-07

State: `PR_OPENED_DONE_WITH_RISK`.

Integration PR: https://github.com/0rl4nd0l/tenn/pull/306

Integration worktree:
`/home/l4nd0/tenn-post-pr301-integration-v1-20260607`

Integration branch:
`safe/extraction-post-pr301-broad-accuracy-integration-v1-20260607`

Source reviewed:

- Branch: `safe/extraction-post-pr301-broad-accuracy-push-v1-20260607`
- Requested source commit:
  `1a7370f4056e40d93e40bf4b070d6c3e4143a66d`
- Replayed source range:
  `10c162a5162b3e5fc1306cdd908b23bfa6f0a5a8..1a7370f4056e40d93e40bf4b070d6c3e4143a66d`

Canonical evidence:

- Live remote canonical was rechecked before push and PR creation:
  `f57560c49c3a06ec65b082af05b103ee24899e6f`.
- The local `migration/clean-runtime-baseline-reconstruct-v1` worktree at
  `/home/l4nd0/tenn-merge-parking-registry-integrate-v1-20260604` was stale and
  diverged (`ahead 50, behind 35`), so no local canonical checkout mutation was
  attempted.
- The source branch was local-only before integration; the PR branch was pushed
  after replaying the source commits onto current `origin/migration`.

Scope review:

- PR file list contains only the post-PR301 task cards, post-PR301 report
  artifacts, touched extraction guard/test files, and extraction/evaluation docs.
- `financial-engine_v2/scripts/broad_extraction_test.py` was listed in the task
  card allowlist but is not modified by the PR diff.
- No source PDF files are changed in `origin/migration...HEAD`; no PDF files were
  staged.

Validation run from the integration worktree:

- Task-card validation passed for all five
  `docs/agent_tasks/extraction_post_pr301_*.md` cards.
- Task-card `check-diff` passed on the clean working tree with
  `--no-write-report`; an additional `origin/migration...HEAD` allowlist check
  reported `changed_count=50` and `disallowed_count=0`.
- `python3 -m py_compile` passed for the touched Python source/test files.
- JSON validation passed for 27 post-PR301 report JSON files.
- `git diff --check origin/migration/clean-runtime-baseline-reconstruct-v1...HEAD`
  passed.
- `python3 scripts/agent_job_registry.py list-active --read-only` passed with no
  active jobs and `lock_acquired=false`.
- Focused pytest passed using the baseline repo venv:
  `187 passed in 2.04s`.
- Ruff is `DATA_MISSING` in this integration worktree because no `ruff` binary
  was available on PATH or under `financial-engine_v2/.venv/bin/ruff`.

GitHub PR state at addendum time:

- PR #306 is open, non-draft, and GitHub reports `mergeable=true`.
- `mergeable_state=unstable` / `mergeStateStatus=UNSTABLE` because
  `lint-and-test` is still pending. `scan` passed.
- Canonical was not merged or otherwise mutated in this integration review.

Unsafe actions avoided:

- No count-24, count-32, broad extraction, broad backfill, or full
  ticker-universe extraction was run.
- No DB, Qdrant, news, memory, source PDF, prompt, gold-label, schema, runtime,
  service, model, or GPU configuration mutation was performed.
- No reset, stash, clean, rebase, branch deletion, or canonical checkout mutation
  was performed.

Next recommended prompt:

```text
Review PR #306 after GitHub checks finish. If checks are green, merge only after
one final read-only recheck of base/head/mergeability/file list. After the PR is
merged, prepare the count-24 approval packet only; do not run count-24/count-32,
broad extraction, backfill, or full ticker-universe extraction without explicit
approval.
```
