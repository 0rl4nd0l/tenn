# Blocking File Classification

Target:

`docs/agent_tasks/cockpit_ui_usefulness_final_canonical_merge_v1_20260521.md`

## Classification

Classification: valid uncommitted Cockpit job-control evidence from a blocked final-canonical-merge attempt, now likely obsolete at the product-change level but still requiring separate preservation.

It is not stale deletion residue and not Strategy Lab evidence.

## Evidence

The file is untracked:

```text
?? docs/agent_tasks/cockpit_ui_usefulness_final_canonical_merge_v1_20260521.md
```

It is not in `git ls-files`.

Task-card contract validation passes with `ok: true`. Key metadata:

- `job_id`: `cockpit_ui_usefulness_final_canonical_merge_v1_20260521`
- `lane`: `Reporting`
- `mutation_mode`: `safe_extension`
- `production_data_access`: `false`
- `output_dir`: `reports/agent_jobs/cockpit_ui_usefulness_final_canonical_merge_v1_20260521`
- Allowed product files are limited to Cockpit Home UI/test paths plus Cockpit task-card/report artifacts.

## Registry State

Current registry `list-active` reports no active jobs.

Current `check-overlap` for the Cockpit final canonical merge task card fails on an active overlapping Cockpit Reporting job:

- `cockpit_ui_overnight_orchestrator_v1_20260521`, by lane `Reporting` and overlapping Cockpit Home file ownership

It also fails on dirty files outside that task card's own allowlist:

- `docs/agent_tasks/cockpit_ui_usefulness_current_head_reapply_v1_20260521.md`
- `docs/agent_tasks/cockpit_ui_usefulness_final_canonical_merge_rerun_v1_20260521.md`
- `docs/agent_tasks/phase3g_collision_cockpit_final_canonical_merge_taskcard_audit_v1_20260521.md`
- Strategy Lab task cards already present in the checkout

## Report Bundle

Current repo bundle present:

- `reports/agent_jobs/cockpit_ui_usefulness_final_canonical_merge_v1_20260521/README.md`
- `reports/agent_jobs/cockpit_ui_usefulness_final_canonical_merge_v1_20260521/diff-check.json`

Requested sibling bundle path absent:

- `/home/l4nd0/tenn-cockpit-ui-usefulness-final-canonical-merge-v1-20260521/reports/agent_jobs/cockpit_ui_usefulness_final_canonical_merge_v1_20260521`

The current bundle reports:

- No merge happened.
- No registry claim happened.
- The intended fast-forward source commit was `2617337678bc82f03024dd06781dc1b52ddf63a9`.
- The job stopped on dirty-file policy before merge.
- The report artifacts were not force-added.

The bundle does not include a `status.json` file.

## Current HEAD Relationship

The intended source commit `2617337678bc82f03024dd06781dc1b52ddf63a9` is not an ancestor of current `HEAD`.

However, current `HEAD` (`7a8c872f8b652a5433afd1614eb4a657b0fc1f8d`) and source commit `2617337678bc82f03024dd06781dc1b52ddf63a9` have the same stable patch-id:

```text
f2d6dffc80de896bbc61a6201348fd11e7c71435
```

They also have no diff for the three relevant paths:

- `cockpit-ui/components/cockpit/home/home-page.tsx`
- `cockpit-ui/lib/cockpit-home-api.test.ts`
- `docs/agent_tasks/cockpit_ui_usefulness_vertical_slice_v1_20260521.md`

Inference: the Cockpit product change targeted by the final canonical merge appears to have been re-applied as current `HEAD`, but the final canonical merge task-card/report evidence remains uncommitted job-control evidence.
