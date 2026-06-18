# Decisions

## Duplicate Work

Decision: proceed as a narrow follow-up, not a duplicate of merged PR #336.

Rationale: PR #336 added the clean same-document HUB binding path, but the
current evidence packet proves the real target text includes both current
`2023-12-31` and comparative `2022-12-31` half-year evidence. The current-base
detector treats multiple dates as ambiguous, so the remaining fix is a smaller
current-period-line preference.

## Implementation Boundary

Decision: one deterministic source-bound fix only.

Accepted evidence:

- `Appendix 4D - Half-Year Ended 31 December 2023`
- `Current period: 1 July 2023 to 31 December 2023`
- comparative prior half-year evidence for `31 December 2022`

The implementation must preserve ambiguity for true conflicts and must not
infer from announcement dates, fiscal labels, title-only dates, or companion
disagreement.
