# rented_gpu_runtime_integrate_nvme_v1_20260514

## Verdict

completed

## Session Declaration

- Agent: Codex
- Lane: Query Orchestration
- Branch: `fast/dev-storage-v1-20260513-170304`
- Worktree: `/home/l4nd0/tenn-fast-dev-storage-v1`
- Execution mode: SAFE EXTENSION
- Contested surfaces touched: yes, `financial-engine_v2/backend/app/routes/cockpit_api.py`, `financial-engine_v2/backend/app/services/cockpit_service.py`, and Cockpit UI chat/settings surfaces
- Collision risk: HIGH by surface, controlled by clean NVMe worktree, shared-registry claim, tight allowlist, and no live remote call
- Decision: proceed

## Source

- Source branch: `safe/rented-gpu-runtime-port-v1-20260514`
- Source worktree: `/home/l4nd0/tenn-rented-gpu-runtime-port-v1-20260514`
- Source commit: `5da86ab3eaba`
- Source subject: `milestone(query): add rented gpu runtime target`
- Integration method: clean `git cherry-pick --no-commit 5da86ab3eaba`, then removed prior clean-port task/report artifacts from this integration diff

## Preflight

- `date -Iseconds`: `2026-05-14T17:47:23+10:00`
- `pwd`: `/home/l4nd0/tenn-fast-dev-storage-v1`
- `git rev-parse --show-toplevel`: `/home/l4nd0/tenn-fast-dev-storage-v1`
- Branch before integration: `fast/dev-storage-v1-20260513-170304`
- HEAD before integration: `4e19b06dfa2d`
- Initial status before task-card creation: clean
- Task-card validation: pass
- Registry `list-active`: pass, `active_jobs: []`
- Registry `check-overlap`: pass, no issues
- Registry claim: pass, shared registry root `/mnt/hdd-data/home/l4nd0/tenn/.git/tenn-agent-registry`
- Source commit verification: pass, `5da86ab3eaba` reachable with expected feature files plus source task/report artifacts

## Runtime Status Check

No runtime was restarted.

- `curl -m 5 -sS http://127.0.0.1:8000/api/health || true`: `{"status":"ok"}`
- `curl -m 5 -sS http://127.0.0.1:8001/health || true`: `{"status":"ok"}`
- `curl -m 5 -sS http://127.0.0.1:8081/api/cockpit/health || true`: healthy response; backend, llama.cpp, Ollama, Qdrant, Redis, cockpit service, GPU, and host reported healthy

## Files Changed

- `docs/agent_tasks/rented_gpu_runtime_integrate_nvme_v1_20260514.md`
- `financial-engine_v2/backend/app/services/cockpit_service.py`
- `financial-engine_v2/backend/app/routes/cockpit_api.py`
- `cockpit-ui/lib/cockpit-types.ts`
- `cockpit-ui/lib/cockpit-store.ts`
- `cockpit-ui/lib/api-client.ts`
- `cockpit-ui/components/cockpit/cockpit-layout.tsx`
- `cockpit-ui/components/cockpit/chat/chat-screen.tsx`
- `cockpit-ui/components/cockpit/settings/settings-screen.tsx`
- `cockpit-ui/lib/marketplace-assistant.ts`
- `cockpit-ui/components/cockpit/cockpit-sidebar.test.tsx`
- `reports/agent_jobs/rented_gpu_runtime_integrate_nvme_v1_20260514/README.md`
- `reports/agent_jobs/rented_gpu_runtime_integrate_nvme_v1_20260514/status.json`
- `reports/agent_jobs/rented_gpu_runtime_integrate_nvme_v1_20260514/diff-check.json`

## Validation Results

- Backend py_compile: pass
  - `PYTHONPYCACHEPREFIX=/tmp/tenn_pycache python3 -m py_compile financial-engine_v2/backend/app/services/cockpit_service.py financial-engine_v2/backend/app/routes/cockpit_api.py`
- Frontend TypeScript: pass
  - `pnpm --dir cockpit-ui exec tsc --noEmit`
