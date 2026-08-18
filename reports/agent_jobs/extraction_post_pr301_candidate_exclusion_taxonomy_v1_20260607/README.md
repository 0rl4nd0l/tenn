# Post-PR301 Candidate Exclusion Taxonomy

Generated: 2026-06-07T04:32:56.394274Z

State: PASSED. Narrow candidate-exclusion hardening completed.

## Rules Added

- `meeting_or_proxy_notice`: title-only `Notice of Annual General Meeting` and `Notice of Meeting and Explanatory` wording now excludes AGM notices without requiring proxy-form text.
- `director_interest_notice`: Appendix 3Y / change-of-director-interest securities notices are excluded as obvious non-financial notices.

## Scope

The changes are deterministic source-title/first-page-text exclusions only. No broad fuzzy exclusion, sample run, DB/Qdrant/news/memory mutation, source PDF edit, prompt/gold-label/schema/runtime/model/GPU config change, broad extraction, backfill, count-24/count-32, or full ticker extraction ran.

## Validation

- Focused classifier pytest: 12 passed.
- Scorecard taxonomy pytest: 3 passed.
- py_compile: passed.
- ruff: passed.
- Full touched pytest: 184 passed.

Milestone 3 may proceed.
