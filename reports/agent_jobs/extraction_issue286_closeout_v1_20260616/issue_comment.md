# Proposed #286 Comment

Status update after merged extraction-only child slices:

- PR #349 merged accounting-number parsing for common accounting metric strings.
  Merge commit: `4b2b9e4c769617e21e94bbc90ec0fc420f170df9`.
- PR #350 merged payload-level structured `field_provenance`.
  Merge commit: `227e1ce0d4e99c4a13ece8012a44adeba4585cdf`.
- PR #351 merged consumer wiring so provenance/eval/review paths prefer
  `field_provenance` with legacy `provenance` fallback.
  Merge commit: `9a61c20cf0db988d06948861644d79698f37138c`.
- Closeout/status report PR: #354.

Keeping #286 open. The parser, payload, and consumer children are complete, but
the acceptance criterion that each persisted metric can be traced to
document/run/source excerpt/page still has a remaining persistence/schema
boundary. That work may touch DB schema, persistence models, migrations, or
stored rows and was intentionally not done under the no-DB/no-schema extraction
safe-extension boundary.

Current closeout decision: `KEEP_OPEN_BOUNDARY_EXPLICIT`.
