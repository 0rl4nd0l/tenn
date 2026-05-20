---
job_id: loose_task_card_blocker_consolidation_v1_20260520
lane: Evaluation
owner: Codex
allowed_files:
  - docs/agent_tasks/loose_task_card_blocker_consolidation_v1_20260520.md
  - docs/agent_tasks/asx_document_type_fixture_contract_integration_v1_20260520.md
  - docs/agent_tasks/strategy_lab_quantdinger_framework_v1_20260520.md
  - docs/agent_tasks/strategy_lab_task_card_blocker_cleanup_v1_20260520.md
  - reports/agent_jobs/asx_document_type_fixture_contract_integration_v1_20260520/
  - reports/agent_jobs/asx_document_type_fixture_contract_integration_v1_20260520/README.md
  - reports/agent_jobs/strategy_lab_quantdinger_framework_v1_20260520/
  - reports/agent_jobs/strategy_lab_quantdinger_framework_v1_20260520/README.md
  - reports/agent_jobs/strategy_lab_quantdinger_framework_v1_20260520/artifact_schema_v1.md
  - reports/agent_jobs/strategy_lab_quantdinger_framework_v1_20260520/checkpoints/
  - reports/agent_jobs/strategy_lab_quantdinger_framework_v1_20260520/checkpoints/checkpoint_00_preflight.md
  - reports/agent_jobs/strategy_lab_quantdinger_framework_v1_20260520/checkpoints/checkpoint_01_tenn_surface_map.md
  - reports/agent_jobs/strategy_lab_quantdinger_framework_v1_20260520/checkpoints/checkpoint_02_quantdinger_fit.md
  - reports/agent_jobs/strategy_lab_quantdinger_framework_v1_20260520/checkpoints/checkpoint_03_artifact_contract.md
  - reports/agent_jobs/strategy_lab_quantdinger_framework_v1_20260520/checkpoints/checkpoint_04_mcp_runtime_policy.md
  - reports/agent_jobs/strategy_lab_quantdinger_framework_v1_20260520/checkpoints/checkpoint_05_strategy_lab_ux.md
  - reports/agent_jobs/strategy_lab_quantdinger_framework_v1_20260520/checkpoints/checkpoint_06_autonomous_value_loops.md
  - reports/agent_jobs/strategy_lab_quantdinger_framework_v1_20260520/checkpoints/checkpoint_07_runtime_compatibility.md
  - reports/agent_jobs/strategy_lab_quantdinger_framework_v1_20260520/checkpoints/checkpoint_08_implementation_backlog.md
  - reports/agent_jobs/strategy_lab_quantdinger_framework_v1_20260520/diff-check.json
  - reports/agent_jobs/strategy_lab_quantdinger_framework_v1_20260520/status.json
  - reports/agent_jobs/strategy_lab_quantdinger_framework_v1_20260520/strategy_lab_quantdinger_framework_v1_20260520_reports.zip
  - reports/agent_jobs/strategy_lab_quantdinger_framework_v1_20260520/task_card_outlines.md
  - reports/agent_jobs/strategy_lab_task_card_blocker_cleanup_v1_20260520/
  - reports/agent_jobs/strategy_lab_task_card_blocker_cleanup_v1_20260520/README.md
  - reports/agent_jobs/strategy_lab_task_card_blocker_cleanup_v1_20260520/diff-check.json
  - reports/agent_jobs/loose_task_card_blocker_consolidation_v1_20260520/
  - reports/agent_jobs/loose_task_card_blocker_consolidation_v1_20260520/README.md
  - reports/agent_jobs/loose_task_card_blocker_consolidation_v1_20260520/diff-check.json
  - reports/agent_jobs/loose_task_card_blocker_consolidation_v1_20260520/status.json
mutation_mode: safe_extension
production_data_access: false
output_dir: reports/agent_jobs/loose_task_card_blocker_consolidation_v1_20260520
approval_required: false
timeout_seconds: 7200
allow_unapproved_safe_extension: true
---

# Task

Consolidate loose task-card blockers in `/home/l4nd0/tenn-runtime` by checkpointing task cards and matching report artifacts as coordination artifacts only.

# Scope

Preserve these task cards:

- `docs/agent_tasks/asx_document_type_fixture_contract_integration_v1_20260520.md`
- `docs/agent_tasks/strategy_lab_quantdinger_framework_v1_20260520.md`
- `docs/agent_tasks/strategy_lab_task_card_blocker_cleanup_v1_20260520.md`
- `docs/agent_tasks/loose_task_card_blocker_consolidation_v1_20260520.md`

Preserve matching report directories for the three loose blockers and this consolidation job. This task must not touch source code, runtime config, Docker/systemd/env, data stores, parser/extraction, Cockpit UI/source, Evaluation Spine/DuckDB files, A2M/news retrieval files, ASX fixture source commit files, or the dirty HDD preserve worktree.

# Required Preflight

Run and report:

- `cd /home/l4nd0/tenn-runtime`
- `readlink -f /home/l4nd0/tenn-runtime`
- `git branch --show-current`
- `git rev-parse --short=12 HEAD`
- `git status --short`
- `git status --short --ignored docs/agent_tasks reports/agent_jobs`
- `git worktree list`
- `git show --stat --oneline --no-renames HEAD`
- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/loose_task_card_blocker_consolidation_v1_20260520.md`
- `python3 scripts/agent_job_registry.py list-active --repo-root /home/l4nd0/tenn-runtime`
- `python3 scripts/agent_job_registry.py check-overlap docs/agent_tasks/loose_task_card_blocker_consolidation_v1_20260520.md --repo-root /home/l4nd0/tenn-runtime`

Claim the registry job only if safe.

# Classification

- ASX integration task: blocked before integration; no ASX fixture source files integrated.
- Strategy Lab task: completed but uncheckpointed; meaningful report bundle exists.
- Strategy Lab cleanup task: blocked because ASX task card was out-of-scope dirt; report exists.

# Validation

Run:

- JSON parse for JSON files in preserved report dirs, if practical.
- `git diff --cached --name-status`
- `git diff --cached --stat`
- staged allowlist leak check from the user request.
- `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/loose_task_card_blocker_consolidation_v1_20260520.md`
- `git diff --cached --check`

# Required Report

Write:

`reports/agent_jobs/loose_task_card_blocker_consolidation_v1_20260520/README.md`

Include confirmed facts, inferred facts, DATA_MISSING, active registry state, exact loose task cards preserved, exact report dirs preserved, classification of each loose artifact, whether reports were force-added, validation commands and exact results, commit hash if committed, final git status, registry release status, and next step.
