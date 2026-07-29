# ASXFP Ticket 06 statutory observation projection

Status: CANDIDATE 3 REJECTED — CLOSEOUT EVIDENCE PROTOCOL REPAIR IN PROGRESS

- stacked_base: `84295111c6ae400de4e6f1c6cd941a45a0f549a3`
- canonical_ancestor: `b01885d6cd55242339662e91d18141aeb725f089`
- authoritative_ticket_sha256:
  `3fec223fffa68a49384064d58ec8e6aa9c4a207b7a7b9f8cd2c08661faade7a4`
- dependency: Ticket 05 exact-head CI passed on draft PR 531
- protected_corpus_access: prohibited
- database_execution: not authorized
- merge: not authorized

## Objective

Promote exactly the ten existing statutory profile metrics through sparse,
immutable observations while preserving current profile readers and all legacy
values when a later extraction omits a metric.

## Candidate 1 review

Candidate 1 commit `73a4fadedc031c490b2748d260ed13cd40b40363`
(tree `8c13c0e30c47119b4dd7710411c8fcc55fdc1025`) was rejected by fresh
reviewer session `019fae5d-a471-7132-8172-1634de79db3b`. The service and
migration expanded to ten metrics, but the ORM model retained revenue-only
checks and a three-character currency column. The task allowlist now includes
that model for the smallest compatible repair.

No protected-data access, database/migration execution, extraction, runtime
action, publication, or merge occurred. Parent-side candidate freezing created
the local review commit above; it was not pushed or published. The offline
implementer environment lacked pytest and Ruff.

## Repair candidate

- repair_seed: `3e31121e68e7d38f7559cd0af80a035c005aadec`
- branch: `codex-x/20260729T145744Z-3e31121e68-e6c12c`
- state: unstaged reviewable delta; no repair commit or tree was created
- product_test_delta_sha256:
  `797985289cf90f91c4b482c9cab4be174de212325fd5ec68628c7472aa319377`
- changed_files:
  - `financial-engine_v2/backend/app/models/financial_observations.py`
  - `financial-engine_v2/backend/tests/test_financial_observations.py`
  - `reports/agent_jobs/asxfp_ticket06_statutory_projection_v1_20260729/README.md`

The ORM now carries the same closed ten-metric check, conditional
`shares_outstanding`/`shares` unit check, and `String(16)` currency storage as
migration `0011`. Focused metadata-only coverage inspects those SQLAlchemy
objects without creating an engine or connecting to a database.

## Repair validation

- PASS: exact repair seed, branch, stacked-base ancestry, and committed path
  scope verified with read-only Git commands.
- PASS: task-card `validate`.
- PASS: read-only AST comparison confirms the ORM contains migration `0011`'s
  exact metric and currency vocabularies, conditional share unit, and
  `String(16)`.
- PASS: `python3 -m py_compile` for the changed model and focused test.
- PASS: `git diff --check`.
- ENVIRONMENT BLOCKED: task-card `check-diff` identifies the three repair files
  as allowlisted, but also sees launcher-owned control artifacts (`SOURCE.md`,
  `bin`, and launcher JSON/wrapper files) as pre-existing untracked paths
  outside the task allowlist.
- BLOCKED: focused pytest did not start because `/usr/bin/python3` has no
  `pytest` module.
- BLOCKED: Ruff did not start because `/usr/bin/python3` has no `ruff` module.

No database, migration, runtime, service, extraction, OCR, model, evaluation,
network, protected-data, commit, staging, push, merge, or deployment action was
performed during the repair.

## Candidate 2 review

The parent froze the repair as Candidate 2 commit
`8eb34326fb5fa19204998d34a00420d202454484` (tree
`322133441d8e7bab2886af818a6fb0b133e5d1ea`). Relative to the Ticket 06 seed
`999648b98437b1ceee4e04267249d72824e7a057`, the complete candidate delta is:

- `docs/agent_tasks/asxfp_ticket06_statutory_projection_v1_20260729.md`
- `docs/extraction/financial_observation_contract.md`
- `financial-engine_v2/backend/app/alembic/versions/0011_expand_statutory_observation_metrics.py`
- `financial-engine_v2/backend/app/api/routes.py`
- `financial-engine_v2/backend/app/models/financial_observations.py`
- `financial-engine_v2/backend/app/services/financial_observations.py`
- `financial-engine_v2/backend/app/services/pipeline.py`
- `financial-engine_v2/backend/tests/test_financial_observations.py`
- `reports/agent_jobs/asxfp_ticket06_statutory_projection_v1_20260729/README.md`

Independent reviewer session `019fae69-29f5-7442-ab42-18c1cea2f71c`
rejected Candidate 2 solely because this closeout report retained stale
pre-freeze evidence: it did not identify the actual candidate commit and tree
or enumerate the complete nine-path seed-to-candidate delta. No product-code,
task-card, test, or other implementation blocker was reported.

This closeout correction changes only this report. Its report-only delta is
unstaged and uncommitted until the parent freezes it; it is not part of the
Candidate 2 commit or tree recorded above.

## Candidate 3 review

The parent froze the Candidate 2 closeout correction as Candidate 3 commit
`7103d1ff3283c6a6a37119848d0b447d85389713` (tree
`77aeddcbeb6d299d7a46414507c8f704bb8e2cdb`). Relative to the Ticket 06 seed
`999648b98437b1ceee4e04267249d72824e7a057`, the complete candidate delta
remains:

- `docs/agent_tasks/asxfp_ticket06_statutory_projection_v1_20260729.md`
- `docs/extraction/financial_observation_contract.md`
- `financial-engine_v2/backend/app/alembic/versions/0011_expand_statutory_observation_metrics.py`
- `financial-engine_v2/backend/app/api/routes.py`
- `financial-engine_v2/backend/app/models/financial_observations.py`
- `financial-engine_v2/backend/app/services/financial_observations.py`
- `financial-engine_v2/backend/app/services/pipeline.py`
- `financial-engine_v2/backend/tests/test_financial_observations.py`
- `reports/agent_jobs/asxfp_ticket06_statutory_projection_v1_20260729/README.md`

Independent reviewer session `019fae70-9be2-7252-8b68-fec47dad9967`
rejected Candidate 3 solely because the closeout evidence protocol required
the tracked report to identify the commit and tree containing that same report,
an impossible self-reference. All prior Candidate 1 and Candidate 2 history,
implementation evidence, validation limitations, and hard stops above remain
in force. No product acceptance criterion or product implementation was
rejected.

This two-file protocol repair changes only the task card and this report. It
records Candidate 3 as the latest frozen predecessor and leaves the report
patch state explicit; it is unstaged and uncommitted until the parent freezes
it under the clarified non-self-referential rule. The parent freeze and a fresh
independent reviewer record or PR record must identify the final commit and
tree that contain this report. This tracked report is not required to embed its
own containing commit hash.
