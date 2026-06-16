# Project Agent Rules - financial-engine_v2

For all Tenn work, `../AGENTS.md` is the constitution. If this file conflicts
with `../AGENTS.md`, follow `../AGENTS.md`.

This file adds local orientation for `financial-engine_v2` only.

## Scope

`financial-engine_v2` contains the active financial document ingestion,
extraction, RAG, retrieval, backend, cockpit, and worker code. Treat product,
runtime, extraction, financial-truth, prompt, DB, Qdrant, Redis, news, model,
GPU, source-PDF, and gold-label surfaces as approval-gated under `../AGENTS.md`.

## Before Editing

- Verify repo path, branch, HEAD, remote, and dirty state.
- Use or create a task card for non-trivial writes.
- Keep edits inside exact `allowed_files`.
- Preserve unrelated dirty files.
- Read subsystem docs only when they are relevant to the task.

## Runtime

Use `../docs/entrypoints.md` only when the task requires runtime startup or
runtime validation. Do not start services for repo-hygiene, docs, report-only,
task-card, hook, or skill cleanup work.

## Validation

Follow `../AGENTS.md` risk-based validation. Narrow code changes should run the
cheapest focused check that exercises the behavior. Broad runtime suites are for
broad runtime changes, not default session closeout.

## Git

Commits and GitHub actions require explicit current task-card scope and user
approval. Do not commit merely to end a session with a clean tree.
