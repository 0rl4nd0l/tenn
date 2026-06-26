# Cockpit Document History Route Guard

Issue: #239

Branch: `safe/issue239-cockpit-doc-history-guard-current-base-v1-20260627`

Base: `origin/migration/clean-runtime-baseline-reconstruct-v1@8a4ffe2837d2950602b222d226d2d516b2076ec0`

## Summary

This job guards `GET /api/cockpit/docs` with the existing local API-key
dependency and updates the Cockpit API client to send the configured API key
when loading document history. The route still returns the same authenticated
operator payload, including `pdf_path`; unauthenticated callers are denied when
`settings.local_api_key` is configured.

## Artifacts

- `STATE.md` - scope, stale-work classification, docs impact, and proof status.
- `VALIDATION.md` - commands run and results.
- `REVIEW.md` - code review gate.
- `PR_BODY.md` - prepared pull request body.
- `validation.json` - machine-readable validation summary.
- `diff-check.json` - task-card diff gate output.
- `status.json` - registry claim status.
