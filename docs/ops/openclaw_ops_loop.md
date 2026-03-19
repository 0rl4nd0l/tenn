# OpenClaw Ops Loop for TENN

Use the documented native path: OpenClaw Gateway + Control UI for chat/session orchestration, with the Tenn bridge only handling isolated worktrees and run manifests.

For local assistant work in Tenn, llama.cpp is the preferred runtime over Ollama. Keep Ollama only where a specific backend or legacy helper still depends on it.

## 1) Pre-flight check

Run before maintenance work:

- `systemctl --user status llama-cpp-qwen25.service --no-pager -n 20`
- `scripts/openclaw-autodev status`
- `scripts/openclaw-autodev doctor`
- `openclaw agent --local --session-id health-chat -m "hi"`

If the local agent health check returns `NO`, `NO_REPLY`, timeout, or abort, repair the host runtime before asking for Tenn work.

Current local llama.cpp source of truth:

- Service unit: `systemd/llama-cpp-qwen25.service`
- Launcher: `scripts/run_llama_server.sh`
- Checked-in launcher default: `http://127.0.0.1:8000/v1`
- Current host override: `~/.config/tenn/llama-server.env` pins `LLAMA_SERVER_HOST=127.0.0.1` and `LLAMA_SERVER_PORT=8001`
- Current OpenClaw provider base URL: `http://127.0.0.1:8001/v1` in `~/.openclaw/openclaw.json`
- Default model path: `models/model.gguf`
- Optional host override file: `~/.config/tenn/llama-server.env`
- Startup profile keeps `mmap` enabled and does not use `--mlock`; this build has no separate `--prefetch` CLI flag.
- Launcher profiles: `interactive` (default `8192/512/256`), `balanced` (`16384/1024/512`), `throughput` (`32768/2048/512`)
- `LLAMA_SERVER_PROFILE` is the clean switch when you want to trade startup/latency against long-prompt throughput without hard-coding raw sizes.

Use `8001` for direct host smoke checks on this machine unless you have removed the override file. If the override is cleared, the launcher falls back to `8000`.

If mmap-based startup stalls in disk sleep on this host, pin `LLAMA_SERVER_MMAP=0` in the override file and restart the service. That direct-read path is currently the working host configuration for Qwen2.5-Coder-14B.

If planner/auth reports `missing_api_key` and you use OpenAI planner mode, bootstrap auth from 1Password CLI:

- `scripts/openclaw_sync_openai_auth_from_1password.py --secret-ref "op://<vault>/<item>/<field>"`

## 2) Native request style

Message OpenClaw naturally. The manager should decide whether to answer directly, analyze, fix, or verify.

Useful examples:

```text
Analyze the news ingestion pipeline and identify the highest-risk breakpoints.
```

```text
Fix the OpenClaw bridge so a follow-up verify run can confirm the patch cleanly.
```

```text
Verify the changes from the previous analysis and tell me what still needs work.
```

## 3) Bridge commands

The Tenn bridge is now a thin execution layer, not a daemon/task queue:

- `scripts/openclaw-autodev analyze "<request>"`
- `scripts/openclaw-autodev fix "<request>"`
- `scripts/openclaw-autodev verify "<request>"`
- `scripts/openclaw-autodev report [run_id]`
- `scripts/openclaw-autodev commands [run_id]`

From an MCP client, prefer the deterministic surface:

- `list_operations` to inspect the allowlisted Tenn operations manifest
- `openclaw_run_operation` with `operation_id` plus `mode=analyze|verify`
- `get_run_report` / `get_run_commands` with line ranges when a run artifact is too large to inspect whole
- `codex_memory_bootstrap`, `codex_memory_recall`, and `codex_memory_write_session` to carry useful context across Codex sessions

Compatibility aliases:

- `run`, `task`, and `task-run` still route into the new manager flow for one release, but they are deprecated.

Removed from the supported path:

- `start`
- `stop`
- `discover`
- `rag-index`
- `worker`
- `gates`

## 4) Safety model

- Analyze and verify runs execute in isolated worktrees; any edits are discarded after the run.
- Fix runs happen in isolated git worktrees under `/tmp/tenn-openclaw/<run_id>/`.
- Fix patches are applied back only when the destination files are not already dirty in the main worktree.
- Protected paths, especially `financial-engine_v2/`, stay blocked unless the request explicitly scopes to them.
- Every run writes a manifest under `autodev/reports/runs/<run_id>/` with `request.json`, `manager.json`, `workers.json`, `commands.json`, and `report.md`.

## 5) Recommended operator loop

1. Ask OpenClaw to analyze a scoped area.
2. Review the findings in chat or with `scripts/openclaw-autodev report`.
3. Ask OpenClaw to fix the specific issue.
4. Ask OpenClaw to verify the change set.
5. Use `scripts/openclaw-autodev commands` if you need the recorded bridge actions.

For MCP-backed assistant work, add one memory step:

6. Write a compact Codex session summary so the next session can recover context with `codex_memory_bootstrap` or `codex_memory_recall`.
