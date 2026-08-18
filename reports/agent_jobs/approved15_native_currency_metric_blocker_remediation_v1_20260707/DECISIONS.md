# Decisions

## D1. Retarget Instead Of Mutating Stale Worktree

The requested source worktree failed guard as STALE_PATH. After user approval,
the work was retargeted to a fresh current-canonical sibling worktree:

/home/l4nd0/tenn-approved15-native-currency-metric-remediation-v1-20260707

## D2. One Fix Class Only

The integrated class is deterministic capital-structure net-debt recovery.
This was chosen because source proof showed expected CSL and FMG net debt can
be derived from source-bound total financial debt less cash.

## D3. QBE Locator Repair Approved And Integrated

After owner approval, the next class was limited to QBE `net_debt`
balance-sheet/source-selection repair. Auditor review tables are now blocked
from claiming formal statement slots, and QBE's selected balance sheet recovers
`Borrowings 4.1` as the current-period total debt source for deriving
`net_debt`.

## D4. Stop Before Income Statement And Share Count Repairs

BHP np_attributable, CSL revenue, CSL np_attributable, and FMG shares_outstanding
are not part of the capital-structure net-debt class. They remain for a later
approved class.

## D5. BHP/CSL NPAT Row Selection Approved And Integrated

After owner approval, the next class was limited to BHP/CSL `np_attributable`
income-statement row-selection repair. The implementation prefers
owner-attributable profit rows over generic profit rows and handles split
shareholder labels/current-period values observed in the BHP and CSL source
tables.

## D6. Stop Before Revenue And Share Count Repairs

At the BHP/CSL NPAT stop point, CSL revenue and FMG shares_outstanding remained
outside that approved class. The scorecard gate still failed with those two
missing expected metrics, so the state stayed PARTIAL_WAITING_ON_USER_NEXT_CLASS.

## D7. CSL Revenue Row Selection Approved And Integrated

After owner approval, the next class was limited to CSL `revenue`
income-statement/source-selection repair. The implementation recovers
line-aligned revenue from formal income-statement rows where a single label cell
contains multiple line items and the current-period value cell contains matching
multi-line values.

## D8. Stop Before FMG Share Count Repair

FMG shares_outstanding remains outside this approved class. The scorecard gate
still fails with that one missing expected metric, so the current state remains
PARTIAL_WAITING_ON_USER_NEXT_CLASS.

## D9. FMG Share Count Repair Approved And Integrated

After owner approval, the final class was limited to FMG `shares_outstanding`
recovery. The implementation only handles source-proven split PyMuPDF
share-capital tables where a same-page preceding table supplies share-count
header context for the period-end data rows. It preserves the guard against
dollar-denominated share-capital values by still requiring share-count evidence
and an absolute count candidate.

The four-case no-write replay now passes with `side_effect_pass=true`, and the
focused scorecard gate passes with 40/40 present-correct expectations and zero
failure classes.
