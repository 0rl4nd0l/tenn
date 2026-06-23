# Tenn Documentation Source Map

Last verified for documentation navigation: 2026-06-23T05:46:00Z.

Verification scope: repo documentation and agent navigation only. This audit did
not start services, probe live runtime endpoints, inspect production stores, or
prove runtime functionality.

Evidence for this snapshot:

- Worktree: `/home/l4nd0/tenn-docs-current-state-consolidation-v1-20260623`
- Branch: `docs/current-state-consolidation-v1-20260623`
- HEAD: `e402bf38e5b959f56c1bed6b35e18ba7371cd8f6`
- Upstream: `origin/migration/clean-runtime-baseline-reconstruct-v1`
- Task card: `docs/agent_tasks/docs_current_state_consolidation_v1_20260623.md`
- Report bundle:
  `reports/agent_jobs/docs_current_state_consolidation_v1_20260623/`
- Current-turn evidence: task-card validation, registry claim/overlap check,
  `git status --short --untracked-files=all`, `git worktree list --porcelain`,
  docs inventory commands, and generated evidence manifest in the report bundle.

Volatile facts above must be rechecked before acting:

```bash
pwd
git branch --show-current
git rev-parse HEAD
git rev-parse --abbrev-ref --symbolic-full-name @{u}
git status --short --untracked-files=all
python3 /home/l4nd0/.agents/skills/tenn-git-guard/scripts/tenn_git_guard.py preflight --repo-root <repo-root> --topic "<topic-or-path>" --json
python3 .agents/skills/tenn-git-guard/scripts/tenn_git_guard.py preflight --repo-root . --topic "<topic-or-path>" --json
```

Use the installed portable guard first. The `.agents/...` command is the
repo-backed fallback from a Tenn control-plane checkout. Runtime/product repos
do not need Tenn-local `scripts/agent_*` files for guard preflight. In a Tenn
control-plane checkout, these local follow-up checks may add focused validation:

```bash
python3 scripts/agent_job_registry.py list-active --read-only --repo-root .
python3 scripts/agent_task_ledger.py --repo-root . validate
```

## Read First

Read these in order:

1. `AGENTS.md` - repo constitution, safety boundaries, source-of-truth hierarchy.
2. The active task card under `docs/agent_tasks/`, when one exists.
3. This file - documentation map and active/archive routing.
4. Relevant repo-backed skills under `.agents/skills/`.
5. Only then read subsystem docs, reports, or historical notes.

Do not browse `docs/agent_tasks/`, `reports/agent_jobs/`, or `docs/claude/`
blindly. They are evidence archives and reference packs, not a single current
operator manual.

## Active Source Map

| Surface | Status | Use when | Freshness rule |
| --- | --- | --- | --- |
| `AGENTS.md` | Active canonical | Any agent work in this repo | Load every turn; current-turn evidence wins over stale docs. |
| `CLAUDE.md` | Active shim | Claude-specific tool behavior | Defers to `AGENTS.md`; should stay narrow. |
| `README.md` | Active human front door | Basic runtime orientation and first-run commands | Runtime claims need fresh probes before being called current. |
| `docs/README.md` | Active docs source map | Deciding what docs to read next | Update when active/archive routing changes. |
| `docs/entrypoints.md` | Active runtime entrypoint doc | Runtime startup or validation tasks only | Do not read for docs-only or repo-hygiene work. |
| `docs/setup/*` | Active setup references | Environment/runtime/troubleshooting details | Treat host paths, ports, models, and services as configured or historical until rechecked. |
| `docs/architecture/00_README.md` | Active architecture index | Product architecture work | `SYSTEM_CONTRACT.md` wins on invariants. |
| `docs/architecture/SYSTEM_CONTRACT.md` | Active architecture contract | Backend, data, RAG, extraction, memory, or financial-truth changes | Policy source, not proof that a runtime currently conforms. |
| `docs/dev_flow/*` | Active agent-ops docs | Control-plane, task-card, registry, worker, handoff, and review workflows | Prefer the most recent validated report when status docs conflict. |
| `.agents/skills/*/SKILL.md` | Active repo-backed skills | Tenn-specific Codex procedures | Use over host/global skills unless unavailable. |
| `docs/agent_registry/task_ledger/*` | Active registry design/snapshot | Duplicate-work and ledger preflight | Live ledger may be absent; record `DATA_MISSING` and run fallback searches. |
| `docs/agent_registry/merge_parking/*` | Active merge-parking reference | Parked branch visibility and merge-review routing | Inventory only; never merge/unpark without explicit approval. |
| `reports/agent_jobs/*` | Evidence archive | Reading task evidence, validation, closeout, or handoff | Reports are evidence; not automatically current state. |
| `docs/agent_tasks/*` | Execution-contract archive | Active or historical task scope | Use active card first; old cards are historical unless reactivated. |
| `docs/claude/*` | Claude reference/archive | Claude-specific historical context | Source files and current repo evidence win. |
| `docs/current_system.md` | Runtime snapshot/reference | Runtime background after source-map and entrypoints | Contains dated host/runtime claims; reverify before treating as current. |
| `docs/ops/*` | Ops runbooks/reference | Host, GPU, model, news, and operations work | May contain older skill/path references; check `AGENTS.md` and `docs/agents/skill-registry.md`. |

