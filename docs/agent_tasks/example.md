---
job_id: tenn-agent-hook-example
lane: Evaluation
owner: Codex
allowed_files:
  - .gitignore
  - AGENTS.md
  - CLAUDE.md
  - .codex/config.toml
  - .codex/hooks.json
  - .claude/settings.json
  - .gemini/settings.json
  - GEMINI.md
  - scripts/agent_job_contract.py
  - scripts/agent_job_hook.py
  - scripts/test_agent_job_hook.py
  - docs/agent_tasks/example.md
  - docs/agent_tasks/fixture.json
  - docs/claude/hooks.md
approval_required: true
timeout_seconds: 1200
output_dir: reports/agent_jobs/tenn-agent-hook-example
mutation_mode: safe_extension
production_data_access: false
---

# Example Tenn Agent Task

This task card exercises the repo-local Codex and Claude hook wrapper for a dev-agent contract change. It is intentionally scoped to agent instructions, hook config, wrapper code, focused tests, and hook documentation.
