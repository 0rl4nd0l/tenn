# Vast GPU Operator Skill Runtime Gate Fix

## Verdict

completed

## Session

- Agent: Codex
- Lane: Query Orchestration
- Supporting lanes: Runtime / Evaluation / Repo Hygiene
- Execution mode: SAFE EXTENSION for docs/skill process; DRY-RUN ONLY for rental workflow
- Collision risk: MEDIUM
- Branch: `fast/dev-storage-v1-20260513-170304`
- Preflight HEAD: `59ff2511f47a`
- Worktree: `/home/l4nd0/tenn-fast-dev-storage-v1`
- Task card: `docs/agent_tasks/vast_gpu_operator_skill_runtime_gate_fix_v1_20260515.md`
- Real rental approval: `NO`

## Preflight Evidence

- `date -Iseconds`: `2026-05-15T15:35:56+10:00`
- `pwd`: `/home/l4nd0/tenn-fast-dev-storage-v1`
- `git rev-parse --show-toplevel`: `/home/l4nd0/tenn-fast-dev-storage-v1`
- `git branch --show-current`: `fast/dev-storage-v1-20260513-170304`
- `git rev-parse --short=12 HEAD`: `59ff2511f47a`
- Initial `git status --short --untracked-files=all`: only this task card was untracked after creation.
- `python3 scripts/agent_job_contract.py validate ...`: `ok: true`, no issues.
- `python3 scripts/agent_job_registry.py list-active`: `active_jobs: []`.
- `python3 scripts/agent_job_registry.py check-overlap ...`: `ok: true`, no issues.
- Claim: succeeded, shared registry record created for `vast_gpu_operator_skill_runtime_gate_fix_v1_20260515`.

## Runtime Baseline

- `curl -m 5 -sS http://127.0.0.1:8000/api/health || true`: `{"status":"ok"}`
- `curl -m 5 -sS http://127.0.0.1:8001/health || true`: `{"status":"ok"}`
- `curl -m 5 -sS http://127.0.0.1:8081/api/cockpit/health || true`: connection refused.

No runtime was restarted or mutated.

## Skill Source

- Skill file updated: `/home/l4nd0/.codex/skills/vast-gpu-operator/SKILL.md`
- Classification: outside repo but user-owned skill config
- Backup path: `/home/l4nd0/.codex/skills/vast-gpu-operator/SKILL.md.bak_20260515`
- Backup command: `cp /home/l4nd0/.codex/skills/vast-gpu-operator/SKILL.md /home/l4nd0/.codex/skills/vast-gpu-operator/SKILL.md.bak_20260515`
- Commit policy: external skill file is not committed into Tenn.

## Repo Docs Created

- `docs/runtime/rented_gpu_runtime_workflow.md`
- `docs/setup/rented_gpu_vast_runtime.md`

Both docs enforce the corrected workflow: GPU visibility is not enough; success requires remote `/v1/models` and local tunnel `/v1/models`.

## Workflow Changes

- Added the core principle that the operator rents a working remote LLM runtime, not merely a GPU box.
- Added required OpenAI-compatible llama.cpp gates:
  - remote `http://127.0.0.1:8001/v1/models`
  - local tunnel `http://127.0.0.1:18001/v1/models`
- Marked `nvidia-smi` as hardware proof only.
- Added pre-rental gates for runtime mode, localhost bind, tunnel, image/template contents, disk, setup duration, cost, destroy confirmation, and synthetic smoke prompt.
- Added image criteria preferring `ghcr.io/ggml-org/llama.cpp:server-cuda` or equivalent with `llama-server`.
- Added rejection criteria for bare `nvidia/cuda:*devel*` images and generic CUDA boxes without `llama-server` and GGUF model.
- Added immediate post-rental remote `/v1/models` gate within 2 minutes.
- Added local tunnel gate with `TENN_RENTED_GPU_LLAMACPP_URL=http://127.0.0.1:18001`.
- Added Tenn smoke gates requiring synthetic prompts and no real Tenn data sent remote.
- Added exact destroy confirmation text: `Confirm destroy Vast instance <INSTANCE_ID>.`
- Added per-attempt report requirements.

## Dry-Run Vast CLI Results

