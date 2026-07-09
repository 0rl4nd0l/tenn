# Automation Candidate Store Layer 1 V0

Status: DONE_WITH_RISK

## Summary

Implemented the first repo-side candidate-store helper for automation backlog
findings. The helper uses deterministic fingerprints, append-only JSONL
records, latest-record resolution, TTL suppression defaults, and resurface
checks for evidence or linked-state changes.

## Scope Completed

- Added `scripts/automation_candidate_store.py`.
- Added `scripts/test_automation_candidate_store.py`.
- Updated `scripts/system_brief.py` to consume candidate-store records when
  `~/.codex/automations/tenn/state/candidates.jsonl` exists.
- Kept validation writes inside temporary directories only.

## Boundaries Preserved

- No write to real host automation candidate state.
- No GitHub issue/comment mutation by automation.
- No timer, systemd, runtime, data-store, extraction-truth, source-PDF,
  gold-label, model/GPU, or secret mutation.

System functionality was not proven; this is a control-plane helper layer.
