---
job_id: appendix5b_fifth_doc_approval_packet_v1_20260517
lane: Evaluation
owner: Codex
allowed_files:
  - docs/agent_tasks/appendix5b_fifth_doc_approval_packet_v1_20260517.md
  - scripts/
  - docs/validation_baseline.md
  - docs/architecture/12_evaluation_and_drift_monitoring.md
  - reports/agent_jobs/appendix5b_fifth_doc_approval_packet_v1_20260517/
approval_required: false
allow_unapproved_safe_extension: true
timeout_seconds: 3600
output_dir: reports/agent_jobs/appendix5b_fifth_doc_approval_packet_v1_20260517
mutation_mode: safe_extension
production_data_access: false
---

# Task

Create a fresh evidence-bound approval packet for one additional cold-store Appendix 5B PDF and add it to the Appendix 5B no-regression floor only if it passes the same approval standard as the existing gated documents.

# Objective

Expand the Appendix 5B no-regression floor from 4 approved/gated documents to 5, but only if the fifth document has clean page-bound evidence and the recurring evaluation gate remains passing.

# Current approved/gated floor

Current gated Appendix 5B docs are reported as:

- GRE Dec 2024
- EQR Dec 2025
- GRE Sep 2025
- 10X Dec 2025

The fifth document is currently DATA_MISSING.

# Hard boundaries

Do not:
- touch the dirty preserve checkout
- edit parser implementation
- edit extraction prompts
- edit canonical financial truth writes
- edit production DB/Qdrant/news/memory state
- run rented GPU jobs
- run broad extraction
- use live network
- add more than one new document
- convert ambiguous evidence into a scored label
- score a document without page/line/current-quarter evidence
- weaken evidence standards
- change the meaning of operating_cash_flow
- silently include unscored probes in the no-regression floor
- do Home/UI/runtime/news work in this task

# Required preflight

From /home/l4nd0/tenn-fast-dev-storage-v1, report:

- pwd
- git branch --show-current
- git rev-parse --short=12 HEAD
- git status --short --untracked-files=all
- git log --oneline -12
- git worktree list
- whether commit 5d08ee34cb2e is locally visible
- whether the recurring gate files are already present in active NVMe
- task-card validation, if supported
- registry/list-active, if supported
- whether active jobs overlap Appendix 5B/evaluation/script/doc surfaces

Do not stop merely because unrelated agents are active.
Stop only for direct overlap with this task card, output_dir, or the specific Appendix 5B/evaluation files being changed.

# Source discovery

Find candidate cold-store Appendix 5B PDFs without mutating production data.

For candidates, identify:
- ticker/company
- report period/date
- source path
- whether it is clearly Appendix 5B
- whether the current-quarter operating cash flow line is visible and unambiguous
- page number
- line/row label
- current-quarter column
- extracted value
- currency/scale if available

Select exactly one best candidate.

Selection criteria:
1. Clearly Appendix 5B.
2. Operating cash flow/current-quarter row is present.
3. Page/line/column evidence is unambiguous.
4. No mixed-period ambiguity.
5. No OCR/font weirdness that prevents verification.
6. Minimal risk of confusing YTD vs current-quarter.
7. Different enough from existing gated docs to improve coverage if possible.

If no candidate meets the standard, do not force it. Report DATA_MISSING and stop.

# Approval packet requirements

Create a report-local approval packet under:

reports/agent_jobs/appendix5b_fifth_doc_approval_packet_v1_20260517/

The approval packet must include:
- selected PDF path
- ticker/company
- period/date
- metric: operating_cash_flow
- expected value
- page number
- row/line label
- column label proving current-quarter context
- currency/scale evidence if available
- screenshot/text/table excerpt reference if available
- reason it is safe to score
- explicit pass/fail/unscored classification
- any ambiguity notes

If the evidence is ambiguous, classify as unscored and do not add to the no-regression floor.

# Integration rules

