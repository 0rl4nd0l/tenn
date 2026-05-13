# Runtime Topology NVMe Consolidation Audit

Date: 2026-05-13T18:18:22+10:00

## Verdict

BLOCKED: runtime migration was not performed.

The audit confirmed the live local runtime still serves from the HDD preserve checkout for llama.cpp and Cockpit UI, while the backend container was launched by the compose project rooted at `/home/l4nd0/tenn`, which resolves to `/mnt/hdd-data/home/l4nd0/tenn`.

Restart was unsafe in this turn because the clean NVMe worktree does not currently contain the runtime artifacts needed for an equivalent launch, and the copied launcher configuration still points back to the HDD preserve checkout:

- `/home/l4nd0/tenn-fast-dev-storage-v1/tools/llama.cpp/build-cuda/bin/llama-server`: missing
- `/home/l4nd0/tenn-fast-dev-storage-v1/cockpit-ui/node_modules`: missing
- `/home/l4nd0/tenn-fast-dev-storage-v1/financial-engine_v2/.venv`: missing
- `/home/l4nd0/tenn-fast-dev-storage-v1/scripts/start_config.env` sets `ENGINE_ROOT="/home/l4nd0/tenn/financial-engine_v2"`, and `/home/l4nd0/tenn` resolves to `/mnt/hdd-data/home/l4nd0/tenn`

No product code, runtime config, model config, databases, Qdrant, embeddings, memory stores, gold labels, extraction prompts, or source PDFs were intentionally modified.

## Preflight

| Check | Result |
| --- | --- |
| `pwd` | `/home/l4nd0/tenn` |
| Git toplevel | `/mnt/hdd-data/home/l4nd0/tenn` |
| Preserve branch | `preserve/dirty-work-20260430T065748Z` |
| Preserve HEAD | `c8e0c00808cb52daa31df22cdeeb41f6c8d50d45` |
| NVMe branch | `fast/dev-storage-v1-20260513-170304` |
| NVMe HEAD | `c8e0c00808cb52daa31df22cdeeb41f6c8d50d45` |
| NVMe status | clean |
| Shared active registry jobs | `[]` |
| Task-card validation | pass |
| Registry claim / overlap | blocked by unrelated untracked preserve task cards outside `allowed_files` |
| GPU guard | pass, exit 0 |
| `:8002` | offline / no listener |

Preserve had unrelated untracked task-card files before this job. This job added only its own task card and report.

## Before Runtime Process Table

| Service | Port | PID(s) | Owner | Launch evidence | CWD / root evidence |
| --- | ---: | --- | --- | --- | --- |
| Backend API | 8000 | container `fe_backend`, host PID `3334235` | Docker compose | `uvicorn app.main:app --host 0.0.0.0 --port 8000` | compose labels: working dir `/home/l4nd0/tenn/financial-engine_v2`; bind mounts from `/home/l4nd0/tenn`, which resolves to HDD preserve. `/proc` cwd unreadable due root/container permissions. |
| llama.cpp router | 8001 | `3334861`, child `3336701` | host process | `tools/llama.cpp/build-cuda/bin/llama-server ... --port 8001 ... --models-dir /mnt/nvme/tenn/models ... --models-preset /home/l4nd0/.config/tenn/llamacpp-presets.ini` | `/mnt/hdd-data/home/l4nd0/tenn` |
| Cockpit Next.js | 8081 | launcher `3336346`, server `3336377` | host process | `pnpm start --port 8081` via `cockpit reboot full` | `/mnt/hdd-data/home/l4nd0/tenn/cockpit-ui` |
| Extraction llama.cpp | 8002 | none | n/a | no listener | offline |

Unrelated process noted but not touched: a Next dev server on port `3001` from `/mnt/hdd-data/home/l4nd0/tenn-home-frontend-wiring-v1-20260513`.

## After Runtime Process Table

No restart was performed, so the after table is intentionally unchanged.

| Service | Port | After state |
| --- | ---: | --- |
| Backend API | 8000 | still served by existing Docker compose stack rooted at `/home/l4nd0/tenn` -> HDD preserve |
| llama.cpp router | 8001 | still served by existing HDD preserve cwd process |
| Cockpit Next.js | 8081 | still served by existing HDD preserve `cockpit-ui` cwd process |
| Extraction llama.cpp | 8002 | still offline |

## Before / After CWD Table

