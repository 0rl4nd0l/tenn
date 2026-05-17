# M40 Service Restore From Known-Good Config

## Session declaration

```text
Lane: Runtime, mapped to repo lane Query Orchestration for the task-card validator
Branch: fast/dev-storage-v1-20260513-170304
Worktree: /home/l4nd0/tenn-fast-dev-storage-v1
Execution mode: SAFE EXTENSION
Intended files: task card, this report, scripts/runtime/m40_llama_router_8001_conservative.sh
Contested surfaces touched: none; no Cockpit routing, model files, data stores, or live systemd units changed
Collision risk: MEDIUM because the plan concerns the local M40 llama.cpp runtime
Decision: staged only; :8001 not intentionally restored; brief accidental start is documented below
```

## Current runtime state

- HEAD at preflight: `d4ef1cb381a9`.
- Worktree was clean at preflight.
- `127.0.0.1:18001` was already listening with `/home/l4nd0/.local/bin/llama-server`, PID `42231`.
- `[::1]:18001` was also occupied by an `ssh` process, PID `69262`.
- `127.0.0.1:8001` was not present in the listener check.
- `nvidia-smi` showed the Tesla M40 24GB at `00000000:2D:00.0` with the llama-server process using about `2611 MiB`.
- Kernel log tail from `journalctl -k -b` showed NVIDIA driver load messages and no fresh NVIDIA Xid in the captured tail.
- `scripts/gpu_process_guard.sh --json` marked the `:18001` known-good smoke server as a rogue because contract-authorised ports are `8001` and `8002`. For this task it was intentionally left running and only reused for validation.
- After the optional `:18001` validation, the known-good llama-server was no longer present on `:18001`; only an `ssh` listener remained on `127.0.0.1:18001`.

## Existing service/config path

System-level service checks:

```bash
systemctl cat llama-cpp-router.service || true
systemctl status llama-cpp-router.service --no-pager || true
systemctl list-unit-files | grep -Ei 'llama|router|model' || true
```

Results:

- System `llama-cpp-router.service` was not found.
- System unit-file list only showed `ollama.service` and `ollama-warmup.service`.

User-level service checks:

```bash
systemctl --user cat llama-cpp-router.service || true
systemctl --user status llama-cpp-router.service --no-pager || true
systemctl --user list-unit-files | grep -Ei 'llama|router|model' || true
systemctl --user cat llama-cpp-qwen25.service || true
systemctl --user status llama-cpp-qwen25.service --no-pager || true
```

Results:

- `llama-cpp-router.service` exists at `/home/l4nd0/.config/systemd/user/llama-cpp-router.service`.
- It is disabled and inactive.
- Its `ExecStart` points to `/mnt/sdb2/home/l4nd0/tenn/scripts/run_llama_server.sh`.
- Its `WorkingDirectory` points to `/mnt/sdb2/home/l4nd0/tenn`.
- `llama-cpp-qwen25.service` also exists, disabled and inactive.
- The legacy unit points to `/home/l4nd0/tenn/scripts/run_llama_server.sh` and logs `StartLimitIntervalSec` as an unknown key in the service section.
- The checked-in `systemd/llama-cpp-router.service` in this worktree also points to `/mnt/sdb2/home/l4nd0/tenn/scripts/run_llama_server.sh`.

## Risky path vs known-good path

Risky or not-yet-restored path:

- `scripts/run_llama_server.sh` defaults to router mode with `--models-dir /mnt/nvme/tenn/models --models-max 1`.
- It can use `~/.config/tenn/llamacpp-presets.ini`, including larger model aliases.
- It is still connected to the APEX/Qwen3.5-class default model history.
- Older failed paths involved auto/large server behavior such as higher context, multiple slots/parallelism, prompt cache, `kv_unified=true`, fit/device-memory behavior, and device confusion.

Known-good conservative path:

- Single Qwen2.5 14B GGUF: `/mnt/hdd-data/home/l4nd0/tenn/models/qwen2.5-14b-instruct-q4_k_m.gguf`.
- Explicit `--device CUDA0`, which was validated as the Tesla M40 in the successful smoke environment.
- `--split-mode none`.
- `--main-gpu 0`.
- `--fit off`.
- `--parallel 1`.
- `--cache-ram 0`.
- `--ctx-size 512`.
- `--n-gpu-layers 8`.
- No APEX/Qwen3.5 load.

## Proposed :8001 command

