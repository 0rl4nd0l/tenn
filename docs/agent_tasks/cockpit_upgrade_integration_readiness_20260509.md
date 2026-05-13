---
job_id: cockpit_upgrade_integration_readiness_20260509
lane: Reporting
owner: Claude
allowed_files:
  - docs/agent_tasks/cockpit_upgrade_integration_readiness_20260509.md
  - reports/agent_jobs/cockpit_upgrade_integration_readiness_20260509/**
approval_required: false
timeout_seconds: 2400
output_dir: reports/agent_jobs/cockpit_upgrade_integration_readiness_20260509
mutation_mode: audit_only
production_data_access: false
---

# Task

Audit current Cockpit upgrade integration readiness. Identify which Cockpit/UI branches are pending, which are already merged, which are obsolete, and which should be integrated first. Produce a precise implementation handoff/task card if appropriate. Do not implement in this audit.

# Hard boundaries

- Do not edit source code.
- Do not stage files.
- Do not commit.
- Do not merge, cherry-pick, rebase, reset, stash, clean, prune, or delete anything.
- Do not restart Cockpit, backend, llama-server, or any runtime process.
- Do not mutate Tenn databases, Qdrant, Postgres, SQLite stores, news stores, company memory, market memory, financial truth, gold/eval data, or runtime data.
- Do not touch Evaluation dirty worktrees.
- Do not touch financial-engine_v2/** unless only reading files to understand route ownership.
- Allowed writes are only:
  - docs/agent_tasks/cockpit_upgrade_integration_readiness_20260509.md
  - reports/agent_jobs/cockpit_upgrade_integration_readiness_20260509/**

# Required preflight

Run and record:

- date -Iseconds
- pwd
- git rev-parse --show-toplevel
- git rev-parse --abbrev-ref HEAD
- git rev-parse HEAD
- git rev-parse --short=12 HEAD
- git status --short --untracked-files=all
- git log --oneline --decorate -15
- git worktree list
- git worktree list --porcelain
- python3 scripts/agent_job_registry.py list-active || true
- python3 scripts/agent_job_registry.py check-overlap docs/agent_tasks/cockpit_upgrade_integration_readiness_20260509.md || true
- python3 scripts/agent_job_contract.py validate docs/agent_tasks/cockpit_upgrade_integration_readiness_20260509.md || true

If graphify-out/GRAPH_REPORT.md exists, inspect the header before broad searches:

- test -f graphify-out/GRAPH_REPORT.md && sed -n '1,120p' graphify-out/GRAPH_REPORT.md || true

# Runtime visibility check

Read-only only:

- ss -ltnp | grep -E ':8081|:3000|:8000|:8001|:8002' || true
- lsof -nP -iTCP:8081 -sTCP:LISTEN || true
- lsof -nP -iTCP:3000 -sTCP:LISTEN || true
- ps -eo pid,ppid,lstart,etime,cmd | grep -Ei 'next|node|pnpm|npm|yarn|turbo|vite' | grep -v grep || true

For each Next/Cockpit PID found:

- readlink -f /proc/<PID>/cwd || true
- tr '\0' '\n' < /proc/<PID>/environ | grep -E '^(PORT|NODE_ENV|NEXT|NEXT_PUBLIC|TENN|PWD)' || true

If :8081 is live:

- curl -sI http://127.0.0.1:8081 | head -30 || true

If :3000 is live:

- curl -sI http://127.0.0.1:3000 | head -30 || true

# Branch/worktree discovery

Find Cockpit-relevant branches/worktrees and classify.

Relevant surfaces:

- cockpit-ui/**
- financial-engine_v2/backend/app/routes/cockpit_api.py
- financial-engine_v2/backend/app/routes/chat.py
- financial-engine_v2/backend/app/services/tenn_chat.py
- cockpit/core/**
- financial-engine_v2/cockpit/**
- docs/agent_tasks/*cockpit*
- reports/agent_jobs/*cockpit*
- reports/agent_jobs/*source-label*
- reports/agent_jobs/*marketplace*

# Audit questions

Answer with evidence:

1. Current runtime branch/HEAD.
2. Main preserve worktree state and registry state.
3. Candidate branch table.
4. Safest first integration target.
5. Implementation handoff if a safe target exists.

# Required report artifacts

Write only under:

reports/agent_jobs/cockpit_upgrade_integration_readiness_20260509/

Required files:

- README.md
- status.json
- candidate_branch_matrix.md
- runtime_visibility.md
- recommended_integration_handoff.md
