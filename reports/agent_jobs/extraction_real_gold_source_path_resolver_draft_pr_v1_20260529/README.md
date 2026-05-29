# Extraction Real-Gold Source Path Resolver Draft PR V1

## Summary

Prepare a draft PR for branch
`safe/extraction-real-gold-source-path-resolver-v1-20260529` targeting
`migration/clean-runtime-baseline-reconstruct-v1`.

This branch fixes the real-gold eval source-asset check so it uses the existing
allowlisted ASX source resolver and restores full `test_extraction_gold_eval.py`
passing without copying source PDFs into the repo.

## Scope

Allowed GitHub mutation: draft PR creation only.

Forbidden and not performed:

- Ready-for-review PR creation.
- PR merge.
- GitHub issue comments, closes, labels, milestones, or body edits.
- Runtime reload, extraction, canary, backfill.
- DB/Qdrant/news/memory/source-PDF/canonical-truth mutation.
- Parser route, prompt, schema, runtime/model/GPU/service, or Cockpit UI
  changes.

## Validation Before PR

Already passed on this branch:

- Full `test_extraction_gold_eval.py`: `24 passed, 5 warnings`.
- Targeted Ruff on `test_extraction_gold_eval.py`: passed.
- `py_compile` for `test_extraction_gold_eval.py`: passed.
- Task-card diff gate: passed.

## Result

Draft PR created and verified:

- PR: https://github.com/0rl4nd0l/tenn/pull/128
- Number: 128
- Title: `[codex] resolve real-gold source path validation`
- State: `OPEN`
- Draft: `true`
- Head branch: `safe/extraction-real-gold-source-path-resolver-v1-20260529`
- Base branch: `migration/clean-runtime-baseline-reconstruct-v1`

Branch head at PR verification:

- Local: `751790ce1fc3990d45bc1fddbeb2b189430f91ef`
- Remote: `751790ce1fc3990d45bc1fddbeb2b189430f91ef`

Remaining blocker before any AAU/runtime canary continuation:

`APPROVE #96 RUNTIME RELOAD AND AAU CANARY extraction_aau_runtime_reload_canary_approval_packet_v1_20260529`
