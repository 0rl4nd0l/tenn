# Remaining Source Label Risk

Source-label semantics were not changed.

The A2M trace identified a separate issue where reporting/source UI semantics can label local evidence misleadingly. This task only ensures ticker-filtered local news evidence is selected and preserved in the evidence/context bundle.

Why this remains separate:

- Source-label wording and source drawer behavior are Reporting/Provenance surfaces, not retrieval selection.
- Changing labels in this task would mix selection logic with UI/source semantics and increase collision risk.
- No source-label tests were added or changed here except preserving source metadata for downstream consumers.

Status: still a blocker for user-visible source-label correctness, not a blocker for this v1 retrieval selection fix.
