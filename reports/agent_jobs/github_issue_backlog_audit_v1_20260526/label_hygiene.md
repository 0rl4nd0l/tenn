# Label Hygiene

## Missing Required Label Families On Open Issues

| Family | Missing Count | Issues |
| --- | --- | --- |
| lane:* | 6 | #76, #61, #55, #53, #41, #40 |
| mode:* | 8 | #87, #86, #76, #61, #55, #53, #41, #40 |
| priority:* | 7 | #76, #71, #61, #55, #53, #41, #40 |
| risk:* | 7 | #76, #71, #61, #55, #53, #41, #40 |
| state:* | 8 | #76, #72, #71, #61, #55, #53, #41, #40 |
| type:* | 8 | #76, #72, #71, #61, #55, #53, #41, #40 |

## Open Issues Needing Cleanup

| Issue | Cleanup Needed | Classification |
| --- | --- | --- |
| #87 [Query Orchestration] A2M recall chat answer lacks required visible evidence | missing mode | DATA_MISSING |
| #86 [Cockpit] Home portfolio panel shows no data | missing mode | DATA_MISSING |
| #76 [Strategy Lab] Convert QuantDinger from infrastructure proof into analyst-useful read-only workflow | missing lane,mode,priority,risk,state,type; missing milestone; legacy/plain labels query-orchestration,reporting | STALE_NEEDS_REVALIDATION |
| #72 [Financial Truth] Appendix 4C candidate sidecar parser v1 | missing state,type; missing milestone | HIGH_RISK_NEEDS_AUDIT_FIRST |
| #71 [Provenance] Source label fixture matrix v1 | missing priority,risk,state,type; missing milestone | STALE_NEEDS_REVALIDATION |
| #61 Cockpit should default visible GPU to the llama-server GPU | missing lane,mode,priority,risk,state,type; missing milestone | NEEDS_REVIEW |
| #55 Cockpit backend restart route has no local auth or CSRF guard while frontend is LAN-bound | missing lane,mode,priority,risk,state,type; missing milestone | HIGH_RISK_NEEDS_AUDIT_FIRST |
| #53 Production Cockpit forms rely on placeholders and unlabeled icon controls | missing lane,mode,priority,risk,state,type; missing milestone | NEEDS_REVIEW |
| #41 missing data | missing lane,mode,priority,risk,state,type; missing milestone; legacy/plain labels bug | DUPLICATE_CANDIDATE |
| #40 failure to request a search | missing lane,mode,priority,risk,state,type; missing milestone | DUPLICATE_CANDIDATE |

## Inconsistencies

- Open issue inconsistent done-state labels: none found.
- Closed issues with `state:ready`: none found.
- Closed issues with `state:needs-review` or `state:parked`: #75 and #77. Both appear integrated and closed, so labels should be cleaned in a later approved GitHub-mutation task.
- Legacy/plain labels on open issues: #76 has `query-orchestration` and `reporting` instead of only `lane:*`; #41 has generic `bug` only.
- Several pre-protocol closed audit issues lack `state:done-*` labels. This is label hygiene, not by itself evidence of unsafe closure.

## Label Inventory Use On Open Issues

| Label | Family | Open Issue Count |
| --- | --- | --- |
| bug | plain | 1 |
| codex | plain | 0 |
| documentation | plain | 0 |
| duplicate | plain | 0 |
| enhancement | plain | 0 |
| future | plain | 1 |
| good first issue | plain | 0 |
| help wanted | plain | 0 |
| invalid | plain | 0 |
| lane:cockpit | lane | 1 |
| lane:evaluation | lane | 17 |
| lane:financial-truth | lane | 6 |
| lane:memory | lane | 5 |
| lane:provenance | lane | 16 |
| lane:query-orchestration | lane | 14 |
| lane:repo-hygiene | lane | 6 |
| lane:reporting | lane | 37 |
| lane:runtime | lane | 9 |
| mode:audit | mode | 39 |
| mode:implementation | mode | 0 |
| mode:issue-closeout | mode | 0 |
| mode:result-review | mode | 0 |
| mode:safe-extension | mode | 6 |
| priority:p0 | priority | 1 |
| priority:p1 | priority | 34 |
| priority:p2 | priority | 11 |
| priority:p3 | priority | 0 |
| product-value | plain | 13 |
| quantdinger | plain | 1 |
| query-orchestration | plain | 1 |
| question | plain | 0 |
| reporting | plain | 1 |
| risk:high | risk | 20 |
| risk:low | risk | 0 |
| risk:medium | risk | 26 |
| seed-regression | plain | 0 |
| state:blocked | state | 0 |
| state:data-missing | state | 5 |
| state:done-audit-only | state | 0 |
| state:done-remediated | state | 0 |
| state:duplicate | state | 0 |
| state:needs-followup | state | 8 |
| state:needs-review | state | 7 |
| state:parked | state | 0 |
| state:ready | state | 30 |
| state:running | state | 0 |
| state:superseded | state | 0 |
| strategy-lab | plain | 1 |
| task:codex-ready | task | 5 |
| type:automation | type | 7 |
| type:bug | type | 14 |
| type:ci | type | 0 |
| type:control-plane | type | 6 |
| type:docs | type | 1 |
| type:regression-seed | type | 0 |
| type:security | type | 0 |
| type:usability | type | 20 |
| type:validation-gap | type | 21 |
| wontfix | plain | 0 |
