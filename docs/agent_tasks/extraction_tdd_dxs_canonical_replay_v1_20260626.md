---
job_id: extraction_tdd_dxs_canonical_replay_v1_20260626
lane: Financial Truth
supporting_lanes:
  - Evaluation
  - Provenance
  - Reporting
owner: Codex
allowed_files:
  - docs/agent_tasks/extraction_tdd_dxs_canonical_replay_v1_20260626.md
  - financial-engine_v2/data/extraction_no_write_cases/confirmed_metric_fixture_cases_v1.json
  - financial-engine_v2/backend/app/services/multipass_extraction.py
  - financial-engine_v2/backend/tests/test_multipass_extraction.py
  - reports/agent_jobs/extraction_tdd_dxs_canonical_replay_v1_20260626/TASK_CARD.md
  - reports/agent_jobs/extraction_tdd_dxs_canonical_replay_v1_20260626/README.md
  - reports/agent_jobs/extraction_tdd_dxs_canonical_replay_v1_20260626/STATE.md
  - reports/agent_jobs/extraction_tdd_dxs_canonical_replay_v1_20260626/DECISIONS.md
  - reports/agent_jobs/extraction_tdd_dxs_canonical_replay_v1_20260626/BOARD.md
  - reports/agent_jobs/extraction_tdd_dxs_canonical_replay_v1_20260626/BOARD_DECISION.json
  - reports/agent_jobs/extraction_tdd_dxs_canonical_replay_v1_20260626/VALIDATION.md
  - reports/agent_jobs/extraction_tdd_dxs_canonical_replay_v1_20260626/NEXT_GOAL.md
  - reports/agent_jobs/extraction_tdd_dxs_canonical_replay_v1_20260626/guard_preflight.json
  - reports/agent_jobs/extraction_tdd_dxs_canonical_replay_v1_20260626/registry_active_jobs.json
  - reports/agent_jobs/extraction_tdd_dxs_canonical_replay_v1_20260626/ledger_validate.json
  - reports/agent_jobs/extraction_tdd_dxs_canonical_replay_v1_20260626/duplicate_work_search.json
  - reports/agent_jobs/extraction_tdd_dxs_canonical_replay_v1_20260626/task_card_validate.json
  - reports/agent_jobs/extraction_tdd_dxs_canonical_replay_v1_20260626/diff-check.json
  - reports/agent_jobs/extraction_tdd_dxs_canonical_replay_v1_20260626/validation.json
  - reports/agent_jobs/extraction_tdd_dxs_canonical_replay_v1_20260626/payload_scorecard.json
  - reports/agent_jobs/extraction_tdd_dxs_canonical_replay_v1_20260626/handoff/HANDOFF.md
  - reports/agent_jobs/extraction_tdd_dxs_canonical_replay_v1_20260626/handoff/NEXT_GOAL.md
  - reports/agent_jobs/extraction_tdd_dxs_canonical_replay_v1_20260626/handoff/LEDGER_ENTRY.json
  - reports/agent_jobs/extraction_tdd_dxs_canonical_replay_v1_20260626/no_write_replay_DXS/input_manifest.json
  - reports/agent_jobs/extraction_tdd_dxs_canonical_replay_v1_20260626/no_write_replay_DXS/replay_results.json
  - reports/agent_jobs/extraction_tdd_dxs_canonical_replay_v1_20260626/no_write_replay_DXS/side_effect_audit.json
  - reports/agent_jobs/extraction_tdd_dxs_canonical_replay_v1_20260626/no_write_replay_DXS/validation.json
  - reports/agent_jobs/extraction_tdd_dxs_canonical_replay_v1_20260626/no_write_replay_DXS/logs/replay.log
  - reports/agent_jobs/extraction_tdd_dxs_canonical_replay_v1_20260626/no_write_replay_EQR/input_manifest.json
  - reports/agent_jobs/extraction_tdd_dxs_canonical_replay_v1_20260626/no_write_replay_EQR/replay_results.json
  - reports/agent_jobs/extraction_tdd_dxs_canonical_replay_v1_20260626/no_write_replay_EQR/side_effect_audit.json
  - reports/agent_jobs/extraction_tdd_dxs_canonical_replay_v1_20260626/no_write_replay_EQR/validation.json
  - reports/agent_jobs/extraction_tdd_dxs_canonical_replay_v1_20260626/no_write_replay_EQR/logs/replay.log
  - reports/agent_jobs/extraction_tdd_dxs_canonical_replay_v1_20260626/no_write_replay_FMG/input_manifest.json
  - reports/agent_jobs/extraction_tdd_dxs_canonical_replay_v1_20260626/no_write_replay_FMG/replay_results.json
  - reports/agent_jobs/extraction_tdd_dxs_canonical_replay_v1_20260626/no_write_replay_FMG/side_effect_audit.json
  - reports/agent_jobs/extraction_tdd_dxs_canonical_replay_v1_20260626/no_write_replay_FMG/validation.json
  - reports/agent_jobs/extraction_tdd_dxs_canonical_replay_v1_20260626/no_write_replay_FMG/logs/replay.log
  - reports/agent_jobs/extraction_tdd_dxs_canonical_replay_v1_20260626/no_write_replay_GRE/input_manifest.json
  - reports/agent_jobs/extraction_tdd_dxs_canonical_replay_v1_20260626/no_write_replay_GRE/replay_results.json
  - reports/agent_jobs/extraction_tdd_dxs_canonical_replay_v1_20260626/no_write_replay_GRE/side_effect_audit.json
  - reports/agent_jobs/extraction_tdd_dxs_canonical_replay_v1_20260626/no_write_replay_GRE/validation.json
  - reports/agent_jobs/extraction_tdd_dxs_canonical_replay_v1_20260626/no_write_replay_GRE/logs/replay.log
  - reports/agent_jobs/extraction_tdd_dxs_canonical_replay_v1_20260626/no_write_replay_MIN/input_manifest.json
  - reports/agent_jobs/extraction_tdd_dxs_canonical_replay_v1_20260626/no_write_replay_MIN/replay_results.json
  - reports/agent_jobs/extraction_tdd_dxs_canonical_replay_v1_20260626/no_write_replay_MIN/side_effect_audit.json
  - reports/agent_jobs/extraction_tdd_dxs_canonical_replay_v1_20260626/no_write_replay_MIN/validation.json
  - reports/agent_jobs/extraction_tdd_dxs_canonical_replay_v1_20260626/no_write_replay_MIN/logs/replay.log
  - reports/agent_jobs/extraction_tdd_dxs_canonical_replay_v1_20260626/no_write_replay_QBE/input_manifest.json
  - reports/agent_jobs/extraction_tdd_dxs_canonical_replay_v1_20260626/no_write_replay_QBE/replay_results.json
  - reports/agent_jobs/extraction_tdd_dxs_canonical_replay_v1_20260626/no_write_replay_QBE/side_effect_audit.json
  - reports/agent_jobs/extraction_tdd_dxs_canonical_replay_v1_20260626/no_write_replay_QBE/validation.json
  - reports/agent_jobs/extraction_tdd_dxs_canonical_replay_v1_20260626/no_write_replay_QBE/logs/replay.log
