# Ops Quickstart (Incident Router)

Use this page to route incidents to the right runbook quickly.

## Incident -> Document

1. NVML/nvidia-smi failure, GPU not visible, NVRM/Xid patterns  
   Use: `01_nvml_host_stabilization_runbook.md`

2. Ollama not using GPU, CUDA arch errors, CPU fallback suspicion  
   Use: `02_ollama_m40_validation_and_mitigation.md`

3. Model too slow/OOM/context too small, tier/routing decisions needed  
   Use: `03_model_tiering_m40_24gb.md`

4. Queue deadlock, overnight pipeline drift, provenance gaps  
   Use: `04_batch_pipeline_architecture_fastapi_celery.md`

5. Need to stand up/recover Phase-1 docker services while keeping GPU on host  
   Use: `05_compose_phase1_host_gpu_blueprint.md`  
   Artifacts:
   - `05.compose.phase1.yml`
   - `05.env.template`

6. Rollout gate decision (go/no-go), durability checks, traceability checks  
   Use: `06_production_hardening_acceptance_suite.md`

## Fast Triage Flow

1. If GPU stability is suspect, always start with `01`.
2. Do not attempt model tier tuning until `01` and `02` are green.
3. For production rollout decisions, `06` is the final arbiter.

## Escalation Rule

If an incident crosses document boundaries:
- Start with the lower-layer dependency first:
  - host stability (`01`) -> runtime (`02`) -> model policy (`03`) -> pipeline/compose (`04`/`05`) -> release gate (`06`).
