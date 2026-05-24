---
job_id: trust_foundation_followup_integrate_canonical_v1_20260524
lane: Evaluation
owner: Codex
allowed_files:
  - docs/agent_tasks/trust_foundation_followup_integrate_canonical_v1_20260524.md
  - docs/agent_tasks/trust_foundation_followup_implementation_controller_v1_20260524.md
  - docs/agent_tasks/source_label_semantic_sufficiency_guard_v1_20260524.md
  - docs/agent_tasks/memory_live_inventory_readonly_v1_20260524.md
  - docs/agent_tasks/a2m_news_live_trace_readonly_v1_20260524.md
  - docs/agent_tasks/gold_metric_coverage_eval_spine_normalizer_v1_20260524.md
  - reports/agent_jobs/trust_foundation_followup_integrate_canonical_v1_20260524/README.md
  - reports/agent_jobs/trust_foundation_followup_integrate_canonical_v1_20260524/status.json
  - reports/agent_jobs/trust_foundation_followup_integrate_canonical_v1_20260524/validation.json
  - reports/agent_jobs/trust_foundation_followup_integrate_canonical_v1_20260524/diff-check.json
  - reports/agent_jobs/trust_foundation_followup_implementation_controller_v1_20260524/README.md
  - reports/agent_jobs/trust_foundation_followup_implementation_controller_v1_20260524/diff-check.json
  - reports/agent_jobs/trust_foundation_followup_implementation_controller_v1_20260524/preflight.json
  - reports/agent_jobs/trust_foundation_followup_implementation_controller_v1_20260524/status.json
  - reports/agent_jobs/trust_foundation_followup_implementation_controller_v1_20260524/validation.json
  - reports/agent_jobs/source_label_semantic_sufficiency_guard_v1_20260524/README.md
  - reports/agent_jobs/source_label_semantic_sufficiency_guard_v1_20260524/status.json
  - reports/agent_jobs/source_label_semantic_sufficiency_guard_v1_20260524/validation.json
  - reports/agent_jobs/memory_live_inventory_readonly_v1_20260524/README.md
  - reports/agent_jobs/memory_live_inventory_readonly_v1_20260524/inventory.csv
  - reports/agent_jobs/memory_live_inventory_readonly_v1_20260524/inventory.json
  - reports/agent_jobs/memory_live_inventory_readonly_v1_20260524/no_mutation_attestation.md
  - reports/agent_jobs/memory_live_inventory_readonly_v1_20260524/read_only_proof.json
  - reports/agent_jobs/memory_live_inventory_readonly_v1_20260524/status.json
  - reports/agent_jobs/a2m_news_live_trace_readonly_v1_20260524/README.md
  - reports/agent_jobs/a2m_news_live_trace_readonly_v1_20260524/no_mutation_attestation.md
  - reports/agent_jobs/a2m_news_live_trace_readonly_v1_20260524/qdrant_probe.json
  - reports/agent_jobs/a2m_news_live_trace_readonly_v1_20260524/retrieval_trace.json
  - reports/agent_jobs/a2m_news_live_trace_readonly_v1_20260524/sqlite_inventory.json
  - reports/agent_jobs/a2m_news_live_trace_readonly_v1_20260524/status.json
  - reports/agent_jobs/a2m_news_live_trace_readonly_v1_20260524/trace_artifacts.json
  - reports/agent_jobs/gold_metric_coverage_eval_spine_normalizer_v1_20260524/README.md
  - reports/agent_jobs/gold_metric_coverage_eval_spine_normalizer_v1_20260524/metric_expectations.csv
  - reports/agent_jobs/gold_metric_coverage_eval_spine_normalizer_v1_20260524/normalized_manifest.json
  - reports/agent_jobs/gold_metric_coverage_eval_spine_normalizer_v1_20260524/scorecards.csv
  - reports/agent_jobs/gold_metric_coverage_eval_spine_normalizer_v1_20260524/status.json
  - reports/agent_jobs/gold_metric_coverage_eval_spine_normalizer_v1_20260524/validation.json
  - financial-engine_v2/backend/app/routes/cockpit_api.py
  - financial-engine_v2/backend/app/services/chat_evidence_guard.py
  - financial-engine_v2/backend/tests/test_build_ui_sources.py
  - financial-engine_v2/backend/tests/test_chat_evidence_guard.py
  - cockpit-ui/components/cockpit/chat/terminal-message.tsx
  - cockpit-ui/components/cockpit/chat/terminal-message.test.tsx
  - scripts/reporting/gold_metric_coverage_eval_spine_normalizer.py
  - scripts/reporting/test_gold_metric_coverage_eval_spine_normalizer.py
approval_required: false
allow_unapproved_safe_extension: true
timeout_seconds: 21600
output_dir: reports/agent_jobs/trust_foundation_followup_integrate_canonical_v1_20260524
mutation_mode: safe_extension
production_data_access: false
---

# Trust Foundation Follow-up Canonical Integration

## Session Declaration

- agent name: Codex
- branch: integrate/trust-foundation-followup-canonical-v1-20260524
- worktree path: /home/l4nd0/tenn-trust-foundation-followup-integrate-canonical-v1-20260524
- lane: Evaluation
- execution mode: MERGE / INTEGRATION REVIEW / SAFE CANONICAL APPLY
- contested surfaces intended: financial-engine_v2/backend/app/routes/cockpit_api.py
- collision risk: MEDIUM-HIGH, controlled by clean integration worktree, shared registry check, source diff review, focused tests, and final canonical fast-forward only if safe.

## Objective

Integrate source milestone commit `f83e8c9a541d` from `safe/trust-foundation-followup-implementation-controller-v1-20260524` into canonical `/home/l4nd0/tenn` if safe, while preserving unrelated canonical task-card dirt.

## Contract Boundaries

- Preserve backend authority, source/evidence label safety, memory store safety, deterministic financial truth, and Eval Spine proof vs inventory boundaries.
- Do not write Qdrant, Postgres, news stores, memory stores, production DB files, runtime topology, Docker, cron, systemd, model, or GPU configuration.
- Do not run live chat synthesis for this integration.
- Do not convert inventory artifacts into accuracy proof or weaken DATA_MISSING.
- Stop on unresolved active-job overlap, broad merge conflict, or forbidden file mutation.

## Validation Plan

- Validate this task card and imported child cards.
- Check and claim the shared registry from the clean integration worktree.
- Cherry-pick `f83e8c9a541d` with `--no-commit`.
- Review changed files, forbidden surfaces, source-label semantics, and normalizer write boundaries before commit.
- Run focused backend pytest, focused Cockpit UI Vitest if the terminal message files are touched, focused normalizer pytest, focused ruff, `py_compile`, Eval Spine manifest validation, JSON validation, and `git diff --check`.
- Run task-card `check-diff`, release the registry claim, write integration report artifacts, commit, then fast-forward canonical if the result remains safe.
