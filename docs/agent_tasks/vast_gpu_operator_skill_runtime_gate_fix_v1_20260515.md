---
job_id: vast_gpu_operator_skill_runtime_gate_fix_v1_20260515
lane: Query Orchestration
owner: Codex
mutation_mode: safe_extension
approval_required: true
approval_id: USER_APPROVED_VAST_GPU_OPERATOR_SKILL_RUNTIME_GATE_FIX_20260515_GPT
production_data_access: false
timeout_seconds: 7200
output_dir: reports/agent_jobs/vast_gpu_operator_skill_runtime_gate_fix_v1_20260515
allowed_files:
  - docs/agent_tasks/vast_gpu_operator_skill_runtime_gate_fix_v1_20260515.md
  - docs/runtime/rented_gpu_runtime_workflow.md
  - docs/setup/rented_gpu_vast_runtime.md
  - reports/agent_jobs/vast_gpu_operator_skill_runtime_gate_fix_v1_20260515/README.md
  - reports/agent_jobs/vast_gpu_operator_skill_runtime_gate_fix_v1_20260515/status.json
  - reports/agent_jobs/vast_gpu_operator_skill_runtime_gate_fix_v1_20260515/diff-check.json
---

# Optional real-rental approval

REAL_RENTAL_TEST_APPROVED: NO

Do not rent, destroy, or mutate paid Vast instances unless `REAL_RENTAL_TEST_APPROVED` is changed to `YES` and the prompt includes an exact maximum cost/time budget and exact destroy confirmation text.

# Task

Fix the rented-GPU operator workflow so it rents a usable OpenAI-compatible llama.cpp runtime, not merely a GPU box, then retest the workflow with a no-cost dry run.

Primary lane: Query Orchestration
Supporting lanes: Runtime / Evaluation / Repo Hygiene
Mode: SAFE EXTENSION for docs/skill process; DRY-RUN ONLY for rental workflow
Expected collision risk: MEDIUM

# Background / failure to prevent

Previous rented GPU attempt failed because the workflow treated `nvidia-smi` success as sufficient. That was wrong.

What happened:
- Vast instance `36739812` was reachable over SSH.
- RTX 4090 was visible with `nvidia-smi`.
- But it was a bare CUDA image:
  - no `llama-server`
  - no `llama-cli`
  - no `.gguf`
  - no useful `/root/onstart.sh`
  - no remote listener on `127.0.0.1:8001`
  - local tunnel `127.0.0.1:18001` had no `/v1/models`
- Tenn needed a remote OpenAI-compatible llama.cpp endpoint, not just a GPU.
- Correct success gate is:
  - remote `curl http://127.0.0.1:8001/v1/models`
  - local tunnel `curl http://127.0.0.1:18001/v1/models`
- Future rental must select or provision a runtime image/template that can reach `/v1/models` within 5-10 minutes.

# Required preflight

Run from:

`/home/l4nd0/tenn-fast-dev-storage-v1`

Commands:

- date -Iseconds
- pwd
- git rev-parse --show-toplevel
- git branch --show-current
- git rev-parse --short=12 HEAD
- git status --short --untracked-files=all
- git worktree list
- python3 scripts/agent_job_contract.py validate docs/agent_tasks/vast_gpu_operator_skill_runtime_gate_fix_v1_20260515.md
- python3 scripts/agent_job_registry.py list-active
- python3 scripts/agent_job_registry.py check-overlap docs/agent_tasks/vast_gpu_operator_skill_runtime_gate_fix_v1_20260515.md
- claim task if safe

Runtime baseline, read-only:

- curl -m 5 -sS http://127.0.0.1:8000/api/health || true
- curl -m 5 -sS http://127.0.0.1:8001/health || true
- curl -m 5 -sS http://127.0.0.1:8081/api/cockpit/health || true

# Phase 1 - Locate current GPU-rent skill/process source

Locate the current Vast/GPU operator skill or workflow text.

Search likely locations read-only:

- `find ~/.claude -iname '*vast*' -o -iname '*gpu*' -o -iname 'SKILL.md' 2>/dev/null | head -100`
- `find /home/l4nd0 -path '*/skills/*' -iname 'SKILL.md' 2>/dev/null | grep -Ei 'vast|gpu|rent|operator' || true`
- `rg -n "vast-gpu|Vast|rented GPU|llama.cpp|TENN_RENTED_GPU|18001|8001|nvidia-smi" ~/.claude /home/l4nd0/tenn-fast-dev-storage-v1 docs scripts 2>/dev/null || true`

