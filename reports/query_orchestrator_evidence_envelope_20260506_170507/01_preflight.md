# Preflight

## Commands

```text
pwd
/home/l4nd0/tenn

git branch --show-current
preserve/dirty-work-20260430T065748Z

git rev-parse HEAD
35593a106febdfe2834e6386201466edbd48ea6f
```

Required commits:

```text
source_label_semantics_present
source_label_propagation_present
no_hit_runtime_semantics_present
```

Agent registry:

```text
active_jobs: []
registry_scope: shared
registry_root: /mnt/sdb2/home/l4nd0/tenn/.git/tenn-agent-registry
```

## Dirty Work Classification

Unrelated existing dirty work at preflight:

- `cockpit-ui/components/cockpit/cockpit-status-bar.tsx`
- `cockpit-ui/components/cockpit/history/history-screen.tsx`
- `cockpit-ui/components/cockpit/marketplace/marketplace-assistant.tsx`
- `cockpit-ui/components/cockpit/marketplace/mission-screen.tsx`
- `cockpit-ui/components/cockpit/news/news-screen.tsx`
- `cockpit-ui/components/cockpit/settings/settings-screen.tsx`
- `cockpit-ui/components/cockpit/verification/tabs/metric-coverage-tab-panel.tsx`
- `cockpit-ui/components/cockpit/verification/verification-screen.tsx`
- `cockpit-ui/components/cockpit/watchlist/watchlist-screen.tsx`
- `tenn_prompt_contracts_response_guidelines.zip`

Additional unrelated live-worktree artifact observed after implementation started:

- `cockpit-ui/components/cockpit/home/`
- `cockpit-ui/lib/mock/`
- `cockpit-ui/types/`
- `tenn_cockpit_home_design_export_20260506/`

None overlap `query_orchestrator.py`, source-label helpers touched here, Cockpit API wrappers, or backend tests changed here. These files were not edited or staged by this task.

## Contract Check

Target system layer: Retrieval/Analysis metadata.

Relevant rules: `SYSTEM_CONTRACT.md` sections 1.1, 1.2, 1.3, 2, 5, 7, 8, and 10; `docs/architecture/21_cockpit_client_contract.md` sections 1, 6.2, 7, and 9.

What must not change: ingestion, extraction, storage, Qdrant, `news.sqlite`, memory stores, session stores, retrieval ranking, financial truth extraction, source drawer UI, Textual `/sources`, legacy `/api/chat`, deep research behavior, or raw chain-of-thought exposure.

Why safe: the patch only adds result metadata and focused tests. It does not call new services, mutate stores, change provider behavior, or change answer synthesis prompts.

DATA_MISSING: architecture-check skill rule files named under `.cursor/rules/00_mandatory_index.md`, `backend_architecture.md`, `embedding_rules.md`, `vector_store_invariants.md`, and `failure_policy.md` were not present in this worktree. Binding checks used `SYSTEM_CONTRACT.md` and the Cockpit client contract.
