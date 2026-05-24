# Preflight

## Repo Identity

- `pwd`: `/home/l4nd0`
- `/home/l4nd0/tenn`: resolves to `/home/l4nd0/tenn-nvme-clean-baseline-reconstruct-v1`
- Repo root: `/home/l4nd0/tenn-nvme-clean-baseline-reconstruct-v1`
- Branch: `migration/clean-runtime-baseline-reconstruct-v1`
- HEAD: `7a8c872f8b652a5433afd1614eb4a657b0fc1f8d`

Recent commits:

```text
7a8c872f feat(reporting): add cockpit home useful now panel
6babc2b8 chore(reporting): preserve cockpit task-card evidence
2bff733e milestone(runtime): set canonical tenn path to nvme runtime
76042591 feat(financial-truth): add asx comparator artifact schema
f425ebc1 milestone(evaluation): checkpoint route parity audit
d5fcd71d milestone(financial-truth): add asx sidecar gate report
8e38d267 feat(financial-truth): add asx document type sidecar artifacts
a56911ac feat(financial-truth): add pure asx document type classifier
```

Commit `6babc2b8a8edb1868fb66f95d89cdf870150ff94` is reachable from current `HEAD`; `git show --no-patch --oneline` reports:

```text
6babc2b8 chore(reporting): preserve cockpit task-card evidence
```

## Initial Dirty State

Initial `git status --short --untracked-files=all` before creating this audit task card:

```text
?? docs/agent_tasks/cockpit_ui_usefulness_current_head_reapply_v1_20260521.md
?? docs/agent_tasks/cockpit_ui_usefulness_final_canonical_merge_rerun_v1_20260521.md
?? docs/agent_tasks/cockpit_ui_usefulness_final_canonical_merge_v1_20260521.md
?? docs/agent_tasks/strategy_lab_consolidation_execution_phase3g_v1_20260521.md
?? docs/agent_tasks/strategy_lab_consolidation_execution_task_card_draft_phase3g_v1_20260521.md
?? docs/agent_tasks/strategy_lab_consolidation_save_plan_phase3f_v1_20260521.md
?? docs/agent_tasks/strategy_lab_offline_adapter_contract_review_phase3d_v1_20260521.md
?? docs/agent_tasks/strategy_lab_offline_implementation_plan_phase3e_v1_20260521.md
```

Relevant `git worktree list` lines from the full command:

```text
/home/l4nd0/tenn-cockpit-ui-usefulness-current-head-v1-20260521    7a8c872f [integrate/cockpit-ui-usefulness-current-head-v1-20260521]
/home/l4nd0/tenn-cockpit-ui-usefulness-integrate-v1-20260521       26173376 [integrate/cockpit-ui-usefulness-integrate-v1-20260521]
/home/l4nd0/tenn-cockpit-ui-usefulness-vertical-slice-v1-20260521  8c855190 [safe/cockpit-ui-usefulness-vertical-slice-v1-20260521]
/home/l4nd0/tenn-nvme-clean-baseline-reconstruct-v1                7a8c872f [migration/clean-runtime-baseline-reconstruct-v1]
```

No worktree named `/home/l4nd0/tenn-cockpit-ui-usefulness-final-canonical-merge-v1-20260521` was present in the full worktree list, and its requested report path did not exist.

## Tooling

`python3 scripts/agent_job_contract.py --help` supports:

```text
validate
check-diff
```

`python3 scripts/agent_job_registry.py --help` supports:

```text
list-active
claim
heartbeat
release
check-overlap
```

This audit task card validation passed with `ok: true`.

Registry `list-active` returned:

```json
{"active_jobs":[],"ok":true,"registry_scope":"shared"}
```

Registry `check-overlap` for this audit task card failed only because existing dirty files are outside this audit allowlist. There were no active registry jobs.

## Closeout Registry Drift

During closeout validation, active registry state changed. Final active jobs included:

```text
cockpit_ui_overnight_orchestrator_v1_20260521
codex_workday_checkin_protocol_v1_20260521
```

`cockpit_ui_overnight_orchestrator_v1_20260521` is a Reporting safe-extension job in `/home/l4nd0/tenn-cockpit-ui-overnight-orchestrator-v1-20260521`. It overlaps the requested Cockpit final canonical merge card by lane and Cockpit Home file ownership.

`codex_workday_checkin_protocol_v1_20260521` is an Evaluation audit-only job in `/home/l4nd0/tenn-workday-checkin-protocol-v1-20260521`. Its allowed files do not include the requested Cockpit final canonical merge blocker.

During one intermediate closeout overlap check, one additional dirty task card appeared outside this audit allowlist:

```text
docs/agent_tasks/cockpit_ui_overnight_orchestrator_v1_20260521.md
```

This audit did not inspect or modify that file.

Final `git status --short --untracked-files=all` no longer showed that file in this checkout.