Classify the skill/process source as:

- inside repo and editable under task card;
- outside repo but user-owned skill config;
- DATA_MISSING.

If the skill file is outside the repo:
- back it up before editing:
  `cp <skill_file> <skill_file>.bak_20260515`
- it is user-approved to edit the skill/process file for this task.
- record the exact path and backup path in the report.
- do not try to commit external skill files into the Tenn repo.
- still commit the repo-side task card/report/docs if created.

If no skill file is found:
- create repo documentation only:
  - `docs/runtime/rented_gpu_runtime_workflow.md`
  - `docs/setup/rented_gpu_vast_runtime.md`
- report DATA_MISSING for actual skill location.

# Phase 2 - Fix the workflow/skill

Update the skill/process so it enforces this corrected contract.

Required wording/concepts to add:

## Core principle

The workflow must rent a working remote LLM runtime, not merely a GPU.

Success requires an OpenAI-compatible llama.cpp endpoint:

- remote: `http://127.0.0.1:8001/v1/models`
- local tunnel: `http://127.0.0.1:18001/v1/models`

`nvidia-smi` is only hardware proof, not runtime proof.

## Required pre-rental gates

Before renting, the skill must ask/verify:

1. What runtime mode is required?
   - For Tenn: `llama.cpp OpenAI-compatible server`.
2. What remote bind is required?
   - `127.0.0.1:8001`, not public internet.
3. What local tunnel is required?
   - `127.0.0.1:18001 -> remote localhost:8001`.
4. Does the image/template already include:
   - `llama-server`
   - a `.gguf` model
   - a startup/onstart command
   - enough disk for model/runtime
5. If not preloaded, is setup possible within 5-10 minutes without broad build/download?
6. What is the hourly cost and hard destroy time?
7. What exact destroy command/confirmation is required?
8. What synthetic no-data smoke prompt will be used?

## Required image/template criteria

Prefer:

- official `ghcr.io/ggml-org/llama.cpp:server-cuda`, or an equivalent image with `llama-server`;
- preloaded GGUF model or mounted model volume;
- startup/onstart command that binds:
  `--host 127.0.0.1 --port 8001`;
- OpenAI-compatible endpoints:
  `/v1/models`
  `/v1/chat/completions`;
- enough disk for selected GGUF model and logs.

Avoid:

- bare `nvidia/cuda:*devel*` images for runtime smoke;
- generic CUDA boxes without `llama-server` and model;
- public bind to `0.0.0.0` unless explicitly secured;
- broad installs/downloads during paid smoke unless explicitly approved.

## Immediate post-rental gates

Within the first 2 minutes after rental, verify:

```bash
ssh ...
nvidia-smi
curl -m 10 -sS http://127.0.0.1:8001/v1/models
```

If remote `/v1/models` fails and no fast already-present runtime/model exists, stop and recommend destroy.

## Local tunnel gate

```bash
export TENN_RENTED_GPU_LLAMACPP_URL=http://127.0.0.1:18001

ssh -i ~/.ssh/vastai_nopass \
  -o IdentitiesOnly=yes \
  -o StrictHostKeyChecking=accept-new \
  -p <VAST_SSH_PORT> \
  -L18001:localhost:8001 \
  root@<VAST_SSH_HOST>
```

Then verify:

```bash
curl -m 10 -sS http://127.0.0.1:18001/v1/models
```

## Tenn smoke gates

Use only synthetic prompts.

Check:

- local default remains local;
- explicit `rented_gpu` routes remote only when endpoint configured;
- auto light/simple stays local;
- auto heavy routes remote only when configured and heavy criteria are present;
- bad endpoint fails clearly;
- no real Tenn data is sent remote.

## Destruction / cost guard

The skill must require exact user confirmation before destroy:

`Confirm destroy Vast instance <INSTANCE_ID>.`

But the skill should proactively recommend destroy when:

- `/v1/models` cannot be reached quickly;
- runtime/model is absent;
- cost window is approaching;
- smoke is complete.

## Report requirements

Each rented-GPU attempt report must include:

