# Review

## Findings

No blocking review findings found in the changed surface.

## Risk Notes

- `insufficient_for_recent_news` is added only when local-news context exists and
  no such source is `claim_verified`.
- Empty local-news retrieval remains the existing `no_hit` case.
- Generic context-only local-news prompts remain context-only unless they match
  the narrower recent/update/news sufficiency gate.

## Residual Risk

Broader Cockpit streaming surfaces were not rerun. The changed code path is
covered by direct `chat_with_tenn()` tests and a `/chat` route envelope test.
