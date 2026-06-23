# Review Board: Broad Extraction Accuracy

## Scope

Explain why Tenn cannot yet claim broad accurate extraction and decide the next
highest-value action.

## Architect

- Evidence inspected: issues #73, #96, #97; post-PR384 matrix; prior real-gold
  and metric-truth reports.
- Finding: the intended architecture is correct but incomplete. The pipeline
  needs document-class routing, source-row evidence, validation gates, and
  scorecard promotion. Current work has improved slices, not the full system.
- Uncertainty: current DB coverage denominator is `DATA_MISSING` in this run.
- Risk: implementing row fixes before measuring current coverage can optimize
  the wrong layer.
- Recommended action: measurement-first sprint, then failure-class fixes.

## Skeptic / Red Team

- Evidence inspected: green replay results and residual list.
- Finding: green no-write replays are regression proof, not broad accuracy
  proof. WHC/EDU passing means they failed closed as expected, not that values
  are corrected.
- Uncertainty: some older artifacts omit row refs and cannot be trusted as
  source-bound truth.
- Risk: a broad prompt/ontology change can make bad metrics look cleaner.
- Recommended action: require source rows and scorecards before code changes.

## Product / Value

- Evidence inspected: open trackers and residuals.
- Finding: the highest product value is not another one-off PDF fix. It is a
  current failure matrix that tells us which class blocks the most accurate
  extraction coverage.
- Uncertainty: exact top blockers may change after fresh #96/#97 refresh.
- Risk: shipping partial extraction as "accurate" creates analyst trust damage.
- Recommended action: produce the scorecard and runtime coverage baseline, then
  fix the top ranked class.

## Validation / Test

- Evidence inspected: post-PR384 validation artifacts and issue #97.
- Finding: validation tooling is now capable enough for focused work, but broad
  extracted-payload scoring remains open.
- Uncertainty: no current count-24/count-32/full-corpus score was run here.
- Risk: denominator drift and cherry-picked pass rates.
- Recommended action: trace raw/captured -> candidate -> accepted -> evaluated
  -> reported for the approved fixture/corpus profile.

## Repo Hygiene / Git Guard

- Evidence inspected: branch state, registry, ledger, PR/issue searches.
- Finding: live ledger is `DATA_MISSING`; committed ledger validates. One
  active control-plane job exists in another worktree. Related open work exists
  (#73/#96/#97, PR #340, PR #131), but no duplicate implementation was started
  by this explain task.
- Uncertainty: current branch has a prior untracked validation task card.
- Risk: starting a new implementation here would overlap existing trackers.
- Recommended action: report-only explanation now; next implementation should
  use a fresh task card from current origin.

## Domain Expert

- Evidence inspected: DXC/WHC residuals, JAY fix, metric-truth reports.
- Finding: accurate financial extraction is mostly a source-evidence problem:
  metric meaning, scale, period, and row provenance must be proven per document
  class. JAY had exact `Net Revenue` rows; DXC and WHC still need row proof.
- Uncertainty: WHC source may contain enough scale evidence, but it has not
  been proven in the current row-proof lane.
- Risk: mapping labels globally will create wrong canonical facts.
- Recommended action: row-proof packets must precede ontology/validator fixes.

## Chair

- Are we solving the real root problem? Partly. Validation and one JAY residual
  are fixed; broad measurement and class repair remain.
- Are we overfitting to one artifact? The risk remains unless the next task
  starts from #96/#97 measurement.
- Are we trapped in report-only loops? Not if the next report gates a specific
  implementation lane and ends with `FIX_PROVEN`, `NO_FIX_PROVEN`, or
  `DATA_MISSING`.
- Are we making broad progress? Yes, but current progress is foundation and
  regression safety, not final accuracy.
- Would a class-based approach be better? Yes. Runtime coverage, scorecard
  actuals, table/openability, scale binding, and metric-label semantics are the
  classes to rank.
- Best next action: proceed with a measurement-first extraction sprint governed
  by #96/#97, then implement the top source-proven failure-class fix.

## Minority Objection

Objection: since the targeted replays are green, proceed directly to fixing WHC
or DXC product code.

Disposition: rejected. The green replays remove validation blockers but do not
prove current broad accuracy or source-row truth for DXC/WHC.
