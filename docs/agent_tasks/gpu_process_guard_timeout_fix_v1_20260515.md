---
job_id: gpu_process_guard_timeout_fix_v1_20260515
lane: Evaluation
owner: Codex
mutation_mode: safe_extension
approval_required: true
approval_id: USER_APPROVED_GPU_PROCESS_GUARD_TIMEOUT_FIX_20260515_GPT
production_data_access: false
timeout_seconds: 3600
output_dir: reports/agent_jobs/gpu_process_guard_timeout_fix_v1_20260515
allowed_files:
  - docs/agent_tasks/gpu_process_guard_timeout_fix_v1_20260515.md
  - scripts/gpu_process_guard.sh
  - scripts/test_gpu_process_guard_timeout.sh
  - tests/test_gpu_process_guard_timeout.py
  - reports/agent_jobs/gpu_process_guard_timeout_fix_v1_20260515/README.md
  - reports/agent_jobs/gpu_process_guard_timeout_fix_v1_20260515/status.json
  - reports/agent_jobs/gpu_process_guard_timeout_fix_v1_20260515/diff-check.json
---

# Task

Fix the restart blocker where `scripts/gpu_process_guard.sh --kill-rogues` can hang indefinitely when `nvidia-smi --query-compute-apps=pid,used_memory` enters kernel D state.
