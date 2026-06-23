# Control Plane PR State Refresh

last_verified_at: 2026-06-23T08:38:11Z
last_verified_commit: 1a0f1a03741d692089a0125ecb2f10691b8da597
verification_scope: PR #378, PR #380, PR #373, and PR #367 report-state refresh only
source_of_truth: live GitHub via `gh pr view`; local ancestry via `git merge-base --is-ancestor`

Historical report bundles are append-only evidence. They can contain status
phrases that were true before later PR merges. Use this refresh page when a
search result lands in an old report for the PRs below.

| PR | Current state | Current evidence | Historical report-state correction |
| --- | --- | --- | --- |
| #378 | MERGED | `gh pr view 378` reports merged at `2026-06-18T10:06:35Z` with merge commit `f44803bba049ea1d2cfe9341b0f9af4379736bdf`; that commit is in current canonical ancestry. | Treat older pre-merge skill-surface-trim readiness wording as stale historical state. |
| #380 | MERGED | `gh pr view 380` reports merged at `2026-06-22T00:04:48Z` with merge commit `4d62fec4e855b313ae89136e947510c627b9bcde`; that commit is in current canonical ancestry. | Treat older merge-gate, push-to-PR, or pending-PR wording as stale historical state. |
| #373 | MERGED | `gh pr view 373` reports merged at `2026-06-18T05:50:15Z` with merge commit `98e632996aae3bff82627a02b75e64cddd927420`; that commit is in current canonical ancestry. | Treat older validating, open, or not-yet-merged worker-bridge wording as stale historical state. |
| #367 | CLOSED, SUPERSEDED | `gh pr view 367` reports `CLOSED` with no merge commit. A live PR comment dated `2026-06-18T08:36:18Z` says PR #367 was superseded by merged PR #375 plus follow-up PR #377. | Treat older pre-supersession branch-continuation wording as stale historical state unless the task is explicitly auditing that archived branch. |

Supporting supersession evidence for PR #367:

| PR | Current state | Evidence |
| --- | --- | --- |
| #375 | MERGED | `gh pr view 375` reports merged at `2026-06-18T08:21:31Z` with merge commit `acb7e9a7df6a9b75d14beff16c750693a4aab5e6`. |
| #377 | MERGED | `gh pr view 377` reports merged at `2026-06-18T08:35:49Z` with merge commit `bae8eda25633cf651849c5681d7ffcb00160fbf9`. |

## Search Guidance

When old report bundles under `reports/agent_jobs/` disagree with this page,
do not rewrite those historical reports unless a separate archival-banner task
explicitly allows it. Prefer citing this page, live GitHub state, and current
canonical ancestry.

Refresh this page by rerunning:

```bash
gh pr view 378 --json number,state,mergedAt,mergeCommit,title,headRefName,baseRefName,url
gh pr view 380 --json number,state,mergedAt,mergeCommit,title,headRefName,baseRefName,url
gh pr view 373 --json number,state,mergedAt,mergeCommit,title,headRefName,baseRefName,url
gh pr view 367 --json number,state,mergedAt,mergeCommit,title,headRefName,baseRefName,url
```
