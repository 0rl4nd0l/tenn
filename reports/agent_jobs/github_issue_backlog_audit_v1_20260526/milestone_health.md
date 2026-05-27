# Milestone Health

M5 is overloaded with 16 open issues. M0 should run next because backlog hygiene, raw issue normalization, branch visibility, and local-ahead work affect the safety of every other lane.

| Milestone | Open Issues | Closed Issues | State | Recommendation |
| --- | --- | --- | --- | --- |
| M0 - Control Plane Hardening | 4 | 4 | open | run next for backlog/control-plane cleanup (#106/#115/#94/#78) |
| M1 - Trust / Provenance Foundation | 4 | 0 | open | steady |
| M2 - Evaluation Spine | 5 | 0 | open | run #105/#104 early; watch active extraction/eval overlap |
| M3 - Query + Memory Integrity | 8 | 0 | open | run after M0 for chat/query blockers (#107 then #119/#120) |
| M4 - Financial Truth Expansion | 4 | 0 | open | steady |
| M5 - Cockpit Analyst Workflow | 16 | 0 | open | overloaded; defer P2 UI/usability until M0/M3 blockers are clearer |
| M6 - Runtime / Local Automation | 4 | 4 | open | review #112/#114 local fixes before new runtime work |

## Issues Missing Milestone

| Issue | Classification | Recommendation |
| --- | --- | --- |
| #76 [Strategy Lab] Convert QuantDinger from infrastructure proof into analyst-useful read-only workflow | STALE_NEEDS_REVALIDATION | Move to M5 or M3; add standard lane/mode/priority/risk/state/type labels. |
| #72 [Financial Truth] Appendix 4C candidate sidecar parser v1 | HIGH_RISK_NEEDS_AUDIT_FIRST | Move to M4; add state/type; keep HIGH risk and P0 only if current. |
| #71 [Provenance] Source label fixture matrix v1 | STALE_NEEDS_REVALIDATION | Move to M1; add priority/risk/state/type. |
| #61 Cockpit should default visible GPU to the llama-server GPU | NEEDS_REVIEW | Move to M6; add runtime/reporting labels after #106 normalization. |
| #55 Cockpit backend restart route has no local auth or CSRF guard while frontend is LAN-bound | HIGH_RISK_NEEDS_AUDIT_FIRST | Move to M0 or M6; add type:security, risk:high, state:needs-review after #106. |
| #53 Production Cockpit forms rely on placeholders and unlabeled icon controls | NEEDS_REVIEW | Move to M5; add reporting/accessibility/usability labels after #106. |
| #41 missing data | DUPLICATE_CANDIDATE | No direct milestone until #106 determines duplicate/stale/actionable. |
| #40 failure to request a search | DUPLICATE_CANDIDATE | No direct milestone until #106 determines duplicate/stale/actionable. |
