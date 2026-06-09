---
job_id: cockpit_llama_server_gpu_default_visibility_v1_20260526
lane: Reporting
supporting_lanes:
  - Evaluation
owner: Codex
allowed_files:
  - docs/agent_tasks/cockpit_llama_server_gpu_default_visibility_v1_20260526.md
  - cockpit-ui/app/api/cockpit/metrics/gpu/route.ts
  - cockpit-ui/app/api/cockpit/health/route.ts
  - cockpit-ui/components/cockpit/gpu-activity-dialog.tsx
  - cockpit-ui/lib/gpu-display.ts
  - cockpit-ui/lib/gpu-display.test.ts
  - reports/agent_jobs/cockpit_llama_server_gpu_default_visibility_v1_20260526/README.md
  - reports/agent_jobs/cockpit_llama_server_gpu_default_visibility_v1_20260526/status.json
  - reports/agent_jobs/cockpit_llama_server_gpu_default_visibility_v1_20260526/validation.json
  - reports/agent_jobs/cockpit_llama_server_gpu_default_visibility_v1_20260526/diff-check.json
approval_required: false
timeout_seconds: 7200
output_dir: reports/agent_jobs/cockpit_llama_server_gpu_default_visibility_v1_20260526
mutation_mode: safe_extension
allow_unapproved_safe_extension: true
production_data_access: false
github_mutation_allowed: branch_push_pr_and_issue_comment
related_issue: 61
---

# Cockpit Llama GPU Default Visibility

## Objective

Make Cockpit's GPU summary default to the GPU that is actually running
`llama-server` when that process-to-GPU mapping is available. Keep all changes
to display semantics only.

## Scope

Allowed mutation is limited to the Cockpit GPU metrics BFF, the existing GPU
activity display, a focused unit test, and this task/report bundle.

## Contract Safety

- Target layer: Client/Reporting plus Next.js BFF route.
- Relevant contract: Cockpit remains a client/orchestration layer and does not
  become an authority for ingestion, retrieval, financial truth, or GPU routing.
- Must not change: model binding, CUDA visibility, launcher defaults, runtime
  services, backend retrieval/storage, DB, Qdrant, news, memory, or financial
  truth.
- GPU process check: required as read-only evidence only; no start/restart.

## Validation

- `scripts/gpu_process_guard.sh --check`
- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/cockpit_llama_server_gpu_default_visibility_v1_20260526.md`
- `python3 scripts/agent_job_registry.py list-active --read-only`
- `python3 scripts/agent_job_registry.py check-overlap docs/agent_tasks/cockpit_llama_server_gpu_default_visibility_v1_20260526.md --repo-root .`
- `python3 scripts/agent_job_registry.py claim docs/agent_tasks/cockpit_llama_server_gpu_default_visibility_v1_20260526.md --repo-root .`
- focused Vitest for GPU ordering helper
- `pnpm --dir cockpit-ui lint`
- `git diff --check`
- task-card `check-diff`
- registry release before closeout

## Hard Stops

- Active same-file collision on Cockpit GPU display/API files.
- Any required change to model/runtime/GPU/service configuration.
- Any DB/Qdrant/news/memory/canonical financial truth mutation.
- Evidence shows a duplicate open PR already owns this issue.
