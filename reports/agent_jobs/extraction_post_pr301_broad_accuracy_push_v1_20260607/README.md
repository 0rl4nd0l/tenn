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
