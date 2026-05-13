# Repo Hygiene / Task-Card Blocker Resolution v1

## Continuation update - 2026-05-13

The user approved exactly one metadata correction: add `allow_unapproved_safe_extension: true` to `docs/agent_tasks/repo_hygiene_task_card_blocker_resolution_20260513.md`.

Metadata correction performed:

```text
approval_required: false
allow_unapproved_safe_extension: true
```

Validation result after correction:

```text
python3 scripts/agent_job_contract.py validate docs/agent_tasks/repo_hygiene_task_card_blocker_resolution_20260513.md
result: ok=true

python3 scripts/agent_job_registry.py check-overlap docs/agent_tasks/repo_hygiene_task_card_blocker_resolution_20260513.md
result: ok=true

python3 scripts/agent_job_registry.py claim docs/agent_tasks/repo_hygiene_task_card_blocker_resolution_20260513.md
result: ok=true; claim acquired
```

Classification reconfirmation:

- `cockpit_upgrade_integration_readiness_20260509.md`: SUPERSEDED_BUT_PRESERVE_TRACE
- `eval_instrumentation_dirty_worktree_audit_20260509.md`: PRESERVE_CURRENT
- `news_memo_signal_routing_candidate_fixture_integration_v1.md`: BLOCKED_NEEDS_REVIEW
- `preserve_dirty_state_classification_20260512.md`: PRESERVE_HISTORICAL
- `system_task_frontend_wiring_status_audit_v1_20260513.md`: PRESERVE_CURRENT

Staging/commit result: the staged set contains only the six allowed task cards and report artifacts under allowed `reports/agent_jobs/...` directories. The exact commit hash is reported in the Codex final response because a commit cannot embed its own final hash in a tracked file before it exists.

Post-commit validation result:

```text
git status --short --untracked-files=all
result before amend: only tracked report refreshes from post-commit validation

python3 scripts/agent_job_registry.py list-active
result after release: ok=true; active_jobs=[]

python3 scripts/agent_job_registry.py check-overlap docs/agent_tasks/system_task_frontend_wiring_status_audit_v1_20260513.md
result after release: ok=true

python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/system_task_frontend_wiring_status_audit_v1_20260513.md
result: ok=true
```

## 1. Executive summary

What was blocked: The `system_task_frontend_wiring_status_audit_v1_20260513` audit could not complete registry check-overlap, claim, or check-diff because four pre-existing untracked task cards were outside its allowlist.

What was classified: Five task cards were inspected and classified:

| path | classification |
| --- | --- |
| `docs/agent_tasks/cockpit_upgrade_integration_readiness_20260509.md` | SUPERSEDED_BUT_PRESERVE_TRACE |
| `docs/agent_tasks/eval_instrumentation_dirty_worktree_audit_20260509.md` | PRESERVE_CURRENT |
| `docs/agent_tasks/news_memo_signal_routing_candidate_fixture_integration_v1.md` | BLOCKED_NEEDS_REVIEW |
| `docs/agent_tasks/preserve_dirty_state_classification_20260512.md` | PRESERVE_HISTORICAL |
| `docs/agent_tasks/system_task_frontend_wiring_status_audit_v1_20260513.md` | PRESERVE_CURRENT |

What was resolved: The previously invalid hygiene metadata was corrected with user approval, validation passed, the job was claimed, and the preservation set is being committed under the valid task card.

What remains blocked: No product implementation is included. The news memo signal-routing fixture integration remains a separate Memory-lane follow-up because its source commit is still not an ancestor of current `HEAD`.

## 2. Preflight

| Item | Evidence |
| --- | --- |
| Branch | `preserve/dirty-work-20260430T065748Z` |
| HEAD | `5295d5cbd7fcaec626d8a99dd006c4663a682372` (`5295d5cbd7fc`) |
| Worktree | `pwd` reported `/home/l4nd0/tenn`; git root is `/mnt/hdd-data/home/l4nd0/tenn` |
| Initial git status | Six untracked task cards after creating this hygiene card: the five listed cards plus `repo_hygiene_task_card_blocker_resolution_20260513.md` |
| Worktrees | `git worktree list` showed current preserve worktree plus many `/mnt/sdb2/home/l4nd0/tenn-*` worktrees and prunable temp worktrees |
| Recent log | `HEAD` is `5295d5c milestone(runtime): let router presets own model sizing`; recent log also includes `d2cb42d milestone(reporting): wire home market update signals` |
| Registry/list-active | `ok: true`, `active_jobs: []`, shared registry root under `.git/tenn-agent-registry` |
| Hygiene validate | Initially failed, then passed after approved `allow_unapproved_safe_extension: true` metadata correction |
| Hygiene check-overlap | Passed after metadata correction |
| Hygiene claim | Passed after metadata correction |
| Chorus | Used read-only. `list_blocked` returned `{"chats":[]}`. It did not expose repo/task/report state in this tool surface, so shell/file evidence is authoritative |

