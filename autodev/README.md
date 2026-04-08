# autodev

Tenn still contains the legacy AutoDev loop, but the supported OpenClaw path is now the native manager bridge:

- `python -m autodev.runtime.native_manager status`
- `python -m autodev.runtime.native_manager doctor`
- `python -m autodev.runtime.native_manager analyze "<request>"`
- `python -m autodev.runtime.native_manager fix "<request>"`
- `python -m autodev.runtime.native_manager verify "<request>"`

The shell entrypoint is:

- `scripts/openclaw-autodev <command>`

Preferred local inference path for the native manager is llama.cpp. Treat Ollama in this subsystem as compatibility/fallback behavior unless a specific workflow still requires it.

Local llama.cpp defaults now live in the repo:

- Launcher: `scripts/run_llama_server.sh`
- User service unit: `systemd/llama-cpp-router.service`
- Default endpoint: `http://127.0.0.1:8000/v1`
- Default model path: `models/model.gguf`
- Optional host override file: `~/.config/tenn/llama-server.env`
- Use the override file when a host-level port conflict requires llama.cpp to stay on a non-default port.
- Startup mode keeps `mmap` enabled and does not use `--mlock`; this build has no separate `--prefetch` flag.
- Launcher profiles: `interactive` (default), `balanced`, `throughput`
- Change the live service profile with `LLAMA_SERVER_PROFILE`, or override the raw sizing flags directly.

What the native manager does:

- Uses isolated repo snapshots for analyze/verify; any edits are discarded with the worktree
- Creates isolated git worktrees under `/tmp/tenn-openclaw/<run_id>/` for fix runs
- Runs Tenn worker prompts through the local coding agent
- Applies fix patches back only when the main worktree is safe
- Writes a run manifest under `autodev/reports/runs/<run_id>/`

Planner model selection:
- Uses `openai/gpt-4.1-mini` when `OPENAI_API_KEY` is present or a valid OpenClaw `openai` auth profile exists in `~/.openclaw/agents/main/agent/auth-profiles.json`.
- Preferred local planner/chat model is `llamacpp/qwen2.5-coder-14b`.
- Set `OPENCLAW_TENN_LOCAL_PLANNER_MODEL=llamacpp/qwen2.5-coder-14b` to pin the main planner/chat agent to local llama.cpp even when OpenAI auth is present.
- Otherwise it falls back to local planner model (`OPENCLAW_TENN_LOCAL_PLANNER_MODEL` or `ollama/<worker_model>`) when OpenAI credentials are absent.
- Force OpenAI-first behavior with `OPENCLAW_TENN_FORCE_OPENAI_PLANNER=1`.
- OpenClaw conversation context target defaults to `65536` tokens (override with `OPENCLAW_TENN_CONTEXT_TOKENS` before running `scripts/openclaw_runtime_recover.py --apply`).
- Local worker `num_ctx` defaults to `32768` (override with `OPENCLAW_TENN_WORKER_NUM_CTX`).
- Local llama.cpp worker endpoint defaults to `http://127.0.0.1:8000/v1` (override with `OPENCLAW_TENN_WORKER_OPENAI_BASE_URL` or `AUTODEV_LLAMA_CPP_BASE_URL`).

## Legacy runtime status

The older queue/daemon path remains in the repo only as a legacy scaffold:

- `autodev.runtime.autodev_loop`
- `autodev.runtime.control`
- `TASKS.md` queueing and discovery

These are no longer the primary OpenClaw integration path and should not be wired into the gateway or Control UI for new work.

## Security model
- Branch safety: no direct work on `main` or `master`; task work runs on `agent/YYYY-MM-DD/<task_slug>`.
- Sandbox execution: gate commands run in Docker when available (no network by default, constrained resources, read-only repo mount with writable `autodev_work/`).
- Restricted fallback runner: used when Docker is unavailable or fails, still governed by strict command allowlist.
- Command allowlist: only approved executables/subcommands are permitted.
- Auto-merge: not enabled by default.
- Auditability: every command execution is logged under `autodev/reports/runs/<run_id>/`.

## Local usage
### First run (Docker recommended)
- Build the gate image:
  - `docker build -t autodev-gates:latest -f autodev/docker/Dockerfile .`
