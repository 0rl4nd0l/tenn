# Extraction Ticket Reconciliation

## Inventory

| Input | Absolute path | SHA-256 |
| --- | --- | --- |
| Spec | `/home/l4nd0/codex-x-pilot/.state/runs/20260723T062310Z-2f5a8aac38-470589/workspace/source/docs/superpowers/specs/2026-07-23-asx-financial-profile-extraction-recovery.md` | `ecba77e0185fe5fe4d38c840624bb7da4ce5f4f6290458c7f6e2b33b3a8b8b67` |
| Plan | `/home/l4nd0/codex-x-pilot/.state/runs/20260723T062310Z-2f5a8aac38-470589/workspace/source/docs/plans/asx_financial_profile_extraction_recovery_plan.md` | `16ff026fa5cec820f9ce4cbe558b6fb4d168e6fc0e23c98854d81b1abf4b12ba` |
| Tickets | `/home/l4nd0/codex-x-pilot/.state/runs/20260723T062310Z-2f5a8aac38-470589/workspace/source/.scratch/asx-financial-profile-extraction-recovery/issues/` | ticket-set hash `664527b0c95f11d3ce4e1841d902b324be34ab1041b5a333d00e3f0e654a2026` |
| ADRs | recovered workspace and ticket package | No standalone ADR files; decisions are embedded in the spec |

The ticket-set hash is SHA-256 over the compact canonical JSON array of the 18
ordered ticket IDs in `run_manifest.json`. Individual source hashes are in
`ARTIFACT_HASHES.json`.

## Status table

| ID | Ticket | Status | Current-truth reconciliation | Blocker / next action |
| --- | --- | --- | --- | --- |
| 01 | Trustworthy real-ASX release scorecards | `OVERLAPS_EXISTING` | Canonical still lacks period-basis/accounting-basis release gates and lets provenance remain diagnostic, but PR #513 changes the metric authority plus `extraction_gold_eval.py` and its scorecard consumer. The precision/recall denominator must follow that authority. | Owner resolves PR #513; refresh canonical; then re-scope only the remaining scorecard gap. |
| 02 | Lock 12-document diagnostic corpus | `DATA_MISSING` | Canonical has 15 prior real fixtures but not the required two independently verified documents for each of six classes, complete labels, or locked source/label manifest. | Separate approval and provision of source PDFs and independently reviewed gold labels. |
| 03 | Lock 36-document release holdout | `DATA_MISSING` | The required 48-document corpus, protected 36-document holdout, source hashes, and review metadata do not exist on canonical. | Complete 01 and 02, then separately authorize/provide protected source and label assets. |
| 04 | Explicit extraction contracts | `OVERLAPS_EXISTING` | Pure document classification exists, but production contracts do not. PR #513 is the open declarative metric-contract authority and directly owns allowed metric semantics. | Do not duplicate. Resolve PR #513 and 02 before a residual routing ticket. |
| 05 | Immutable observation seam | `DEPENDS_ON` | Canonical still mutates `asx_periodic_financials`; no immutable observation store exists. The atomic seam must consume the final metric authority, and PR #513 changes `pipeline.py` persistence behavior. | Resolve PR #513 first; then a code-only seam may be reclassified `READY` without running migrations or touching data. |
| 06 | Project all statutory metrics | `DEPENDS_ON` | No observation projection exists. PR #513 also decides the declarative canonical/persistence metric set. | Depends on 05 and owner-resolved PR #513. |
| 07 | Quarter-only and YTD observations | `DEPENDS_ON` | Sidecar parsers preserve current-quarter/YTD roles, and PR #517 improved current-column binding, but production output/persistence cannot retain both typed bases. | Depends on 04 and 05; preserve PR #517 rather than reimplement it. |
| 08 | Appendix 4C cash profile | `OVERLAPS_EXISTING` | A read-only 4C parser exists, but production/profile authority for the eight requested metrics does not. PR #513 currently centralizes the allowed metric contract and explicitly avoids unauthorized ontology expansion. | Owner resolves PR #513; then depends on 07 and source-approved diagnostic cases. |
| 09 | Statutory versus adjusted | `OVERLAPS_EXISTING` | Canonical has statutory guards, but no separate adjusted disclosure/profile lane. PR #508 owns NPAT owner attribution and OCI boundaries; PR #513 owns metric authority. | Exact owner instruction for PRs #508/#513; do not modify either draft. |
| 10 | Restatement precedence | `DEPENDS_ON` | No immutable observations or supersession model exists. | Depends on 06 and 07. |
| 11 | Evidence-backed review | `DEPENDS_ON` | An extraction-review service exists, but it is not connected to the proposed observation/profile conflict model. | Depends on 08, 09, and 10. |
| 12 | Scanned announcements | `DATA_MISSING` | Canonical has OCR/openability diagnostics but not the required trusted scanned-document evidence lane. | Depends on 01/04/05 and separately approved scanned PDFs plus reviewed labels. |
| 13 | Table/current-period selection | `SUPERSEDED` | Merged PR #517 binds current-period rows/columns to exact source evidence and preserves comparative abstention. The old broad repair card would duplicate that canonical fix; quarter/YTD persistence and corpus-driven residuals belong in 07 and future diagnostic tickets. | Retire this card. Create a new bounded failure-family ticket only after 02/07 evidence exists. |
| 14 | Scale/currency/cash-flow normalization | `DEPENDS_ON` | Canonical already has fail-closed scale/native-currency gates and PR #517 current-cell binding, but no approved diagnostic 4C slice exists for remaining sign/subtotal repairs. | Depends on 02 and 08; repair only measured failure families. |
| 15 | Retire direct legacy writes | `DEPENDS_ON` | Canonical direct writes remain the production path; no authoritative observation projection exists. | Depends on 06, 08, 09, 10, and 11. |
| 16 | Pass locked 48-document gate | `DATA_MISSING` | No complete locked corpus, frozen extraction configuration, or authorized runtime evaluation is available. | Depends on 03 and 11–15; runtime/model/source execution requires separate approval. |
| 17 | 12-company canary | `DATA_MISSING` | A final canary is explicitly outside this supervisor's authority. | Depends on 16 and separate owner authorization. Runtime truth stays `DATA_MISSING`. |
| 18 | Reversible bounded backfills | `DATA_MISSING` | No approved canary or bounded company/date window exists; backfill is separately owner-controlled. | Depends on 17 and explicit data/backfill approval. |

No whole ticket is `DONE`; several canonical foundations are useful but do not
satisfy an entire card. No ticket is currently `READY`.

## Shortest safe order

This preserves the existing ticket graph while applying current-truth holds:

1. Owner disposition of PR #513, then refresh canonical.
2. Reconcile and execute residual 01 (scorecard contract) if it no longer
   overlaps.
3. Separately approve/provide the 12-document source-and-label package for 02.
4. Execute residual 04, then code-only 05.
5. Execute 07, then 08; execute 06, 09, and 10 as their prerequisites clear.
6. Execute measured diagnostic repairs 12 and 14; ticket 13 stays retired.
7. Execute 11, then 15.
8. Separately approve/provide the protected holdout for 03, then execute 16.
9. Obtain separate runtime authorization for 17.
10. Obtain separate bounded data/backfill authorization for 18.

PR #508 must be owner-resolved before 09. Focused evidence must be green before
any approved regression pool. The integration spine advances only after exact
diff review, focused tests, no-write replay, fixed-denominator scorecard
comparison, clean export, and an independent reviewer pass.
