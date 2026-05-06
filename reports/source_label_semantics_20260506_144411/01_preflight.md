# Preflight

## Required Commands

```text
$ pwd
/home/l4nd0/tenn

$ git branch --show-current
preserve/dirty-work-20260430T065748Z

$ git rev-parse HEAD
b9ace36e5e02e1f551b6a09209bb81beb527633a

$ git status --short
?? tenn_prompt_contracts_response_guidelines.zip

$ git merge-base --is-ancestor b9ace36e5e02 HEAD && echo a2m_retrieval_selection_present
a2m_retrieval_selection_present
```

`git log --oneline -n 25` showed HEAD:

```text
b9ace36 fix(query): include ticker-filtered news evidence for company chat
```

## Dirty Work Assessment

Pre-existing dirty work was limited to:

- `tenn_prompt_contracts_response_guidelines.zip`

That file was not touched or staged. No dirty overlap existed in required source-label, reporting, chat metadata, or test files before implementation.

## Contract Check

Target layer:

- Retrieval-to-analysis metadata
- Answer metadata serialization
- Client presentation metadata

Relevant contract rules:

- Preserve deterministic financial truth boundaries.
- Do not mutate Qdrant, ingestion state, news.sqlite, or memory stores.
- Do not use LLM outputs as canonical financial numbers.
- Do not label irrelevant, empty, operational, memory-only, or local holdings context as source-backed financial truth.

What must not change:

- Retrieval ranking and selection behavior.
- Financial truth extraction.
- Ingestion, indexing, and memory persistence.
- Synthesis prompt architecture.

Why safe:

- Changes are additive label metadata and tests.
- Existing sources remain visible but gain conservative evidence roles.
- Runtime degraded and missing-evidence states are surfaced without weakening unsupported-claim blocking.

## Session Declaration

```text
Lane: Provenance
Branch: preserve/dirty-work-20260430T065748Z
Worktree: /mnt/sdb2/home/l4nd0/tenn
Execution mode: SAFE EXTENSION MODE
Intended files: allowed source-label/chat metadata/UI/test/report files
Contested surfaces touched: yes, answer metadata/source serialization and agent-loop degradation metadata
Collision risk: MEDIUM
Decision: proceed
```
