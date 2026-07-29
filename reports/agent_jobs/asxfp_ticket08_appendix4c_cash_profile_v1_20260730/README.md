# ASXFP Ticket 08 Appendix 4C cash profile

Status: REJECTION REPAIRED — INDEPENDENT RE-REVIEW PENDING

## Authority

- base commit: `dc4e99e305218dfea072e9c78cb13476dc6899fe`
- base tree: `cb80b0320c3b3293c1182ae926f57baa5d21bdb6`
- rejection-repair start commit:
  `0879ff320cedc3a36ab962cea248d1fc2a04c253`
- rejection-repair start tree:
  `13b362907caaa55cbd00cbe77faa2d7b43108098`
- authoritative ticket SHA-256:
  `75f62f979076014333a8c958e8a085c0639b76fad8f5df65542cae02355b6dca`
- task card:
  `docs/agent_tasks/asxfp_ticket08_appendix4c_cash_profile_v1_20260730.md`

## Bounded implementation

The existing standalone table-only Appendix 4C parser now exposes a focused
cash-profile builder. Exact form items cover customer receipts, operating,
investing and financing cash flow, PP&E capex, ending cash, unused financing,
and disclosed estimated funding quarters.

Deterministic values always win. The only fallback seam accepts explicit
caller-supplied values, fills missing allowlisted field/period pairs, and
rejects incomplete evidence, mismatched line items/period roles, unsupported
fields, revenue, profit/NPAT, and net debt.

Every accepted profile observation carries row/cell coordinates and labels,
source span, raw value, period basis/evidence, and currency/scale evidence.
Ticket 07 `period_only` and `year_to_date` values remain separate.

The rejection repair now dereferences every fallback table/page/row/column
claim and authenticates the raw cell, labels, line item, canonical source span,
period role/evidence, currency, scale, and resolved header context. Fabricated,
ambiguous, inherited-unprovable, or out-of-range claims fail closed.

Deterministic duplicates are grouped before selection. Semantically equivalent
duplicates use documented stable precedence; any value, unit, currency, scale,
or period disagreement abstains with an explicit warning and blocks fallback
for that field-period. This includes a 4.6 versus 5.5 `cash_end` disagreement.

## Validation evidence

- Authority SHA-256 matched:
  `75f62f979076014333a8c958e8a085c0639b76fad8f5df65542cae02355b6dca`.
- Exact rejection-repair start commit/tree matched the supplied authority.
- Task-card `validate`: passed (`ok: true`, no issues).
- Rejection-repair focused and adjacent validation: `44 passed, 1 warning`
  under pytest. The warning is the pre-existing unknown
  `asyncio_default_fixture_loop_scope` config option.
- Ruff `0.15.6` for the changed parser and focused tests: passed.
- `python3 -m py_compile` for parser and focused tests: passed.
- `git diff --check`: passed.
- The six repaired files transferred from the Codex X child were verified
  byte-for-byte by SHA-256 before local validation.
- The Codex X launcher could not stage because its launcher-owned audit file
  was read-only. The exact repair delta was therefore frozen into this clean
  delivery worktree for ordinary local commit and exact-commit re-review.

## Boundary compliance

No PDF, protected holdout, extraction, OCR, model, runtime, service, database,
queue, GPU, deployment, activation, production write, GitHub mutation, push,
PR, or merge action occurred.

## Remaining risks

- The isolated profile API is not production-routed by design. A later,
  separately authorized ticket must choose any production integration.
- Item 2.1(c) is intentionally the only Appendix 4C capex mapping. Other
  acquisition or intangible rows are not combined or inferred.
- Publication and exact-head CI remain separate delivery steps.
- Independent re-review of this repaired candidate is pending.
