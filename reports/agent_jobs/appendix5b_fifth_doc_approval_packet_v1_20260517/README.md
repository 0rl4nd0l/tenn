# Appendix 5B Fifth Document Approval Packet

## 1. Executive summary

This task selected one cold-store Appendix 5B candidate, PRM December 2025, and built a report-local evidence packet for `operating_cash_flow`.

The source evidence is clean: page 8 of the selected PDF is Appendix 5B page 1, line 1.9, with `Current quarter $A'000` value `(246)`, equivalent to `-246000` AUD.

The document was not added to the Appendix 5B no-regression floor. The active NVMe branch does not contain the existing Appendix 5B scorer/gate stack, and this task card does not allow restoring backend evaluation service files from the isolated gate worktree. Promoting the document here would either require unsupported backend file restoration or a parallel scoring implementation, both outside scope.

## 2. Confirmed facts

- Worktree: `/home/l4nd0/tenn-fast-dev-storage-v1`
- Branch: `fast/dev-storage-v1-20260513-170304`
- HEAD: `f22a9ae8da5a`
- Commit `5d08ee34cb2e` is locally visible.
- Active NVMe did not have `scripts/run_extraction_evaluation_gates.py`, `scripts/test_extraction_evaluation_gates.py`, `scripts/run_appendix5b_no_regression_gate.py`, or the Appendix 5B backend scorer/service files on disk.
- Task-card validation initially failed because safe-extension jobs with `approval_required: false` need `allow_unapproved_safe_extension: true`; after the user said "Proceed", that field was added and validation passed.
- Registry claim succeeded for `appendix5b_fifth_doc_approval_packet_v1_20260517`.
- Selected PDF SHA-256: `3e9df824c77762ef5cc642f7efe0adc81f9576d8cb73ae2912fced76a4836645`.

## 3. Inferred facts

- PRM would improve coverage because it is a new ticker/company relative to the current reported gated floor.
- The selected source is low ambiguity because the line, page, column label, period, currency, and scale all appear together on the same Appendix 5B page.

## 4. DATA_MISSING

- Controlled Docling candidate artifact for PRM in active NVMe.
- Active-branch Appendix 5B scorer/gate scripts and backend evaluation services.
- Task-card permission to restore backend Appendix 5B evaluation service files.

## 5. Preflight results

- `pwd`: `/home/l4nd0/tenn-fast-dev-storage-v1`
- `git branch --show-current`: `fast/dev-storage-v1-20260513-170304`
- `git rev-parse --short=12 HEAD`: `f22a9ae8da5a`
- `git status --short --untracked-files=all` before card creation: clean output.
- `git log --oneline -12`: top commit was `f22a9ae8 milestone(memory): release nvme fastdev integration claim`.
- `git worktree list`: showed many isolated Appendix 5B worktrees, including `/home/l4nd0/tenn-appendix5b-recurring-gate-integration-v1-20260517` at `5d08ee34`.
- Commit `5d08ee34cb2e`: visible.
- Recurring gate files already present in active NVMe: no.
- Task-card validation: passed after adding `allow_unapproved_safe_extension: true`.
- Registry/list-active: supported; no active jobs at claim time.
- Overlap: no active direct overlap observed.

## 6. Candidate inventory summary

Cold-store discovery found Appendix 5B filename candidates under `/mnt/hdd-cold/tenn/asx-docs/`.

Sampled candidates:
- PRM December 2025: selected; clean source evidence.
- LMS January 2026: not selected; bounded text sample did not surface line 1.9.
- BC8 January 2026: not selected; bounded text sample surfaced activity-report content before Appendix 5B evidence.
- HRN January 2026: not selected; bounded text sample did not surface unambiguous line 1.9 evidence.

Detailed inventory is in `candidate_inventory.json`.

## 7. Selected fifth document and why

Selected document:

`/mnt/hdd-cold/tenn/asx-docs/PRM/financial_performance/2026-01-29_quarterly-activities-appendix-5b-cash-flow-report_11faaa3d-4a2c-440f-972f-c2f5630e21ae.pdf`

Reasons:
- Clearly Appendix 5B.
- Same page shows company, current-quarter date, column labels, currency/scale, and line 1.9.
- Current-quarter and year-to-date values are distinct and easy to separate.
- No OCR/font ambiguity was observed in the diagnostic text extraction.

## 8. Approval packet details

