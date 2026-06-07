Sloppy live-fix proof plan:

Focus on `sloppy-proof-intentional-issue.js`.

That file is intentionally disposable and intentionally broken. Fix the
placeholder implementation with the smallest change that makes
`npm run test:ci` pass. Remove debugging leftovers and placeholder markers in
that file only. Do not touch production code.
