# Automation GitHub Dedupe Layer 2 V0

Status: DONE_WITH_RISK

## Summary

Implemented the Layer 2 read-only GitHub dedupe gate for automation backlog
candidates. The helper queries GitHub issues and PRs through read-only `gh`
commands, classifies exact duplicates separately from review-only fuzzy
matches, and exposes a candidate-store bridge for recording high-confidence
duplicates without mutating live host state.

## Boundaries

- Control-plane helper only.
- Read-only GitHub checks only.
- No host automation state writes.
- No runtime, data, extraction, timer, service, model/GPU, Docker, or secret
  mutation.

System functionality is not proven by this layer; this is a control-plane gate.

## Result

- Local helper/tests validated.
- Live GitHub read-only smoke validated the installed `gh` command shape.
- No live automation candidate state was written.
- No GitHub issue/comment/merge/write operation was performed by the helper.
