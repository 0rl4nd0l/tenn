# No-Write Harness Review Metadata Repair

State: DONE_WITH_RISK

Added explicit Docs Impact and Model/Worker Routing metadata to the PR #379 task
cards so the current Tenn review gate can evaluate the closeout without relying
on implicit report prose.

No harness code, tests, manifest cases, extraction behavior, source PDFs,
runtime config, venvs, dependency files, or production data were changed.

Docs Impact Check:

- docs_impact: DOCS_UPDATED
- docs_checked: the four PR #379 task cards
- docs_changed: the four PR #379 task cards
- docs_followup: NONE
- reason: metadata fields now record the already-documented no-write command,
  docling profile, publish boundary, and review repair.

Model/Worker Routing:

- task_tier: small for this metadata-only repair
- recommended_model: standard coding model
- actual_model: Codex GPT-5
- worker_model_allowed: false
- worker_decision_limit: no workers used
- escalation_needed: false

Task Ledger:

- live registry preflight: active_jobs empty
- ledger update: DATA_MISSING because `scripts/agent_task_ledger.py` is not
  present on this PR branch

Residual facts unchanged: WHC remains extraction-red in the saved no-write replay,
and docling-backed replay remains `DATA_MISSING` until an approved venv exists.