- Run one iteration:
  - `python -m autodev.runtime.autodev_loop --once`
  - or `python3 -m autodev.runtime.autodev_loop --once`

### Local venv fallback (no Docker)
- `bash autodev/scripts/bootstrap_dev_env.sh`
- `source .venv-autodev/bin/activate`
- `python -m autodev.runtime.autodev_loop --once`

- One-shot run:
  - `python -m autodev.runtime.autodev_loop --once`
- Continuous run:
  - `python -m autodev.runtime.autodev_loop --daemon`

### Optional configuration
Set `AUTODEV_*` variables or create `autodev/autodev.yaml`:
- `AUTODEV_REPO_PATH`
- `AUTODEV_DEFAULT_BRANCH`
- `AUTODEV_MAX_RETRIES` (default `10`)
- `AUTODEV_ALLOW_NETWORK` (default `false`)
- `AUTODEV_PR_MODE` (`github` or `local_patch`, default `local_patch`)
- `AUTODEV_DAEMON_INTERVAL_SECONDS`
- `AUTODEV_GATE_TIMEOUT_SECONDS`
- `AUTODEV_USE_DOCKER` (default `true`)
- `AUTODEV_DOCKER_IMAGE` (default `autodev-gates:latest`)
- `AUTODEV_DOCKERFILE_PATH` (default `autodev/docker/Dockerfile`)
- `AUTODEV_DOCKER_AUTO_BUILD` (default `true`)
- `AUTODEV_MAX_CHANGED_LINES_PER_ATTEMPT` (default `300`)
- `AUTODEV_MAX_CHANGED_FILES` (default `20`)
- `AUTODEV_WORKER` (default `local_patch`)
- `AUTODEV_PROTECTED_PATHS` (comma-delimited denylist)
- `AUTODEV_BASELINE_PATH` (default `autodev/baselines/baseline_metrics.json`)
- `AUTODEV_ALLOW_BASELINE_INIT` (default `0`)
- `AUTODEV_ALLOW_BASELINE_UPDATE` (default `0`)
- `AUTODEV_PROTECTED_METRICS` (comma list of metrics to guard)
- `AUTODEV_REGRESSION_TOLERANCE_JSON` (JSON map like `{\"metric\": 0.01}`)
- `AUTODEV_ENABLE_DEBATE` (default `1`)
- `AUTODEV_DEBATE_STRICTNESS` (default `strict`)
- `AUTODEV_DEBATE_REQUIRE_3_FAILURE_MODES` (default `1`)

## Regression guard
- Baseline file lives at `autodev/baselines/baseline_metrics.json` by default.
- Every run writes `autodev/reports/runs/<run_id>/regression.json`.
- Key decisions:
  - `pass`: current metrics are within tolerance.
  - `fail`: protected metric regression beyond tolerance.
  - `baseline_initialized`: baseline created (requires `AUTODEV_ALLOW_BASELINE_INIT=1` and successful gates).
  - `baseline_updated`: baseline refreshed (requires `AUTODEV_ALLOW_BASELINE_UPDATE=1` and successful gates).
  - `baseline_init_blocked`: baseline missing and init flag not enabled.
- PR/completion is blocked when regression guard fails.

## Debate layer
- Each run writes:
  - `autodev/reports/runs/<run_id>/debate_pre.json`
  - `autodev/reports/runs/<run_id>/debate_post.json` (or `not_run` marker)
- Roles:
  - proposer: minimal plan and known risks
  - skeptic: adversarial failure-mode review and veto capability
  - auditor: policy/compliance review and veto capability
- A skeptic/auditor veto blocks progress and can trigger stop-retries behavior.
- Debate is advisory to safety checks; deterministic gates and regression guard remain authoritative.

## PR creation setup (least privilege)
- Use `AUTODEV_PR_MODE=github` only when a least-privilege GitHub token and `gh` authentication are already configured.
- If unavailable, runtime falls back to local patch instructions in the run report directory.

## Stop/disable daemon safely
- If started in foreground, stop with `Ctrl+C`.
- If started by scheduler/service, disable that scheduler job and verify no `autodev_loop --daemon` process remains.
- Confirm shutdown by checking no new files are appended under `autodev/reports/daily/`.
