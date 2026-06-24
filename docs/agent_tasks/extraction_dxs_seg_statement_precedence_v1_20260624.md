---
job_id: extraction_dxs_seg_statement_precedence_v1_20260624
lane: Financial Truth
supporting_lanes:
  - Evaluation
  - Provenance
owner: Codex
allowed_files:
  - docs/agent_tasks/extraction_dxs_seg_statement_precedence_v1_20260624.md
  - financial-engine_v2/backend/app/services/multipass_extraction.py
  - financial-engine_v2/backend/tests/test_multipass_extraction.py
  - reports/agent_jobs/extraction_dxs_seg_statement_precedence_v1_20260624/README.md
  - reports/agent_jobs/extraction_dxs_seg_statement_precedence_v1_20260624/STATE.md
  - reports/agent_jobs/extraction_dxs_seg_statement_precedence_v1_20260624/DECISIONS.md
  - reports/agent_jobs/extraction_dxs_seg_statement_precedence_v1_20260624/guard_preflight.json
  - reports/agent_jobs/extraction_dxs_seg_statement_precedence_v1_20260624/registry_active_jobs.json
  - reports/agent_jobs/extraction_dxs_seg_statement_precedence_v1_20260624/ledger_validate.json
  - reports/agent_jobs/extraction_dxs_seg_statement_precedence_v1_20260624/task_card_validate.json
  - reports/agent_jobs/extraction_dxs_seg_statement_precedence_v1_20260624/duplicate_work_search.json
  - reports/agent_jobs/extraction_dxs_seg_statement_precedence_v1_20260624/issue97.json
  - reports/agent_jobs/extraction_dxs_seg_statement_precedence_v1_20260624/source_review_board_decision.json
  - reports/agent_jobs/extraction_dxs_seg_statement_precedence_v1_20260624/validation.json
  - reports/agent_jobs/extraction_dxs_seg_statement_precedence_v1_20260624/replay_results_after_fix.json
  - reports/agent_jobs/extraction_dxs_seg_statement_precedence_v1_20260624/scorecard_after_fix.json
  - reports/agent_jobs/extraction_dxs_seg_statement_precedence_v1_20260624/scorecard_gate_after_fix.json
  - reports/agent_jobs/extraction_dxs_seg_statement_precedence_v1_20260624/LEDGER_ENTRY.json
  - reports/agent_jobs/extraction_dxs_seg_statement_precedence_v1_20260624/raw_replay_after_fix/input_manifest.json
  - reports/agent_jobs/extraction_dxs_seg_statement_precedence_v1_20260624/raw_replay_after_fix/replay_results.json
  - reports/agent_jobs/extraction_dxs_seg_statement_precedence_v1_20260624/raw_replay_after_fix/side_effect_audit.json
  - reports/agent_jobs/extraction_dxs_seg_statement_precedence_v1_20260624/raw_replay_after_fix/validation.json
  - reports/agent_jobs/extraction_dxs_seg_statement_precedence_v1_20260624/raw_replay_after_fix/logs/replay.log
  - reports/agent_jobs/extraction_dxs_seg_statement_precedence_v1_20260624/logs/focused_validation.log
  - reports/agent_jobs/extraction_dxs_seg_statement_precedence_v1_20260624/logs/replay_after_fix.log
  - reports/agent_jobs/extraction_dxs_seg_statement_precedence_v1_20260624/logs/scorecard_after_fix.log
  - reports/agent_jobs/extraction_dxs_seg_statement_precedence_v1_20260624/logs/ruff_validation.log
approval_required: false
allow_unapproved_safe_extension: true
timeout_seconds: 21600
output_dir: reports/agent_jobs/extraction_dxs_seg_statement_precedence_v1_20260624
mutation_mode: safe_extension
production_data_access: false
github_mutation_allowed: false
docs_impact: DOCS_NOT_REQUIRED
docs_checked:
  - AGENTS.md
  - docs/README.md
  - docs/dev_flow/REPO_PATH_OWNERSHIP_AND_WORK_PRESERVATION.md
  - .agents/skills/tenn-financial-metric-extraction/SKILL.md
  - .agents/skills/tenn-fix/SKILL.md
  - .agents/skills/tenn-git-guard/SKILL.md
docs_changed: []
docs_followup: NONE
reason: "Owner approved a scoped SAFE EXTENSION from the issue #97 source-review board packet: DXS stapled/group statement selection and SEG appendix-wrapper versus full financial statement precedence only."
task_tier: critical
recommended_model: "high reasoning plus focused tests"
actual_model: "Codex GPT-5"
why_this_model: "The work changes Financial Truth extractor selection behavior and must separate source-proven DXS/SEG defects from ANZ policy, candidate-review approval, net-debt semantics, and broad parser mapping."
worker_model_allowed: false
worker_decision_limit: "No worker delegation; implementation authority stays in this audited lane."
escalation_needed: false
task_scope: safe_extension
---

# DXS/SEG Statement Precedence Safe Extension

## Objective

Implement only the source-proven DXS/SEG extractor-class statement precedence
fix authorized by the issue #97 source-review board follow-up:

- DXS: prefer the consolidated stapled/group financial statements over parent
  entity or non-group statement tables when selecting statement metrics.
- SEG: prefer the full financial statement tables over Appendix 4D wrapper
  summary tables when both are present.

## Scope

- Start from canonical `origin/migration/clean-runtime-baseline-reconstruct-v1`
  at or after merge commit `61d5c9eeac054422eac5230d382cc4e2b36eec6a`.
- Run Tenn git guard, read-only registry, task-ledger validation, task-card
  validation, and duplicate-work search before edits.
- Change only `financial-engine_v2/backend/app/services/multipass_extraction.py`
  and focused tests in
  `financial-engine_v2/backend/tests/test_multipass_extraction.py`.
- Add positive and negative tests for class-level statement precedence.
- Rerun affected no-write replay and the approved-15 #97 scorecard after any
  fix.

## Hard Stops

- Do not change gold fixtures, source PDFs, prompts, schema, database, Qdrant,
  Redis, news, memory, model, GPU, or runtime state.
- Do not decide ANZ bank metric policy.
- Do not decide candidate-review approval.
- Do not decide net-debt semantics.
- Do not perform a broad parser rewrite or global metric mapping change.
- Stop if source evidence points outside DXS/SEG statement precedence.

## Validation

- Focused regression tests for DXS group/stapled precedence and SEG full
  statement over Appendix 4D wrapper precedence.
- Affected no-write replay for DXS/SEG fixtures.
- Approved-15 issue #97 scorecard.
- Report docs impact, ledger status, duplicate-work classification, validation
  commands, remaining blockers, and runtime functionality proof status.
