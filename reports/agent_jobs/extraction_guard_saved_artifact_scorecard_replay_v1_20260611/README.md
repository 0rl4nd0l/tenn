# Guard Saved-Artifact Scorecard Replay

State: DONE_WITH_RISK

This report aggregates saved-artifact guard outcomes only. It did not run extraction, count samples, service routes, backfills, production persistence, or GitHub writes.

## Guard Summary

- WHC `9640d9f1-a45b-492d-8df5-9bad0f46431c`: prior runtime replay failed `validation_gate:missing_period_end`; current WHC period-binding replay is `ok`, `period_end=2022-06-30`, with 8 accepted non-null metrics.
- CTN `dec0b5f1-e6d2-48d8-ad9d-16ffd540ee39`: saved-artifact replay preserved `+1` document / `+6` metrics.
- HUB `419bcca8-213e-4706-8962-8e3bd8adf091`: saved-artifact replay preserved `+1` document / `+9` metrics.
- LBL `551c6b84-1053-405c-a833-4ecc018e2045`: remains fail-closed; exact source-bound half-year period-end date is still missing.
- AZJ `488d6f1a-0180-4fca-8dcf-c4cdfc0f342e`: expected scale gap was not reproduced; scale-table repair path remains closed from this evidence.
- NSR `f2240712-9dde-41e0-88fa-29c1a0080dab`: remains clean thousands-scale control.

Saved-artifact aggregate gain from the repair packets represented here is +3 documents / +23 metrics. This is not a broad current scorecard claim.

## Next Step

Do not run count-24 from this packet. The next bounded action is either an explicit push/PR update for the WHC branch, or an approved broader saved-artifact scorecard profile if merge gating requires it.
