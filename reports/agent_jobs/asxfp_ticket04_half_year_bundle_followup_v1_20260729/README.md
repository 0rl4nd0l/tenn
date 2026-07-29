# ASXFP Ticket 04 half-year bundle follow-up

Status: READY_FOR_DRAFT_PR

- canonical_base: `b01885d6cd55242339662e91d18141aeb725f089`
- classification: `NEW_FAILURE_CLASS`
- permanent_gate: synthetic cross-page half-year bundle regression
- implementer: `20260729T122958Z-f3bbcab50c-229d1c`, accepted
- implementer_session: `019fadda-c7ed-7430-822f-8e38622f038b`
- reviewer: `20260729T123718Z-599ccdfaf0-bfedbc`, `ACCEPT`
- reviewer_session: `019fade1-4523-7b02-aff4-6899835576a4`
- candidate_commit: `3fb10c95ce01ecf6e8e7d730ec15f4ed16cb92f1`
- candidate_tree: `41532f66e89c7a084e70770cb1b7441083442e6b`
- frozen_diff_sha256: `832b9afc19e117aa7dfc198ea42eb586731984cd1969eea4e79326d3eb6de0d5`
- validation: 68 focused tests passed; 6 related source-classifier cases
  passed; lint, compile, task-card, scope, and diff checks passed
- validation_gap: two optional Docling-backed run-multipass cases could not
  load in the disposable environment; Ruff format is also non-green on the
  unchanged baseline versions of both Python files
- publication: pending
- tier_2_actions: prohibited
