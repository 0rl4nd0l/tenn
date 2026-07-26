---
job_id: llama_router_fail_closed_v1_20260726
lane: Reporting
owner: Codex
allowed_files:
  - scripts/run_llama_server.sh
  - scripts/test_llama_server_launchers.py
  - docs/setup/environment.md
  - reports/agent_jobs/llama_router_fail_closed_v1_20260726/TASK_CARD.md
  - reports/agent_jobs/llama_router_fail_closed_v1_20260726/STATE.md
  - reports/agent_jobs/llama_router_fail_closed_v1_20260726/DECISIONS.md
  - reports/agent_jobs/llama_router_fail_closed_v1_20260726/VALIDATION.md
  - reports/agent_jobs/llama_router_fail_closed_v1_20260726/CODE_REVIEW.json
approval_required: true
approval_context: "USER_APPROVED_2026-07-26: proceed with the bounded source remediation identified by the read-only post-PR523 llama diagnosis."
approval_token: LLAMA_ROUTER_FAIL_CLOSED_SOURCE_REPAIR
timeout_seconds: 3600
output_dir: reports/agent_jobs/llama_router_fail_closed_v1_20260726
mutation_mode: safe_extension
production_data_access: false
runtime_activation_allowed: false
document_processing_allowed: false
store_writes_allowed: false
model_or_config_changes_allowed: false
github_mutation_allowed: false
live_ledger_mutation_allowed: false
registry_claim_release_allowed: false
---

# Fail closed when llama router mode is requested

Repair the launcher so an explicit router-mode request cannot silently fall
back to the configured single-model GPT-OSS server when the capability probe
fails. Add focused regression coverage. Do not start llama, process documents,
change stores/models/config, or perform GitHub mutations.
