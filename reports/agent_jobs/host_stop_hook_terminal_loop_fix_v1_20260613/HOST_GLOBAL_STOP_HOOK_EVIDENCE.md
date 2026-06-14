# Host Global Stop Hook Evidence

This PR does not track `/home/l4nd0/.codex/hooks/stop_check.py`.

Current host-local evidence at PR preservation time:

- Path: `/home/l4nd0/.codex/hooks/stop_check.py`
- Mode: `755`
- SHA-256: `313b1040dde552fd441b4d77f89b1316221a64fbb7295ec284f0eb53acfe7738`
- Behavior preserved by focused self-check:
  - first terminal dirty warning emits
  - repeated identical terminal dirty warning suppresses
  - non-terminal dirty warnings still emit

Key implementation markers observed in the host hook:

- `DEFAULT_CACHE_DIR = Path("/tmp/codex-stop-check")`
- `TERMINAL_GOAL_STATUSES = {"complete", "blocked", "usage_limited", "budget_limited"}`
- `terminal_handoff_complete(payload)`
- `repeated_terminal_warning(repo, messages)`

The host hook remains host-local. The repo PR preserves the evidence and the
report-local self-check only.
