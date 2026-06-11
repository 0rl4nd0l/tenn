# tenn-auto-progress

Use this skill when Tenn needs Codex to choose the next safe unit of work from
GitHub issues and milestones without starting execution. The default mode is
read-only planning. GitHub writes, product/runtime/data work, commits, pushes,
and issue execution are forbidden unless a later task card and user approval
explicitly permit them.

## Purpose

`tenn-auto-progress` turns a broad instruction such as "make progress toward
production readiness" into a bounded planning packet:

- scan open issues, labels, and milestones with read-only GitHub commands
- rank safe candidate issues
- classify each candidate against Tenn autonomy mandates
- build compact context packs for the best candidates
- draft task-card packets for a verifier or owner to approve
- stop before source, product, runtime, data, GitHub, or commit mutation

## Default Boundaries

Allowed by default:

- read `AGENTS.md`, relevant repo-backed skills, task cards, and reports
- use `gh issue view`, `gh issue list`, `gh api`, and `gh pr list` read-only
- inspect local Git state with read-only Git commands
- write report-local planning artifacts under `reports/agent_jobs/...`
- draft task-card text inside report artifacts
- create or update this skill only when a task card allowlist permits it

Forbidden by default:

- commit, push, merge, rebase, cherry-pick, reset, stash, clean, or delete
- create, edit, label, comment on, close, or reopen GitHub issues or PRs
- mutate product/backend/frontend/runtime/extraction/data files
- mutate DB, Qdrant, news, memory, backfills, source PDFs, gold labels,
  extraction prompts, runtime/model/GPU config, production data, or services
- start services or run product/runtime/extraction validation
- execute a candidate issue instead of only planning it

## Workflow

1. Preflight:
   - verify `pwd`, branch, HEAD, upstream, origin, and dirty state
   - inspect active registry with
     `python3 scripts/agent_job_registry.py list-active --read-only --repo-root .`
   - validate the task card when one exists

2. Issue and milestone scan:
   - read the controlling issue first, usually issue #291 for this workflow
   - scan open ready issues and current milestones with byte-capped output
   - prefer labels over keyword search when search syntax or output is noisy
   - record unavailable or truncated evidence as `DATA_MISSING`

3. Candidate ranking:
   - prefer M0/control-plane/repo-hygiene/evaluation issues
   - prefer `state:ready`, `mode:audit`, `mode:safe-extension`, and low or
     medium risk labels
   - demote high-risk, product/runtime/data, security-sensitive, or ambiguous
     ownership issues
   - demote issues requiring GitHub writes, service starts, broad tests, or data
     mutation

4. Mandate classification:
   - `REPORT_AUTONOMY`: report-local audit, scan, classification, or packet only
   - `PRESERVATION_AUTONOMY`: preserve evidence without changing source truth
   - `LOW_RISK_REMEDIATION_AUTONOMY`: narrow control-plane/docs/tooling change
     only after task-card permission
   - `CONTROL_PLANE_PARKING_AUTONOMY`: park merge/branch/status evidence without
     merging or deleting
   - `PR_TRIAGE_AUTONOMY`: read-only PR classification unless GitHub writes are
     explicitly approved
   - `OWNER_APPROVAL_REQUIRED`: any source/product/runtime/data/GitHub/commit or
     destructive boundary

5. Context-pack creation:
   - produce a compact packet for each top candidate with issue metadata, why it
     matters, evidence paths, likely allowed files, hard stops, validation, and
     unknowns
   - do not paste large issue bodies when a focused summary is enough

6. Draft task-card creation:
   - draft task-card packets inside the report bundle
   - keep `allowed_files` exact and conservative
   - mark packets as drafts, not active execution contracts
   - require verifier/owner approval before converting a packet into a real task
     card or executing it

7. Stop states:
   - `DONE`: read-only planner packet complete and validated
   - `DONE_WITH_RISK`: useful packet exists but evidence is truncated or missing
   - `WAITING_ON_USER`: next useful step crosses an approval boundary
   - `BLOCKED_EXTERNAL`: required GitHub/repo/registry evidence is unavailable
   - `DATA_MISSING`: specific evidence was not available from safe reads

## Phase Model

- Phase 1: read-only planner. Create skill docs and report artifacts only.
- Phase 2: issue-to-task-card dry run. Generate a task-card packet for one
  selected issue and stop before execution.
- Phase 3: one-job execution. Execute exactly one approved task card, validate,
  and stop before commits or GitHub writes unless separately approved.

## Verifier Boundary

A verifier must be able to answer these before Phase 2 or Phase 3:

- Is the issue still open and still the same risk/lane/state?
- Is the candidate free of product/runtime/data mutation?
- Does the task-card allowlist cover every intended path exactly?
- Are registry and dirty-state checks clean enough for the work?
- Is the validation plan focused and non-destructive?
- Are GitHub writes, commits, and branch operations still disabled?
