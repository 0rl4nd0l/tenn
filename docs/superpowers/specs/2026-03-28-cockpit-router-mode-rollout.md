# Cockpit Router Mode Rollout — Safe Local Hot-Switching

**Date:** 2026-03-28
**Status:** Draft
**Branch:** cloud/session-20260319
**Goal:** Enable safe, operator-visible `llama.cpp` router mode in cockpit for local model hot-switching without changing backend authority or mixing in remote-provider routing.

---

## 1. Problem Statement

Cockpit already contains substantial support for `llama.cpp` router mode, including:

- router-mode detection from process args and `/v1/models`
- hot-switching via `POST /models/load`
- stalled child-process detection for known llama.cpp router failure cases
- a fallback restart path for non-router mode
- a path to relaunch a single-model server into router mode

However, router mode is not yet safe to treat as a default operator path because:

1. **Runtime behavior is environment-dependent.** The launcher only enables router mode when `LLAMA_SERVER_ROUTER_MODE=1` is set and the binary supports `--models-dir`; otherwise it silently falls back to single-model mode.
2. **Failure handling is real but under-tested.** The code explicitly works around a known router-mode bug where crashed child processes can remain stuck in `loading`.
3. **Topology selection is ambiguous.** Cockpit’s preboot flow reasons about the first discovered `llama-server` process even though the repo explicitly recognizes multi-server topologies.
4. **Operator visibility is incomplete.** The code can detect many failure states, but the product-level story is still “hot-switch vs restart,” not “router mode available, active, unavailable, or degraded.”
5. **Remote-provider routing is a separate concern.** Anthropic or other API providers should not be introduced in the same rollout because they expand scope into auth, egress, cost, privacy, and mixed-provider policy.

The goal is to make cockpit router mode safe and explicit for local operation first, while preserving single-model restart behavior as the fallback.

---

## 2. Chosen Approach

**Cockpit-only, opt-in router mode rollout with preflight validation and explicit fallback.**

This rollout does **not** change backend routing, extraction, retrieval, or embedding behavior. It improves only cockpit’s local model-switch workflow.

The system should:

- expose router mode as an explicit cockpit capability
- validate that router mode is genuinely available before offering hot-switch behavior
- make multi-server ambiguity explicit instead of guessing
- preserve restart-based switching as the safe fallback
- add direct automated coverage around the existing router-mode control path

This rollout intentionally excludes Anthropic and any other remote provider. Provider routing is Phase 2 and should be designed separately.

---

## 3. Architecture Overview

### Current control flow

```
User chooses model in cockpit preboot
  ↓
Preboot discovers llama-server process
  ↓
Preboot infers current mode
  ├── router mode → compare selected model against loaded router models
  └── single-model → compare selected path against running -m path
  ↓
If switch needed:
  ↓
switch_model()
  ├── router mode → warm page cache → POST /models/load → poll /v1/models
  └── single-model → stop server → replace -m/-a args → restart and poll readiness
```

### Target control flow

```
User opens cockpit preboot
  ↓
Preflight evaluates runtime capability
  ├── router mode available and healthy
  ├── router mode configured but unavailable (with reason)
  └── single-model only
  ↓
If multiple llama-server processes exist:
  ├── explicit selection or
  └── block router-mode activation until resolved
  ↓
User opts into router mode
  ↓
Switch request
  ├── hot-switch via router API when validated
  └── explicit fallback to restart path otherwise
```

### Key principle

```
Router mode = local runtime loading strategy
Provider routing = local vs remote execution policy
```

These must remain separate.

---

## 4. Scope Boundaries

### In scope

- cockpit preboot runtime capability detection
- cockpit operator UX for router-mode availability and failures
- `llamacpp_manager` validation and model-switch control flow
- launcher/runtime checks for local router-mode support
- cockpit tests for router-mode detection and switching behavior

### Out of scope

- backend `model_routing.yaml`
- backend `route_request()` behavior
- extraction pipeline behavior
- retrieval / RAG logic
- embeddings or vector-store invariants
- Anthropic or any other cloud provider
- multi-model backend policy changes

---

## 5. Component Design

### 5.1 Preboot capability state

**Primary file:** [financial-engine_v2/cockpit/ui/preboot.py](/home/l4nd0/tenn/financial-engine_v2/cockpit/ui/preboot.py)

Preboot should expose a first-class runtime state, not just infer “router vs single-model” from the current process.

Required user-visible states:

- `single_model_active`
- `router_mode_active`
- `router_mode_available_not_active`
- `router_mode_unavailable`
- `router_mode_degraded`

Source of truth for `router_mode_available_not_active`:

