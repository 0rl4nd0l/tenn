# Validation

Validation is updated at closeout. Initial evidence collected before final
checks:

| Command | Exit | Notes |
| --- | ---: | --- |
| `git fetch origin migration/clean-runtime-baseline-reconstruct-v1` | 0 | Refreshed current base in the shared checkout before worktree creation. |
| `git worktree add /home/l4nd0/tenn-auto-progress-issue234-phase3-dry-run-review-20260615 --detach origin/migration/clean-runtime-baseline-reconstruct-v1` | 0 | Created clean detached current-base sibling worktree. |
| `git switch -c control-plane/issue234-diff-check-dirt-classification-v1-20260615 origin/migration/clean-runtime-baseline-reconstruct-v1` | 0 | Moved the untracked report-only packet onto current origin base `107adb03852558d42795b28c3a5ec887e7cd0c64` before commit. |
| `gh pr view 344 --repo 0rl4nd0l/tenn --json ...` | 0 | PR #344 is merged. |
| `git ls-tree -r --name-only origin/migration/clean-runtime-baseline-reconstruct-v1 ...` | 0 | Confirmed `scripts/auto_progress.py` and the merged V2 report bundle exist on current base. |
| `python3 scripts/agent_job_registry.py list-active --read-only` | 0 | Registry read-only; no active jobs; no lock acquired. |
| `gh issue view 234 --repo 0rl4nd0l/tenn --json ...` | 0 | Issue #234 is open/ready and matches the planner candidate. |
| `gh issue view 98 --repo 0rl4nd0l/tenn --json ...` | 0 | Issue #98 is closed. |
| `git status --short --untracked-files=all -- reports/agent_jobs/extraction_contract_parity_guard_v1_20260526/diff-check.json` | 0 | No dirty status for the historical parity artifact. |
| `git status --short --untracked-files=all -- reports/agent_jobs/extraction_contract_parity_guard_v1_20260526/diff-check.json docs/agent_tasks/extraction_count24_approval_packet_current_canonical_v1_20260609.md` in shared checkout | 0 | Count-24 packet remains untracked; target parity artifact not dirty. |

Final validation commands are recorded below after they are run.

## Final Validation

| Command | Exit | Notes |
| --- | ---: | --- |
| `python3 scripts/agent_job_contract.py validate docs/agent_tasks/extraction_contract_parity_diff_check_dirt_classification_v1_20260602.md` | 0 | Task card parsed and allowlist is exact. |
| `python3 scripts/agent_job_registry.py list-active --read-only` | 0 | Registry remained read-only with `active_jobs: []` and `lock_acquired: false`. |
| `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/extraction_contract_parity_diff_check_dirt_classification_v1_20260602.md --no-write-report` | 1 then 0 | First run failed because `audit_only` cards with a task-card file need `allow_audit_code_changes: true`; after adding that explicit flag, check-diff passed with no disallowed files. |
| `git diff --check` | 0 | No whitespace errors. |
| Changed-path guard including ignored report files | 0 | Eight changed/ignored paths found; all are exactly in the task-card allowlist. |

## Final Changed-Path Guard

```text
changed_or_ignored_path_count: 8
disallowed_path_count: 0
OK docs/agent_tasks/extraction_contract_parity_diff_check_dirt_classification_v1_20260602.md
OK reports/agent_jobs/extraction_contract_parity_diff_check_dirt_classification_v1_20260602/APPROVAL_PACKET.md
OK reports/agent_jobs/extraction_contract_parity_diff_check_dirt_classification_v1_20260602/CLASSIFICATION.md
OK reports/agent_jobs/extraction_contract_parity_diff_check_dirt_classification_v1_20260602/DATA_MISSING.md
OK reports/agent_jobs/extraction_contract_parity_diff_check_dirt_classification_v1_20260602/EVIDENCE.md
OK reports/agent_jobs/extraction_contract_parity_diff_check_dirt_classification_v1_20260602/ISSUE_REFRESH.md
OK reports/agent_jobs/extraction_contract_parity_diff_check_dirt_classification_v1_20260602/README.md
OK reports/agent_jobs/extraction_contract_parity_diff_check_dirt_classification_v1_20260602/VALIDATION.md
```

## Boundary Confirmation

- In the original report-only run, no GitHub mutation, commit, or push was
  performed.
- No cleanup, restore, stash, reset, merge, rebase, cherry-pick, branch delete,
  or worktree delete was performed.
- No product/runtime/data/extraction files were modified.
- No extraction work, broad validation, service start, or dependency install was
  performed.
- The count-24 extraction approval packet was not touched.

## 2026-06-25 Publish Refresh Validation

The publish refresh is appended from a fresh current-base worktree:

```text
worktree: /home/l4nd0/tenn-issue234-current-base-publish-v1-20260625
branch: control-plane/issue234-diff-check-current-base-v1-20260625
base_head: b3b3a154590f36e61d297c1ac79fe623526f0b28
source_packet: 35abf15bd04cf437363aae9e392722ac5a69890a
```

Final publish-refresh validation is recorded in `PUBLISH_REFRESH.md` and
`CODE_REVIEW.json`.
