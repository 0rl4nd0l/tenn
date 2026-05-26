# Evidence

## Listener And Process Tree

Read-only commands:

```bash
ss -ltnp | rg ':8001'
ps -eo pid,ppid,stat,etime,cmd | rg 'llama-server|run_llama|llama-cpp|openclaw'
```

Findings:

- `0.0.0.0:8001` is listening under `llama-server` PID `3958508`.
- Parent process for PID `3958508` is PID `996`.
- PID `3958508` command uses `/home/l4nd0/tenn-runtime/tools/llama.cpp/build-cuda/bin/llama-server`, `--host 0.0.0.0`, `--port 8001`, `--models-dir /mnt/tenn-nvme2/tenn/models`, and API key argument `local-openai-key`.
- Child worker PID `3959547` listens on `127.0.0.1:58395` with model alias `model:qwen3.5-35b-a3b-apex`.

## Systemd Evidence

Read-only commands:

```bash
systemctl --user status llama-cpp-router.service llama-cpp-qwen25.service --no-pager
systemctl --user show llama-cpp-router.service llama-cpp-qwen25.service -p MainPID -p ActiveState -p ExecStart
journalctl --user -u llama-cpp-router.service -u llama-cpp-qwen25.service --since '2026-05-25 00:00:00'
```

Findings:

- `llama-cpp-router.service` is loaded but inactive/dead.
- `llama-cpp-qwen25.service` is loaded but inactive/dead.
- Both units report `MainPID=0` and `ExecStart=/home/l4nd0/tenn-runtime/scripts/run_llama_server.sh`.
- Journal evidence since 2026-05-25 only shows repeated `StartLimitIntervalSec` warnings for `llama-cpp-qwen25.service`, not an active owning invocation.

## GPU Guard

Read-only command:

```bash
bash scripts/gpu_process_guard.sh --check
```

Result:

- Exit code `0`.
- Warnings: `nvidia-smi` query returned exit `255`, so VRAM/process memory details were unavailable from the guard.

## Duplicate Search

Read-only GitHub search found only source issue #82 for the same root cause.
