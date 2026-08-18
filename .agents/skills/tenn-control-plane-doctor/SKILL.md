---
name: tenn-control-plane-doctor
description: Run and explain Tenn's deterministic read-only control-plane doctor. Use when Orlando asks to audit, inspect, diagnose, check health or drift, or run the control-plane doctor across canonical Git, deployed automation, runner policy, systemd templates, host skills, hooks, candidate state, marker semantics, or control-plane documentation freshness. Never use it to repair findings.
---

# Tenn Control Plane Doctor

Run the existing doctor as a diagnostic boundary. Do not duplicate its checks or
turn findings into remediation.

## Workflow

1. Read `AGENTS.md` and verify the requested checkout:

   ```bash
   pwd
   git branch --show-current
   git rev-parse HEAD
   git remote -v
   git status --short --untracked-files=all
   git ls-remote origin refs/heads/migration/clean-runtime-baseline-reconstruct-v1
   ```

   Require a clean, valid Tenn checkout containing
   `scripts/control_plane_doctor.py`. If current canonical is required but the
   checkout differs from fresh remote canonical, stop with `DATA_MISSING` or ask
   for explicit retarget/update approval. Do not fetch, switch, or fast-forward
   implicitly.

2. Run Tenn Dev Status and `tenn-git-guard` read-only preflight. Use full guard
   detail only when stale paths, ownership, duplicate work, or a readiness
   decision requires it.

3. Run the deterministic backend and preserve its exit code:

   ```bash
   python3 scripts/control_plane_doctor.py --repo-root . --json
   ```

   Exit `0` means all checks passed. Exit `1` means warnings or missing evidence
   exist without a hard failure. Exit `2` means a hard failure or the command
   could not complete safely. Treat exit `1` as diagnostic output, not a failed
   invocation.

4. Validate the JSON before interpreting it:

   - `schema_version` is `tenn_control_plane_doctor_v1`;
   - `read_only` is `true`;
   - `summary.exit_code` equals the process exit code;
   - every check has `id`, `status`, `severity`, `summary`, and `evidence`;
   - every status is `PASS`, `WARN`, `FAIL`, or `DATA_MISSING`.

   Stop with `BROKEN` if the output is invalid or exit semantics disagree.

5. Explain every check in plain language. Label current evidence as `VERIFIED`,
   `INFERRED`, `CONFLICT`, or `DATA_MISSING`. Summarize counts, then list
   `FAIL`, `DATA_MISSING`, and `WARN` findings before `PASS` findings.

6. Keep proof boundaries explicit:

   - A valid fresh JSON result proves the doctor command worked.
   - A `PASS` proves only the checked contract and surfaces agreed.
   - Services, timers, logs, artifacts, tests, and the doctor report are activity
     evidence, not proof that automation, ingestion, extraction, or another live
     pipeline produced its intended output.
   - Use the `Runtime Functionality Proof` table from `AGENTS.md` before calling
     any underlying runtime-like system `WORKING`.

7. Rank at most three next actions by safety and operational value. Make each
   remediation a separate approval-gated task. Prefer one coherent drift family
   rather than broad repair.

## Output

Return:

- checkout, local HEAD, fresh remote canonical, and guard result;
- doctor process exit, overall status, and status counts;
- one row per check with status, plain-language meaning, and decisive evidence;
- doctor functionality: `WORKING`, `PARTIAL`, `BROKEN`, or `DATA_MISSING`;
- underlying system functionality: independently proven status or
  `DATA_MISSING`;
- ranked next actions and the exact approval boundary.

Do not write a report unless the user requests durable evidence or the active
`/goal` requires `tenn-goal-report`.

## Hard Stops

Do not repair findings, fetch or retarget Git, start or restart services, reload
systemd, synchronize host skills, edit hooks, update candidate state, or mutate
GitHub, runtime, data, extraction, ledger, or registry state without separate
explicit approval for that exact action.
