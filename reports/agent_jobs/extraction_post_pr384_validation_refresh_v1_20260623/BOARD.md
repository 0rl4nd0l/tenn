# Review Board

## Scope

Decide what to do after the post-PR384 validation refresh on canonical
`e402bf38`.

## Architect

- Evidence inspected: task card, PR #384 merge state, replay validation JSON,
  focused pytest reports, post-merge matrix.
- Finding: PR #384's JAY recovery is stable on canonical, and the validation
  environment remediation successfully removed the pytest blocker for focused
  tests.
- Uncertainty: DXC and WHC row-level source evidence was not collected in this
  run.
- Risk: starting a product fix from replay outputs alone would violate the
  source-row proof policy.
- Recommended action: proceed to a row-proof packet, not product code.

## Skeptic / Red Team

- Evidence inspected: WHC/EDU replay outputs and row refs.
- Finding: WHC/EDU passing means expected failure, not accepted extraction
  quality. It proves fail-closed behavior, not corrected values.
- Uncertainty: some guard cases still contain `unknown` row refs for derived
  or cash-flow metrics, which may deserve later provenance hardening.
- Risk: overclaiming "all row issues fixed" from green replay status.
- Recommended action: explicitly separate validation gates from row repair.

## Product / Value

- Evidence inspected: residual list in the matrix.
- Finding: the next useful production-readiness work is to retire or confirm
  the remaining DXC/WHC residuals with exact row evidence.
- Uncertainty: PR #340 may already contain useful WHC openability evidence, but
  it is not a duplicate validation refresh.
- Risk: spending another sprint on report-only artifacts without a path to a
  narrow source-proven fix.
- Recommended action: create one bounded row-proof lane that can either unlock
  a narrow fix or close with `NO_FIX_PROVEN`.

## Validation / Test

- Evidence inspected: pytest reports, replay `validation.json`,
  side-effect audits, replay result summaries.
- Finding: the two prior blockers are closed for this sample: focused pytest
  ran via overlay, and the full compatible guard plus WHC/EDU replays
  completed with side effects clean.
- Uncertainty: this is not a broad count sample or full-universe extraction.
- Risk: denominator drift if these 9 cases are presented as broad accuracy.
- Recommended action: use these results as regression evidence only.

## Repo Hygiene / Git Guard

- Evidence inspected: branch state, ledger validation, registry check, duplicate
  PR/issue search, worktree status.
- Finding: no active jobs and no duplicate open PR for this validation refresh.
  Live ledger file is missing; committed ledger is valid. PR #340 is related
  WHC evidence work but not duplicate.
- Uncertainty: live ledger absence remains a control-plane data-missing signal.
- Risk: report artifacts are ignored by default and need force-add if this
  branch is published.
- Recommended action: continue report-only locally or force-add report artifacts
  only if a PR is requested.

## Domain Expert

- Evidence inspected: JAY row refs, WHC/EDU mixed-unit diagnostics, residual
  DXC/WHC status.
- Finding: JAY is genuinely source-bound to `Net Revenue` rows. DXC cannot map
  `net operating income` to canonical `ebit` without industry/source context.
  WHC scale repair requires explicit source scale rows or table headers.
- Uncertainty: source PDFs may contain the needed scale evidence, but this run
  did not inspect them.
- Risk: broad metric-label mapping could contaminate banking, insurance, or
  operational-income contexts.
- Recommended action: row-proof first, code second.

## Chair

- Root problem: validation incompleteness and row-proof gaps after PR #384.
- Are we solving the real root problem? Yes for validation; not yet for row
  mapping.
- Are we overfitting to one document? The replay set covers JAY, guard cases,
  and WHC/EDU regressions, but row repair must remain document/source-bound.
- Are we trapped in report-only loops? Not if the next row-proof lane has a
  hard stop and can unlock a specific code fix or close `NO_FIX_PROVEN`.
- Would a class-based approach be better? Yes: address row-proof classes
  (`metric_label_mismatch`, `scale_unknown`) rather than another one-off PDF
  patch.
- Production-readiness value: highest next value is exact source-row proof for
  DXC and WHC, because validation blockers are now closed.
- Decision: proceed with a bounded row-proof packet; no product code until that
  packet proves a narrow fix.

## Minority Objection

Objection: since all replays passed, proceed directly to a WHC or DXC product
fix.

Disposition: rejected. Replay pass proves the validation harness and expected
case behavior. It does not prove that DXC `net operating income` is canonical
`ebit`, or that WHC scale can be safely repaired without source-row scale
metadata.