Preferred staged command, after stopping the `:18001` smoke server if it is still running:

```bash
M40_RESTORE_8001_CONFIRMED=1 /home/l4nd0/tenn-fast-dev-storage-v1/scripts/runtime/m40_llama_router_8001_conservative.sh
```

Exact underlying command:

```bash
/home/l4nd0/.local/bin/llama-server \
  --model /mnt/hdd-data/home/l4nd0/tenn/models/qwen2.5-14b-instruct-q4_k_m.gguf \
  --host 127.0.0.1 \
  --port 8001 \
  --n-gpu-layers 8 \
  --ctx-size 512 \
  --device CUDA0 \
  --split-mode none \
  --main-gpu 0 \
  --fit off \
  --parallel 1 \
  --cache-ram 0
```

Manual background form:

```bash
M40_RESTORE_8001_CONFIRMED=1 nohup /home/l4nd0/tenn-fast-dev-storage-v1/scripts/runtime/m40_llama_router_8001_conservative.sh \
  > /tmp/llama-server-8001-conservative.log 2>&1 &
```

This is intentionally not installed into systemd in this task. A later install step should update or replace the user-unit path only after this command passes validation on `:8001`.

## Rollback command

If the manual foreground command is running, stop it with `Ctrl-C`.

If it was started in the background:

```bash
pkill -TERM -f 'llama-server.*--port 8001\b' || true
sleep 2
ss -ltnp | grep -E ':8001|:18001' || true
```

If a systemd unit is later wired to this wrapper, rollback should be:

```bash
systemctl --user stop llama-cpp-router.service
systemctl --user disable llama-cpp-router.service
systemctl --user daemon-reload
```

## Validation checklist

Before starting:

```bash
ss -ltnp | grep -E ':8001|:18001' || true
nvidia-smi
journalctl -k -b --no-pager | grep -iE 'xid|nvrm|cuda|gpu' | tail -160
```

If `:18001` is still running, stop the smoke server before starting `:8001` so there is only one independent M40 llama-server:

```bash
pkill -TERM -f 'llama-server.*--port 18001\b' || true
sleep 2
ss -ltnp | grep -E ':8001|:18001' || true
```

After starting `:8001`:

```bash
curl -s http://127.0.0.1:8001/health
curl -s http://127.0.0.1:8001/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model":"local","messages":[{"role":"user","content":"Reply exactly: ok"}],"max_tokens":8,"temperature":0}'
nvidia-smi
journalctl -k -b --no-pager | grep -iE 'xid|nvrm|cuda|gpu' | tail -160
```

Pass criteria:

- `/health` returns `{"status":"ok"}`.
- Chat completion returns assistant content `ok`.
- `nvidia-smi` shows the process on the Tesla M40, not the GT 1030.
- Kernel log tail shows no fresh NVIDIA Xid after the request.
- No APEX/Qwen3.5 model load was attempted.

## Optional :18001 validation performed

Because the known-good `:18001` server was already running, it was validated but not killed:

- `curl -s http://127.0.0.1:18001/health || true` returned `{"status":"ok"}`.
- A `/v1/chat/completions` request with `max_tokens: 8` returned assistant content `ok`.
- `nvidia-smi` showed llama-server PID `42231` on the Tesla M40 using about `2611 MiB`.
- `journalctl -k -b` showed no fresh NVIDIA Xid in the captured tail after validation.

## Safety incident during staging

While testing the wrapper safety path, the `:18001` llama-server had already disappeared and only an `ssh` listener remained on `:18001`. Because the initial wrapper only blocked when a `:18001` llama-server was present, it briefly started the conservative command on `127.0.0.1:8001` as PID `92805`. That was stopped immediately with `TERM`; the follow-up listener check showed no `:8001`, and `nvidia-smi` showed no M40 compute process.

The wrapper now refuses to start unless `M40_RESTORE_8001_CONFIRMED=1` is set, so a direct validation run cannot bind `:8001` accidentally.

## Remaining risks

- `:8001` has not been intentionally restored or validated yet in this task.
- `:8001` was briefly started accidentally during wrapper guard testing, then stopped immediately; no production service was installed, enabled, or left running.
- The current live user unit still points to older checkout paths and `scripts/run_llama_server.sh`; do not restart it expecting the conservative command.
- This is Qwen2.5 conservative mode, not APEX/Qwen3.5 restoration.
- `:18001` remains an independent smoke server and should be stopped before a real `:8001` restore attempt.
