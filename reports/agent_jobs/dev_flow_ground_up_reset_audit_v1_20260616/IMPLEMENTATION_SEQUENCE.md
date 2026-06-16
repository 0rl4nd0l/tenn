# Implementation Sequence

## Shot 1: Design And Wrappers

1. Create task card for dev-flow wrappers only.
2. Add instruction-only repo skills:
   - `tenn-issue`
   - `tenn-review-board`
   - `tenn-fix`
   - `tenn-worker`
   - `tenn-explain`
   - `tenn-code-reviewer`
   - `tenn-improve-codebase-architecture`
   - `tenn-git-guard`
3. Do not delete or edit existing host skills.
4. Make wrappers point to existing skills/scripts.
5. Add example artifact templates.
6. Validate task card, registry read-only, `git diff --check`, and path guard.

## Shot 2: Backend Guard Integration

1. Add a report-only Git guard script or wrapper only if approved.
2. Make `/issue`, `/review-board`, and `/fix` call Git guard preflight.
3. Add worktree/branch/PR relationship output.
4. Add worker result enforcement.
5. Keep cleanup disabled.

## Shot 3: Trial Run

1. Run `/issue` on issue #78 or #291 without GitHub writes.
2. Produce `ISSUE.md`, `MILESTONES.md`, context pack, and `NEXT_GOAL.md`.
3. Review whether the command reduced operator burden.

## Shot 4: Controlled Execution

1. Run `/fix` on one low-risk control-plane issue.
2. Use one worker if useful.
3. Run focused validation and code-reviewer.
4. Stop before PR unless approved.

## Success Criteria

- Orlando can use fewer commands.
- Git Hygiene is automatic and quiet.
- Report-only loops end in decisions.
- Workers cannot leave invisible dirt.
- Product/runtime/extraction boundaries stay explicit.
