# Extraction Broad Robustness Post-Hardening Sample V1

## Summary

Ran one bounded broad extraction robustness sample against `/data/asx/docs`
after the broad-failure hardening in `ff830187`. The run used `llama.cpp`
through the local router on `8001`, seed `20260601`, and requested `8`
documents.

This is robustness/status evidence only. It is not a gold accuracy result and
does not authorize canary promotion, canonical writes, broad backfill, or full
extraction graduation.

## Candidate Filter

- Input `financial_performance` PDFs: `28,633`.
- Candidate PDFs retained: `26,462`.
- Excluded before sampling: `2,171`.
- Exclusion reasons: `meeting_results_notice=2116`,
  `advisory_only_document=50`,
  `unaudited_financial_update_without_formal_statements=5`.

## Result

- Documents sampled: `8`.
- Unique tickers sampled: `7`.
- Status distribution: `ok=4`, `failed=4`.
- Success rate: `50.0%`.
- Failure classes: `classifier_low_confidence=3`, `validation_gate=1`.
- Runtime total: `587.4s`; max document time: `158.71s`.
- Successful documents averaged `5.0` non-null metrics.

## Failure Digest

- `CCR`: low-confidence classifier failure on a customer/revenue announcement,
  `0/10` metrics.
- `IMR`: `validation_gate:scale_unknown` on an Appendix 4C/business update,
  despite `5/10` metrics.
- `AAM`: low-confidence classifier failure on `notice-of-annual-general-meeting-proxy-form`,
  `0/10` metrics.
- `IXC`: low-confidence classifier failure on `notice-of-annual-general-meeting-proxy-form`,
  `0/10` metrics.

## Accepted Documents

- `ASL`: quarterly activities/cash-flow report, `ok`, `5/10` metrics,
  `scale=thousands`.
- `CCR`: FY21 annual report, `ok`, `8/10` metrics, `scale=thousands`.
- `IVR`: quarterly activities/cash-flow report, `ok`, `3/10` metrics,
  `scale=millions`.
- `NC6`: Appendix 4C cash-flow report, `ok`, `4/10` metrics,
  `scale=thousands`.

## Boundaries

- Backend startup: false.
- Canary/process-document route: false.
- Real-gold eval route: false.
- Broad backfill: false.
- Database, Qdrant, news, memory, or canonical financial row mutation: false.
- Source PDF copy or mutation: false.
- Parser, prompt, schema, or model/GPU config change: false.
- Cockpit UI or GitHub mutation: false.

## Cleanup

Dedicated GPU activity token `2b95e9e8e37a4bda9ced243eeb7dc4f5` was cleared.
The transient router unit was stopped. Ports `8000` and `8001` were closed
after shutdown, GPU-exclusive activity was inactive, and the GPU process guard
reported no llama-server processes.

## Next Safe Step

The post-hardening sample improved the bounded status distribution from the
previous `3/8` accepted run to `4/8` accepted, and the old AGM result/poll and
unaudited-update failures did not recur. Remaining blockers are narrower:
AGM/proxy notice candidate exclusion, one Appendix 4C/business-update
`scale_unknown` case, and low-confidence filtering for non-financial customer
announcements. This is still not full ticker-universe extraction graduation.
