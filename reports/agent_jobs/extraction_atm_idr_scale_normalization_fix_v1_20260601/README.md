# Extraction ATM IDR Scale Normalization Fix V1

## Result

Implemented the code/test fix for the remaining ATM scale blocker. This card
does not prove runtime graduation because it did not rerun backend extraction.

Root cause: in the live ATM Docling cache, statement-unit text such as
`Expressed in Millions of Rupiah` is present in `sections`, while the selected
statement tables have no unit text. Table scale detection returned `unknown`,
so Pass 1's Appendix 4E `trillions` context survived into Pass 3a.

Fix: `multipass_extraction.py` now detects explicit IDR millions units from
formal financial-statement section text and applies that deterministic source
unit before Pass 3a.

## Validation

- New focused regression failed before the fix.
- Focused scale regressions: `5 passed`.
- Full multipass suite: `171 passed`.
- Targeted Ruff: passed.
- `py_compile`: passed.
- Live cache probe: `table_scale=unknown`, `section_scale=millions`.

## Boundary

No runtime extraction rerun, backend/worker/router restart, direct datastore
mutation, source PDF mutation, fixture/gold-label mutation, schema migration,
Qdrant/news/memory write, Cockpit UI, or GitHub mutation was performed.

## Next Safe Step

Rerun the same bounded seven-document backend-route canary and real-gold
scorecard to prove ATM moves from quarantine to trusted and the canary reaches
7/7 trusted fixtures.
