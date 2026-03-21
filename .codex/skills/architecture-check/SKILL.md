---
name: architecture-check
description: Validate proposed backend, RAG, vector store, and embedding changes against mandatory architecture rules before implementation. Use for architecture compliance checks or before editing sensitive retrieval surfaces.
---

# Architecture Check

Use this skill for analysis-only reviews of proposed or in-progress changes.

## Read First

- `.cursor/rules/00_mandatory_index.md`
- `.cursor/rules/backend_architecture.md`
- `.cursor/rules/embedding_rules.md`
- `.cursor/rules/vector_store_invariants.md`
- `.cursor/rules/failure_policy.md`

## Workflow

1. Read the relevant rule files before judging the change.
2. Inspect the proposed diff, touched files, or described design.
3. For each change, classify against the rules:
   - `COMPLIANT`
   - `VIOLATES RULE`
   - `REQUIRES MIGRATION`
4. If any item is `VIOLATES RULE`, refuse implementation and cite the exact rule text and location.
5. If a change intentionally alters an invariant, require a migration/design document before proceeding.

## Invariants To Check

- No `sentence-transformers` introduction.
- No new runtime embedding backend beyond Ollama + `nomic-embed-text`.
- No fallback embedding logic that bypasses fail-fast behavior.
- No non-deterministic or UUID vector IDs for chunks.
- No SQLite vector store reintroduction.
- Distance metric must remain `COSINE`.
- Dimension mismatch must fail fast; no silent tolerance.
- Multiple embedding models at runtime are forbidden.
- `document_id` format changes require migration planning.

## Output

Return a structured architecture review with:

- Change summary
- Rule file and section checked
- Status per rule
- Short explanation
- Final verdict: `APPROVED` or `REFUSED`

## Constraints

- Analysis only. Do not edit code while using this skill.
- When rules and implementation ideas conflict, rules win.