Only if the approval packet is clean:
1. Add the new doc/metric to the Appendix 5B no-regression floor using the existing pattern.
2. Preserve existing approved docs unchanged.
3. Run the recurring extraction evaluation gate.
4. Gate must remain passing.
5. Update validation docs minimally to mention the expanded floor.

If the gate fails after adding the fifth doc:
- keep the approval packet/report
- do not claim the floor expanded successfully
- classify failure
- recommend next safe step
- do not patch parser logic in this task unless the failure is only task-local data wiring and remains within allowed files

# Validation required

Run focused validation only:

- recurring Appendix 5B/evaluation wrapper
- focused pytest for the gate tests
- targeted ruff on changed Python files
- JSON artifact checks if reports are emitted
- check for accidental raw PDF/tmp/core/generated heavy files
- git diff --check
- task-card check-diff if supported

Do not run broad extraction, rented GPU jobs, or production data mutations.

# Required report

Write:
- reports/agent_jobs/appendix5b_fifth_doc_approval_packet_v1_20260517/README.md
- reports/agent_jobs/appendix5b_fifth_doc_approval_packet_v1_20260517/status.json

Optional but useful:
- reports/agent_jobs/appendix5b_fifth_doc_approval_packet_v1_20260517/approval_packet.json
- reports/agent_jobs/appendix5b_fifth_doc_approval_packet_v1_20260517/candidate_inventory.json

README.md must include:
1. Executive summary
2. Confirmed facts
3. Inferred facts
4. DATA_MISSING
5. Preflight results
6. Candidate inventory summary
7. Selected fifth document and why
8. Approval packet details
9. Evidence-bound assessment
10. Whether the doc was added to the no-regression floor
11. Gate results before/after if applicable
12. Tests/checks run with exact results
13. Files changed
14. Files intentionally not touched
15. Risks and blockers
16. Recommended next safe step
17. Project Memory save recommendation
18. Final repo/worktree status
19. Registry claim/release status if supported

status.json must include:
- job_id
- mode
- lane
- branch
- head
- selected_pdf
- selected_ticker
- selected_period
- approved_for_scoring
- added_to_gate
- gate_status
- validation_status
- changed_files
- data_missing
- recommended_next_step
- save_recommendation

# Definition of done

Done when one of these is true:

Success path:
- one fifth Appendix 5B doc has a clean approval packet
- it has been added to the no-regression floor
- recurring gate passes
- focused tests/checks pass
- no parser/canonical/runtime/data changes were made
- final report is written

Blocked path:
- no suitable fifth doc is found or evidence is ambiguous
- no gate expansion is claimed
- DATA_MISSING is clearly reported
- final report is written

# Hard stops

Stop and report only if:
- task card validation fails
- registry/list-active shows direct conflict on this task card/output_dir or Appendix 5B/eval files
- active NVMe has unexpected dirty files touching the same Appendix 5B/eval files
- commit 5d08ee34cb2e or the recurring gate pattern cannot be inspected and active files are insufficient
- candidate evidence is ambiguous
- adding the fifth doc would require parser/extraction/canonical-write changes
- validation would require rented GPU, network, or production data mutation
- recurring gate fails for reasons outside this task’s allowed scope
- the task would need to touch the dirty preserve checkout

After creating/validating the task card:

1. Validate task card using repo-supported tooling if available.
2. Run registry/list-active if available.
3. Claim only this narrow task if supported.
4. Do not claim broad Financial Truth or Evaluation ownership if narrower file/path claim is supported.
5. If unrelated jobs are active, continue and record them in the report.
6. If directly overlapping Appendix 5B/eval work is active, stop and report.
7. Discover candidate cold-store Appendix 5B PDFs.
8. Select exactly one candidate if evidence is clean.
9. Build the report-local approval packet.
10. Add it to the no-regression floor only if clean.
11. Run focused validation.
12. Write final report under reports/agent_jobs/appendix5b_fifth_doc_approval_packet_v1_20260517/.
13. Run check-diff if supported.
14. Release only this task’s registry claim if supported.
15. Stop and report. Do not broaden into parser work or a sixth document.
