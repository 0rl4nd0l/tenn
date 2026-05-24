---
job_id: strategy_lab_status_card_browser_smoke_v1_20260524
lane: Reporting
owner: Codex
mutation_mode: audit_only
approval_required: false
production_data_access: false
timeout_seconds: 7200
output_dir: reports/agent_jobs/strategy_lab_status_card_browser_smoke_v1_20260524
allowed_files:
  - docs/agent_tasks/strategy_lab_status_card_browser_smoke_v1_20260524.md
  - reports/agent_jobs/strategy_lab_status_card_browser_smoke_v1_20260524/
  - reports/agent_jobs/strategy_lab_status_card_browser_smoke_v1_20260524/README.md
  - reports/agent_jobs/strategy_lab_status_card_browser_smoke_v1_20260524/status.json
---

# Strategy Lab Status Card Browser Smoke V1

Audit the landed Strategy Lab / QuantDinger Cockpit Home status card from
commit `0211a5b46091cd4858e402d10e3499a1e96819ab`.

## Scope

- Confirm branch and HEAD.
- Validate this task card.
- Run registry `list-active` and `check-overlap`.
- Inspect the Strategy Lab status route, status contract, server helper, Home
  card, Home insertion point, and focused tests.
- Rerun focused existing validation if available without dependency install.
- Run a browser/dev-server smoke only if supported without dependency install,
  production data access, runtime/data-store mutation, or prohibited service
  startup.
- Report whether the card displays honest pending-review/read-only wording and
  does not claim live functionality.

## Forbidden

- Do not touch `docs/agent_tasks/task_card_dirt_hygiene_v1_20260524.md`.
- Do not touch `backend_chat_evidence_guard_v1_20260524`.
- Do not implement trading, broker, paper/live execution, real QuantDinger
  transport/client/adapter, Tenn DB/Qdrant/news/memory/financial-truth writes,
  runtime/model/GPU config, dependency installation, service startup beyond a
  safe frontend-only dev server smoke, or unrelated repo hygiene.

## Deliverables

- `reports/agent_jobs/strategy_lab_status_card_browser_smoke_v1_20260524/README.md`
- `reports/agent_jobs/strategy_lab_status_card_browser_smoke_v1_20260524/status.json`
