---
job_id: extraction_post_pr301_dxc_lbl_containment_v1_20260607
lane: Financial Truth
supporting_lanes:
  - Evaluation
  - Query Orchestration
  - Provenance
  - Repo Hygiene
owner: Codex
allowed_files:
  - docs/agent_tasks/extraction_post_pr301_dxc_lbl_containment_v1_20260607.md
  - reports/agent_jobs/extraction_post_pr301_dxc_lbl_containment_v1_20260607/README.md
  - reports/agent_jobs/extraction_post_pr301_dxc_lbl_containment_v1_20260607/status.json
  - reports/agent_jobs/extraction_post_pr301_dxc_lbl_containment_v1_20260607/pre_containment_snapshot.json
  - reports/agent_jobs/extraction_post_pr301_dxc_lbl_containment_v1_20260607/post_containment_verification.json
  - reports/agent_jobs/extraction_post_pr301_dxc_lbl_containment_v1_20260607/containment_ledger.json
  - reports/agent_jobs/extraction_post_pr301_dxc_lbl_containment_v1_20260607/validation.json
  - reports/agent_jobs/extraction_post_pr301_dxc_lbl_containment_v1_20260607/diff-check.json
  - reports/agent_jobs/extraction_post_pr301_dxc_lbl_containment_v1_20260607/raw_commands.log
approval_required: false
allow_unapproved_safe_extension: true
timeout_seconds: 7200
output_dir: reports/agent_jobs/extraction_post_pr301_dxc_lbl_containment_v1_20260607
mutation_mode: safe_extension
production_data_access: false
---

# Post-PR301 DXC/LBL Accepted-Output Containment

## Objective

Verify whether unsafe DXC/LBL accepted outputs identified by PR #301 exist in
the inspected runtime DB/Qdrant state. If exact rows or points exist, contain
only those exact outputs after pre-snapshot. If no exact rows or points exist,
produce a no-op containment proof.

## Scope

Branch:
`safe/extraction-post-pr301-broad-accuracy-push-v1-20260607`.

Worktree:
`/home/l4nd0/tenn-post-pr301-broad-accuracy-push-v1-20260607`.

Mode: CONTROLLED CONTAINMENT / REPORT-LOCAL UNLESS EXACT MATCHES EXIST.

## Input Evidence

- PR #301 merge commit:
  `10c162a5162b3e5fc1306cdd908b23bfa6f0a5a8`.
- PR #301 report:
  `reports/agent_jobs/extraction_post_pr299_accepted_output_audit_v1_20260606/`.
- Unsafe document IDs:
  `f8a24788-dbe0-48f7-ad41-654f2c8a3845` for DXC and
  `551c6b84-1053-405c-a833-4ecc018e2045` for LBL.

## Allowed Runtime Mutation

Only exact DXC/LBL financial rows and matching Qdrant points identified from PR
#301 accepted-output evidence may be contained. No broad ticker deletion, no
unrelated DB/Qdrant/news/memory mutation, and no source PDF movement or edits.

## Required Work

- Identify exact DXC and LBL document IDs, extraction run IDs, row keys, and any
  Qdrant point IDs from PR #301 artifacts or mark unavailable fields as
  `DATA_MISSING`.
- Snapshot exact candidate rows/points before any mutation.
- Check whether rows/points exist in the current inspected DB/Qdrant.
- If no matching rows/points exist, write a no-op containment proof and do not
  mutate.
- If matching rows/points exist, prefer supported quarantine/suppression. If no
  supported quarantine exists, delete/suppress only exact rows/points after
  pre-snapshot and write post-containment verification.
- Verify exposure paths no longer surface exact unsafe rows/points if route
  checks are available.
- Confirm no unrelated rows or points changed.

## Hard Stops

- Stop before broad extraction, count-16, count-24, count-32, broad backfill, or
  full ticker-universe extraction.
- Stop before production mutation unless exact rows/points are identified and
  pre-snapshotted.
- Stop before Qdrant/news/memory mutation unless exact matching points are
  identified and pre-snapshotted.
- Stop before source PDF edits, prompt/gold-label/schema/runtime/model/GPU
  config changes, or unrelated cleanup.

## Validation

- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/extraction_post_pr301_dxc_lbl_containment_v1_20260607.md`
- Safe registry active-record inspection or `DATA_MISSING`.
- JSON validation for report artifacts.
- `git diff --check`.
- `git diff --cached --check` if staging.
- `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/extraction_post_pr301_dxc_lbl_containment_v1_20260607.md --repo-root .`
- Verify no source PDFs are staged.

## Final Report Requirements

Report exact identifiers found or missing, snapshot method, containment action
or no-op proof, post-verification, side-effect audit, files touched, unsafe
actions avoided, `DATA_MISSING`, and whether Milestone 2 may proceed.
