# Regression Adjudication

last_verified_at: 2026-06-29
verification_scope: control-plane workflow only; no product, runtime, data, or
extraction functionality was proven by this document
owner: Codex
source_of_truth_files:
- AGENTS.md
- docs/README.md
- docs/dev_flow/SKILLS_SURFACE.md
- .agents/skills/tenn-fix/SKILL.md
- .agents/skills/tenn-review-board/SKILL.md

## Purpose

Use this workflow when a bug, failure, metric, gate, route, daemon behavior, or
extraction result appears to be broken again after Orlando believed it was
fixed.

The goal is to classify the failure before coding. Do not patch from the
headline symptom until the branch, canonical lineage, old fix, current repro,
test coverage, and runtime proof status are explicit.

## Trigger Phrases

Run this workflow when the prompt includes language like:

- "we fixed this already"
- "broken again"
- "regressed"
- "keeps coming up"
- "why is this still broken"
- "shouldn't this be fixed"
- "same bug"
- a surprising count, score, pass rate, daemon status, or evaluation result
  after a claimed fix

## Required Preflight

Before interpreting the failure, capture current target identity:

```bash
pwd
git branch --show-current
git rev-parse HEAD
git remote -v
git rev-parse --abbrev-ref --symbolic-full-name @{u}
git status --short --untracked-files=all
python3 /home/l4nd0/.agents/skills/tenn-git-guard/scripts/tenn_git_guard.py preflight --repo-root <repo-root> --topic "<bug-or-path>" --json
```

If dirty state overlaps the suspected files, stop or move to a clean sibling
worktree before coding. If the target is not the intended branch, classify the
case as `STALE_BRANCH` until proven otherwise.

## Classifications

Choose one primary classification and list secondary contributing factors when
useful.

| Classification | Meaning | Next action |
| --- | --- | --- |
| `STALE_BRANCH` | The current checkout, runtime path, artifact root, or service workdir is not the branch or surface that contains the alleged fix. | Re-target to current canonical or the active runtime surface before coding. |
| `FIX_NOT_IN_CANONICAL` | The old fix exists on a branch, PR, report, or stale worktree, but is not in the selected canonical path. | Adopt, review, merge, park, or supersede the existing work; do not reimplement first. |
| `NARROW_FIX_ONLY` | The old fix covered one document, route, input, parser case, or runtime wrapper, but the current breakage is a broader class. | Convert to a failure-class task and add a class-level gate before broad claims. |
| `RUNTIME_NOT_PROVEN` | Code, tests, PRs, reports, or artifacts changed, but the intended live output was not proven fresh or changed. | Run the AGENTS.md Runtime Functionality Proof table before claiming fixed. |
| `TEST_GAP` | No durable test, harness, fixture, eval, smoke, or gate would have failed when the issue returned. | Add the smallest permanent regression gate before or with the fix. |
| `NEW_FAILURE_CLASS` | The symptom resembles an old bug, but root cause, source class, route class, document class, or runtime surface is different. | Treat it as new scoped work; do not call the old fix failed unless evidence proves equivalence. |
| `TRUE_REGRESSION` | The same contract passed on the same canonical/runtime surface and now fails after a newer change. | Use red/green repair: preserve the failing repro, identify the introducing change when feasible, patch narrowly, rerun the gate. |
| `DATA_MISSING` | Required current evidence, old-fix lineage, repro, artifact, runtime proof, or branch ancestry cannot be verified. | Stop or continue only with labeled read-only evidence gathering. |

## Required Evidence Packet

An adjudication packet can be a report section, issue comment draft, board
input, or fix-plan section. It must include:

- `target_identity`: repo root, branch, HEAD, upstream, canonical head, dirty
  state, guard decision.
- `alleged_old_fix`: PR, commit, branch, report, task card, issue, or handoff
  where the fix was claimed.
- `canonical_lineage`: whether the old fix is an ancestor of the selected
  canonical base, or `DATA_MISSING`.
- `current_repro`: exact command/query/input, expected result, actual result,
  exit status, and artifact paths.
- `scope_comparison`: whether the old and current failures share root cause,
  route, source class, document class, runtime path, and output surface.
- `permanent_gate`: test, fixture, harness, smoke, eval, or proof command that
  will fail if this issue returns.
- `runtime_functionality_proof`: required for daemon, runtime, ingestion,
  extraction, automation, collector, scheduler, service, or pipeline claims;
  otherwise `not_required`.
- `classification`: one primary value from the table above.
- `next_action`: implement, adopt existing work, run runtime proof, create an
  issue, park, supersede, ask owner, or stop with `DATA_MISSING`.

## Runtime-Like Work

For daemon, runtime, ingestion, extraction, automation, collector, scheduler,
service, or pipeline work, do not treat a green test, successful PR, fresh log,
timer, report, or artifact as proof that the system works.

Use the Runtime Functionality Proof table from `AGENTS.md`. If intended live
output freshness, delta, or gate status is missing, classify the case as
`RUNTIME_NOT_PROVEN` or `DATA_MISSING`, not `TRUE_REGRESSION`.

## Implementation Rules

- Do not code until a primary classification exists.
- Do not reimplement work that already exists in an open PR, merged canonical
  path, stale-preserve branch, or owner-boundary surface.
- Do not weaken, skip, xfail, or delete the existing gate to make the
  resurfacing bug disappear.
- For `TEST_GAP`, add or name the permanent gate before claiming the fix.
- For `NARROW_FIX_ONLY` or `NEW_FAILURE_CLASS`, avoid broad readiness claims
  until a class-level gate exists.
- For `TRUE_REGRESSION`, use a narrow red/green loop and record the command
  that failed before the patch and passed after the patch.

## Output Template

```markdown
## Regression Adjudication

- target_identity: VERIFIED | DATA_MISSING
- alleged_old_fix: VERIFIED | DATA_MISSING
- canonical_lineage: VERIFIED | DATA_MISSING
- current_repro: VERIFIED | DATA_MISSING
- scope_comparison: same | broader | different | DATA_MISSING
- permanent_gate: present | added | missing | DATA_MISSING
- runtime_functionality_proof: WORKING | PARTIAL | BROKEN | DATA_MISSING | not_required
- classification: STALE_BRANCH | FIX_NOT_IN_CANONICAL | NARROW_FIX_ONLY | RUNTIME_NOT_PROVEN | TEST_GAP | NEW_FAILURE_CLASS | TRUE_REGRESSION | DATA_MISSING
- next_action: <one concrete action>
```

## Closeout

Close with one of these outcomes:

- `ADOPT_EXISTING_WORK`
- `RETARGET_TO_CANONICAL`
- `ADD_REGRESSION_GATE`
- `IMPLEMENT_NARROW_FIX`
- `RUN_RUNTIME_PROOF`
- `CREATE_OR_UPDATE_ISSUE`
- `PARK_OR_SUPERSEDE`
- `WAITING_ON_USER`
- `DATA_MISSING`

Do not close with a vague "fixed again" claim. The closeout must name the
classification, the gate or proof used, files touched, validation result, and
the next operational action.
