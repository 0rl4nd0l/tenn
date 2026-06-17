# Decisions

## D1: Proceed With Narrow Broad-Run Surface

Decision: `accepted`

Reason: current pass 4 payload already includes `row_refs`, `provenance`, `field_provenance`, `metric_source_scales`, and `metric_scale_sources`. The broad runner was dropping them. Surfacing them is the smallest useful fix and avoids canonical truth mutation.

## D2: Keep Risk Flags Report-Only

Decision: `accepted`

Reason: the handoff selected evidence surfacing before fail-closed scale/magnitude behavior. The implemented flags live in broad-run records and summaries only; they are not wired to `_validate_gate` or persistence.

## D3: Use Generic Risk Codes

Decision: `accepted`

Codes implemented:

- `scale_unknown_with_metrics`
- `metric_exceeds_native_sanity_cap`
- `all_checked_metrics_below_minimum`
- `mixed_metric_source_scales`
- `payload_scale_differs_from_metric_source_scale`
- `metric_source_scale_missing`
- `metric_revenue_ratio_high`

Reason: these cover WHC/HCW/EDU/LBL-style evidence patterns without ticker-specific acceptance behavior.

## D4: Keep Implementation Out Of `multipass_extraction.py`

Decision: `accepted`

Reason: the requested slice was broad-run surfacing. Changing extraction or canonical validation would cross the task boundary.

## D5: No GitHub Mutation

Decision: `accepted`

Reason: user explicitly prohibited push or PR without approval. Closeout is local only.
