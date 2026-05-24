---
job_id: appendix5b_backend_gate_services_restore_v1_20260517
lane: Evaluation
owner: Codex
allowed_files:
  - docs/agent_tasks/appendix5b_backend_gate_services_restore_v1_20260517.md
  - scripts/run_appendix5b_no_regression_gate.py
  - scripts/test_appendix5b_no_regression_gate.py
  - scripts/run_extraction_evaluation_gates.py
  - scripts/test_extraction_evaluation_gates.py
  - scripts/build_appendix5b_manifest_from_docling.py
  - scripts/build_asx_appendix5b_label_review_packet.py
  - scripts/import_asx_appendix5b_confirmed_labels.py
  - scripts/run_appendix5b_candidate_artifacts.py
  - scripts/score_asx_appendix5b_candidates.py
  - scripts/
  - financial-engine_v2/backend/app/services/asx_appendix5b_candidate_artifacts.py
  - financial-engine_v2/backend/app/services/asx_appendix5b_candidate_scorer.py
  - financial-engine_v2/backend/app/services/asx_appendix5b_confirmed_label_importer.py
  - financial-engine_v2/backend/app/services/asx_appendix5b_label_review_packet.py
  - financial-engine_v2/backend/app/services/asx_appendix5b_manifest_builder.py
  - financial-engine_v2/backend/app/services/asx_appendix5b_parser.py
  - financial-engine_v2/backend/app/services/
  - financial-engine_v2/backend/tests/test_asx_appendix5b_candidate_artifacts.py
  - financial-engine_v2/backend/tests/test_asx_appendix5b_candidate_scorer.py
  - financial-engine_v2/backend/tests/test_asx_appendix5b_confirmed_label_importer.py
  - financial-engine_v2/backend/tests/test_asx_appendix5b_label_review_packet.py
  - financial-engine_v2/backend/tests/test_asx_appendix5b_manifest_builder.py
  - financial-engine_v2/backend/tests/test_asx_appendix5b_parser.py
  - financial-engine_v2/backend/tests/
  - docs/architecture/12_evaluation_and_drift_monitoring.md
  - docs/validation_baseline.md
  - reports/agent_jobs/appendix5b_backend_gate_services_restore_v1_20260517/
approval_required: true
timeout_seconds: 7200
output_dir: reports/agent_jobs/appendix5b_backend_gate_services_restore_v1_20260517
mutation_mode: safe_extension
production_data_access: false
---

# Task

Restore the existing Appendix 5B backend scorer/parser/candidate service stack needed by the no-regression wrapper, then promote PRM Dec 2025 into the Appendix 5B no-regression floor only if the recurring gate passes.

# Objective

Resolve the blocker from the prior task:
- active NVMe lacks the Appendix 5B backend gate/scorer/parser service files needed by the source wrapper.

Then:
- run the recurring Appendix 5B evaluation gate;
- include PRM only if the gate passes;
- preserve evidence-bound approval semantics;
- avoid canonical writes and production-data mutation.

# Current no-regression floor

Current gated floor before PRM:
- GRE Dec 2024
- EQR Dec 2025
- GRE Sep 2025
- 10X Dec 2025

Candidate to promote:
- PRM Dec 2025
- Metric: operating_cash_flow
- Evidence:
  - PDF page: 8
  - Appendix 5B page: 1
  - Line: 1.9 Net cash from / (used in) operating activities
  - Column: Current quarter $A'000
  - Source value: (246)
  - Normalized value: -246000 AUD

# Source commits/worktrees to inspect

1. Repeatable no-regression gate:
   - branch: safe/appendix5b-10x-no-regression-suite-v1-20260517
   - worktree: /home/l4nd0/tenn-appendix5b-10x-no-regression-suite-v1-20260517
   - commit: ae2dfd81cdfc

2. Recurring gate integration:
   - branch: safe/appendix5b-recurring-gate-integration-v1-20260517
   - worktree: /home/l4nd0/tenn-appendix5b-recurring-gate-integration-v1-20260517
   - commit: 5d08ee34cb2e

3. PRM approval packet:
   - commit: 55f746aabb10
   - report dir: reports/agent_jobs/appendix5b_fifth_doc_approval_packet_v1_20260517/

4. Prior blocked task:
   - docs/agent_tasks/appendix5b_gate_stack_prm_promotion_v1_20260517.md
   - reports/agent_jobs/appendix5b_gate_stack_prm_promotion_v1_20260517/

# Hard boundaries

Do not:
- touch the dirty preserve checkout
- edit extraction prompts
- edit canonical financial truth writes
- edit production DB/Qdrant/news/memory state
- run rented GPU jobs
- run live network
- run broad extraction
- do Home/UI/runtime/news work
- add any document other than PRM
- weaken evidence standards
- change the meaning of operating_cash_flow
- silently include unscored probes in the no-regression floor
- fabricate candidate artifacts
- convert ambiguous evidence into a scored label
- broaden into Appendix 4C/4D/4E
- broaden into full metric extraction redesign

Allowed only because this task needs it:
- restore existing Appendix 5B backend scorer/parser/candidate service files under financial-engine_v2/backend/app/services/
- add/update focused backend tests under financial-engine_v2/backend/tests/ only for the restored Appendix 5B eval service stack

# Required preflight

From /home/l4nd0/tenn-fast-dev-storage-v1, report:

- pwd
- git branch --show-current
- git rev-parse --short=12 HEAD
- git status --short --untracked-files=all
- git log --oneline -12
- git worktree list
- whether commits ae2dfd81cdfc, 5d08ee34cb2e, and 55f746aabb10 are locally visible
- whether source worktrees exist and are clean/dirty
- whether PRM approval packet exists and evidence matches `(246)` / `-246000 AUD`
- whether prior blocked report exists
- task-card validation, if supported
- registry/list-active, if supported
- whether active jobs overlap Appendix 5B/evaluation/backend service/test surfaces
- note unrelated untracked `docs/agent_tasks/m40_8001_conservative_validation_v1_20260517.md` if still present, but do not modify it

Do not stop merely because unrelated agents/files exist.
Stop only for direct overlap with this task card, output_dir, Appendix 5B eval scripts, backend Appendix 5B services, or focused backend tests being changed.

# Implementation requirements

1. Inspect source commits/worktrees ae2dfd81cdfc and 5d08ee34cb2e.
2. Identify exactly which backend services the Appendix 5B no-regression wrapper imports and which are missing in active NVMe.
3. Restore only the existing Appendix 5B scorer/parser/candidate service files needed for the wrapper.
4. Preserve behavior from the source gate branches.
5. Add/update focused backend tests only if needed to validate imports/service behavior.
6. Bring the recurring wrapper/gate files into active NVMe only if still missing.
7. Verify the PRM approval packet.
8. Add PRM to the no-regression floor only if:
   - approval packet evidence is present and matches reported value;
   - backend gate/scorer/parser services import successfully;
   - the gate can run service-free/non-mutating;
   - the recurring gate passes.
9. If controlled Docling/candidate artifact generation is required, run only the smallest existing local command needed, and only if service-free and non-mutating.
10. Update validation docs minimally if and only if the no-regression floor expands to five docs.

# Promotion rules

PRM can be marked promoted only if all are true:
- PRM approval packet remains evidence-bound.
- PRM is scored as operating_cash_flow current-quarter Appendix 5B line 1.9.
- Normalized expected value is -246000 AUD.
- Existing four-doc floor remains passing.
- Recurring gate passes with PRM included.
- Focused backend import/service tests pass.
- No parser prompt/canonical/runtime/production data changes were made.

If any condition fails:
- keep PRM approval-packet-only;
- do not claim a five-document floor;
- report the blocker and next safe step.

# Validation required

Run focused validation only:

- backend import check for restored Appendix 5B services
- focused backend pytest for restored services, if tests exist or are added
- recurring Appendix 5B/evaluation wrapper
- focused pytest for no-regression/gate tests
- targeted ruff on changed Python files
- JSON artifact checks if reports are emitted
- check for accidental raw PDF/tmp/core/generated heavy files
- git diff --check
- task-card check-diff if supported

Do not run:
- broad extraction
- rented GPU jobs
- network calls
- production data mutations
- full frontend/UI tests
- dirty preserve checkout commands except harmless visibility via worktree list

# Required report

Write:
- reports/agent_jobs/appendix5b_backend_gate_services_restore_v1_20260517/README.md
- reports/agent_jobs/appendix5b_backend_gate_services_restore_v1_20260517/status.json

Optional but useful:
- reports/agent_jobs/appendix5b_backend_gate_services_restore_v1_20260517/import_check.txt
- reports/agent_jobs/appendix5b_backend_gate_services_restore_v1_20260517/gate_result.json
- reports/agent_jobs/appendix5b_backend_gate_services_restore_v1_20260517/promotion_decision.json
- reports/agent_jobs/appendix5b_backend_gate_services_restore_v1_20260517/service_inventory.json

README.md must include:
1. Executive summary
2. Confirmed facts
3. Inferred facts
4. DATA_MISSING
5. Preflight results
6. Source commits/worktrees inspected
7. Missing backend service inventory
8. Files restored into active NVMe
9. PRM approval packet verification
10. Whether PRM was added to the no-regression floor
11. Gate results before/after if applicable
12. Backend import/test results
13. Other tests/checks run with exact results
14. Files changed
15. Files intentionally not touched
16. Risks and blockers
17. Recommended next safe step
18. Project Memory save recommendation
19. Final repo/worktree status
20. Registry claim/release status if supported

status.json must include:
- job_id
- mode
- lane
- branch
- head
- source_commits_available
- backend_services_restored
- restored_service_files
- prm_approval_packet_found
- prm_promoted_to_floor
- gate_status
- backend_validation_status
- validation_status
- changed_files
- data_missing
- recommended_next_step
- save_recommendation

# Definition of done

Success path:
- active NVMe contains required Appendix 5B backend gate/scorer/parser services
- backend imports/tests pass
- recurring Appendix 5B gate runs
- PRM is added to the no-regression floor
- recurring gate passes with five docs
- no parser prompt/canonical/runtime/production-data changes were made
- final report is written

Blocked path:
- backend service restoration cannot be safely done under allowed scope, or PRM cannot be safely run/promoted
- PRM remains approval-packet-only
- DATA_MISSING/blocker is clearly reported
- final report is written

# Hard stops

Stop and report only if:
- task card validation fails
- approval is required and not granted by repo/tooling
- registry/list-active shows direct conflict on this task card/output_dir, Appendix 5B eval scripts, backend Appendix 5B services, or focused backend tests
- active NVMe has unexpected dirty files touching the same Appendix 5B/backend service/test surfaces
- source commits/worktrees are unavailable and active files are insufficient
- PRM approval packet is missing or evidence does not match `(246)` / `-246000 AUD`
- promotion requires extraction prompt changes or canonical-write changes
- validation requires rented GPU, network, production data mutation, or dirty preserve checkout
- recurring gate fails for reasons outside this task’s allowed scope
- restoring services requires broad backend redesign rather than restoring existing Appendix 5B eval service files
- the task would need to touch the dirty preserve checkout
