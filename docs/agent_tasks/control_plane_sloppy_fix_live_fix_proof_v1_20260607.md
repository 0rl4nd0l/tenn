---
job_id: control_plane_sloppy_fix_live_fix_proof_v1_20260607
lane: Evaluation
supporting_lanes:
  - Reporting
  - Repo Hygiene
owner: Codex
allowed_files:
  - PLAN.md
  - package.json
  - sloppy-proof-intentional-issue.js
  - docs/agent_tasks/control_plane_sloppy_fix_live_fix_proof_v1_20260607.md
  - reports/agent_jobs/control_plane_sloppy_fix_live_fix_proof_v1_20260607/README.md
  - reports/agent_jobs/control_plane_sloppy_fix_live_fix_proof_v1_20260607/validation.json
approval_required: true
timeout_seconds: 1800
output_dir: reports/agent_jobs/control_plane_sloppy_fix_live_fix_proof_v1_20260607
mutation_mode: safe_extension
production_data_access: false
---

# Task

Create a disposable Sloppy Fix proof PR that intentionally contains one
fixable issue, then verify whether automatic Sloppy Fix can produce and push a
real fix commit.

# Scope

Use a clean branch based on live `origin/main`. Add only disposable proof files
and this task card. Do not change production/runtime code.

# Required Behavior

- Add one intentionally broken proof file with deterministic Sloppy-local issue
  patterns.
- Add a minimal root `package.json` so Sloppy's configured
  `npm run test:ci` command has a proof-specific test target.
- Add `PLAN.md` so Sloppy fix mode is directed at the disposable proof file.
- Open a PR to `main`.
- Let Sloppy Scan and automatic Sloppy Fix run.
- Inspect whether Sloppy produces a pushed fix branch/commit.

# Hard Boundaries

- Do not merge the disposable proof PR.
- Do not edit production runtime, DB, Qdrant, Redis, news stores, memory stores,
  source PDFs, gold labels, extraction prompts, parser routing, model/GPU
  config, backfills, migrations, or production data.
- Do not edit existing workflows or `.sloppy.yml`.
- Do not delete branches unless explicitly approved after evidence capture.

# Required Validation

- Tenn task-card validation.
- Tenn task-card `check-diff`.
- Local proof test should fail before Sloppy fixes the proof file.
- YAML/static validation is not required because no workflow is edited.
- `git diff --check`.
- Live GitHub evidence: PR URL, Sloppy Scan run, Sloppy Fix run, and any fix
  branch/commit produced by Sloppy.

# Definition Of Done

- Disposable proof PR exists.
- Sloppy Fix live result is classified as fixed, skipped, or no-op with exact
  run/branch/commit evidence.
- Report records whether the proof PR remains open or is closed.