- Ticker/company: PRM / Prominence Energy Ltd
- Period: quarter ended 31 December 2025
- Metric: `operating_cash_flow`
- Expected value: `-246000`
- Raw value: `(246)`
- Page: PDF page 8, Appendix 5B page 1
- Row/line: `1.9 Net cash from / (used in) operating activities`
- Column: `Current quarter $A'000`
- Currency/scale: AUD thousands
- YTD value shown separately: `(479)`

## 9. Evidence-bound assessment

The source evidence is clean for manual approval-packet purposes. It is not enough to add the document to the gate in this branch because the controlled scorer/gate stack is absent from active NVMe and cannot be restored within this task card's allowed files.

Classification: `UNSCORED_BLOCKED_GATE_INFRA_MISSING`.

## 10. Whether the doc was added to the no-regression floor

No. `added_to_gate=false`.

## 11. Gate results before/after if applicable

Not applicable. The recurring Appendix 5B gate could not be run in active NVMe because the gate and scorer stack are absent from the branch.

## 12. Tests/checks run with exact results

- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/appendix5b_fifth_doc_approval_packet_v1_20260517.md`: PASS after adding `allow_unapproved_safe_extension: true`.
- `python3 scripts/agent_job_registry.py list-active`: PASS, no active jobs at claim time.
- `python3 scripts/agent_job_registry.py claim docs/agent_tasks/appendix5b_fifth_doc_approval_packet_v1_20260517.md`: PASS.
- `pdftotext -layout -f 8 -l 8 <selected PRM PDF> -`: PASS, surfaced Appendix 5B page 1 and line 1.9 evidence.
- JSON artifact checks with `python3 -m json.tool`: PASS.
- Heavy-file guard for raw PDF/tmp/core/generated files in the task output: PASS, no output.
- `git diff --check`: PASS, no output.
- `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/appendix5b_fifth_doc_approval_packet_v1_20260517.md`: PASS, `ok=true`.
- Recurring Appendix 5B/evaluation wrapper: not run, blocked because active NVMe lacks the gate/scorer stack.
- Focused pytest for gate tests: not run, blocked because active NVMe lacks the gate test files.
- Targeted ruff on changed Python files: not applicable; no Python files were changed.

## 13. Files changed

- `docs/agent_tasks/appendix5b_fifth_doc_approval_packet_v1_20260517.md`
- `reports/agent_jobs/appendix5b_fifth_doc_approval_packet_v1_20260517/README.md`
- `reports/agent_jobs/appendix5b_fifth_doc_approval_packet_v1_20260517/status.json`
- `reports/agent_jobs/appendix5b_fifth_doc_approval_packet_v1_20260517/approval_packet.json`
- `reports/agent_jobs/appendix5b_fifth_doc_approval_packet_v1_20260517/candidate_inventory.json`

## 14. Files intentionally not touched

- Parser implementation.
- Extraction prompts.
- Canonical financial truth writes.
- Production DB, Qdrant, news, and memory state.
- Dirty preserve checkout.
- Backend Appendix 5B service files absent from active NVMe.
- Cockpit Home/UI/runtime/news files.

## 15. Risks and blockers

- Blocker: active NVMe lacks the recurring Appendix 5B gate stack and backend scorer services.
- Risk: scoring this PRM document with an ad hoc replacement would weaken the established evidence standard.
- Risk: restoring backend service files under this task would violate the task card allowed-files boundary.

## 16. Recommended next safe step

Integrate the existing Appendix 5B evaluation/gate stack into active NVMe under a separate task card that explicitly allows the required backend evaluation service files. Then run the PRM packet through controlled Docling/candidate artifact generation and the recurring gate before promoting it.

## 17. Project Memory save recommendation

Save that PRM December 2025 has clean page 8 Appendix 5B line 1.9 source evidence for `operating_cash_flow = -246000`, but was not promoted because active NVMe lacks the Appendix 5B gate stack under this task scope.

## 18. Final repo/worktree status

Final `git status --short --untracked-files=all` showed the task card as untracked; report files are present under `reports/agent_jobs/appendix5b_fifth_doc_approval_packet_v1_20260517/` but are ignored by git status in this checkout.

## 19. Registry claim/release status if supported

Registry claim succeeded and was released:

- `python3 scripts/agent_job_registry.py release appendix5b_fifth_doc_approval_packet_v1_20260517`: PASS, `ok=true`.
