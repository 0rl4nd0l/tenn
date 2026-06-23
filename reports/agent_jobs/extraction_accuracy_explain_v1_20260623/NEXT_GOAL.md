# Next Goal

Start a measurement-first extraction sprint from current
`origin/migration/clean-runtime-baseline-reconstruct-v1`.

## Objective

Explain broad extraction accuracy with current evidence, then fix the top
source-proven failure class.

## Required Lanes

1. Runtime coverage refresh for issue #96:
   - documents;
   - PDF path existence;
   - extractor version;
   - terminal extraction status;
   - financial rows by ticker and document class.
2. Extracted-payload scorecard for issue #97:
   - run or load current extracted payloads for the approved confirmed metric
     fixture set;
   - score exact/tolerated/missing/null/abstain/unsupported/quarantine.
3. Source-row proof:
   - DXC `metric_label_mismatch`;
   - WHC `scale_unknown/openability`.
4. Implementation:
   - only after the matrix identifies the top source-proven failure class.

## Hard Stop

Do not change product code, parser behavior, metric ontology, prompts, source
PDFs, gold labels, DB/Qdrant/news/memory stores, model/runtime config, or
canonical writes from ambiguous evidence.
