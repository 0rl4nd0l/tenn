# Watchlist Triage Standard

## Scope and Trigger

Apply this standard for requests that ask to prioritize watchlist names, identify urgency, or recommend immediate follow-up across a watchlist.

## Inputs and Evidence Contract

1. Treat this as prioritization guidance, not full thesis generation.
2. Use only confirmed current-turn evidence for urgency ranking.
3. Separate confirmed triggers from speculative observations.
4. If evidence is insufficient for a ticker, label it as unknown.
5. Do not fabricate ranking confidence where signal is weak.

## Execution Steps

1. Coverage Pass:
State which watchlist names were evaluated and which were not.

2. Urgency Pass:
Rank names by urgency with brief evidence-backed reasoning.

3. Actionability Pass:
Provide one immediate next action per ranked ticker.

4. Risk Pass:
Call out downside or uncertainty for top-priority names.

5. Unknowns Pass:
List missing signals that block confident ranking.

## Output Contract

Use this top-level section order:

1. `Coverage:`
2. `Priority Ranking:`
3. `Immediate Actions:`
4. `Risks and Caveats:`
5. `Unknowns:`

Inside `Priority Ranking:`, use numbered items with ticker, urgency level, and one-line rationale.

Every substantive factual line must include user-visible source grounding.

## Memory and Follow-up Rules

1. Watchlist triage does not auto-write memory.
2. Recommended actions must be explicit, bounded, and user-confirmable.
3. If confidence is low, recommend data collection before action.
