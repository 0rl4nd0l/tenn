---
job_id: cockpit_home_market_movers_news_snapshot_v1_20260507
lane: Reporting
owner: Codex
allowed_files:
  - docs/agent_tasks/cockpit_home_market_movers_news_snapshot_v1_20260507.md
  - reports/agent_jobs/cockpit_home_market_movers_news_snapshot_v1_20260507/**
  - reports/agent_jobs/cockpit_home_market_movers_news_snapshot_v1_20260507/INVESTIGATION.md
  - reports/agent_jobs/cockpit_home_market_movers_news_snapshot_v1_20260507/README.md
  - reports/agent_jobs/cockpit_home_market_movers_news_snapshot_v1_20260507/diff-check.json
  - reports/agent_jobs/cockpit_home_market_movers_news_snapshot_v1_20260507/status.json
  - cockpit-ui/types/cockpit-home.ts
  - cockpit-ui/lib/cockpit-home-contract.ts
  - cockpit-ui/lib/cockpit-home-api.ts
  - cockpit-ui/lib/cockpit-home-api.test.ts
  - cockpit-ui/lib/cockpit-home-contract.test.ts
  - cockpit-ui/lib/mock/cockpit-home-fixtures.ts
  - cockpit-ui/app/api/cockpit/home/route.ts
  - cockpit-ui/components/cockpit/home/**
  - financial-engine_v2/backend/app/routes/cockpit_api.py
  - financial-engine_v2/backend/app/services/cockpit_home.py
  - financial-engine_v2/backend/tests/test_cockpit_home_market_movers.py
approval_required: false
allow_unapproved_safe_extension: true
timeout_seconds: 7200
output_dir: reports/agent_jobs/cockpit_home_market_movers_news_snapshot_v1_20260507
mutation_mode: safe_extension
production_data_access: false
---

# Task

Investigate and, only if safe, wire Cockpit Home Market Movers / News Snapshot v1.

The goal is to expose deterministic market movers or a clearly labelled news snapshot only if an existing backend/local source can support it with source/as_of/provenance. Do not synthesize market movers or news from LLM narrative.

# Hard boundaries

Do not fabricate movers, source IDs, price changes, headlines, or staleness. Do not mutate news stores, Qdrant, embeddings, ingestion pipelines, query orchestrator routing, financial truth, memory, market movers scrapers, narrative synthesis, or unrelated Cockpit tabs.

# Required output

Write investigation and final report under:

reports/agent_jobs/cockpit_home_market_movers_news_snapshot_v1_20260507/

Proceed to implementation only if deterministic source fields exist and collision risk stays LOW or controlled MEDIUM. If no safe source exists, report only and leave NO_MARKET_MOVERS_ENDPOINT / DATA_MISSING.