| Service | Before | After | NVMe? |
| --- | --- | --- | --- |
| Backend API | Docker compose root `/home/l4nd0/tenn/financial-engine_v2` -> `/mnt/hdd-data/home/l4nd0/tenn/financial-engine_v2` | unchanged | no |
| llama.cpp router parent | `/mnt/hdd-data/home/l4nd0/tenn` | unchanged | no |
| llama.cpp router loaded child | `/mnt/hdd-data/home/l4nd0/tenn` | unchanged | no |
| Cockpit Next.js launcher/server | `/mnt/hdd-data/home/l4nd0/tenn/cockpit-ui` | unchanged | no |

## Health Probes

These probes were run before any restart decision. They describe the existing HDD-backed runtime.

| Probe | Result | Latency |
| --- | --- | ---: |
| `http://127.0.0.1:8000/api/health` | `200`, `{"status":"ok"}` | 0.000739s |
| `http://127.0.0.1:8001/health` | `200`, `{"status":"ok"}` | 0.000230s |
| `http://127.0.0.1:8001/v1/models` | `200`; model list returned; `model:qwen3.5-35b-a3b-apex` loaded | 0.000442s |
| `http://127.0.0.1:8081/api/cockpit/health` | `200`; backend, llama.cpp, Ollama, Qdrant, Redis, cockpit service, GPU, and host reported healthy | 0.095085s |
| `http://127.0.0.1:8081/api/cockpit/home` | timeout, no response body | 20.000094s |

## Stop / Start Commands

No stop/start commands were executed.

Equivalent safe restart commands are DATA_MISSING because:

- the normal `cockpit` symlink resolves to `/home/l4nd0/tenn/scripts/cockpit`, which is the HDD preserve checkout;
- the NVMe copy of `scripts/start_config.env` still points `ENGINE_ROOT` and `COMPOSE_FILE` at `/home/l4nd0/tenn/financial-engine_v2`;
- starting llama.cpp from the NVMe script would look for the NVMe `tools/llama.cpp/build-cuda/bin/llama-server`, which is absent;
- starting Cockpit from NVMe would need dependency installation or another explicit dependency strategy because `cockpit-ui/node_modules` is absent;
- editing launcher config or rebuilding/installing runtime dependencies was outside the allowed file set and could change runtime/config state beyond this audit.

## Runtime Now Serves From NVMe?

No. Runtime still serves from HDD preserve.

## Services Still Pointing To HDD Preserve

- Backend compose project and bind mounts
- llama.cpp router parent process
- llama.cpp loaded model child process
- Cockpit Next.js launcher and server

## Files Changed

- `docs/agent_tasks/runtime_topology_nvme_consolidation_v1_20260513.md`
- `reports/agent_jobs/runtime_topology_nvme_consolidation_v1_20260513/README.md`
- `reports/agent_jobs/runtime_topology_nvme_consolidation_v1_20260513/diff-check.json`

## Validation Results

| Validation | Result |
| --- | --- |
| Task-card validate | pass |
| Registry list-active | pass, no active jobs |
| Registry check-overlap | blocked by unrelated untracked preserve task cards |
| Registry claim | blocked by unrelated untracked preserve task cards |
| GPU process guard | pass, exit 0 |
| Current listeners | `:8000`, `:8001`, `:8081`; no `:8002` listener |
| Health probes | existing runtime mostly healthy; Cockpit Home endpoint timed out |
| NVMe git status before restart gate | clean |
| Restart gate | fail / blocked |
| `check-diff` artifact | written to `diff-check.json`; result blocked by unrelated preserve task cards |

## Remaining Blockers

1. Decide whether launcher configuration may be changed to point canonical startup at `/home/l4nd0/tenn-fast-dev-storage-v1`.
2. Decide whether ignored runtime dependencies may be installed or built in the NVMe worktree.
3. Decide whether Docker compose containers may be recreated from NVMe compose files while preserving the same named volumes and host service endpoints.
4. Clear or isolate the unrelated preserve task-card dirt if strict registry claim/check-diff enforcement is required.
5. Investigate the existing `/api/cockpit/home` timeout separately; it existed before migration and should not be conflated with topology consolidation.

## Next Safe Step

Create a follow-up safe-extension task that explicitly allows either:

- updating host-local launch routing to the NVMe worktree and installing/building ignored runtime dependencies there; or
- running a one-shot manual NVMe-based compose/Cockpit/llama launch plan with explicit commands, without editing product code or data stores.

The follow-up should include a pre-approved rollback path for restoring the current HDD-backed runtime if any health probe regresses.

## `/save` Recommendation

Recommended after user review: `/save` this BLOCKED topology audit so future runtime work starts from the confirmed blockers instead of rediscovering HDD launcher resolution, missing NVMe runtime artifacts, and the pre-existing Cockpit Home timeout.
