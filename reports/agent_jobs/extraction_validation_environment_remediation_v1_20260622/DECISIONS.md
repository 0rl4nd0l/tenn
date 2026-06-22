# Decisions

## Decision 1: Do Not Add Pytest To Runtime Requirements

Adding pytest to `financial-engine_v2/backend/requirements.txt` would make the
runtime/replay environment heavier and blur production versus validation
dependencies. The remediation instead creates an ephemeral overlay venv under
`/tmp` and leaves runtime venvs unchanged.

## Decision 2: Preserve Venv Symlink Paths

The first exact multipass helper run failed because resolving
`financial-engine_v2/.venv/bin/python` followed the symlink to the base uv
interpreter, losing the venv site-packages. The helper now preserves the
explicit venv path and has a regression test for that behavior.

## Decision 3: Timeout Means DATA_MISSING

A case timeout is infrastructure uncertainty. It must not count as a successful
product extraction and must not be conflated with a source-bound extraction
failure. Timeout rows are therefore infrastructure failures and drive aggregate
status to `DATA_MISSING` when side effects remain clean.

## Decision 4: Update Existing Draft PR

The remediation belongs on PR #384 because that branch exposed the validation
failure and already contains the JAY fix whose pytest coverage previously could
not run.
