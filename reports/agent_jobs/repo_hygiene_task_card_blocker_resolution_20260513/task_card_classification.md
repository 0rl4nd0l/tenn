# Task Card Classification

## docs/agent_tasks/cockpit_upgrade_integration_readiness_20260509.md

Classification: SUPERSEDED_BUT_PRESERVE_TRACE

Evidence:

```text
validate: ok=true
lane: Reporting
mutation_mode: audit_only
output_dir: reports/agent_jobs/cockpit_upgrade_integration_readiness_20260509
production_data_access: false
matching report files: README.md, status.json, candidate_branch_matrix.md, runtime_visibility.md, recommended_integration_handoff.md, diff-check.json
report status evidence: recommended_first_integration=c0549d754cb501254873b34c66d9aec7d12b95d8
current repo evidence: git log --all --grep='wire home market update signals' returned d2cb42d and c0549d7
```

Confirmed: The task card is valid audit-only metadata and has a matching report directory.

Confirmed: Its report recommended the Home market-update/news snapshot target. A later current-branch commit subject `milestone(reporting): wire home market update signals` exists at `d2cb42d`, so the handoff is no longer the current implementation target.

Inferred: Preserve the task card and reports as traceability for why `c0549d7` was selected, but do not treat the task as blocking implementation once preserved.

Follow-up: No direct product work. Commit/preserve the card and report artifacts in a valid hygiene pass.

## docs/agent_tasks/eval_instrumentation_dirty_worktree_audit_20260509.md

Classification: PRESERVE_CURRENT

Evidence:

```text
validate: ok=true
lane: Evaluation
mutation_mode: audit_only
output_dir: reports/agent_jobs/eval_instrumentation_dirty_worktree_audit_20260509
production_data_access: false
matching report files: README.md, status.json, diff_risk_assessment.md, dirty_file_matrix.md, preservation_options.md, diff-check.json
report status evidence: recommended_next_action=create a safe integration task card
```

Confirmed: The task card is valid audit-only metadata and has a matching report directory.

Confirmed: The report classifies an external eval instrumentation worktree and recommends a follow-up safe integration task. It is not a current preserve product-code diff.

Inferred: Preserve as a current Evaluation follow-up record. It should not block Reporting implementation after preservation, but the underlying evaluation work still needs a separate owner and task card.

Follow-up: Create a dedicated Evaluation integration card if the runtime provenance instrumentation should land.

## docs/agent_tasks/news_memo_signal_routing_candidate_fixture_integration_v1.md

Classification: BLOCKED_NEEDS_REVIEW

Evidence:

```text
validate: ok=true
lane: Memory
mutation_mode: safe_extension
allow_unapproved_safe_extension: true
output_dir: reports/agent_jobs/news_memo_signal_routing_candidate_fixture_integration_v1
production_data_access: false
matching report files: final_report.md, status.json, diff-check.json
report status evidence: status=blocked
blocked_reason: Task-card registry claim failed because dirty files outside allowed_files are present in the shared worktree.
current repo evidence: git merge-base --is-ancestor 0e5e7df9d155 HEAD returned 1
```

Confirmed: The task card is valid and includes the validator-required `allow_unapproved_safe_extension: true`.

Confirmed: Its report says integration was blocked before cherry-pick and no validation tests ran.

Confirmed: Source commit `0e5e7df9d155` is not an ancestor of current `HEAD`.

Inferred: Preserve as an unresolved Memory/Query Orchestration/Evaluation blocker, not as completed historical trace.

Follow-up: Re-run or close this integration under a Memory-lane task after repo hygiene is valid.

## docs/agent_tasks/preserve_dirty_state_classification_20260512.md

Classification: PRESERVE_HISTORICAL

Evidence:

```text
validate: ok=true
lane: Reporting
mutation_mode: audit_only
output_dir: reports/agent_jobs/preserve_dirty_state_classification_20260512
production_data_access: false
matching report files: README.md, diff-check.json
report evidence: final status showed four untracked task-card files
current status evidence: current preflight showed the same four plus system_task_frontend_wiring_status_audit_v1_20260513.md and this hygiene card
```

Confirmed: The task card is valid audit-only metadata and has a matching report directory.

Confirmed: The report explains the prior dirty-state context and identifies the same task-card blockers later seen by the system/frontend audit.

Inferred: Preserve as historical trace. It is partly superseded by the system/frontend wiring audit and this hygiene classification.

Follow-up: No direct product work. Preserve with reports, then treat as historical.

## docs/agent_tasks/system_task_frontend_wiring_status_audit_v1_20260513.md

Classification: PRESERVE_CURRENT

Evidence:

```text
validate: ok=true
lane: Reporting
mutation_mode: audit_only
output_dir: reports/agent_jobs/system_task_frontend_wiring_status_audit_v1_20260513
production_data_access: false
matching report files: README.md, status.json, frontend_wiring_map.md, task_status_matrix.md, risk_register.md, validation_matrix.md, diff-check.json
status blockers: four pre-existing untracked task cards blocked registry check-overlap, claim, and check-diff
```

Confirmed: The task card is valid audit-only metadata and has a matching report directory.

Confirmed: Its status file identifies the same four task-card blockers this hygiene task was asked to resolve.

Inferred: Preserve as the current system/frontend audit baseline. It should not block implementation after the four prior cards are preserved, but its listed next steps should be rerun after cleanup.

Follow-up: Rerun registry check-overlap and check-diff for this card after a valid hygiene preservation commit.

## Hygiene Task Card Blocker

The new card `docs/agent_tasks/repo_hygiene_task_card_blocker_resolution_20260513.md` was created with the exact user-provided content. Validation failed:

```text
field: approval_required
message: safe_extension jobs require approval_required=true unless allow_unapproved_safe_extension=true
```

Because the handoff required exact content and the validator rejected that content, this run cannot safely claim, stage, or commit the preservation set. The resolution status is BLOCKED SAFELY.
