---
job_id: extraction_whc_edu_mixed_unit_failclosed_v1_20260621
lane: Financial Truth
supporting_lanes:
  - Financial Truth
  - Provenance
  - Evaluation
owner: Codex
allowed_files:
  - docs/agent_tasks/extraction_whc_edu_mixed_unit_failclosed_v1_20260621.md
  - financial-engine_v2/backend/app/services/multipass_extraction.py
  - financial-engine_v2/backend/tests/test_multipass_extraction.py
  - reports/agent_jobs/extraction_whc_edu_mixed_unit_failclosed_v1_20260621/TASK_CARD.md
  - reports/agent_jobs/extraction_whc_edu_mixed_unit_failclosed_v1_20260621/STATE.md
  - reports/agent_jobs/extraction_whc_edu_mixed_unit_failclosed_v1_20260621/DECISIONS.md
  - reports/agent_jobs/extraction_whc_edu_mixed_unit_failclosed_v1_20260621/CODE_REVIEW.json
  - reports/agent_jobs/extraction_whc_edu_mixed_unit_failclosed_v1_20260621/validation.json
  - reports/agent_jobs/extraction_whc_edu_mixed_unit_failclosed_v1_20260621/diff-check.json
  - reports/agent_jobs/extraction_whc_edu_mixed_unit_failclosed_v1_20260621/NEXT_GOAL.md
  - reports/agent_jobs/extraction_whc_edu_mixed_unit_failclosed_v1_20260621/exact_replay/input_manifest.json
  - reports/agent_jobs/extraction_whc_edu_mixed_unit_failclosed_v1_20260621/exact_replay/replay_results.json
  - reports/agent_jobs/extraction_whc_edu_mixed_unit_failclosed_v1_20260621/exact_replay/side_effect_audit.json
  - reports/agent_jobs/extraction_whc_edu_mixed_unit_failclosed_v1_20260621/exact_replay/validation.json
  - reports/agent_jobs/extraction_whc_edu_mixed_unit_failclosed_v1_20260621/exact_replay/logs/replay.log
  - financial-engine_v2/data/extraction_no_write_cases/whc_edu_mixed_unit_cases_v1.json
  - scripts/test_extraction_no_write_replay.py
  - financial-engine_v2/.venv/
approval_required: false
allow_unapproved_safe_extension: true
timeout_seconds: 7200
output_dir: reports/agent_jobs/extraction_whc_edu_mixed_unit_failclosed_v1_20260621
mutation_mode: safe_extension
production_data_access: false
github_mutation_allowed: true
docs_impact: DOCS_NOT_REQUIRED
docs_checked:
  - reports/agent_jobs/extraction_whc_edu_certified_manifest_replay_v1_20260621/NEXT_GOAL.md
  - financial-engine_v2/backend/app/services/multipass_extraction.py
docs_changed: []
docs_followup: NONE
reason: "The user approved proceeding from the local WHC/EDU certified replay red proof. This lane adds the smallest live validation gate repair and reruns only the focused no-write manifest."
task_tier: critical
recommended_model: "high reasoning"
actual_model: "Codex GPT-5"
why_this_model: "Financial-truth validation gate behavior and no-write exact replay safety."
worker_model_allowed: false
worker_decision_limit: "orchestrator_only"
escalation_needed: false
---

# WHC/EDU Mixed-Unit Fail-Closed Repair

## Objective

Implement the smallest live extraction validation fix that makes WHC and EDU
mixed-unit accepted-output cases fail closed, then rerun the certified
two-case `docling-no-write` replay.

## Red Proof

- Manifest:
  `financial-engine_v2/data/extraction_no_write_cases/whc_edu_mixed_unit_cases_v1.json`
- Prior exact replay:
  `reports/agent_jobs/extraction_whc_edu_certified_manifest_replay_v1_20260621/exact_replay/validation.json`
- Prior result: `FAIL`, `side_effect_pass=true`
- Failure: both WHC and EDU observed `ok` while expected `failed`.

## Scope

- Touch only the live validation gate and its focused tests.
- Reuse existing payload-local `metric_source_scales`; do not re-parse source
  documents or infer corrected values.
- Preserve the existing certified manifest and no-write harness.
- Write report-local validation evidence only.

## Explicit Non-Goals

- No broad extraction.
- No count sample, backfill, or full-universe extraction.
- No DB, Qdrant, Redis, news, runtime, source-PDF, gold-label, prompt, or
  dependency-file writes.
- No service start.
- GitHub mutation is limited to pushing this continuation branch and opening one
  fresh PR after validation passes.
- No merge, rebase, cherry-pick, reset, stash, clean, branch deletion, or
  worktree deletion.

## Validation

- Task-card validation.
- Focused `_validate_gate` regression tests.
- Focused no-write replay harness tests.
- Exact WHC/EDU `docling-no-write` replay; ready only if `PASS` and
  `side_effect_pass=true`.
- Diff check against allowed files.
- Code review.