approval_required: false
allow_unapproved_safe_extension: true
timeout_seconds: 10800
output_dir: reports/agent_jobs/extraction_tdd_dxs_canonical_replay_v1_20260626
mutation_mode: safe_extension
production_data_access: false
github_mutation_allowed: false
docs_impact: DOCS_FOLLOWUP
docs_checked:
  - AGENTS.md
  - docs/README.md
  - docs/dev_flow/REPO_PATH_OWNERSHIP_AND_WORK_PRESERVATION.md
  - .agents/skills/tenn-financial-metric-extraction/SKILL.md
  - .agents/skills/tenn-git-guard/SKILL.md
docs_changed: []
docs_followup: "Document the Appendix 5B source-text section-total recovery and source-PDF text fallbacks if this fixture-lane fix is promoted beyond the current extraction blocker workstream."
reason: "Report-local canonical DXS no-write replay using the existing fixture-loop manifest contract; extractor behavior changed narrowly for source-bound DXS/FMG/GRE replay blockers, with no API, schema, runtime, prompt, source PDF, or gold-label change."
task_tier: critical
recommended_model: "high reasoning"
actual_model: "Codex GPT-5"
worker_model_allowed: false
task_scope: safe_validation_then_report_local
---

# DXS Canonical No-Write Replay

## Objective

Run `DXS_CONFIRMED_METRIC` from a fresh canonical-based worktree after the
stale fixture-loop branch was found to be missing already merged DXS
statement-precedence work.

## Scope

- Use branch `safe/extraction-tdd-dxs-canonical-replay-v1-20260626` created
  from `origin/migration/clean-runtime-baseline-reconstruct-v1` at
  `c877da6eb114826365339379f10a8a06e82221a5`.
- Preserve the stale fixture-loop worktree untouched.
- Add the certified confirmed-metric no-write manifest from the prior
  fixture-loop branch because canonical does not yet contain it.
- Run `DXS_CONFIRMED_METRIC` first through the baseline no-write replay profile.
- After DXS passes, extend this task card one confirmed-metric case at a time,
  continuing in the approved order: `EQR_CONFIRMED_METRIC`,
  `FMG_CONFIRMED_METRIC`, `GRE_CONFIRMED_METRIC`,
  `MIN_CONFIRMED_METRIC`, `QBE_CONFIRMED_METRIC`.
- If DXS replay exposes a source-bound metric failure, make at most one narrow
  deterministic extractor/test change inside the allowlist and rerun focused
  validation plus DXS replay.
- Write artifacts only under this report directory.

## Hard Stops

- No DB, Qdrant, Redis, news, memory, runtime, backfill, source-PDF, gold-label,
  prompt, model, GPU, service-config, or production-data mutation.
- No merge, rebase, cherry-pick, commit, push, reset, stash, clean, GitHub
  write, source-PDF mutation, or gold-label mutation.
- Stop on parser/runtime/source-PDF/fixture-policy/FX ambiguity or any
  source-bound metric failure that cannot be fixed with one narrow
  deterministic change under an updated task card.

## Validation

- Repo identity checks.
- Portable Tenn git-guard preflight.
- Task-card validation.
- Ledger validation/search.
- Registry read-only check.
- Duplicate-work checks.
- DXS/EQR/FMG/GRE/MIN/QBE no-write replay validation and side-effect audit.
- Report-local payload scorecard/validation summary.
- `git diff --check`, `check-diff`, and `check-report-artifacts`.
