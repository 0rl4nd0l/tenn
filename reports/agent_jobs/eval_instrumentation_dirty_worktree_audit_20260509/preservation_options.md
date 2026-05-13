# Preservation Options and Recommendation

## Per-file action mapping
- `financial-engine_v2/backend/app/main.py` → preserve_now_in_new_branch_or_commit
- `financial-engine_v2/backend/app/services/docling_extract.py` → preserve_now_in_new_branch_or_commit
- `financial-engine_v2/backend/app/services/method_isolated_extraction.py` → preserve_now_in_new_branch_or_commit
- `financial-engine_v2/backend/app/services/multipass_extraction.py` → preserve_now_in_new_branch_or_commit
- `financial-engine_v2/backend/tests/test_docling_extract.py` → preserve_now_in_new_branch_or_commit
- `financial-engine_v2/backend/tests/test_extraction_gold_eval.py` → preserve_now_in_new_branch_or_commit
- `scripts/run_real_extraction_eval.py` → preserve_now_in_new_branch_or_commit
- `scripts/test_run_real_extraction_eval.py` → preserve_now_in_new_branch_or_commit

## Candidate next actions (required single safe action)
- `create a safe integration task card`

## Why this action
- Main preserve has moved to a newer tip (`dabbc45...`) while this worktree is on ancestor commit (`49a5d34...`) with local deltas.
- A follow-on integration task card is the safest path: it preserves the work, avoids direct branch merge risk, and requires explicit revalidation on preserve tip.

## Hard stop before execution
- Resolve `check-diff` scope issue from extra untracked `docs/agent_tasks/cockpit_upgrade_integration_readiness_20260509.md` in the main preserve working tree if strict task enforcement is required.
- Keep audit-only mode: no mutation to source in the dirty worktree until re-integration begins.
