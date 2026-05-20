# M5 - Cockpit Strategy Lab UX Framework

Design only. No Cockpit UI files were edited.

## When To Keep Workflows In Existing Surfaces

Use Chat when:

- the user asks one-off questions about a strategy idea;
- the output is a short research note;
- no persistent experiment state is needed;
- the answer can remain clearly source-labeled and non-canonical.

Use Company / Memory when:

- the workflow is one ticker's thesis, qualitative memory, or source review;
- the output belongs to company/market/thesis memory proposal flows;
- no backtest/factor/portfolio experiment is being managed.

Use Watchlist when:

- the workflow is monitoring a finite list of tickers;
- the output is an opportunity scan or alert;
- the job does not require comparing experiment runs.

Use Verification when:

- the workflow evaluates extraction, metric, provenance, or gold-label evidence;
- the output is about financial truth correctness, not strategy performance.

## When To Create A Strategy Lab Tab

Create a Strategy Lab tab only after these are true:

- at least two Strategy Lab artifact types exist;
- artifacts have schema validation;
- a review queue exists;
- result statuses and limitations are visible;
- the UI can separate research context from financial truth;
- QuantDinger or any sidecar remains behind Tenn's policy layer;
- no live/paper execution controls are present.

## Proposed Tab Layout

Top navigation inside Strategy Lab:

- Ideas
- Backtests
- Sweeps
- Factors
- Regimes
- Risk
- Portfolio Lab
- Review Queue
- Evidence
- Admin Debug

Admin Debug is hidden by default and is not a substitute for Cockpit UX.

## Core Components

- Idea card: hypothesis, universe, source of idea, review state, next safe test.
- Backtest result card: run status, benchmark comparison, drawdown, assumptions, limitations.
- Sweep table: parameters, objective metric, rank, overfit warning, data gaps.
- Factor test matrix: quantiles, IC, spread, turnover, stability.
- Regime panel: performance by regime, sample counts, classifier caveats.
- Risk card: drawdown, exposure, turnover, concentration, liquidity, scenario warnings.
- Portfolio experiment card: current-vs-proposed simulation, source of holdings, personal-data label.
- Review queue item: approve/reject/defer/promote-to-task-card.
- Evidence alignment view: artifact inputs, raw outputs, Tenn evidence labels, source refs, DATA_MISSING rows.
- Robustness warning strip: overfit, lookahead, survivorship, insufficient sample, benchmark missing, sidecar unavailable.

## Review Queue Requirements

Every machine-generated artifact enters `PENDING_REVIEW`.

Human actions:

- approve for research context;
- reject;
- request more evidence;
- promote to future task card;
- mark blocked by truth/runtime/execution boundary.

Disallowed UI actions:

- direct memory write;
- direct financial truth write;
- start paper trade;
- start live trade;
- broker key entry;
- turn on live execution;
- hide limitations.

## Evidence Alignment View

The view should show:

- source-of-idea;
- sidecar tool call;
- raw output artifact reference;
- schema validation status;
- benchmark and assumptions;
- evidence labels;
- unsupported claims;
- `DATA_MISSING`;
- human review decision;
- link back to originating Chat/Company/Watchlist context.

## QuantDinger UI Position

QuantDinger's own UI should remain admin/debug only:

- useful for setup checks, raw sidecar inspection, and diagnosing sidecar failures;
- not embedded as the main Cockpit Strategy Lab UI;
- not used to bypass Tenn evidence labels, review queue, or tool policy;
- not used for broker credentials from inside Tenn unless a separate security project approves it.

## DATA_MISSING

- No current Strategy Lab screen exists.
- No rendered UX was tested.
- No QuantDinger UI was run.
