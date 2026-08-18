# RAG Query Commentary Hybrid Source Contract

Issue: #252

Branch: `safe/issue252-rag-query-contract-current-base-v1-20260627`

Base: `origin/migration/clean-runtime-baseline-reconstruct-v1@6dc50b558c4ec88157d4353d9c493a80ed0e91d5`

## Summary

This job makes `/rag/query` truthful about supported `source` values. The route
now accepts only backend-implemented sources, `asx_docs` and `news`.
Unsupported `commentary` and `hybrid` values are rejected by request validation
instead of being accepted and returning a 501 stub.

## Artifacts

- `STATE.md` - scope, evidence, docs impact, and functionality proof status.
- `VALIDATION.md` - commands run and results.
- `REVIEW.md` - code review gate.
- `PR_BODY.md` - prepared pull request body.
- `validation.json` - machine-readable validation summary.
- `diff-check.json` - task-card diff gate output.
- `status.json` - registry claim status.