## 3. Task-card classification table

| path | lane | mutation_mode | output_dir | matching report exists? | classification | evidence | action taken | follow-up needed |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `docs/agent_tasks/cockpit_upgrade_integration_readiness_20260509.md` | Reporting | audit_only | `reports/agent_jobs/cockpit_upgrade_integration_readiness_20260509` | Yes | SUPERSEDED_BUT_PRESERVE_TRACE | Validator `ok=true`; report recommended `c0549d7`; current log has later `d2cb42d` with the same subject | Classified only; not staged | Preserve reports as traceability |
| `docs/agent_tasks/eval_instrumentation_dirty_worktree_audit_20260509.md` | Evaluation | audit_only | `reports/agent_jobs/eval_instrumentation_dirty_worktree_audit_20260509` | Yes | PRESERVE_CURRENT | Validator `ok=true`; report recommends a safe integration task card | Classified only; not staged | Separate Evaluation integration review |
| `docs/agent_tasks/news_memo_signal_routing_candidate_fixture_integration_v1.md` | Memory | safe_extension | `reports/agent_jobs/news_memo_signal_routing_candidate_fixture_integration_v1` | Yes | BLOCKED_NEEDS_REVIEW | Validator `ok=true`; report status `blocked`; source commit `0e5e7df9d155` is not in current `HEAD` | Classified only; not staged | Memory-lane owner should rerun/close after hygiene |
| `docs/agent_tasks/preserve_dirty_state_classification_20260512.md` | Reporting | audit_only | `reports/agent_jobs/preserve_dirty_state_classification_20260512` | Yes | PRESERVE_HISTORICAL | Validator `ok=true`; report explains the same dirty task-card class | Classified only; not staged | Preserve as historical trace |
| `docs/agent_tasks/system_task_frontend_wiring_status_audit_v1_20260513.md` | Reporting | audit_only | `reports/agent_jobs/system_task_frontend_wiring_status_audit_v1_20260513` | Yes | PRESERVE_CURRENT | Validator `ok=true`; status names the four task-card blockers | Classified only; not staged | Rerun overlap/check-diff after valid hygiene commit |

## 4. Report artifact classification

Matching report dirs inspected:

- `reports/agent_jobs/cockpit_upgrade_integration_readiness_20260509/`
- `reports/agent_jobs/eval_instrumentation_dirty_worktree_audit_20260509/`
- `reports/agent_jobs/news_memo_signal_routing_candidate_fixture_integration_v1/`
- `reports/agent_jobs/preserve_dirty_state_classification_20260512/`
- `reports/agent_jobs/system_task_frontend_wiring_status_audit_v1_20260513/`

Status files found:

- `cockpit_upgrade_integration_readiness_20260509/status.json`
- `eval_instrumentation_dirty_worktree_audit_20260509/status.json`
- `news_memo_signal_routing_candidate_fixture_integration_v1/status.json`
- `system_task_frontend_wiring_status_audit_v1_20260513/status.json`

DATA_MISSING:

- `preserve_dirty_state_classification_20260512` has no `status.json`; its `README.md` and `diff-check.json` were used instead.
- Report directories are ignored by normal short status; none were force-added because this run could not safely commit.

Reports force-added or not: Not force-added. No staging was performed.

## 5. Resolution performed

Files added:

- `docs/agent_tasks/repo_hygiene_task_card_blocker_resolution_20260513.md`
- `reports/agent_jobs/repo_hygiene_task_card_blocker_resolution_20260513/README.md`
- `reports/agent_jobs/repo_hygiene_task_card_blocker_resolution_20260513/task_card_classification.md`
- `reports/agent_jobs/repo_hygiene_task_card_blocker_resolution_20260513/status.json`

Files force-added: None.

