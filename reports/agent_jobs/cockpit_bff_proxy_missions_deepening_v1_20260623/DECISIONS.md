# Decisions

- Use the existing shared `proxyBackendRequest` helper instead of adding another helper layer.
- Keep this slice to the marketplace missions route cluster only.
- Preserve explicit route-level `runtime = 'nodejs'` and `maxDuration = 30` exports.
- Do not migrate adjacent marketplace match, alert, scan, benchmark, or price-intelligence routes in this PR.