- `vastai show instances || true`: no active instances were listed; the CLI printed a deprecation notice recommending `vastai show instances-v1`.
- `vastai search offers 'gpu_name=RTX_4090' || true`: returned offer rows. Top displayed row was offer `28888234`, `2x RTX_4090`, `$0.5881/hr`; visible rows included multiple 4090 offers. The offer output did not include image/template, `llama-server`, GGUF model, or onstart evidence.
- `vastai search offers 'gpu_name=RTX_3090' || true`: returned offer rows. Top displayed row was offer `20210305`, `2x RTX_3090`, `$0.2547/hr`; visible rows included multiple 3090 offers. The offer output did not include image/template, `llama-server`, GGUF model, or onstart evidence.
- `vastai --help`: CLI supports `search offers`, `search templates`, `create instance`, `destroy instance`, and related commands.
- `vastai search --help`: invalid for this CLI because `search` is not a standalone command.
- `vastai search offers --help`: confirms custom offer query syntax and available offer fields.
- `vastai create instance --help`: confirms `--image` is required at minimum and `--template_hash`, `--disk`, `--ssh`, `--direct`, and `--onstart-cmd` are available.
- `vastai search templates --help`: confirms safe template search syntax and fields such as `image`, `docker_login_repo`, `hash_id`, `recommended_disk_space`, and `ssh_direct`.
- `vastai search templates 'image in ["ghcr.io/ggml-org/llama.cpp:server-cuda","ghcr.io/ggml-org/llama.cpp:full-cuda"]' || true`: `[]`.
- `vastai search templates 'docker_login_repo=ghcr.io/ggml-org/llama.cpp' || true`: `[]`.

No instance was created, destroyed, stopped, or tunneled.

## Scenario A Decision

Input: `nvidia/cuda:12.4.1-devel-ubuntu22.04`, no `llama-server`, no GGUF, no onstart, 40 GB disk, RTX 4090.

Decision: `reject_for_smoke`.

Reason: this is a GPU box, not a Tenn runtime. Do not rent for smoke unless the task is explicitly runtime provisioning with budget and setup approval. If already rented, recommend destroy or stop and request bootstrap approval.

## Scenario B Decision

Input: `ghcr.io/ggml-org/llama.cpp:server-cuda` or equivalent, `llama-server` present, GGUF present or mounted, onstart binds `127.0.0.1:8001`, `/v1/models` expected within 2 minutes.

Decision: `acceptable` only with max cost/time cap and exact destroy policy.

Required sequence: rent only after explicit approval, immediately test remote `/v1/models`, then tunnel `127.0.0.1:18001 -> remote localhost:8001`, then test local `/v1/models`, then run only synthetic Tenn smoke prompts.

## Next Real-Rental Checklist

- `REAL_RENTAL_TEST_APPROVED: YES`
- max hourly rate
- max runtime minutes
- max total budget
- target image/template or template hash
- model path or mounted GGUF volume
- onstart command binding `--host 127.0.0.1 --port 8001`
- exact destroy confirmation policy
- synthetic no-data smoke prompt

If any item is missing, do not rent.

## Files Changed

- `docs/agent_tasks/vast_gpu_operator_skill_runtime_gate_fix_v1_20260515.md`
- `docs/runtime/rented_gpu_runtime_workflow.md`
- `docs/setup/rented_gpu_vast_runtime.md`
- `reports/agent_jobs/vast_gpu_operator_skill_runtime_gate_fix_v1_20260515/README.md`
- `reports/agent_jobs/vast_gpu_operator_skill_runtime_gate_fix_v1_20260515/status.json`
- `reports/agent_jobs/vast_gpu_operator_skill_runtime_gate_fix_v1_20260515/diff-check.json`
- External, not committed: `/home/l4nd0/.codex/skills/vast-gpu-operator/SKILL.md`

## Files Intentionally Not Touched

- Tenn product code
- Runtime scripts
- DBs, Qdrant, Postgres, company memory, market memory, news DBs, Financial Truth
- Local runtime processes
- Vast paid instances

## Validation Results

- `git diff --check`: passed.
- Repo diff inspection: no Tenn product code changed.
- `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/vast_gpu_operator_skill_runtime_gate_fix_v1_20260515.md`: passed with no disallowed files.
- `git diff --cached --check`: passed after staging exact repo artifacts.
- Registry release and final active-job check are expected after commit; final command output is reported in the assistant closeout because releasing the claim is outside the committed artifact.
- Final post-commit `git status --short --untracked-files=all` is reported in the assistant closeout because committing this report changes HEAD.

## DATA_MISSING

- No exact Vast runtime template/hash was found for `ghcr.io/ggml-org/llama.cpp:server-cuda` or `full-cuda` by the safe template searches.
- No real instance ID, SSH host/port, created time, destroy deadline, remote `/v1/models`, local tunnel `/v1/models`, model IDs, or synthetic generation result exists because `REAL_RENTAL_TEST_APPROVED` was `NO`.
- Vast offer search output does not prove runtime image/template contents.

## Project Memory Save Recommendation

Save this routing lesson: Vast rental workflow must verify a remote OpenAI-compatible llama.cpp runtime with remote and tunneled `/v1/models`; `nvidia-smi` is insufficient, and bare CUDA images should be rejected for Tenn smoke unless the task is explicitly runtime provisioning with budget and destroy approval.
