# Cockpit Llama GPU Default Visibility

Job: `cockpit_llama_server_gpu_default_visibility_v1_20260526`
Related issue: #61
Lane: Reporting
Mode: safe extension
Generated: 2026-06-01T20:55:00+10:00

## Decision

Implemented a display-ordering fix for Cockpit GPU visibility. The BFF routes
that feed the sidebar and live GPU dialog now move the GPU running
`llama-server` to the front of the returned GPU list when a process-to-GPU UUID
mapping is available. The helper preserves host order when no llama process is
mapped.

## Runtime Evidence

Read-only GPU probes during this task showed:

- Host GPU 0: NVIDIA GeForce GT 1030, 1 / 2048 MiB.
- Host GPU 1: Tesla M40 24GB, 13615 / 24576 MiB.
- Active compute process: PID 599026, `llama-server`, 13612 MiB on GPU UUID
  `GPU-8ca6f48a-7934-31b2-ebe6-a65201e888d6`.
- The active process command included `--port 42443`, `--main-gpu 0`, and
  a model path that is intentionally redacted from this committed report.

That proves the original issue shape is currently present: the first host GPU
is not the active llama-server GPU.

## Implementation

- Added `cockpit-ui/lib/gpu-display.ts` with:
  - `selectPrimaryLlamaGpuUuid()`
  - `prioritizeGpusForDisplay()`
- Wired the helper into:
  - `cockpit-ui/app/api/cockpit/health/route.ts`
  - `cockpit-ui/app/api/cockpit/metrics/gpu/route.ts`
- Added focused unit tests for host-order preservation, llama GPU promotion,
  task-label fallback, and chat/router runtime preference.

## Boundaries

No model binding, CUDA visibility, launcher defaults, runtime service, DB,
Qdrant, news store, memory store, backend retrieval/storage, parser, prompt,
gold label, or canonical financial truth surface was changed.

## Validation

Passed:

- `scripts/gpu_process_guard.sh --check`
- task-card validate
- registry list-active / check-overlap / claim / refreshed claim
- `corepack pnpm --dir cockpit-ui install --frozen-lockfile`
- `corepack pnpm --dir cockpit-ui exec vitest run lib/gpu-display.test.ts`
  - 1 file, 4 tests passed
- `corepack pnpm --dir cockpit-ui exec eslint app/api/cockpit/health/route.ts app/api/cockpit/metrics/gpu/route.ts lib/gpu-display.ts lib/gpu-display.test.ts`
- `git diff --check`

Broader validation caveats:

- `corepack pnpm --dir cockpit-ui test -- lib/gpu-display.test.ts` invoked the
  full Vitest suite in this environment and failed on pre-existing Home and
  Marketplace tests outside this diff.
- `corepack pnpm --dir cockpit-ui lint` failed on pre-existing
  `thesis-audit-screen.tsx` unescaped quote errors and warnings outside this
  diff.

## Remaining Blockers

- The broader Cockpit UI suite still has unrelated failures that should be
  handled by their own task card or existing open UI validation issues.
