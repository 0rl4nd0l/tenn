# Control Plane Doctor

The control-plane doctor is a deterministic, read-only diagnostic for comparing
Tenn's repo definitions with the effective deployed and host surfaces. It
reports drift; it never repairs it.

## Operator Command

From a current Tenn control-plane checkout:

```bash
python3 scripts/control_plane_doctor.py --repo-root . --json
```

The default command reads these surfaces:

- canonical Git ref
  `origin/migration/clean-runtime-baseline-reconstruct-v1`;
- current remote canonical SHA from a read-only `git ls-remote` query;
- deployed automation checkout
  `/home/l4nd0/tenn-codex-automations-v1-20260516`;
- repo and deployed `scripts/codex_automation_runner.py`;
- repo `systemd/user/` templates and installed user units;
- repo `.agents/skills/` and host `/home/l4nd0/.agents/skills`;
- `/home/l4nd0/.codex/hooks.json` and absolute Python targets named by it;
- automation candidate state under
  `~/.codex/automations/tenn/state/candidates.jsonl`;
- `report_review_status.py` and `system_brief.py` missing-marker semantics;
- skill-surface and control-plane-status freshness metadata.

Paths and the canonical ref can be overridden for fixtures or another host:

```bash
python3 scripts/control_plane_doctor.py \
  --repo-root . \
  --canonical-ref HEAD \
  --deployed-root /path/to/deployed \
  --host-skills-root /path/to/host-skills \
  --hooks-file /path/to/hooks.json \
  --installed-units-root /path/to/systemd/user \
  --candidate-state /path/to/candidates.jsonl \
  --doc /path/to/freshness-doc.md \
  --json
```

Repeated `--doc` options replace the two default freshness documents.

## JSON Contract

The top-level object contains:

- `schema_version`: `tenn_control_plane_doctor_v1`;
- `read_only`: always `true`;
- `repo_root` and `canonical_ref`;
- `summary`: aggregate `status`, `exit_code`, and counts;
- `checks`: check objects sorted by stable `id`.

Every check has:

- `id`;
- `status`: `PASS`, `WARN`, `FAIL`, or `DATA_MISSING`;
- `severity`: `info`, `warning`, or `error`;
- `summary`;
- `evidence`: check-specific paths, hashes, SHAs, counts, or mismatches.

Exit codes are:

| Exit | Meaning |
| --- | --- |
| `0` | Every check passed. |
| `1` | At least one warning or missing evidence exists, with no hard failure. |
| `2` | At least one check failed or the command could not complete safely. |

Drift is generally a warning because the command is diagnostic and cannot know
whether an owner-approved deployment or host synchronization is pending.
Malformed JSONL, unreadable policy output, and unresolved required Git identity
are failures.

## Check Semantics

- Git parity compares canonical and deployed HEAD. Task-branch HEAD is reported
  separately because a legitimate implementation branch will differ after its
  first commit. A remote-tracking canonical ref is verified against its remote
  branch with `git ls-remote`; a stale cached ref warns and unavailable remote
  truth is `DATA_MISSING`, so cached state cannot produce a parity `PASS`.
- Runner policy executes only the runner's `list` command, validates explicit
  model and reasoning values for small-policy jobs, and compares repo/deployed
  runner hashes.
- Template and skill checks hash files. Extra installed files are evidence but
  do not fail parity; missing or mismatched repo-defined files warn.
- Hook checking parses JSON and extracts absolute `.py` command targets. It
  does not execute hooks.
- Candidate checking reads JSON Lines and requires each non-empty line to be a
  JSON object. Absence is `DATA_MISSING`; malformed rows fail.
- Marker checking statically detects the known semantic split where missing
  markers are optional in the marker parser but can reappear as `stale_report`
  queue items in the brief.
- Docs freshness requires `last_verified_commit` and evaluates
  `stale_if_files` changes between that commit and canonical. A durable snapshot
  without machine-readable metadata warns.

## Safety And Limits

The command performs filesystem reads and read-only Git or policy-list
subprocesses, including a remote-ref query. It does not fetch, write reports,
repair paths, start services, reload systemd, synchronize skills, retarget
worktrees, change Git state, or mutate GitHub, runtime, data, ledger, or
registry state.

Focused tests exercise the public CLI for verified healthy output, stale cached
remote warning output, and hard canonical-ref failure. Current CI runs
`scripts/test_control_plane_doctor.py` as its own focused pytest step.

A `PASS` proves only that the configured effective surfaces agree with the
checked repo contracts. It is not Runtime Functionality Proof for automation,
ingestion, extraction, or any other live pipeline. A `WARN`, `FAIL`, or
`DATA_MISSING` result should be routed into a separately approved remediation
task rather than repaired by this command.
