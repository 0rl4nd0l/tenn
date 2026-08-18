# Validation

Status: `PASS_WITH_RISK`

## TDD Evidence

- RED: stale cached canonical CLI fixture failed with missing
  `remote_canonical_sha` evidence.
- GREEN: minimal `git ls-remote` verification made the stale-cache fixture pass.
- Existing hard-error behavior passed the new full CLI exit-2 fixture without
  additional production code.
- Integration RED: prior healthy fixture used helper API plus `HEAD`, which is
  now explicitly unverified.
- Integration GREEN: healthy fixture now invokes the public CLI with a verified
  remote-tracking ref and preserves the no-write snapshot assertion.

## Current Results

- Eight unittest cases: PASS.
- Eight focused pytest cases via ephemeral `uvx`: PASS; one unrelated pytest
  config warning.
- Real doctor: expected exit `1/WARN`, eight checks, no failures,
  `canonical_ref_fresh=true`, cached/remote canonical `21b7f6df`.
- `git diff --check`: PASS before report closeout.
- Pytest import in host Python: `DATA_MISSING`; ephemeral validation used per
  Tenn validation autonomy.

## Pending

- Task-card schema, allowed-diff, report-artifact, and closeout checks: PASS.
- CI YAML structural parse: PASS.
- Ruff via ephemeral `uvx`: PASS.
- Skeptical review: no critical or warning findings; one fail-closed timeout
  classification suggestion.
- Final remote canonical and source-preservation checks remain immediately
  before the local commit.
