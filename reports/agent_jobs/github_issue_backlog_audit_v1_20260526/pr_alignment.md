# PR Alignment

## Open PRs

All 21 open PRs lacked explicit issue references in available PR body/comment metadata. This is a backlog-health issue because PRs can land or stall outside the GitHub Issue backlog.

High-risk PRs:

- #39: draft, `UNSTABLE`, 346 changed files, current branch PR head; local branch is ahead of origin by two commits not reflected in remote PR state.
- #19: `DIRTY`, 532 changed files, no issue linkage.
- #22: `DIRTY`, 37 changed files, no issue linkage.
- #24 and #30: `UNSTABLE`, no issue linkage.
- #23/#25/#31/#32/#33/#34: likely duplicate/superseded documentation-startup PR cluster; consolidate before merge.

| PR | Draft | Merge State | Head | Base | Changed Files | Issue Refs | Audit Risk |
| --- | --- | --- | --- | --- | --- | --- | --- |
| #39 [codex] integrate trust foundation next phase | True | UNSTABLE | migration/clean-runtime-baseline-reconstruct-v1 | migration/clean-runtime-baseline-reconstruct-base-36130cbd | 346 | none | NO_EXPLICIT_ISSUE_LINK, MERGE_OR_CI_RISK, LARGE_PR, CURRENT_BRANCH_REMOTE_BEHIND_LOCAL_AHEAD_COMMITS |
| #34 docs: align backend startup and API documentation | True | CLEAN | cursor/technical-documentation-updates-aaac | main | 3 | none | NO_EXPLICIT_ISSUE_LINK, DOCS_DUPLICATE_CLUSTER |
| #33 Document agent startup wrappers and price API | True | CLEAN | cursor/documentation-automation-system-a9ff | main | 4 | none | NO_EXPLICIT_ISSUE_LINK, DOCS_DUPLICATE_CLUSTER |
| #32 Clarify canonical backend startup docs | True | CLEAN | cursor/codebase-documentation-alignment-475f | main | 3 | none | NO_EXPLICIT_ISSUE_LINK, DOCS_DUPLICATE_CLUSTER |
| #31 docs: clarify canonical agent startup | True | CLEAN | cursor/documentation-automation-system-906e | main | 2 | none | NO_EXPLICIT_ISSUE_LINK, DOCS_DUPLICATE_CLUSTER |
| #30 hold(c2): cockpit routing regression tests (blocked by baseline import issue) | False | UNSTABLE | cloud/c2-cockpit-routing-regression-tests-20260421-122136 | plan/ideation-combinations-2026-04-11 | 2 | none | NO_EXPLICIT_ISSUE_LINK, MERGE_OR_CI_RISK |
| #25 docs: align canonical startup docs with wrapper contracts | True | CLEAN | cursor/codebase-documentation-alignment-f3de | main | 2 | none | NO_EXPLICIT_ISSUE_LINK, DOCS_DUPLICATE_CLUSTER |
| #24 Add date filters to QualContextReader; harden preboot routing and extraction runtime startup; improve llama-server launcher and add tests | False | UNSTABLE | codex/fix-issues-from-pr-review-comments | cloud/session-20260319 | 8 | none | NO_EXPLICIT_ISSUE_LINK, MERGE_OR_CI_RISK |
| #23 docs: align canonical startup and validation runbooks | True | CLEAN | cursor/codebase-documentation-alignment-d407 | main | 3 | none | NO_EXPLICIT_ISSUE_LINK, DOCS_DUPLICATE_CLUSTER |
| #22 Bootstrap reproducible PDF extraction environment (two venvs + audit) | True | DIRTY | cursor/provably-correct-financial-pdf-extraction-system-b0c9 | cloud/session-20260319 | 37 | none | NO_EXPLICIT_ISSUE_LINK, MERGE_OR_CI_RISK |
| #19 Recovery/reconstruction | False | DIRTY | recovery/reconstruction | main | 532 | none | NO_EXPLICIT_ISSUE_LINK, MERGE_OR_CI_RISK, LARGE_PR |
| #17 feat: add /api/chat endpoint with LLM agent loop and tool calling | True | CLEAN | cursor/development-environment-setup-8547 | main | 4 | none | NO_EXPLICIT_ISSUE_LINK |
| #16 docs: align ingestion runbooks with current runtime behavior | True | CLEAN | cursor/codebase-documentation-alignment-f3f3 | main | 5 | none | NO_EXPLICIT_ISSUE_LINK |
| #15 Add .venv to .gitignore and Cockpit TUI instructions to AGENTS.md | True | CLEAN | cursor/development-environment-setup-e9b8 | main | 3 | none | NO_EXPLICIT_ISSUE_LINK |
| #14 Harden script runtime, extraction accounting, zero-row quality gate, and test stubs | False | CLEAN | codex/locate-last-hit-update-date | main | 8 | none | NO_EXPLICIT_ISSUE_LINK |
| #13 Add optimization plan and codebase review doc (2026-03-18) | False | CLEAN | codex/conduct-code-review-and-optimization-plan | main | 1 | none | NO_EXPLICIT_ISSUE_LINK |
| #12 System bug scan hardening: CLIs, stubs, and quality gates | True | CLEAN | cursor/system-bug-scan-c80b | main | 6 | none | NO_EXPLICIT_ISSUE_LINK |
| #11 Environment update status | True | CLEAN | cursor/environment-update-status-ef1a | cursor/cockpit-agent-testing-1c9c | 2 | none | NO_EXPLICIT_ISSUE_LINK |
| #10 Deep analysis environment | True | CLEAN | cursor/deep-analysis-environment-f6f1 | cursor/cockpit-agent-testing-1c9c | 16 | none | NO_EXPLICIT_ISSUE_LINK |
| #9 Cockpit agent testing | True | CLEAN | cursor/cockpit-agent-testing-1c9c | main | 2 | none | NO_EXPLICIT_ISSUE_LINK |
| #1 Add YouTube transcript ingest workflow and docs | False | DIRTY | codex/develop-youtube-transcript-scraper | main | 4 | none | NO_EXPLICIT_ISSUE_LINK, MERGE_OR_CI_RISK |

