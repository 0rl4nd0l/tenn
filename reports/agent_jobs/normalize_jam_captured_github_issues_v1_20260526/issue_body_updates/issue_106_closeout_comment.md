#106 normalization complete.

Report: `reports/agent_jobs/normalize_jam_captured_github_issues_v1_20260526/`

Outcome:

- #40 classified `DATA_MISSING` with adjacent links to #83, #104, #107, and #116.
- #41 classified `DATA_MISSING` with links to #86, #116, #83, and #114.
- #53 normalized in place as a Cockpit accessible-form-controls audit/remediation candidate.
- #55 normalized in place as a high-risk restart-route guard/security audit.
- #61 normalized in place as a runtime/reporting honesty issue for active `llama-server` GPU visibility.

Validation performed:

- Read #106 and all five target issues.
- Checked Jam metadata/screenshots for #40 and #41; console evidence remained `DATA_MISSING`.
- Ran duplicate/supersession searches for each target.
- Applied existing labels and milestones only to the target issues.
- Read back every edited issue and confirmed labels/milestones.
- Produced before/after matrix and JSON report artifacts.
- Ran task-card validation/check-diff, JSON validation, `git diff --check`, final registry read-only check, and final git status.

No product/backend/frontend/runtime code, data stores, memory stores, parser routing, prompts, gold labels, model/runtime/GPU/service config, PRs, branches, or unrelated issues were mutated.
