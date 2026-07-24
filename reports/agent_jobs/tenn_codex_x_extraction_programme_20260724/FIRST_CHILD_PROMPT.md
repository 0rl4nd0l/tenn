# Exact First Child Prompt

Candidate ticket: `ASXFP_01_SCORECARDS`

Status: `HELD — OVERLAPS_EXISTING`

Exact prompt:
`proposed_run_package/prompts/ASXFP_01_SCORECARDS-implementer-01.held.txt`

Prompt SHA-256:
`270529ebe90bf0655a7eafcb060f9dea1f1a1da02888510cd1728e637827a8ae`

The prompt is complete and immutable for the pinned
`2f5a8aac38cf31ecbed3bcb50420fbd5b32ec8d7` run revision. It deliberately
contains a fail-closed pre-launch hold because open draft PR #513 changes the
metric authority and real-gold evaluation consumers needed by ticket 01.

It must not be launched. After exact owner disposition of PR #513, refresh
canonical identity and regenerate the prompt if the base, ticket, spec, scope,
or authority hash changes. Reusing this prompt on a new spine would violate the
design contract's artifact-derived prompt rule.
