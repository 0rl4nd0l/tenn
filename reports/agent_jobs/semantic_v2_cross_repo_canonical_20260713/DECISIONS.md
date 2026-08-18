# Decisions

- Use `selected_base()` as the single canonical identity source after Git
  discovery. This keeps comparison-base, canonical-head, and path-ownership
  decisions aligned.
- Preserve the existing Tenn canonical ref representation when the selected
  base is the Tenn fallback, protecting V1 output compatibility.
- Derive a non-fallback canonical ref with Git's symbolic-ref resolution, so
  `origin/master` reports `refs/remotes/origin/master`.
- Compare the checked-out canonical branch to the local name derived from the
  selected canonical branch, removing the Tenn-only branch literal.
- When no environment or marker override exists, read the target repository's
  shared registry and select exactly one non-stale active V2 record whose
  resolved worktree equals the target repository.
- Preserve silence for legacy V1 jobs and no matching V2 job. Fail closed for
  an ambiguous or invalid matching V2 selector.
- Reuse the selected registry read for closeout identity matching instead of
  creating a second selector path.
- Keep V2 semantic classification, ledger, capability, and report rules
  unchanged.
- Do not append `DECISION_ENTRY.json`. After final review and validation, use
  the declared `PUBLISH` capability for one bounded commit, push, PR, and merge
  containing only allowed files; do not deploy or activate runtime changes.