## Current Docs Audit Snapshot

Confirmed during this audit:

- `AGENTS.md` is the top-level agent constitution.
- `CLAUDE.md` is intentionally narrow and defers to `AGENTS.md`.
- `.agents/skills/` has 10 repo-backed skill entrypoints.
- The docs tree is large: 694 files under `docs/`, including 413 task cards.
- `reports/agent_jobs/` is a large evidence archive and is gitignored.
- The active registry accepted
  `docs_current_state_consolidation_v1_20260623` with no active overlap.
- The live Agent Task Ledger path was resolved but missing; the committed ledger
  snapshot exists and was empty in this run.
- Read-only listener/service checks at 2026-06-23T05:52:43Z observed
  `llama-cpp-router.service` active, `llama-server` listening on `8001`, Redis
  listening on `6379`, and Ollama listening on `11434`. This is activity
  evidence only, not runtime functionality proof.

Not proven during this audit:

- Backend health, Cockpit health, Qdrant, Postgres, or Docker container
  functionality. No Tenn backend listener on `8000`, Cockpit listener on
  `8081`, Qdrant listener on `6333`, or Postgres listener on `5432` was
  observed during the read-only listener check.
- Runtime data path availability or freshness.
- Current validation suite pass/fail state.
- Current model loaded or successful inference in any runtime.
- Production extraction, ingestion, news, memory, or financial-truth behavior.

## Conflict Handling

When docs disagree, use this freshness order:

1. Current user instruction.
2. Current-turn repo, GitHub, command, or report evidence.
3. Active task card.
4. `AGENTS.md`, this source map, and relevant repo-backed skills.
5. Recent validated reports under `reports/agent_jobs/`.
6. Architecture contract and subsystem docs.
7. Older snapshots, Claude reference docs, loose notes, and historical reports.

If the conflict still remains, write `DATA_MISSING` instead of selecting a
confident answer.

## Do Not Touch Without A Separate Task

- Product/runtime/backend/extraction/parser/gold-label/evaluator logic.
- DB, Qdrant, Redis, news stores, memory stores, source PDFs, production data,
  migrations, secrets, service configs, Docker volumes, or runtime bindings.
- GitHub writes, branch cleanup, merges, rebases, force operations, pruning, or
  parked-work changes.
- Host/global Codex, Claude, OpenCode, or shell configuration.

## Maintenance Rule

When adding or changing docs:

- Update this source map if the active/archive routing changes.
- Time-bound volatile statements with "last verified" evidence.
- Prefer adding an archive/reference note to stale docs over deleting history.
- Keep `AGENTS.md` concise; move repeatable procedures to `.agents/skills` or
  focused docs.
