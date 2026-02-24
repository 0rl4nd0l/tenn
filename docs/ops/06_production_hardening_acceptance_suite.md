# 06 - Production Hardening Acceptance Suite

Use this as the rollout gate before scaling workloads.

## Pass/Fail Rules
- Every item has binary pass/fail.
- Any fail blocks production scale-up until resolved.
- Record evidence for each run (timestamp + operator + outputs/log refs).

## A. GPU / NVML

### A1 - NVML stable across 3 reboots
- Check: after each reboot, run GPU visibility and NVML health checks.
- Pass: all three reboots show successful NVML initialization and stable GPU enumeration.
- Fail action: return to `01_nvml_host_stabilization_runbook.md` branching process.

### A2 - Persistence and device nodes stable
- Check: persistence service healthy and `/dev/nvidia*` nodes present each boot.
- Pass: no missing nodes, no flapping service.
- Fail action: repair persistence/device-node path before further testing.

### A3 - No repeated NVRM/Xid errors
- Check: kernel logs during observation window.
- Pass: no repeating NVRM/Xid pattern.
- Fail action: stop scale-up; investigate hardware/driver branch issues.

## B. Ollama

### B1 - GPU-confirmed inference run
- Check: representative model run with Ollama logs + host telemetry.
- Pass: M40 shows memory/compute activity and no fallback errors.
- Fail action: apply `02_ollama_m40_validation_and_mitigation.md` fix path.

### B2 - No `no kernel image` / CUDA arch mismatch pattern
- Check: logs and run output.
- Pass: no architecture mismatch errors.
- Fail action: switch to source-built/pinned artifact with sm_52 support.

### B3 - Degraded-mode policy verified
- Check: CPU fallback policy can be engaged intentionally.
- Pass: CPU mode runs with reduced tier/context and expected SLA downgrade.
- Fail action: fix fallback controls before production release.

## C. Queues and Workers

### C1 - Queue health and no deadlocks
- Check: enqueue/dequeue flow across `ingest`, `embed`, `score`, `llm_gpu`, `llm_cpu`.
- Pass: jobs progress; no stuck queue with active workers.
- Fail action: inspect broker/workers, fix routing/concurrency policy.

### C2 - GPU queue concurrency is enforced
- Check: `llm_gpu` queue executes strictly one job at a time.
- Pass: no concurrent GPU tasks observed.
- Fail action: tighten worker pool/queue config immediately.

### C3 - Overnight sustained run sanity
- Check: one overnight batch cycle completes without GPU dropout or deadlock.
- Pass: completed run with no critical runtime faults.
- Fail action: pause scheduling, remediate failing subsystem, rerun burn-in.

## D. Postgres and Qdrant Durability

### D1 - Postgres backup/restore dry-run
- Check: backup artifact created and restored to test target.
- Pass: restored DB passes basic integrity and row-count sanity checks.
- Fail action: fix backup process before production.

### D2 - Qdrant snapshot/restore dry-run
- Check: snapshot and restore to non-prod target.
- Pass: collection metadata and sample retrieval checks succeed.
- Fail action: fix vector backup policy before scale-up.

### D3 - Artifact storage growth controls
- Check: disk growth trend and retention policy behavior during overnight run.
- Pass: no runaway growth outside expected envelope.
- Fail action: enforce retention/archival and rerun overnight sanity.

## E. Application and Provenance Integrity

### E1 - Provenance completeness on generated artifacts
- Check each output includes traceable fields:
  - source doc IDs
  - model/version
  - prompt template version
  - extractor version
  - job run ID
  - timestamp
- Pass: all required fields present for sampled outputs.
- Fail action: block release until provenance writes are fixed.

### E2 - Reproducibility sanity
- Check rerun deterministic job with unchanged inputs/versions.
- Pass: equivalent output class + matching lineage metadata expectations.
- Fail action: investigate nondeterminism and version drift.

### E3 - Alert pipeline traceability
- Check event flags/summaries map to upstream sources and scoring runs.
- Pass: full lineage from alert -> score -> docs.
- Fail action: disable autonomous alert actions until lineage gap is fixed.

## Final Rollout Gate

Production scaling is allowed only when:
1. A1-A3 pass
2. B1-B3 pass
3. C1-C3 pass
4. D1-D3 pass
5. E1-E3 pass

If any fail, remain in stabilization mode and rerun suite after remediation.