## Recently Closed PRs

Reviewed 15 closed PRs returned by `gh pr list --state closed --limit 20`.

| PR | State | Merged At | Head | Base |
| --- | --- | --- | --- | --- |
| #35 Make Sloppy Fix manual-only | MERGED | 2026-05-21T11:03:57Z | safe/sloppy-fix-manual-only-main-pr-v1-20260521 | main |
| #29 merge(c5-multipass-extraction-performance-profile-20260421-122136): integrate validated cloud task | MERGED | 2026-04-21T03:04:34Z | cloud/c5-multipass-extraction-performance-profile-20260421-122136 | plan/ideation-combinations-2026-04-11 |
| #28 merge(c4-system-contract-conformance-matrix-20260421-122136): integrate validated cloud task | MERGED | 2026-04-21T03:04:29Z | cloud/c4-system-contract-conformance-matrix-20260421-122136 | plan/ideation-combinations-2026-04-11 |
| #27 merge(c3-extraction-truth-real-gold-eval-20260421-122136): integrate validated cloud task | MERGED | 2026-04-21T03:04:24Z | cloud/c3-extraction-truth-real-gold-eval-20260421-122136 | plan/ideation-combinations-2026-04-11 |
| #26 merge(c1-extraction-quality-gap-audit-20260421-122136): integrate validated cloud task | MERGED | 2026-04-21T03:04:19Z | cloud/c1-extraction-quality-gap-audit-20260421-122136 | plan/ideation-combinations-2026-04-11 |
| #21 QA harness: make cockpit boot work in cloud | MERGED | 2026-03-19T08:07:38Z | cursor/cloud-agent-testing-framework-9aef | cloud/session-20260319 |
| #20 Stabilize agent execution: canonical entrypoints + portable paths | MERGED | 2026-03-19T03:17:12Z | cursor/agent-usability-audit-framework-cbc1 | main |
| #18 Add deterministic news intelligence pipeline and Cockpit access APIs | CLOSED | not merged | cursor/news-intelligence-pipeline-f490 | main |
| #8 Development environment setup | MERGED | 2026-03-01T05:25:21Z | cursor/development-environment-setup-af53 | main |
| #7 ci: bind fix job to OPEN env and add OpenAI auth preflight | MERGED | 2026-02-28T00:41:09Z | wip/rehydrated-2026-02-27 | main |
| #6 ci: normalize OPENAI_API_KEY for codex workflows | MERGED | 2026-02-28T00:17:07Z | wip/rehydrated-2026-02-27 | main |
| #5 ci: create CODEX_HOME in codex preflight | MERGED | 2026-02-28T00:06:59Z | wip/rehydrated-2026-02-27 | main |
| #4 Wip/rehydrated 2026 02 27 | MERGED | 2026-02-27T23:53:26Z | wip/rehydrated-2026-02-27 | main |
| #3 Wip/rehydrated 2026 02 27 | MERGED | 2026-02-27T23:20:18Z | wip/rehydrated-2026-02-27 | main |
| #2 Wip/rehydrated 2026 02 27 | MERGED | 2026-02-27T23:09:52Z | wip/rehydrated-2026-02-27 | main |
