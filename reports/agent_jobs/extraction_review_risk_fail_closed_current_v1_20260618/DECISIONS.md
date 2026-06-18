# Decisions

- Preserve the local fail-closed gate by replaying it onto current canonical,
  not by widening extraction scope.
- Fail only accepted rows with `risk_level == "review"`.
- Keep `risk_level == "info"` rows accepted so lower-severity metadata gaps stay
  visible.
- Keep the gate in the broad-run validation script; do not mutate runtime
  extraction or canonical persisted data.
- Use saved count-24 JSON for replay proof; do not run PDFs through extraction.
- Local commit preservation is complete.
- After the owner replied `Approve`, GitHub mutation is limited to pushing this
  branch and opening a PR only. Do not merge, force-push, or mutate issues.
