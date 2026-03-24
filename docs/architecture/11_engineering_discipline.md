# Tenn Engineering Discipline

## Pre-Merge Checklist

- [ ] Plan written in tasks/todo.md
- [ ] Invariants reviewed
- [ ] Tests executed
- [ ] No architecture drift introduced
- [ ] Vector baseline verified (if embeddings changed)
- [ ] RAG stability verified (if retrieval changed)
- [ ] Lessons logged (if bug fix)

This document formalizes Tenn's engineering operating model.

## Extraction Evaluation Standard

Extraction accuracy must be validated for **generalization**, not just accuracy on known fixtures.

- The 6-fixture regression gate catches prompt and code regressions but does not certify production readiness.
- Extraction changes must be tested against documents from different companies, sectors, report types (4D, 4E, 5B, full IFRS), and accounting conventions.
- Production validation requires a broader, continuously expanding document set beyond the fixture suite.
- Do not overfit prompts to fixture-specific patterns — a fix that improves one fixture while degrading unseen documents is a net loss.
