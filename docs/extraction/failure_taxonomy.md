# Extraction Hardening Failure Taxonomy

This taxonomy is for synthetic fixture scoring only.

## Classification outcomes

- `correct`
  - Expected value present and numerically aligned.
- `wrong`
  - Numeric extraction present but outside tolerance.
  - Expected-null metric extracted as non-null.
- `missing`
  - Expected metric value not present in extraction output.
- `abstain`
  - Metric marked optional and not present. No penalty, but not counted as pass.
- `quarantine`
  - Context mismatch (`period_end`, `currency`, `scale`) between fixture and extracted payload.

## Mapping to hardening semantics

- `wrong` is a hard failure candidate in live accuracy gating.
- `missing` is a hard failure candidate and should feed prompt/process diagnostics.
- `abstain` lowers the score while preserving that extraction was not forced.
- `quarantine` is excluded from aggregate gating and treated as metadata hygiene signal.

## Operational intent

The taxonomy preserves fail-fast behavior for invalid context while allowing optional
metrics to remain abstain-only without masking wrong values in required fields.
