---
job_id: news_loader_ollama_url_hardening_integrate_nvme_v1_20260515
lane: Query Orchestration
owner: Codex
mutation_mode: safe_extension
approval_required: true
approval_id: USER_APPROVED_NEWS_LOADER_OLLAMA_URL_HARDENING_INTEGRATE_NVME_20260515_GPT
production_data_access: false
timeout_seconds: 3600
output_dir: reports/agent_jobs/news_loader_ollama_url_hardening_integrate_nvme_v1_20260515
allowed_files:
  - docs/agent_tasks/news_loader_ollama_url_hardening_integrate_nvme_v1_20260515.md
  - scripts/load_news_to_qdrant.py
  - financial-engine_v2/backend/tests/test_load_news_to_qdrant.py
  - reports/agent_jobs/news_loader_ollama_url_hardening_integrate_nvme_v1_20260515/README.md
  - reports/agent_jobs/news_loader_ollama_url_hardening_integrate_nvme_v1_20260515/status.json
  - reports/agent_jobs/news_loader_ollama_url_hardening_integrate_nvme_v1_20260515/diff-check.json
---

# Task

Integrate committed loader hardening `a1802c757b54` into active NVMe.

# Boundaries

- No live news sync.
- No DB/Qdrant mutation.
- No runtime restart.
- No Docker build.
- No rented GPU/APEX work.
