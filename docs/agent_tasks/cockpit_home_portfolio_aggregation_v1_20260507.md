---
job_id: cockpit_home_portfolio_aggregation_v1_20260507
lane: Reporting
owner: Codex
allowed_files:
  - docs/agent_tasks/cockpit_home_portfolio_aggregation_v1_20260507.md
  - reports/agent_jobs/cockpit_home_portfolio_aggregation_v1_20260507/**
  - reports/agent_jobs/cockpit_home_portfolio_aggregation_v1_20260507/INVESTIGATION.md
  - reports/agent_jobs/cockpit_home_portfolio_aggregation_v1_20260507/README.md
  - reports/agent_jobs/cockpit_home_portfolio_aggregation_v1_20260507/diff-check.json
  - reports/agent_jobs/cockpit_home_portfolio_aggregation_v1_20260507/status.json
  - cockpit-ui/types/cockpit-home.ts
  - cockpit-ui/lib/cockpit-home-contract.ts
  - cockpit-ui/lib/cockpit-home-api.ts
  - cockpit-ui/lib/cockpit-home-api.test.ts
  - cockpit-ui/lib/cockpit-home-contract.test.ts
  - cockpit-ui/lib/mock/cockpit-home-fixtures.ts
  - cockpit-ui/app/api/cockpit/home/route.ts
  - cockpit-ui/components/cockpit/home/**
  - cockpit-ui/components/cockpit/home/home-page.tsx
  - financial-engine_v2/backend/app/routes/cockpit_api.py
  - financial-engine_v2/backend/app/services/cockpit_home.py
  - financial-engine_v2/backend/tests/test_cockpit_home_portfolio.py
approval_required: false
allow_unapproved_safe_extension: true
timeout_seconds: 7200
output_dir: reports/agent_jobs/cockpit_home_portfolio_aggregation_v1_20260507
mutation_mode: safe_extension
production_data_access: false
---

# Task

Investigate and, only if safe, wire Cockpit Home Portfolio Aggregation / Day Change v1.

The goal expose deterministic portfolio total, currency handling, pricing coverage, and day-change status from existing holdings/local backend state. Holdings remain local personal data, not financial truth.

# Hard boundaries

Do not fabricate portfolio totals, day change, FX conversions, or pricing coverage. Do not relabel holdings as financial truth. Do not touch financial truth, extraction, memory, Qdrant, embeddings, query orchestration, news ingestion, market movers, narrative synthesis, or unrelated Cockpit tabs.

# Required output

Write investigation and final report under:

reports/agent_jobs/cockpit_home_portfolio_aggregation_v1_20260507/

Proceed to implementation only if deterministic source fields exist and collision risk stays LOW or controlled MEDIUM.
