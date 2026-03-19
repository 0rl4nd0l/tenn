# 02 - Ollama on Tesla M40 (sm_52): Validation and Mitigation

Goal: ensure Ollama uses Tesla M40 reliably on Ubuntu 22.04 headless.

Prerequisite:
- Complete `01_nvml_host_stabilization_runbook.md` first.

## Detection: How We Know GPU Is Actually Being Used

Use all layers below; do not rely on one signal.

### A. Ollama Runtime Signals
- Confirm Ollama daemon is running and model is loaded.
- Inspect Ollama logs for GPU backend initialization and CUDA path.
- Check for explicit fallback messages that indicate CPU path.

Expected positive indicators:
- GPU backend initialization messages without CUDA arch errors.
- Stable model load and inference timing improvements vs CPU baseline.

### B. Host Telemetry Signals
- During an inference run, check GPU memory usage rise and compute activity.
- Validate that activity is on the M40 device (not only GT1030 or CPU-only).

Expected positive indicators:
- M40 memory allocation increases on model load.
- M40 utilization/compute spikes during generation.

### C. End-to-End Functional Signal
- Run a representative prompt with known runtime profile.
- Compare latency/profile to known CPU-only behavior.

Expected positive indicator:
- Runtime characteristics align with GPU-assisted inference.

## Failure Modes (Symptom -> Likely Cause)

1. `CUDA error 209: no kernel image available for execution on the device`
- Likely cause: binary built without `sm_52` kernels for Maxwell.

2. Ollama starts but inference stays CPU-like
- Likely cause: silent fallback due to backend init failure, runtime mismatch, or unsupported build flags.

3. Intermittent GPU usage / random fallback
- Likely cause: host NVML instability, driver stack drift, or GPU runtime errors under load.

4. Model load fails only on larger tiers
- Likely cause: VRAM pressure/KV cache constraints or fragmentation, not necessarily architecture incompatibility.

## Fix Plan

### 1) Pinning Policy (Baseline)
- Pin NVIDIA driver branch to validated production branch (current policy: 535 family).
- Pin Ollama version once validated against M40.
- Maintain a version matrix doc: driver, kernel, Ollama, model tiers.

### 2) Source Build Strategy (If prebuilt lacks sm_52)
- Build Ollama from source with CUDA architecture list explicitly including `sm_52`.
- Use reproducible build inputs and record commit/tag + build flags.
- Produce a packaged deploy artifact to avoid ad-hoc host builds.

Build acceptance gates before promotion:
- No GPU backend init errors in logs.
- Representative model runs on M40 without `no kernel image` pattern.
- Stable behavior across reboot and service restart.

### 3) Controlled Rollout
- Canary host or canary window first.
- Keep previous known-good Ollama package available.
- Promote only after acceptance suite pass.

## Ops Policy: Upgrade, Rollback, and Fallback

### Upgrade Gates
Upgrade only when all are true:
- NVML stable across three reboots.
- Candidate build passes GPU detection and representative load tests.
- No recurring NVRM/Xid in observation window.

### Rollback Policy
Rollback immediately if:
- `no kernel image` or repeated backend init failures appear.
- GPU usage disappears for representative runs.
- Stability regressions show in acceptance checks.

Rollback target:
- Last pinned known-good Ollama + driver matrix.

### CPU-Only Fallback Policy
If GPU unavailable:
- Force CPU mode explicitly to avoid misleading partial behavior.
- Restrict to smaller tiers and shorter contexts.
- Move heavy research to overnight windows only.
- Disable high-throughput expectations and update SLOs.

### Reduced Tier Policy Under Degradation
- Use smallest operational tier first.
- Cap context and concurrent jobs aggressively.
- Defer noncritical batch jobs until GPU path restored.

## Command Example Class (Non-binding)
- Service status checks
- Log tailing/grep for CUDA init and fallback markers
- Telemetry sampling during prompt execution
- Version inventory output capture

(Exact commands are environment-dependent; keep in local ops scripts if needed.)
