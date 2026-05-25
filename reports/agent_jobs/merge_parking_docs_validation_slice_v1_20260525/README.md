# Merge Parking Docs Validation Slice v1

## Scope

- GitHub issue: #68.
- Lane: Reporting.
- Supporting lanes: Evaluation, Repo Hygiene.
- Execution mode: SAFE EXTENSION.
- Target system layer: repo-native control-plane documentation and validation only.
- Contract boundary: no product, backend, frontend, runtime, financial truth, memory, Qdrant, DB, news, parser-routing, extraction, Docker, cron, systemd, model, GPU, merge execution, or Git-ref mutation changes.

## Preflight Declaration

- Agent: Codex.
- Branch: `audit/repo-hygiene-safe-audits-v1-20260525`.
- Starting HEAD: `24bab3fc17a0`.
- Worktree: `/home/l4nd0/tenn-repo-hygiene-audits-v1-20260525`.
- Intended files: merge parking docs/schemas/helper/tests, task card, and this report directory.
- Contested surfaces touched: none.
- Collision risk: LOW. The active Strategy Lab job touches a different branch/worktree and non-overlapping files.
- Decision: proceed.

## Result

Implemented the merge parking documentation and validation slice by adapting the already completed `de3f1f56` slice onto the current hygiene branch, while preserving the lighter `schema.md` and `parked/README.md` docs created by the earlier merge parking registry surface.

The slice now provides:

- Human-readable merge parking README and registry index.
- Registry frontmatter schema and entry schema.
- Entry template with required review metadata.
- Changed-file-scoped validation helper.
- Focused tests for valid entries, invalid status, missing required fields, review-required metadata, changed-file scope, and template frontmatter.

Parking remains review-only. The helper validates artifacts; it does not merge, cherry-pick, rebase, claim Git refs, delete branches, reset, stash, or clean worktrees.

## Validation

- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/merge_parking_docs_validation_slice_v1_20260525.md`: passed.
- `python3 scripts/agent_job_registry.py list-active`: passed; active Strategy Lab job observed with no file overlap.
- `python3 scripts/agent_job_registry.py check-overlap docs/agent_tasks/merge_parking_docs_validation_slice_v1_20260525.md`: passed.
- `python3 scripts/agent_job_registry.py claim docs/agent_tasks/merge_parking_docs_validation_slice_v1_20260525.md`: passed.
- `python3 -m json.tool docs/agent_registry/merge_parking/merge_parking_entry_schema_v1.json`: passed.
- `python3 -m json.tool docs/agent_registry/merge_parking/registry_schema_v1.json`: passed.
- `python3 scripts/merge_parking_registry.py validate docs/agent_registry/merge_parking/REGISTRY.md docs/agent_registry/merge_parking/_entry_template.md docs/agent_registry/merge_parking/merge_parking_entry_schema_v1.json docs/agent_registry/merge_parking/registry_schema_v1.json`: passed.
- `python3 scripts/merge_parking_registry.py validate --changed`: passed; only relevant merge-parking artifacts were checked.
- `python3 -m py_compile scripts/merge_parking_registry.py scripts/test_merge_parking_registry.py`: passed.
- `uv run --with pytest --with pyyaml python -m pytest scripts/test_merge_parking_registry.py -q`: passed, 6 tests.
- `uv run --with ruff ruff check scripts/merge_parking_registry.py scripts/test_merge_parking_registry.py`: passed.
- `python3 -m json.tool reports/agent_jobs/merge_parking_docs_validation_slice_v1_20260525/status.json`: passed.
- `python3 -m json.tool reports/agent_jobs/merge_parking_docs_validation_slice_v1_20260525/validation.json`: passed.
- `git diff --check`: passed.
- `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/merge_parking_docs_validation_slice_v1_20260525.md`: passed.
- `python3 scripts/agent_job_registry.py release merge_parking_docs_validation_slice_v1_20260525`: passed.

## Next Recommended Slice

Add one concrete parked-entry example for a completed-but-unmerged branch only after the owner selects that branch. Keep that as documentation plus validation, still without merge execution or branch mutation.

## Not Done

- No real parked work was registered.
- No historical artifacts were scanned or forced into the new schema.
- No merge, cherry-pick, rebase, reset, stash, cleanup, branch deletion, or Git-ref claim automation was implemented.
