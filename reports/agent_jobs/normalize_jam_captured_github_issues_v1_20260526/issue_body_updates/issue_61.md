## Tenn Issue Contract Normalization

Task: `cockpit_llama_server_gpu_default_visibility_v1_20260526`

Classification: normalized in place as a task-card-ready runtime/reporting
honesty issue.

## Lane

Primary lane: Runtime
Supporting lanes: Reporting
Mode: audit_first

## GitHub Tracking

Recommended labels applied by #106 normalization: `lane:runtime`, `lane:reporting`, `mode:audit`, `priority:p1`, `risk:medium`, `state:ready`, `type:bug`, `type:usability`

Milestone: M6 - Runtime / Local Automation

## Source Evidence

Original issue evidence sampled on branch
`migration/clean-runtime-baseline-reconstruct-v1` at `6eb30d3f0988`:

- Active `llama-server` child PID `3959547` served `model:qwen3.5-35b-a3b-apex`.
- `nvidia-smi --query-compute-apps` mapped that PID to GPU UUID `GPU-8ca6f48a-7934-31b2-ebe6-a65201e888d6`.
- Host inventory mapped that UUID to host GPU index `1`, Tesla M40 24GB, with about `17211 / 24576 MiB` used.
- Host GPU index `0` was NVIDIA GeForce GT 1030 with about `1 / 2048 MiB` used.
- Cockpit could still surface the GT 1030 as the default/primary visible GPU.

## Why This Matters

Runtime observability should show the GPU carrying the local model first. Showing
the first enumerated host adapter as the primary model GPU can mislead operators,
especially on multi-GPU hosts where CUDA runtime indexing differs from host GPU
indexing.

## Required Task Card

`docs/agent_tasks/cockpit_llama_server_gpu_default_visibility_v1_20260526.md`

## Required Report Path

`reports/agent_jobs/cockpit_llama_server_gpu_default_visibility_v1_20260526/`

## Allowed Files / Surfaces

- Task card and report artifacts.
- Read-only runtime/GPU evidence collection.
- Read-only inspection of Cockpit runtime summary and GPU Activity surfaces.
- Focused UI/backend tests for multi-GPU display ordering only in a later task card.
- Runtime status rendering files only in a later safe-extension task that names exact files.

## Forbidden Files / Surfaces

- Model binding, launcher defaults, CUDA visibility, GPU routing, or service startup behavior.
- Runtime/model/GPU/service config mutation.
- DB, Qdrant, news, or memory mutation.
- Canonical financial truth mutation.
- Parser routing, extraction prompts, or gold labels.
- Broad replacement of health/status architecture.

## Validation

- Confirm current active `llama-server` PID and model endpoint if running.
- Map active model process PID to GPU UUID and host GPU index when available.
- Verify Cockpit default/primary visible GPU ordering.
- Confirm fallback behavior when process-to-GPU mapping is unavailable.
- Add regression coverage for a multi-GPU host where active model process is not host GPU index 0 in a later implementation task.

## Hard Stops

- Active model process or GPU telemetry is unavailable and cannot be represented as `DATA_MISSING`.
- A proposed fix changes GPU routing or launcher config instead of display semantics.
- Required evidence collection would mutate runtime services.
- Duplicate tracker covers the same root cause and validation path.

## Definition of Done

- Cockpit defaults to the active model GPU when it can be resolved.
- Other GPUs remain visible as secondary hardware.
- Host GPU index and runtime-visible CUDA index are not conflated.
- If active model GPU cannot be resolved, Cockpit reports a degraded or `DATA_MISSING` state instead of implying host GPU index 0 is the model GPU.

## DATA_MISSING

- Current active `llama-server` process and GPU UUID at the active HEAD.
- Current Cockpit runtime summary behavior after recent runtime/reporting changes.
- Whether GPU Activity issue #90 remediation changes the available process/GPU evidence.

## Follow-Up / Parking / Dependencies

- Related but not duplicate: #90 covers GPU Activity reporting no processes while llama-server is healthy.
- Related but not duplicate: #113 covers remaining llama-server `:8001` owner evidence.
- This issue covers default visible/primary GPU selection.
