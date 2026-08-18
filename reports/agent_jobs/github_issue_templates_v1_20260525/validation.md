# Validation

## Results

- PASS: YAML parsed for all issue templates:
  - `.github/ISSUE_TEMPLATE/config.yml`
  - `.github/ISSUE_TEMPLATE/tenn_task.yml`
  - `.github/ISSUE_TEMPLATE/tenn_bug_regression_seed.yml`
  - `.github/ISSUE_TEMPLATE/tenn_audit_finding.yml`
  - `.github/ISSUE_TEMPLATE/tenn_followup_remediation.yml`
  - `.github/ISSUE_TEMPLATE/tenn_branch_merge_review.yml`
- PASS: required shared fields are present and required in each issue form:
  - lane
  - mode
  - priority
  - risk
  - type
  - milestone recommendation
  - source evidence
  - why it matters
  - required task card path
  - required report path
  - allowed files / surfaces
  - forbidden files / surfaces
  - validation
  - hard stops
  - definition of done
  - DATA_MISSING
  - follow-up / parking / dependency links
- PASS: bug/regression seed template requires blast-radius assessment.
- PASS: bug/regression seed template requires root-cause vs workaround.
- PASS: audit finding template requires follow-up policy.
- PASS: follow-up remediation template requires source issue/report link and
  `FOLLOWUP_REQUIRED` / `FOLLOWUP_RECOMMENDED` classification.
- PASS: branch/merge review template requires the requested branch
  classification values.
- PASS: form label and milestone options use only the activated issue-system
  labels and M0-M6 milestone recommendations.
- PASS: `python3 -m json.tool reports/agent_jobs/github_issue_templates_v1_20260525/status.json`.
- PASS: `python3 scripts/agent_job_contract.py validate docs/agent_tasks/github_issue_templates_v1_20260525.md`.
- PASS: `python3 scripts/agent_job_registry.py check-overlap docs/agent_tasks/github_issue_templates_v1_20260525.md --repo-root .`.
- PASS: `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/github_issue_templates_v1_20260525.md`.
- PASS: `git diff --check`.

## GitHub Mutation

No live GitHub issue, PR, comment, label, milestone, or Project mutation was
performed. No `gh` mutation command or GitHub connector mutation was used for
this task.

## Notes

The task was moved into a clean isolated worktree because the canonical
`/home/l4nd0/tenn` checkout already contained unrelated untracked task cards
outside this task's allowlist.
