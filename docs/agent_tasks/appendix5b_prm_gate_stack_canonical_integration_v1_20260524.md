---
job_id: appendix5b_prm_gate_stack_canonical_integration_v1_20260524
lane: Evaluation
owner: Codex
allowed_files:
  - docs/agent_tasks/appendix5b_prm_gate_stack_canonical_integration_v1_20260524.md
  - docs/agent_tasks/appendix5b_backend_gate_services_restore_v1_20260517.md
  - financial-engine_v2/backend/app/services/asx_appendix5b_candidate_artifacts.py
  - financial-engine_v2/backend/app/services/asx_appendix5b_candidate_scorer.py
  - financial-engine_v2/backend/app/services/asx_appendix5b_confirmed_label_importer.py
  - financial-engine_v2/backend/app/services/asx_appendix5b_label_review_packet.py
  - financial-engine_v2/backend/app/services/asx_appendix5b_manifest_builder.py
  - financial-engine_v2/backend/app/services/asx_appendix5b_parser.py
  - financial-engine_v2/backend/tests/test_asx_appendix5b_candidate_artifacts.py
  - financial-engine_v2/backend/tests/test_asx_appendix5b_candidate_scorer.py
  - financial-engine_v2/backend/tests/test_asx_appendix5b_confirmed_label_importer.py
  - financial-engine_v2/backend/tests/test_asx_appendix5b_label_review_packet.py
  - financial-engine_v2/backend/tests/test_asx_appendix5b_manifest_builder.py
  - financial-engine_v2/backend/tests/test_asx_appendix5b_parser.py
  - scripts/build_appendix5b_manifest_from_docling.py
  - scripts/build_asx_appendix5b_label_review_packet.py
  - scripts/import_asx_appendix5b_confirmed_labels.py
  - scripts/run_appendix5b_candidate_artifacts.py
  - scripts/run_appendix5b_no_regression_gate.py
  - scripts/run_extraction_evaluation_gates.py
  - scripts/score_asx_appendix5b_candidates.py
  - scripts/test_appendix5b_no_regression_gate.py
  - scripts/test_extraction_evaluation_gates.py
  - docs/architecture/12_evaluation_and_drift_monitoring.md
  - docs/validation_baseline.md
  - reports/agent_jobs/appendix5b_backend_gate_services_restore_v1_20260517/README.md
  - reports/agent_jobs/appendix5b_backend_gate_services_restore_v1_20260517/appendix5b_no_regression_report.json
  - reports/agent_jobs/appendix5b_backend_gate_services_restore_v1_20260517/baseline_artifacts/eqr_q4_fy2026_appendix5b.rerun_artifact.json
  - reports/agent_jobs/appendix5b_backend_gate_services_restore_v1_20260517/baseline_artifacts/gre_asx_june2025_alt.rerun_artifact.json
  - reports/agent_jobs/appendix5b_backend_gate_services_restore_v1_20260517/baseline_artifacts/gre_q4_fy2025_appendix5b.rerun_artifact.json
  - reports/agent_jobs/appendix5b_backend_gate_services_restore_v1_20260517/baseline_artifacts/gre_q_2025-09-30.rerun_artifact.json
  - reports/agent_jobs/appendix5b_backend_gate_services_restore_v1_20260517/baseline_artifacts/pek_asx_july2025_probe.rerun_artifact.json
  - reports/agent_jobs/appendix5b_backend_gate_services_restore_v1_20260517/baseline_artifacts/tenx_artifact.json
  - reports/agent_jobs/appendix5b_backend_gate_services_restore_v1_20260517/confirmed_labels_prm_included.json
  - reports/agent_jobs/appendix5b_backend_gate_services_restore_v1_20260517/diff-check.json
  - reports/agent_jobs/appendix5b_backend_gate_services_restore_v1_20260517/gate_result.json
  - reports/agent_jobs/appendix5b_backend_gate_services_restore_v1_20260517/import_check.txt
  - reports/agent_jobs/appendix5b_backend_gate_services_restore_v1_20260517/prm_artifact.json
  - reports/agent_jobs/appendix5b_backend_gate_services_restore_v1_20260517/prm_docling_runner.out
  - reports/agent_jobs/appendix5b_backend_gate_services_restore_v1_20260517/prm_docling_runner.py
  - reports/agent_jobs/appendix5b_backend_gate_services_restore_v1_20260517/prm_manifest.json
  - reports/agent_jobs/appendix5b_backend_gate_services_restore_v1_20260517/prm_q_2025-12-31.docling.json
  - reports/agent_jobs/appendix5b_backend_gate_services_restore_v1_20260517/prm_q_2025-12-31_source.pdf.docling.json
  - reports/agent_jobs/appendix5b_backend_gate_services_restore_v1_20260517/promotion_decision.json
  - reports/agent_jobs/appendix5b_backend_gate_services_restore_v1_20260517/recurring_eval_report.json
  - reports/agent_jobs/appendix5b_backend_gate_services_restore_v1_20260517/service_inventory.json
  - reports/agent_jobs/appendix5b_backend_gate_services_restore_v1_20260517/status.json
  - reports/agent_jobs/appendix5b_prm_gate_stack_canonical_integration_v1_20260524/README.md
  - reports/agent_jobs/appendix5b_prm_gate_stack_canonical_integration_v1_20260524/status.json
  - reports/agent_jobs/appendix5b_prm_gate_stack_canonical_integration_v1_20260524/validation.json
  - reports/agent_jobs/appendix5b_prm_gate_stack_canonical_integration_v1_20260524/diff-check.json
  - reports/agent_jobs/appendix5b_prm_gate_stack_canonical_integration_v1_20260524/code_review.json
  - reports/agent_jobs/appendix5b_prm_gate_stack_canonical_integration_v1_20260524/appendix5b_no_regression_report.json
  - reports/agent_jobs/appendix5b_prm_gate_stack_canonical_integration_v1_20260524/recurring_eval_report.json
approval_required: false
allow_unapproved_safe_extension: true
timeout_seconds: 7200
output_dir: reports/agent_jobs/appendix5b_prm_gate_stack_canonical_integration_v1_20260524
mutation_mode: safe_extension
production_data_access: false
---

# Appendix 5B PRM Gate Stack Canonical Integration

Integrate the fast-dev Appendix 5B PRM-inclusive parser, scorer, report-local gate, focused tests, documentation, and report evidence into canonical Tenn.

## Boundaries

- Keep all Appendix 5B outputs report-local and evaluation-only.
- Do not write canonical financial truth.
- Do not change parser routing, production extraction, DBs, Qdrant, news, memory, runtime services, Docker, systemd, cron, symlinks, mounts, Cockpit UI, dependencies, lockfiles, models, or GPU/runtime config.
- Use `/home/l4nd0/tenn-fast-dev-storage-v1` as read-only source.
- Exclude generated/cache/data files and the report bundle's source-PDF symlink into cold storage.

## Validation

- Task-card validation and registry overlap.
- `git diff --check`.
- Python compileall for changed services and scripts.
- Focused Appendix 5B pytest.
- Offline/report-local Appendix 5B no-regression gate and extraction-evaluation wrapper.
- JSON validation for preserved report artifacts.
- Proof of `canonical_write=false`.
- Proof that no parser-routing import/change was added.
- Task-card check-diff.
