---
name: intelligence-pack-review
description: Analyze the latest reports/weekly JSON intelligence pack and produce a four-section executive brief without modifying any data stores.
---

# Intelligence Pack Review

Use this skill for read-only analysis of the latest weekly intelligence pack.

## Workflow

1. Find the newest file under `reports/weekly/*.json`.
2. Read the JSON and confirm the key top-level aggregates.
3. Analyze:
   - top risk concentration
   - emerging tickers or spikes
   - retrieval themes from `rag_summary`
   - follow-up query opportunities

## Required Output Sections

Produce exactly these four sections in order:

1. `SECTION 1: Risk Concentration`
2. `SECTION 2: Emerging Risk Signals`
3. `SECTION 3: Retrieval Insight`
4. `SECTION 4: Recommended Follow-Up Queries`

## Constraints

- Read-only.
- Do not query or modify the database or Qdrant.
- Do not rewrite the source JSON.
