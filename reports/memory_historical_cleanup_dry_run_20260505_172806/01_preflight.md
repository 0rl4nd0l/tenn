# Preflight

## Session Declaration

Lane: Memory
Branch: preserve/dirty-work-20260430T065748Z
Worktree: /mnt/sdb2/home/l4nd0/tenn
Execution mode: AUDIT MODE + DRY-RUN ONLY
Intended files: `reports/memory_historical_cleanup_dry_run_20260505_172806/*`
Contested surfaces touched: none
Collision risk: MEDIUM for copied-DB dry-run analysis; HIGH for any live DB mutation
Decision: proceed with copied-DB dry run only.

## Contract Position

Target system layer: Storage, copied company-memory SQLite only.
Relevant contract rules: backend authority, mandatory pipeline layering, data preservation/no silent corruption, and memory ownership boundaries from `docs/architecture/SYSTEM_CONTRACT.md`, `18_cockpit_memory.md`, and `22_memory_ownership_map.md`.
What must not change: live company memory, live market memory, live thesis memory, live session/operational state, Qdrant, ingestion, retrieval/ranking, source labels, answer synthesis, and financial truth.
Why safe: all mutation was limited to `reports/memory_historical_cleanup_dry_run_20260505_172806/copied_db/company_memory.sqlite`.
GPU process check required: no; this task does not spawn, restart, or depend on llama-server.

## Required Commands

```text
pwd
/home/l4nd0/tenn

git branch --show-current
preserve/dirty-work-20260430T065748Z

git rev-parse HEAD
adb76fac485e90b00ab0253ca83e180aa214255d

git status --short
 M cockpit-ui/components/cockpit/marketplace/matches-screen.test.tsx
 M cockpit-ui/components/cockpit/marketplace/matches-screen.tsx
 M cockpit-ui/lib/marketplace-api.ts
 M cockpit-ui/next-env.d.ts
 M financial-engine_v2/backend/app/routes/cockpit_api.py
 M financial-engine_v2/backend/app/services/marketplace_requirement_resolver.py
 M financial-engine_v2/backend/app/services/marketplace_scanner.py
 M financial-engine_v2/backend/app/services/marketplace_scoring.py
 M financial-engine_v2/backend/tests/test_marketplace_requirement_preparation.py
 M financial-engine_v2/backend/tests/test_marketplace_requirement_resolver.py
 M financial-engine_v2/backend/tests/test_marketplace_scanner.py
 M financial-engine_v2/backend/tests/test_marketplace_scoring.py
?? tenn_prompt_contracts_response_guidelines.zip

git log --oneline -n 15
adb76fa milestone(evaluation): add confirmed metric coverage scorecard profile
79030e5 audit(memory): plan historical cleanup after fanout guard
a7dd791 fix(memory): guard company memory against memo ticker fanout
fb880c6 milestone(news-entity-linking): harden effective ticker coverage
24cfc90 milestone(extraction-gold): add five ASX real-gold labels
84dbb20 milestone(memory): prove company memory fanout root cause
9ee7c6e milestone(docs): record canonical10 baseline confirmation
22356f2 milestone(news-entity-linking): link A2M recall articles
c128e09 Fix cockpit evidence truncation diagnostics
80d4ab2 milestone(cockpit): add SQLite busy timeout for state store
d7778be milestone(holdings): record final routing validation
0a2d497 milestone(news-memory): remediate overnight news ingestion partials
a48c2e1 milestone(query-orchestration): route holdings intent and confirm route aliases
a886b14 milestone(validation): make routing smoke opt-in
ff28b7d milestone(marketplace): catch compact forbidden variants in deal scoring

git merge-base --is-ancestor 84dbb2019ac0 HEAD && echo root_cause_present
root_cause_present

git merge-base --is-ancestor a7dd7913ad6e HEAD && echo fanout_guard_present
fanout_guard_present

git merge-base --is-ancestor 79030e5a5008 HEAD && echo cleanup_plan_present
cleanup_plan_present
```

## Source Artifact Checks

- Cleanup plan folder exists: yes.
- Required candidate CSVs exist: yes.
- Row-total consistency check: passed, total classified rows = 1998.
- Direct live SQLite read against `financial-engine_v2/data/reports/research_memory/company_memory.sqlite` failed with `attempt to write a readonly database`; this matches the prior audit and is why all DB inspection used the copied DB.