- Focused Vitest: pass, 3 files / 7 tests
  - `pnpm --dir cockpit-ui exec vitest run components/cockpit/cockpit-sidebar.test.tsx components/cockpit/settings/settings-screen.test.tsx lib/api-client.test.ts`
- No-remote smoke: pass
  - With rented GPU endpoint env vars unset, explicit `rented_gpu` raises `Rented GPU runtime is not configured. Set TENN_RENTED_GPU_LLAMACPP_URL before selecting rented_gpu.`
  - With rented GPU endpoint env vars unset, `auto` light context resolves to `('local', 'auto_rented_gpu_not_configured')`
  - The no-remote smoke used the existing preserve venv for dependencies while forcing `PYTHONPATH` to this NVMe checkout; no dependency install was performed
- Static whitespace check: pass
  - `git diff --check`
  - `git diff --cached --check`
- Final task-card diff check: pass, see `diff-check.json`

## Behavior Status

- `local | rented_gpu | auto` chat runtime target: present.
- Runtime target persisted in Cockpit preferences: present; patching `chat_runtime_target` is independent from other preferences.
- Chat requests send `runtime_target`: present for blocking and streaming chat requests.
- Rented GPU model discovery in Settings: present through runtime targets and rented GPU model group when remote models are discoverable.
- Rented GPU turns use runtime-scoped `LlamaCppClient`: present; remote turns create a rented GPU client and route normal chat through `/local` against that runtime.
- Local-first/default behavior: preserved. Default and invalid/missing preference fall back to `local`.
- Fail-fast missing endpoint: preserved. Explicit `rented_gpu` selection fails before fallback or remote client use when `TENN_RENTED_GPU_LLAMACPP_URL` is unset.
- Auto routing rule: preserved. `auto` uses rented GPU only when endpoint is configured and the turn is heavy: long prompt, attached sources, or strategy mode. Simple turns stay local.
- Settings runtime toggle and endpoint/health display: present.

## Impact Boundaries

- Marketplace assistant impact: type/runtime propagation only; behavior outside accepting `rented_gpu` as a source/runtime label was not changed.
- Source-label/provenance impact: none. Rented GPU data is runtime routing metadata, not source/evidence or financial-truth provenance.
- Runtime scripts / Docker / compose / model lifecycle scripts: not touched.
- Extraction / embeddings / vector config / Qdrant / Postgres / news / memory data: not touched.
- Financial Truth and source-label implementation files: not touched.

## Live Rented GPU Smoke Gap

No live rented GPU endpoint call was performed in this task.

Future live smoke setup:

```bash
export TENN_RENTED_GPU_LLAMACPP_URL=http://127.0.0.1:18001
ssh -i ~/.ssh/id_ed25519 -p <VAST_SSH_PORT> -L18001:localhost:8001 root@<VAST_SSH_HOST>
```

Future live smoke recommendation: with a user-approved tunnel task, verify `/v1/models`, explicit `rented_gpu` chat, `auto` heavy-turn routing, and clear failure after tunnel shutdown. Keep that task no-data and avoid financial-truth or memory writes.

## DATA_MISSING

- Live rented GPU endpoint health was not verified.
- Live rented GPU generation behavior was not verified.
- No SSH tunnel host/port was provided in this task.

## Final Git / Registry Status

- Final pre-commit diff is limited to allowed files.
- Registry release: pass; `rented_gpu_runtime_integrate_nvme_v1_20260514` released.
- Registry `list-active`: pass; `active_jobs: []`.
- Final git status after commit: to be recorded in the assistant closeout.

## Project Memory Save Recommendation

Save a project memory note after merge: rented GPU runtime-target integration was brought from `5da86ab3eaba` into `/home/l4nd0/tenn-fast-dev-storage-v1`, keeps local as default, fail-fasts on missing `TENN_RENTED_GPU_LLAMACPP_URL`, avoids live remote calls, and still needs a future tunnel smoke.
