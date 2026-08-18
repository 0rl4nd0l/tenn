# Classification Matrix

| Field | `github_outstanding_issue_creation_v1_20260526.md` | `codex_nightly_lockup_report_v1_20260526.md` |
| --- | --- | --- |
| Current git state before audit | Untracked task card; ignored report bundle | Tracked task card; tracked report bundle |
| Primary classification | `ALREADY_COMPLETED` | `ALREADY_COMPLETED` |
| Secondary note | Still needed as provenance for already-created GitHub issues | Still needed as evidence while #115 remains open |
| Job ID | `github_outstanding_issue_creation_v1_20260526` | `codex_nightly_lockup_report_v1_20260526` |
| Lane | `Evaluation` | `Reporting` |
| Requested primary lane | `Repo Hygiene` | `Repo Hygiene` |
| Owner | `Codex` | `Codex` |
| Output directory | `reports/agent_jobs/github_outstanding_issue_creation_v1_20260526` | `reports/agent_jobs/codex_nightly_lockup_report_v1_20260526` |
| Intended GitHub action | Create missing issues only after duplicate search | None; report-only |
| GitHub result | Created #94 and #95 | Related open tracker #115 |
| Duplicate status | Not duplicate; completed issue-creation task with durable evidence gap | Not duplicate; already tracked local task/report |
| Supersession status | Not superseded | Not superseded |
| Required report path present | Yes | Partially; required `diff-check.json` is absent |
| Preservation decision | Preserve and commit card plus report artifacts | No new preservation needed |
| Safe next action | Commit durable evidence only; do not rerun issue creation | Decide #115 closeout or runner follow-up separately |
| Cleanup recommendation | Do not delete | Do not delete |

## Open-Issue Evidence

- #94 exists and remains open, but it targets the older
  `a2m_backend_reload_news_status_activation_smoke_v1_20260525.md` and
  `automation_audit_issue_preservation_v1_20260525.md` task cards, not the
  current `github_outstanding_issue_creation_v1_20260526.md` card.
- #95 exists and remains open as the source-drawer semantics issue created by
  `github_outstanding_issue_creation_v1_20260526`.
- #115 exists and remains open for the nightly lock-up report decision.
- #111 is closed and should not be started as the next issue-resolution target.
