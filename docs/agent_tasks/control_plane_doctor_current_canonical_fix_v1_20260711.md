---
job_id: control_plane_doctor_current_canonical_fix_v1_20260711
lane: Reporting
supporting_lanes:
  - Repo Hygiene
  - Evaluation
owner: Codex
allowed_files:
  - docs/agent_tasks/control_plane_doctor_current_canonical_fix_v1_20260711.md
  - scripts/control_plane_doctor.py
  - scripts/test_control_plane_doctor.py
  - docs/dev_flow/CONTROL_PLANE_DOCTOR.md
  - .github/workflows/ci.yml
  - reports/agent_jobs/control_plane_doctor_current_canonical_fix_v1_20260711/README.md
  - reports/agent_jobs/control_plane_doctor_current_canonical_fix_v1_20260711/STATE.md
  - reports/agent_jobs/control_plane_doctor_current_canonical_fix_v1_20260711/DECISIONS.md
  - reports/agent_jobs/control_plane_doctor_current_canonical_fix_v1_20260711/VALIDATION.md
  - reports/agent_jobs/control_plane_doctor_current_canonical_fix_v1_20260711/NEXT_GOAL.md
approval_required: true
approval_context: "USER_APPROVED_2026-07-11: preserve source commit 231b4626 read-only; retarget its exact doctor files onto fresh canonical 21b7f6df; fix remote-ref freshness false-pass; add full CLI warning/error fixtures; add or justify focused CI coverage; do not push/open PR or mutate PR #478, host, systemd, runtime, data, extraction, ledger, or registry surfaces."
timeout_seconds: 7200
output_dir: reports/agent_jobs/control_plane_doctor_current_canonical_fix_v1_20260711
mutation_mode: safe_extension
production_data_access: false
github_mutation_allowed: false
live_ledger_mutation_allowed: false
docs_impact: DOCS_UPDATED
docs_checked:
  - docs/dev_flow/CONTROL_PLANE_DOCTOR.md
  - .github/workflows/ci.yml
  - docs/dev_flow/CONTROL_PLANE_STATUS.md
docs_changed:
  - docs/dev_flow/CONTROL_PLANE_DOCTOR.md
docs_followup: "none"
reason: "Remote freshness semantics, new CLI fixtures, and focused CI coverage change the doctor validation and operator contract."
task_tier: large
recommended_model: "high reasoning"
actual_model: "Codex GPT-5"
why_this_model: "The retarget must preserve exact source behavior while closing a canonical-truth false-pass, integrating current CI, and respecting stale-source and PR #478 boundaries."
worker_model_allowed: false
worker_decision_limit: "No workers; retarget, remote-truth semantics, CLI fixtures, CI, and documentation are one coupled review-fix lane."
escalation_needed: false
task_scope: safe_extension
base_ref: origin/migration/clean-runtime-baseline-reconstruct-v1
base_head: 21b7f6df7904bff5bed6033cb181f75b4f0f04ae
---

# Control Plane Doctor Current-Canonical Review Fix

## Objective

Retarget the exact doctor implementation from preserved commit `231b4626` onto
current canonical and close the publication-readiness findings without widening
into remediation.

## Exact Changes

- Port the doctor script, focused tests, and focused doctor document exactly as
  the starting point.
- Verify current remote canonical with a read-only `git ls-remote` probe, grade
  unavailable/mismatched remote truth explicitly, and prevent cached-ref false
  passes.
- Add public CLI warning and error outcome fixtures.
- Add the focused doctor test to current canonical CI.
- Create only this task card and report-local closeout artifacts beyond those
  implementation files.

## Hard Stops

- Preserve `/home/l4nd0/tenn-control-plane-doctor-v1-20260711` and commit
  `231b4626` unchanged.
- Do not edit `AGENTS.md`, `tenn-fix`, `tenn-git-guard`, or
  `CODEX_OPERATOR_GUIDE.md` from PR #478.
- Do not push, open, or merge a PR.
- Do not repair doctor findings or mutate host config, systemd, deployed
  checkout, runtime, data, extraction, ledger, or registry state.

## TDD Sequence

1. Port the reviewed baseline files.
2. Add one CLI stale-remote fixture and capture RED; implement remote freshness
   grading and reach GREEN.
3. Add one CLI hard-error fixture and capture RED; implement minimal behavior
   if required and reach GREEN.
4. Add focused CI invocation and update operator documentation.
5. Run focused tests, doctor functionality proof, contracts, diff review, and
   final Git Guard.

## Done Criteria

- Source commit remains byte-for-byte unchanged and clean.
- Branch is based on exact canonical `21b7f6df` unless remote truth drifts.
- Cached origin state cannot produce a false canonical-parity PASS.
- Full CLI fixtures prove exit `0`, `1`, and `2` behavior.
- Current CI runs the focused doctor test.
- Only exact allowlisted files differ and no forbidden surface is mutated.
