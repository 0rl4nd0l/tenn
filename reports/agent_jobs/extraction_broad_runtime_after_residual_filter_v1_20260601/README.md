# Extraction Broad Runtime After Residual Filter V1

This report bundle captures a bounded post-filter broad extraction robustness
sample after `63e844b1`.

Boundaries:

- Sample size: 8 documents.
- Seed: `20260601`.
- Docs root: `/data/asx/docs`.
- Runtime: existing broad extraction script plus local llama.cpp router.
- Output: report-local JSON only.
- No canonical database writes, source-PDF mutation, code change, schema change,
  Qdrant/news/memory mutation, Cockpit UI change, or GitHub mutation.

The output file is predeclared as `broad_test_20260601T140000Z.json` and is
used through the script `--resume` path so task-card diff checks can enforce an
exact allowlist.

## Result

The bounded sample completed 8/8 documents with status distribution
`ok=3`, `failed=5`, success rate `37.5%`, total runtime `735.0s`, and max
document time `235.1s`.

Failure classes:

- `validation_gate=4`
- `classifier_low_confidence=1`

Failure split:

- CMM annual-general-meeting presentation: non-candidate presentation class.
- MFG notice of full-year results briefing: non-candidate briefing/notice
  class.
- CMM capital-raising announcement: non-candidate capital-raise/update class.
- MFD product/service launch announcement: non-candidate launch/update class.
- PLS formal annual report incorporating Appendix 4E: real extraction blocker,
  with large-PDF/PyMuPDF fallback, `$'000` statement headers, `scale_unknown`,
  and payload period end still aligned to publication date rather than the
  statement year ended 30 June 2023.

This run is useful cross-ticker robustness evidence, not full extraction
graduation.