- instance ID
- GPU/model
- image/template
- price/hr
- SSH host/port
- created time
- destroy deadline
- remote `/v1/models` result
- local tunnel `/v1/models` result
- exact model IDs
- synthetic generation result if run
- whether any real data was sent remote
- destroy recommendation
- DATA_MISSING.

# Phase 3 - Add repo-side docs if missing

Create/update these docs, if they do not already exist:

- `docs/runtime/rented_gpu_runtime_workflow.md`
- `docs/setup/rented_gpu_vast_runtime.md`

These docs should summarize:

- corrected workflow
- pre-rental gates
- image/template requirements
- tunnel commands
- smoke sequence
- destroy/cost policy
- previous failure pattern: "GPU verified is not runtime verified"
- Tenn-specific env var:
  `TENN_RENTED_GPU_LLAMACPP_URL=http://127.0.0.1:18001`

# Phase 4 - No-cost dry-run retest

Do not rent.

Run only no-cost commands:

- `vastai show instances || true`
- `vastai search offers 'gpu_name=RTX_4090' || true`
- `vastai search offers 'gpu_name=RTX_3090' || true`
- any Vast template/image search command available from CLI help, if safe:
  - `vastai --help`
  - `vastai search --help`
  - `vastai create instance --help`
- do not create an instance.

Dry-run the decision logic against two scenarios:

## Scenario A - bad previous image

Input:

- image: `nvidia/cuda:12.4.1-devel-ubuntu22.04`
- llama-server: absent
- GGUF: absent
- onstart: absent
- disk: 40GB
- GPU: RTX 4090

Expected decision:

- do not use for smoke
- do not rent unless task is explicitly runtime provisioning
- if already rented, destroy or stop for bootstrap approval.

## Scenario B - acceptable runtime image

Input:

- image: `ghcr.io/ggml-org/llama.cpp:server-cuda` or equivalent
- llama-server: present
- GGUF model: present or mounted
- onstart binds `127.0.0.1:8001`
- `/v1/models` expected within 2 minutes

Expected decision:

- acceptable candidate
- rent only with max cost/time cap
- immediately test remote `/v1/models`
- then tunnel and test local `/v1/models`.

# Optional real-rental retest - disabled by default

Because `REAL_RENTAL_TEST_APPROVED: NO`, do not rent.

If this prompt is rerun with `REAL_RENTAL_TEST_APPROVED: YES`, then require these fields before renting:

- max hourly rate:
- max runtime minutes:
- max total budget:
- target image/template:
- model path or model mount:
- onstart command:
- exact destroy confirmation policy:

If any are missing, do not rent.

# Explicitly forbidden

Do not:

- rent a Vast instance
- destroy a Vast instance
- open long-running tunnel
- download model
- build llama.cpp
- run broad install
- expose llama-server publicly
- send real data to remote
- mutate DBs, Qdrant, Postgres, company memory, news, Financial Truth
- edit Tenn product code
- change runtime scripts
- restart local runtime
- commit external skill files into Tenn repo

# Validation

Run:

- `git diff --check`
- if skill/doc files edited, inspect diff and confirm no product code changed
- `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/vast_gpu_operator_skill_runtime_gate_fix_v1_20260515.md`
- `python3 scripts/agent_job_registry.py release vast_gpu_operator_skill_runtime_gate_fix_v1_20260515`
- `python3 scripts/agent_job_registry.py list-active`
- `git status --short --untracked-files=all`

If `check-diff` rejects external skill edits, record the limitation and still validate repo-side docs/report artifacts.

# Commit rules

Commit only repo-side task card/docs/report artifacts.

Suggested commit:

```text
milestone(query): harden rented gpu operator workflow
```

Commit body:

```text
adds runtime-not-hardware success gate
requires /v1/models before Tenn smoke
avoids bare CUDA images
adds cost/destroy guard
adds no-cost dry-run strategy
no rental performed
```

# Final report

Write:

`reports/agent_jobs/vast_gpu_operator_skill_runtime_gate_fix_v1_20260515/README.md`

Include:

- verdict:
  completed / partial / blocked
- branch / HEAD / worktree
- skill file path updated, if any
- backup path, if external skill edited
- repo docs created/updated
- dry-run Vast CLI results
- Scenario A decision result
- Scenario B decision result
- next real-rental checklist
- files changed
- validation results
- final git status
- DATA_MISSING
- Project Memory save recommendation
