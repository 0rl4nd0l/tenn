# approved15 native-currency metric blocker remediation v1

state: DONE_APPROVED15_FOUR_CASE_SLICE
date: 2026-07-07
worktree: /home/l4nd0/tenn-approved15-native-currency-metric-remediation-v1-20260707
branch: safe/approved15-native-currency-metric-remediation-v1-20260707
base_commit: 94dedc2913d4dbfc1913ca6fae897ca2ce4a0579

## Scope

The stale source handoff was read from:

/home/l4nd0/tenn-approved15-native-currency-status-policy-v1-20260702/reports/agent_jobs/approved15_low_confidence_status_policy_v1_20260701/handoff/remediation_orchestration_20260707/HANDOFF.md

The stale continuation worktree failed guard as STALE_PATH. After user approval,
work moved to this fresh current-canonical sibling worktree.

## Implemented Classes

Implemented one deterministic capital-structure net-debt class:

- Source-bound native-currency payloads can remain `ok` only when currency,
  period, scale, row refs, provenance, and metric source scales are bound.
- Balance-sheet total debt recovery now handles:
  - explicit `Total debt` rows;
  - current plus non-current borrowing rows;
  - multiline Docling grouped rows where labels and current-period values are
    split by newlines;
  - `Borrowings and finance lease liabilities` as strong debt evidence.
- Balance-sheet explicit `Net debt` rows can be recovered deterministically.

After owner approval, implemented exactly one additional class:

- QBE `net_debt` balance-sheet/source-selection repair.
- Auditor review pages are disqualified from claiming formal statement slots
  even when they mention the consolidated balance sheet.
- PyMuPDF balance-sheet grouped rows that put labels in a bundle and current
  values in following blank-label rows now align `Borrowings 4.1` with
  `3,679,000,000`, not the comparative `2,664,000,000`.

After owner approval, implemented exactly one additional class:

- BHP/CSL `np_attributable` income-statement row-selection repair.
- BHP shareholder-attributable profit rows whose label and current-period value
  are split across PyMuPDF cells now recover `Attributable to BHP shareholders`
  as `11,304,000,000`.
- CSL shareholder split rows now recover `- Shareholders of CSL Limited` as
  `401,000,000`, replacing generic `Net profit for the period` only when the
  existing NPAT source is generic profit.

After owner approval, implemented exactly one additional class:

- CSL `revenue` income-statement/source-selection repair.
- Formal income-statement rows whose label cell contains multiple line items
  now align the current-period value line with the matching revenue label.
- CSL page 11 `Total operating revenue` now recovers `8,332,000,000` from the
  current-period value line `8,332`, not the adjacent `Cost of sales` value.

After owner approval, implemented exactly one additional class:

- FMG `shares_outstanding` share-capital/source-selection repair.
- FMG page 30 Note 5(a) PyMuPDF output splits the share-count column headers
  from the data rows into adjacent same-page tables; preferred share-source
  recovery now uses that prior header context only when it supplies share-count
  evidence.
- FMG page 30 `At 31 December 2025` now recovers issued shares
  `3,078,964,918` with provenance `share_capital:page_30:At 31 December 2025`.

## Outcome

Focused four-case scorecard:

- red baseline: 33 present_correct, 3 present_wrong_value, 4 missing_expected_metric, 7 blockers
- first green: 35 present_correct, 2 present_wrong_value, 3 missing_expected_metric, 5 blockers
- QBE green: 36 present_correct, 2 present_wrong_value, 2 missing_expected_metric, 4 blockers
- BHP/CSL NPAT green: 38 present_correct, 0 present_wrong_value, 2 missing_expected_metric, 2 blockers
- CSL revenue green: 39 present_correct, 0 present_wrong_value, 1 missing_expected_metric, 1 blocker
- final FMG shares green: 40 present_correct, 0 present_wrong_value, 0 missing_expected_metric, 0 blockers

Fixed blockers:

- CSL_H_2025-12-31 net_debt: 9,993,000,000
- FMG_H_2025-12-31 net_debt: 1,013,000,000
- QBE_H_2025-06-30 net_debt: 1,555,000,000
- BHP_A_2021-06-30 np_attributable: 11,304,000,000
- CSL_H_2025-12-31 np_attributable: 401,000,000
- CSL_H_2025-12-31 revenue: 8,332,000,000
- FMG_H_2025-12-31 shares_outstanding: 3,078,964,918

Remaining blockers:

- none in the approved four-case blocker slice

## Forbidden Boundaries Preserved

- No DB, Qdrant, Redis, news, memory, source PDF, gold label, prompt, model,
  runtime config, service, DXS, GitHub, push, merge, rebase, reset, stash, or
  branch cleanup mutation.
- No broad approved15 replay.
- No count-24/count-32 work.
- /home/l4nd0/tenn dirt was not touched.
