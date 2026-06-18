# Decisions

- Preserve the local fail-closed gate by replaying it onto current canonical,
  not by widening extraction scope.
- Fail only accepted rows with `risk_level == "review"`.
- Keep `risk_level == "info"` rows accepted so lower-severity metadata gaps stay
  visible.
- Keep the gate in the broad-run validation script; do not mutate runtime
  extraction or canonical persisted data.
- Use saved count-24 JSON for replay proof; do not run PDFs through extraction.
- Treat this as local preservation plus validation only. No push or PR is
  authorized.
- Treat the latest owner `Proceed` as approval for local commit preservation
  only; GitHub mutation remains unauthorized.
