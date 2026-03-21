# Task Process

## Source Trace
- `docs/architecture/11_engineering_discipline.md` (Confirmed)
- `docs/entrypoints.md` (Confirmed)
- `docs/cloud_workflow.md` (Confirmed)
- `CLAUDE.md` (Confirmed)

---

## Task Template

Use this template when starting any non-trivial implementation task.

```
## Task: [Short name]

### Scope
- Subsystem: [which component]
- Files to modify: [list]
- Files to read first: [list]

### Goal
[What specific behavior changes]

### Invariants to preserve
- [List any known invariants that must not break]

### Safety check
- [ ] No secrets touched
- [ ] No DB schema changes (or explicitly confirmed OK)
- [ ] No validation gates removed
- [ ] Scope is narrow (≤ 5 files, ≤ 300 lines)

### Validation plan
- [ ] Lint: `python -m ruff check ...`
- [ ] Tests: `pytest ...`
- [ ] [Additional gates if pipeline/embeddings affected]
```

---

## Task Classification

| Task Type | Required Reading | Required Validation |
|-----------|-----------------|---------------------|
| API route change | `docs/architecture/07_rag_contract.md`, `main.py`, route file | Lint + backend tests |
| Ingestion/pipeline change | `04_ingestion_pipeline.md`, `05_pdf_extraction_and_chunking.md` | Lint + backend tests + canonical dataset checks |
| Embedding/vector change | `06_embeddings_and_vector_store.md` | Lint + backend tests + canonical regression + financial gates |
| RAG change | `07_rag_contract.md`, `rag.py` | Lint + backend tests + canonical regression |
| Celery/worker change | `09_worker_and_celery_contract.md`, `celery_app.py`, `worker_tasks.py` | Lint + backend tests |
| Model router change | `model-routing.md`, `router.py` | Lint + backend tests + RAG stability check |
| Financial extraction change | `financial_metrics_extraction_analysis.md` | Lint + backend tests + financial gates |
| Config/env change | `docs/setup/environment.md`, `core/config.py` | Lint + backend tests + smoke |
| Ops/script change | `docs/entrypoints.md`, relevant script | Lint + script tests + smoke |
| Documentation change | Relevant source docs | `bash scripts/check_markdown_hygiene.sh` |

---

## Task Execution Flow

```
1. Read this file + CLAUDE.md
        │
        ▼
2. Read source docs for the relevant subsystem
        │
        ▼
3. Write plan (use template above)
        │
        ▼
4. Implement (minimal, targeted change)
        │
        ▼
5. Run lint + tests
        │
        ▼
6. If pipeline/embedding/RAG: run canonical checks + financial gates
        │
        ▼
7. Verify pre-merge checklist (docs/architecture/11_engineering_discipline.md)
        │
        ▼
8. If Cloud PR: push to branch → prepare_cloud_worktree.sh → narrow PR
```

---

## What to Do When Blocked

1. Do not brute-force. Stop and diagnose.
2. Check `docs/claude/skills/debugging.md` for the relevant subsystem.
3. Check `docs/ops/quickstart.md` for incident routing.
4. If the block is scope creep, surface it: ask the user to narrow or split the task.
5. If the block is a missing fixture or baseline, document it in `docs/claude/gap-analysis.md`.

---

## Active Task Tracking

For tasks spanning multiple steps, use the TodoWrite tool to track progress.
Mark tasks `in_progress` before starting and `completed` immediately upon finishing.
Never batch completions.
