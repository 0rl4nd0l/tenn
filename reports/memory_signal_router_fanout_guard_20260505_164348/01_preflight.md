# Preflight

## Required Commands

```text
pwd
/home/l4nd0/tenn

git branch --show-current
preserve/dirty-work-20260430T065748Z

git rev-parse HEAD
fb880c6ec0e2451855e80fbd203b924f14270ebc

git status --short
 M cockpit-ui/components/cockpit/marketplace/matches-screen.test.tsx
 M cockpit-ui/components/cockpit/marketplace/matches-screen.tsx
?? tenn_prompt_contracts_response_guidelines.zip

git log --oneline -n 8
fb880c6 milestone(news-entity-linking): harden effective ticker coverage
24cfc90 milestone(extraction-gold): add five ASX real-gold labels
84dbb20 milestone(memory): prove company memory fanout root cause
9ee7c6e milestone(docs): record canonical10 baseline confirmation
22356f2 milestone(news-entity-linking): link A2M recall articles
c128e09 Fix cockpit evidence truncation diagnostics
80d4ab2 milestone(cockpit): add SQLite busy timeout for state store
d7778be milestone(holdings): record final routing validation
```

## Stop Checks

- `git merge-base --is-ancestor 84dbb2019ac0 HEAD`: exit 0
- `reports/memory_contamination_root_cause_20260505_161634/`: present
- Existing strict xfail fixture: present at `financial-engine_v2/backend/tests/test_memory_signal_router.py`
- Target files before editing: no unrelated uncommitted edits
- Existing dirty files: Cockpit UI marketplace files and one untracked zip, unrelated to this lane

## Required Source Inspection

Read before editing:

- reports/memory_contamination_root_cause_20260505_161634/README.md
- reports/memory_contamination_root_cause_20260505_161634/01_write_path_trace.md
- reports/memory_contamination_root_cause_20260505_161634/02_fanout_root_cause.md
- reports/memory_contamination_root_cause_20260505_161634/04_fixture_reproduction_plan.md
- reports/memory_contamination_root_cause_20260505_161634/06_safe_fix_options.md
- reports/memory_contamination_root_cause_20260505_161634/07_tests_to_add.md
- financial-engine_v2/backend/app/services/memory_signal_router.py
- financial-engine_v2/backend/app/services/company_memory.py
- financial-engine_v2/backend/app/services/market_memory.py
- financial-engine_v2/backend/tests/test_memory_signal_router.py

## Contract Check

Target system layer: backend Storage and memory write-path routing.

Relevant contract rules:

- SYSTEM_CONTRACT.md §1.1: backend is the source of truth
- SYSTEM_CONTRACT.md §2.1-§2.2: preserve layer boundaries and avoid duplicate pipelines
- SYSTEM_CONTRACT.md §5.1: retrieval is backend-owned
- SYSTEM_CONTRACT.md §7: no parallel systems
- SYSTEM_CONTRACT.md §8: fail fast on ambiguity
- SYSTEM_CONTRACT.md §10.2-§10.3: state invariants and do not introduce fallbacks, approximations, or parallel systems

Must not change:

- live memory rows
- schema/migrations
- ingestion/reprocessing
- Qdrant/vector state
- answer synthesis
- retrieval ranking
- source labels
- alias canonicalization
- company analysis behavior

Why safe:

- The fix is isolated to router signal emission before company-memory persistence.
- Tests use only pytest `tmp_path` SQLite stores.
- No live DB, Qdrant, ingestion, or cleanup path was invoked.
- Ambiguous multi-ticker statements fail closed by skipping company-memory writes rather than guessing targets.

DATA_MISSING:

- `.cursor/rules/00_mandatory_index.md`
- `.cursor/rules/backend_architecture.md`
- `.cursor/rules/embedding_rules.md`
- `.cursor/rules/vector_store_invariants.md`
- `.cursor/rules/failure_policy.md`

Those files were not present in this worktree. `SYSTEM_CONTRACT.md` was used as the active authority.