Files not touched: No application code, runtime config, data store, frontend/backend source file, tests, package files, existing tracked code, or unrelated dirty file was modified.

Commit hash if committed: Recorded in final Codex response.

## 6. Validation

Exact commands and results:

```text
python3 scripts/agent_job_contract.py validate docs/agent_tasks/repo_hygiene_task_card_blocker_resolution_20260513.md
result: failed; approval_required safe_extension validation error

python3 scripts/agent_job_registry.py list-active
result: ok=true; active_jobs=[]

python3 scripts/agent_job_registry.py check-overlap docs/agent_tasks/repo_hygiene_task_card_blocker_resolution_20260513.md
result: failed; validation failed before overlap check

python3 scripts/agent_job_registry.py claim docs/agent_tasks/repo_hygiene_task_card_blocker_resolution_20260513.md
result: failed; validation failed before claim; no claim acquired

python3 scripts/agent_job_contract.py validate <each of the five inspected cards>
result: all five inspected cards returned ok=true
```

Check-diff result: Failed for a tooling limitation inside allowed files. `scripts/agent_job_contract.py` validates the task card but exact-matches `allowed_files`; it does not expand `reports/agent_jobs/.../**` directory globs. The rejected files are all report artifacts under the report directories explicitly listed in this task card.

`git diff --check` result: Passed with no output and exit 0.

`python3 -m json.tool reports/agent_jobs/repo_hygiene_task_card_blocker_resolution_20260513/status.json >/dev/null` result: Passed with no output and exit 0.

Additional final validation:

```text
python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/repo_hygiene_task_card_blocker_resolution_20260513.md
result: failed; validation failed because approval_required=false under safe_extension without allow_unapproved_safe_extension=true

python3 scripts/agent_job_registry.py check-overlap docs/agent_tasks/system_task_frontend_wiring_status_audit_v1_20260513.md
result: failed; now reports the four prior task cards plus this hygiene task card as outside the system audit allowlist

python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/system_task_frontend_wiring_status_audit_v1_20260513.md
result: failed; now reports the four prior task cards plus this hygiene task card as outside the system audit allowlist
```

## 7. Remaining risks

- Stale/superseded task cards: Cockpit upgrade readiness is superseded as implementation guidance but should be preserved for traceability.
- Lanes needing review: Evaluation instrumentation remains a real follow-up; news memo fixture integration remains blocked and not in current `HEAD`.
- Ignored reports policy: Matching report artifacts are ignored by default and are force-added in this preservation commit.
- Unresolved DATA_MISSING: No status.json exists for `preserve_dirty_state_classification_20260512`; Chorus did not show repo/task/report state through available tools.
- Contract risk: Resolved for this hygiene job by the approved `allow_unapproved_safe_extension: true` metadata correction.

## 8. Next safe step

After the preservation commit, rerun system audit check-overlap/check-diff. Use the preserved system audit report to select the next scoped validation or implementation task. Do not treat the blocked news memo fixture integration as complete; it needs its own Memory-lane follow-up if still desired.

## 9. Project Memory save recommendation

SAVE_RECOMMENDED.

Target categories:

- Active Tasks / Todos
- Open Risks / Blockers
- Repo / GitHub / Codex Audit Notes
- Validation Baselines

Reason: This run surfaced a new contract/tooling blocker: the exact requested hygiene task card is invalid under current validator rules.

## 10. Final state

Final git status:

```text
?? docs/agent_tasks/cockpit_upgrade_integration_readiness_20260509.md
?? docs/agent_tasks/eval_instrumentation_dirty_worktree_audit_20260509.md
?? docs/agent_tasks/news_memo_signal_routing_candidate_fixture_integration_v1.md
?? docs/agent_tasks/preserve_dirty_state_classification_20260512.md
?? docs/agent_tasks/repo_hygiene_task_card_blocker_resolution_20260513.md
?? docs/agent_tasks/system_task_frontend_wiring_status_audit_v1_20260513.md
```

Staged/committed state: Pending staged validation and preservation commit.

Registry release status: Claim acquired and released.

DATA_MISSING list:

- Chorus repo/task/report state unavailable through exposed read-only tool surface.
- No current-turn proof that `preserve_dirty_state_classification_20260512` has a machine-readable `status.json`.
- Final commit hash cannot be embedded into this committed report before the commit exists; final response records it.