- launcher capability probe against the configured `llama-server` binary (`--help` contains `models-dir`)
- cockpit config / env opt-in state
- discoverable models directory or router-known model inventory
- absence of an already-active router-mode process for the selected target runtime

Each non-active state must carry a concrete reason, for example:

- binary missing `--models-dir`
- router API unreachable
- no models discovered
- multiple candidate servers found
- model list/name reconciliation failed

This status should drive whether cockpit offers a true hot-switch path or only a restart path.

### 5.2 Router-mode opt-in

**Primary files:**
[financial-engine_v2/cockpit/ui/preboot.py](/home/l4nd0/tenn/financial-engine_v2/cockpit/ui/preboot.py)
[financial-engine_v2/cockpit/core/config.py](/home/l4nd0/tenn/financial-engine_v2/cockpit/core/config.py)
[scripts/run_llama_server.sh](/home/l4nd0/tenn/scripts/run_llama_server.sh)

Router mode should be operator-enabled, not silently assumed.

Behavior:

- default remains single-model semantics
- cockpit may advertise router mode as available
- router mode becomes active only through explicit configuration / selection
- unsupported environments must report the exact reason and remain on the restart path

### 5.3 Topology resolution

**Primary files:**
[financial-engine_v2/cockpit/integrations/llamacpp_manager.py](/home/l4nd0/tenn/financial-engine_v2/cockpit/integrations/llamacpp_manager.py)
[financial-engine_v2/cockpit/ui/preboot.py](/home/l4nd0/tenn/financial-engine_v2/cockpit/ui/preboot.py)

Current behavior uses the first discovered `llama-server` process for the cockpit launch path, which is too ambiguous for default router-mode use.

Required behavior:

- if exactly one relevant local chat runtime exists, use it
- if multiple relevant runtimes exist, surface them explicitly
- do not silently bind to an arbitrary process for router-mode operations
- if topology is ambiguous, hot-switch must be blocked until resolved

This is especially important where the repo may run both chat and extraction runtimes on canonical ports.

### 5.4 Hot-switch validation

**Primary file:** [financial-engine_v2/cockpit/integrations/llamacpp_manager.py](/home/l4nd0/tenn/financial-engine_v2/cockpit/integrations/llamacpp_manager.py)

Hot-switching via `/models/load` remains the preferred runtime path only when validation succeeds.

Preconditions:

- router mode confirmed by process shape or `/v1/models`
- model name resolvable in router API state
- intended target server identified
- router API responsive before load request
- loaded-model state transitions observable

Failure handling:

- detect terminal `failed` / `error` states
- detect stuck `loading` via child-port probe
- surface operator-readable failure reasons
- do **not** silently auto-restart after a router-mode load failure in the first rollout
- instead, surface an explicit operator choice to retry, switch models, or use the restart path manually

### 5.5 Restart fallback remains canonical fallback

**Primary files:**
[financial-engine_v2/cockpit/integrations/llamacpp_manager.py](/home/l4nd0/tenn/financial-engine_v2/cockpit/integrations/llamacpp_manager.py)
[scripts/run_llama_server.sh](/home/l4nd0/tenn/scripts/run_llama_server.sh)

Single-model restart behavior must remain intact and well-lit:

- it is the compatibility path for unsupported hosts
- it is the rollback path for unsupported or ambiguous router-mode activation
- it is the manual recovery path after router-mode load failure in the first rollout
- it remains the safe path when topology or capability is ambiguous

Router mode should not remove restart behavior; it should sit on top of it.

### 5.6 Extraction auto-load blast radius

**Primary file:** [financial-engine_v2/cockpit/core/action_runtime_guards.py](/home/l4nd0/tenn/financial-engine_v2/cockpit/core/action_runtime_guards.py)

Cockpit extraction runtime guards already call `load_model_api()` directly to auto-load the extraction model when router mode is available.

Implications:

- any new capability-state logic in `llamacpp_manager` must be compatible with extraction auto-load
- topology checks must not accidentally block the extraction guard path without a clear remediation message
- the rollout must review whether extraction auto-load should reuse the same capability / topology checks or deliberately remain narrower

This file is in scope for review and likely for light integration changes, even though the rollout remains cockpit-only.

---

## 6. Data Contracts and Runtime States

### Router capability payload

Preboot should compute and consume a structured capability payload similar to:

```json
{
  "mode": "single_model_active",
  "router_supported": false,
  "router_configured": false,
  "router_api_reachable": false,
  "selected_server_port": "8001",
  "candidate_servers": 1,
  "reason": "binary_missing_models_dir_support"
}
```

This does not need to be persisted as a new system of record; it is a runtime diagnostic structure for cockpit only.

### Switch result payload

Switch operations should resolve to a structured result with explicit outcome:

