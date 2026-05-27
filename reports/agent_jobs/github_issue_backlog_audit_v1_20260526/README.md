# GitHub Issue Backlog Audit v1 - 20260526

Mode: audit_only / issue_inventory. No GitHub, product, runtime, data, branch, label, milestone, or PR state was mutated.

## Summary

- GitHub target confirmed: `0rl4nd0l/tenn` (https://github.com/0rl4nd0l/tenn).
- Repo root: `/home/l4nd0/tenn-nvme-clean-baseline-reconstruct-v1` via `/home/l4nd0/tenn-runtime`.
- Branch/HEAD: `migration/clean-runtime-baseline-reconstruct-v1` at `3725591cf76ec1a56428a476e23dbd1ebc4050fc`.
- Remote tracking branch: `origin/migration/clean-runtime-baseline-reconstruct-v1` at `8635833b7d7359ed55daf0495eb49c5457bab91d`.
- Current branch is ahead of origin by 2 commits: `a7da52d2` and `3725591c`. These local commits carry nightly lock-up/news repair evidence tied to #112/#114/#115, so they are branch work at risk until reviewed/published.
- Open issues: 53. Closed issues reviewed: 31. Open PRs: 21. Closed PRs reviewed: 15.
- Labels: 59. Milestones: 7. Worktrees observed: 248, including 22 prunable entries.

## Preflight

- `docs/process/github_issue_system_protocol.md`: FOUND.
- `.github/ISSUE_TEMPLATE/`: FOUND with Tenn task, audit finding, follow-up remediation, branch review, bug/regression seed, and config forms.
- `docs/process/codex_skill_sources/github_issue_system/`: FOUND with closeout, finder, and resolution-reviewer skill mirrors.
- Registry read-only initially returned `active_jobs: []`. After task-card validation, registry read-only showed one active Financial Truth job, `extraction_contract_parity_guard_v1_20260526`, in `/home/l4nd0/tenn-extraction-contract-parity-guard-v1-20260526`; no file overlap with this report-only bundle was apparent.
- Pre-existing dirty state before this task: `docs/agent_tasks/github_outstanding_issue_creation_v1_20260526.md` was already untracked and unrelated. It was not touched.

## Classification Counts

| Classification | Count |
| --- | --- |
| BLOCKED | 5 |
| DATA_MISSING | 5 |
| DUPLICATE_CANDIDATE | 2 |
| HIGH_RISK_NEEDS_AUDIT_FIRST | 2 |
| NEEDS_FOLLOWUP | 8 |
| NEEDS_REVIEW | 4 |
| PARKED | 3 |
| READY_TO_RUN | 22 |
| STALE_NEEDS_REVALIDATION | 2 |

## Highest Risk Findings

1. Branch visibility risk: local commits `a7da52d2` and `3725591c` are ahead of origin and tied to #112/#114/#115. They are visible in issue comments but not yet remote-integrated.
2. PR alignment risk: all 21 open PRs lack explicit `#issue` references in PR body/comments from available metadata; PR #39 is draft/unstable and is also the current branch PR head.
3. Label/template hygiene risk: 8 open issues lack milestones, and 10 open issues need some label/template cleanup.
4. Closed audit safety risk: no high-confidence buried unresolved finding was confirmed, but #64 closed a worktree/task-card hygiene audit without explicit follow-up refs in the closeout comment; current #94/#115 partially cover the later risk.
5. M5 is overloaded with 16 open issues, mostly UI/usability. M0 should run first to clean control-plane visibility before broad M5 execution.

## Recommended Next Codex Goal

Run #106 first: `raw_jam_issue_contract_normalization_v1_20260526`, audit-only unless explicitly approved for GitHub metadata updates. It converts the most ambiguous raw issues (#40/#41/#53/#55/#61) into task-card-ready backlog items or duplicate/stale decisions, and it improves the safety of any later closeout.
