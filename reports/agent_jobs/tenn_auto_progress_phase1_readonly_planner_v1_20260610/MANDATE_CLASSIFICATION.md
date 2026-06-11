# Mandate Classification

## Mandates Used

| Mandate | Applies Here | Allowed in Phase 1 | Stop Boundary |
| --- | --- | --- | --- |
| `REPORT_AUTONOMY` | Yes | Read-only scans, report bundle, rankings, context packs | Source/product/runtime/data/GitHub mutation |
| `ISSUE_291_READONLY_PLANNER` | Yes | Skill skeleton, issue/milestone scan, draft packets | Execution of any issue |
| `PRESERVATION_AUTONOMY` | Limited | Preserve evidence in report artifacts | Changing historical artifacts |
| `GENERATED_CLEANUP_AUTONOMY` | No | None | Any cleanup requires separate task card |
| `LOW_RISK_REMEDIATION_AUTONOMY` | Not yet | Skill docs only because task card allowed them | Product or runtime files |
| `CONTROL_PLANE_PARKING_AUTONOMY` | Not yet | May propose parking later | Merge, rebase, branch deletion |
| `PR_TRIAGE_AUTONOMY` | Read-only only | None beyond issue evidence | PR comments, labels, closes, merges |
| `WORKSTREAM_LEDGER_AUTONOMY` | Report-only | Candidate ledger in this bundle | Durable ledger mutation outside allowlist |
| `OWNER_APPROVAL_REQUIRED` | Yes for Phase 2+ | Approval manifest only | Real task card creation/execution, commits, GitHub writes |

## Candidate Mapping

| Issue | Phase 1 Mandate | Later Mandate Needed |
| --- | --- | --- |
| #291 | `REPORT_AUTONOMY`, `ISSUE_291_READONLY_PLANNER` | Owner approval for Phase 2 dry-run continuation |
| #281 | `REPORT_AUTONOMY` context pack only | Phase 2 issue-to-card dry run; execution requires task-card approval |
| #234 | `REPORT_AUTONOMY` context pack only | Report-only classification or owner-approved artifact decision |
| #139 | `REPORT_AUTONOMY` context pack only | Owner decision on restore vs retire |
| #282 | `REPORT_AUTONOMY` only | Product-boundary review before execution |
| #140 | `REPORT_AUTONOMY` only | Filesystem cleanup approval |
