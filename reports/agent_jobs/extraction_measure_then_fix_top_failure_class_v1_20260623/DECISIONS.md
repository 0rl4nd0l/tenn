
# Decisions

Generated: 2026-06-23T07:54:28.496693Z

- Broad extraction accuracy is still not solved: #96 terminal coverage and #97 current-payload scoring still have zero overlapping current actual payloads for the approved confirmed fixture set.
- DXC `metric_label_mismatch:ebit:net_operating_income` is `NO_FIX_PROVEN`; no mapping was implemented.
- WHC annual report period binding is `FIX_PROVEN`; the narrow fix was implemented.
- No canonical writes, DB/Qdrant/Redis/news/memory/source-PDF/prompt/gold/schema/model/GPU mutation, or broad backfill was performed.
- `count-24/count-32` is not justified by this run.
