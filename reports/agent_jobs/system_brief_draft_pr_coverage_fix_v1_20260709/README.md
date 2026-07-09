# System Brief Draft PR Coverage Fix V1

Status: LOCAL_VALIDATED

## Summary

Fixed the system brief draft-PR queue so reviewable drafts are not silently
omitted. Current control-plane/system-brief/automation drafts remain normal
`draft_pr` queue items, while older unrelated drafts are still surfaced as
lower-priority `stale_draft_pr` items.

## Boundaries

- Control-plane helper only.
- Read-only GitHub PR discovery only.
- No GitHub writes by the helper.
- No runtime, data, extraction, timer, service, model/GPU, Docker, or secret
  mutation.

System functionality is not proven by this layer; this is a control-plane queue
coverage fix.

## Result

- Regression test added for #491-style system brief draft PR coverage.
- Live read-only smoke shows #491-#495 as `draft_pr`.
- Older unrelated draft PRs are shown as `stale_draft_pr` below active stack
  items.
