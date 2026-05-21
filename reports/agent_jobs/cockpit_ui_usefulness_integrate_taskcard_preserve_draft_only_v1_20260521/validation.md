# Validation

Validation before exact-path staging:

- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/cockpit_ui_usefulness_integrate_taskcard_preserve_draft_only_v1_20260521.md`: PASS.
- `python3 scripts/agent_job_registry.py check-overlap docs/agent_tasks/cockpit_ui_usefulness_integrate_taskcard_preserve_draft_only_v1_20260521.md --repo-root .`: FAIL on unrelated dirty files outside this task allowlist.
- `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/cockpit_ui_usefulness_integrate_taskcard_preserve_draft_only_v1_20260521.md --repo-root .`: FAIL on unrelated dirty files outside this task allowlist; wrote `diff-check.json`.
- `git diff --check`: PASS.

Unrelated dirty files observed by registry/check-diff:

- `docs/agent_tasks/cockpit_ui_usefulness_final_canonical_merge_v1_20260521.md`
- `docs/agent_tasks/strategy_lab_consolidation_execution_phase3g_v1_20260521.md`
- `docs/agent_tasks/strategy_lab_consolidation_execution_task_card_draft_phase3g_v1_20260521.md`
- `docs/agent_tasks/strategy_lab_consolidation_save_plan_phase3f_v1_20260521.md`
- `docs/agent_tasks/strategy_lab_offline_adapter_contract_review_phase3d_v1_20260521.md`
- `docs/agent_tasks/strategy_lab_offline_implementation_plan_phase3e_v1_20260521.md`

Known live-repo caveat: broad `check-overlap` / `check-diff` for this preservation task can fail on unrelated dirty files that are intentionally outside this task's allowlist. Exact-path staging is used to avoid absorbing that unrelated dirt.

Final staged/commit validation is reported in the assistant closeout.

## Exact Staging Validation

Exact staged files were limited to this preservation task card, the target Cockpit integration task card, the prior collision-audit task card/report bundle, and this preservation report bundle.

`git diff --cached --check` reported:

```text
docs/agent_tasks/cockpit_ui_usefulness_integrate_v1_20260521.md:22: new blank line at EOF.
```

The Cockpit task-card artifact was preserved as-is rather than edited during this draft-only preservation step.

## Post-Preservation Phase 3G Check

After the preservation commit, Phase 3G task-card validation passed.

Fresh Phase 3G registry `check-overlap` failed only on:

```text
docs/agent_tasks/cockpit_ui_usefulness_final_canonical_merge_v1_20260521.md is dirty outside current task card allowed_files
```

The original blocker `docs/agent_tasks/cockpit_ui_usefulness_integrate_v1_20260521.md` was no longer reported as dirty outside Phase 3G.
