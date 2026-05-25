# Repo-Native Goal Schema Slice Review and Integration

## Scope

- GitHub issue: #69.
- Lane: Reporting.
- Supporting lanes: Evaluation, Repo Hygiene.
- Execution mode: SAFE EXTENSION for the current hygiene branch; integration planning for the live migration branch.
- Target system layer: repo-native control-plane documentation and validation only.
- Contract boundary: no product, backend, frontend, runtime, financial truth, memory, Qdrant, DB, news, parser-routing, extraction, Docker, cron, systemd, model, GPU, merge execution, or Git-ref mutation changes.

## Preflight Declaration

- Agent: Codex.
- Branch: `audit/repo-hygiene-safe-audits-v1-20260525`.
- Starting HEAD: `a423421babb2`.
- Worktree: `/home/l4nd0/tenn-repo-hygiene-audits-v1-20260525`.
- Intended files: goal/status schema docs, changed-file-scoped helper/tests, task card, and this report directory.
- Contested surfaces touched: none.
- Collision risk: LOW. The active Strategy Lab job is in a separate branch/worktree and has no file overlap.
- Decision: proceed.

## Result

Reviewed `cf825692cc8448820b6b493ad4baeeebabfcf9eb` and adopted its additive repo-native goal schema slice into this safe audit branch.

Added:

- `docs/goals/README.md`
- `docs/goals/_template.md`
- `docs/goals/goal_schema_v1.json`
- `reports/agent_jobs/status_schema_v1.json`
- `scripts/agent_goal_contract.py`
- `scripts/test_agent_goal_contract.py`
- `docs/agent_tasks/task_card_schema_notes_v1.md`

The helper validates explicit files or changed files only. It does not scan or enforce historical goal/status artifacts by default.

## Source Slice Review

- Referenced commit exists locally: `cf825692cc8448820b6b493ad4baeeebabfcf9eb`.
- Local branches containing it: `safe/repo-native-goal-schema-slice-v1-20260524-clean-codex`, `safe/merge-parking-docs-validation-slice-v1-20260524`.
- Remote branch check for `origin/safe/repo-native-goal-schema-slice-v1-20260524-clean-codex`: not found.
- Source slice touched only docs, schemas, helper/test files, task card, and report artifacts.

## Integration Decision

- Safe audit branch integration: complete.
- Live migration branch integration: not performed.

The live migration worktree `/home/l4nd0/tenn-nvme-clean-baseline-reconstruct-v1` is on `migration/clean-runtime-baseline-reconstruct-v1`, is ahead of origin by 10 commits, and has untracked task cards. This task did not mutate that branch. The safe next step for the live branch is an owner-approved merge or PR from the pushed audit branch after reviewing the stacked control-plane commits.

## Validation

- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/repo_native_goal_schema_slice_review_integration_v1_20260525.md`: passed.
- `python3 scripts/agent_job_registry.py list-active`: passed; active Strategy Lab job observed with no file overlap.
- `python3 scripts/agent_job_registry.py check-overlap docs/agent_tasks/repo_native_goal_schema_slice_review_integration_v1_20260525.md`: passed.
- `python3 scripts/agent_job_registry.py claim docs/agent_tasks/repo_native_goal_schema_slice_review_integration_v1_20260525.md`: passed.
- `git cat-file -t cf825692cc8448820b6b493ad4baeeebabfcf9eb`: returned `commit`.
- `git ls-remote --heads origin safe/repo-native-goal-schema-slice-v1-20260524-clean-codex`: no remote branch returned.
- `python3 -m json.tool docs/goals/goal_schema_v1.json`: passed.
- `python3 -m json.tool reports/agent_jobs/status_schema_v1.json`: passed.
- `python3 scripts/agent_goal_contract.py validate docs/goals/_template.md docs/goals/goal_schema_v1.json reports/agent_jobs/status_schema_v1.json`: passed.
- `python3 -m py_compile scripts/agent_goal_contract.py scripts/test_agent_goal_contract.py`: passed.
- `uv run --with pytest --with pyyaml python -m pytest scripts/test_agent_goal_contract.py -q`: passed, 6 tests.
- `uv run --with ruff ruff check scripts/agent_goal_contract.py scripts/test_agent_goal_contract.py`: passed.
- `python3 scripts/agent_goal_contract.py validate --changed`: passed.
- `python3 -m json.tool reports/agent_jobs/repo_native_goal_schema_slice_review_integration_v1_20260525/status.json`: passed.
- `python3 -m json.tool reports/agent_jobs/repo_native_goal_schema_slice_review_integration_v1_20260525/validation.json`: passed.
- `python3 -m json.tool reports/agent_jobs/repo_native_goal_schema_slice_review_integration_v1_20260525/integration_readiness.json`: passed.
- `git diff --check`: passed.
- `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/repo_native_goal_schema_slice_review_integration_v1_20260525.md`: passed.
- `python3 scripts/agent_job_registry.py release repo_native_goal_schema_slice_review_integration_v1_20260525`: passed.

## Not Done

- No live migration branch merge, cherry-pick, or rebase was performed.
- No broad CI gate was added.
- No merge parking entry was created for this slice.
- No product/runtime/data-store files were touched.
