# DATA_MISSING

- `scripts/agent_job_registry.py list-active --read-only --repo-root .` is not integrated in this baseline; fallback lock-backed `list-active` was used.
- GitHub Project field access/schema was not checked.
- Exact 2026-05-26 nightly-news fetch failure cause is absent from the two-line log.
- Definitive launcher/owner for live `llama-server :8001` beyond PPID 996 is unresolved.
- `nvidia-smi` memory/process details were unavailable during GPU guard check.
- Remote freshness and CI state for `safe/registry-readonly-no-lock-list-active-v1-20260525` were not fetched/checked.
