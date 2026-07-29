# ASXFP Ticket 08 Appendix 4C cash profile

Status: IMPLEMENTED — BOUNDED LOCAL VALIDATION COMPLETE

## Authority

- base commit: `dc4e99e305218dfea072e9c78cb13476dc6899fe`
- base tree: `cb80b0320c3b3293c1182ae926f57baa5d21bdb6`
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

## Validation evidence

- Authority SHA-256 matched:
  `75f62f979076014333a8c958e8a085c0639b76fad8f5df65542cae02355b6dca`.
- Exact base commit/tree matched the task authority.
- Task-card `validate`: passed (`ok: true`, no issues).
- Focused and adjacent pytest validation:
  `39 passed, 1 warning` (the warning is an inherited unknown pytest config
  option in the reused local environment).
- `python3 -m py_compile` for both changed Python files: passed.
- Ruff `0.15.6` for both changed Python files: passed.
- `git diff --check`: passed.
- The seven delivery paths match the accepted Codex X candidate byte for byte
  before this validation-evidence refresh.

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