```json
{
  "ok": true,
  "path": "router_hot_switch",
  "target_model": "qwen2.5-14b-instruct",
  "fallback_used": false,
  "message": "Model loaded successfully"
}
```

Failure cases should also be explicit:

```json
{
  "ok": false,
  "path": "router_hot_switch",
  "fallback_used": false,
  "message": "child process appears dead while model remained in loading state"
}
```

---

## 7. Validation and Failure Taxonomy

| Failure | Detection | User-visible handling | Fallback |
|---------|-----------|-----------------------|----------|
| Router binary unsupported | launcher capability check | `router mode unavailable` with reason | single-model restart |
| Router API unreachable | preflight probe | `router mode unavailable` with reason | single-model restart |
| Multiple candidate servers | topology discovery | block hot-switch until selection is explicit | single-model restart or manual resolution |
| Model not present in router | model list reconciliation | hot-switch blocked with explicit message | choose valid model or restart |
| Router child stuck in `loading` | stalled-load probe | hot-switch failure surfaced explicitly | retry or restart |
| Router-mode detection mismatch | process vs HTTP disagreement | `router mode degraded` | restart path only |
| Model load timeout | `/v1/models` polling timeout | explicit failure state | retry or restart |

---

## 8. Test Plan

**Primary test area:** [financial-engine_v2/cockpit/tests](/home/l4nd0/tenn/financial-engine_v2/cockpit/tests)

Required automated coverage:

1. router-mode detection from process args
2. router-mode detection from `/v1/models` response shape
3. capability-state calculation for supported vs unsupported binaries
4. model-name / filesystem-stem reconciliation
5. hot-switch success path via `/models/load`
6. hot-switch terminal failure path
7. stalled child-process detection path
8. restart fallback path
9. restart-into-router-mode path
10. multi-server ambiguity behavior
11. extraction auto-load behavior when router mode is available / unavailable
12. UI-facing preboot status, mode labels, and launch-path messaging

No rollout to default should happen without these tests.

---

## 9. Rollout Strategy

### Stage 1 — Internal opt-in

- router mode remains disabled by default
- supported hosts can enable it deliberately
- operator feedback and failure messages are hardened
- test coverage lands first

### Stage 2 — Supported-host default

Only after Stage 1 proves stable:

- enable by default only on hosts that pass capability checks
- keep explicit fallback to single-model restart
- preserve visible runtime-state reporting

### Stage 3 — Re-evaluate defaults

Only after repeated successful use:

- decide whether cockpit should prefer router mode whenever supported
- do not extend this decision to backend services automatically

---

## 10. Phase 2 (Separate Future Work) — Anthropic Provider

Anthropic should be designed as a separate provider-routing layer after local router mode is stable.

Reasons:

- different trust/cost/latency/privacy surface
- different auth and secret handling
- different failure and retry semantics
- not part of local model hot-switching

Recommended first remote roles:

- `orchestrator`
- `deep_reasoning`

Not part of this rollout:

- backend routing
- extraction workloads
- embeddings
- transparent mixed-provider fallback

---

## 11. Files Changed

| File | Status | Purpose |
|------|--------|---------|
| `financial-engine_v2/cockpit/ui/preboot.py` | Modified | capability display, topology handling, router-mode UX |
| `financial-engine_v2/cockpit/integrations/llamacpp_manager.py` | Modified | capability checks, topology-safe switching, structured switch outcomes |
| `financial-engine_v2/cockpit/core/action_runtime_guards.py` | Modified | align extraction auto-load with router capability and topology checks |
| `financial-engine_v2/cockpit/core/config.py` | Modified | cockpit-only router-mode opt-in config |
| `scripts/run_llama_server.sh` | Modified | explicit router-mode capability reporting / launch semantics |
| `financial-engine_v2/cockpit/tests/test_preboot_router_mode.py` | New | preboot router capability and selection tests |
| `financial-engine_v2/cockpit/tests/test_llamacpp_manager_router_mode.py` | New | switch, detection, timeout, and fallback tests |
| `financial-engine_v2/cockpit/tests/test_action_runtime_guards_router_mode.py` | New | extraction auto-load behavior under router capability states |

---

## 12. Out of Scope

- backend `route_request()` or `model_routing.yaml`
- changing backend queues or model roles
- enabling remote model providers
- changing extraction runtime topology
- changing authorized backend ownership or retrieval boundaries

---

## 13. Recommendation

Proceed with cockpit-only router mode, but **do not make it the default in the first implementation**.

The codebase already supports router mode strongly enough to justify hardening it, but the current failure handling, topology ambiguity, and lack of dedicated test coverage make an unconditional default premature.
