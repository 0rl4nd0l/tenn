# Parked Entry: extraction-live-contract-truth-gates-v1-20260603-nvme

- Status: `HIGH_RISK_PARENT_BATCH`
- Branch: `safe/extraction-live-contract-truth-gates-v1-20260603-nvme`
- Lane: Financial Truth
- Worktree: `/mnt/tenn-nvme2/tenn/tmp/tenn-extraction-contract-restore-v1-nvme`
- Base/HEAD: `ab06d41ba534307dfbb4469b4ca12dcd12e1c8b1`
- Merge target inference from inventory: `migration/clean-runtime-baseline-reconstruct-v1`

## Why Parked

This is the high-risk parent extraction batch. It contains a large amount of
validated sub-work, but the parent worktree is still dirty on shared extraction
surfaces and should not be treated as a single review or merge candidate.

## Evidence Present

- Parent task card exists:
  `extraction_live_contract_truth_gate_restore_v1_20260603`
- Parent summary and validation exist.
- Inventory observed:
  - `424` staged paths
  - `4` unstaged paths
  - `2` untracked paths
- Overlapping shared extraction code/tests:
  - `financial-engine_v2/backend/app/services/multipass_extraction.py`
  - `financial-engine_v2/backend/tests/test_extraction_pre_canary_truth_gates.py`
  - `financial-engine_v2/backend/tests/test_multipass_extraction.py`
  - `financial-engine_v2/scripts/test_broad_extraction_test.py`
- Evidence-backed sub-slices exist inside the batch, including:
  - AEG formal-units statement recovery
  - Appendix 4E full-dollar scale recovery
  - BBN attributable-profit row recovery

## Risk

- High.
- Shared extraction code overlap.
- Dirty parent batch bundles many staged report/task-card artifacts with core
  code changes.

## Recommended Next Action

Do not merge this parent batch. Preserve it as parked inventory, then separate
narrow review slices into clean branches before any merge-review attempt. First
recommended mining order from the 2026-06-04 remaining review is BPT income-tax
NPAT guard, COL adjusted-NPAT guard, then BBN attributable-profit row recovery.
