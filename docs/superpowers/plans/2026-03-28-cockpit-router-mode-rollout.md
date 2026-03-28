# Cockpit Router Mode Rollout — Implementation Plan

> **For agentic workers:** Implement this plan task-by-task. Keep scope strictly to cockpit-local router mode. Do not add Anthropic or backend routing changes in this plan.

**Goal:** Safely enable cockpit-local `llama.cpp` router mode for hot model switching, behind explicit opt-in and strong preflight checks, while preserving the existing single-model restart path as fallback.

**Architecture:** Cockpit preboot computes router capability and topology state, exposes operator-visible runtime status, and chooses between router hot-switch and restart-based switching. `llamacpp_manager` remains the switching control plane. `action_runtime_guards` is included because extraction auto-load already depends on `load_model_api()`.

**Tech Stack:** Python 3.11+, Textual cockpit UI, local `llama.cpp` runtime, `scripts/run_llama_server.sh`, pytest

**Spec:** `docs/superpowers/specs/2026-03-28-cockpit-router-mode-rollout.md`

---

## File Map

| File | Action | Responsibility |
|------|--------|---------------|
| `financial-engine_v2/cockpit/ui/preboot.py` | **Modify** | Capability state display, topology handling, launch-path UX, explicit router-mode opt-in |
| `financial-engine_v2/cockpit/integrations/llamacpp_manager.py` | **Modify** | Capability probes, topology-safe switching, structured outcomes, manual restart fallback hooks |
| `financial-engine_v2/cockpit/core/action_runtime_guards.py` | **Modify** | Keep extraction auto-load aligned with router capability / topology behavior |
| `financial-engine_v2/cockpit/core/config.py` | **Modify** | Cockpit router-mode opt-in config and runtime flag plumbing |
| `scripts/run_llama_server.sh` | **Modify** | Explicit router-mode capability reporting / launch semantics |
| `financial-engine_v2/cockpit/tests/test_preboot_router_mode.py` | **Create** | Preboot capability-state and UI-mode tests |
| `financial-engine_v2/cockpit/tests/test_llamacpp_manager_router_mode.py` | **Create** | Router detection, `/models/load`, stalled-load, restart fallback tests |
| `financial-engine_v2/cockpit/tests/test_action_runtime_guards_router_mode.py` | **Create** | Extraction auto-load behavior under router capability states |

---

## Task 1: Baseline Current Router-Mode Behavior with Tests

**Files:**
- Create: `financial-engine_v2/cockpit/tests/test_llamacpp_manager_router_mode.py`
- Create: `financial-engine_v2/cockpit/tests/test_preboot_router_mode.py`

Write the tests first so the rollout hardens existing behavior instead of hand-waving around it.

- [ ] **Step 1: Add manager tests for current router detection**

Cover:
- process-arg router-mode detection (`--models-dir` and no `-m`)
- HTTP response-shape router-mode detection
- `list_models_api()` state normalization

- [ ] **Step 2: Add manager tests for current failure paths**

Cover:
- `load_model_api()` success path
- terminal failure state
- stuck `loading` detection via `_is_loading_stalled()`
- timeout path

- [ ] **Step 3: Add preboot tests for current launch-path selection**

Cover:
- router mode shows hot-switch path
- single-model mode shows restart path
- selection of currently loaded router model

- [ ] **Step 4: Run focused tests**

```bash
cd financial-engine_v2
export PATH="$PWD/.venv/bin:$PATH"
pytest cockpit/tests/test_llamacpp_manager_router_mode.py cockpit/tests/test_preboot_router_mode.py -q
```

- [ ] **Step 5: Commit**

```bash
git add financial-engine_v2/cockpit/tests/test_llamacpp_manager_router_mode.py \
        financial-engine_v2/cockpit/tests/test_preboot_router_mode.py
git commit -m "milestone(cockpit): baseline router-mode switching tests

Working: cockpit router-mode control paths now have focused manager and preboot coverage
Tested: pytest cockpit/tests/test_llamacpp_manager_router_mode.py cockpit/tests/test_preboot_router_mode.py -q"
```

---

## Task 2: Introduce Explicit Router Capability State

**Files:**
- Modify: `financial-engine_v2/cockpit/integrations/llamacpp_manager.py`
- Modify: `financial-engine_v2/cockpit/ui/preboot.py`

Add a concrete runtime capability model rather than inferring everything from the current process.

- [ ] **Step 1: Define a capability-state structure**

Required fields:
- active mode
- router supported by binary
- router configured by cockpit/user
- router API reachable
- candidate server count
- selected server identity
- reason string for unavailable/degraded cases

- [ ] **Step 2: Add capability probe helpers in `llamacpp_manager.py`**

Helpers should support:
- checking launcher/binary support for `--models-dir`
- checking router API reachability
- combining process discovery and HTTP state into a single capability result

- [ ] **Step 3: Use capability state in preboot**

Replace implicit mode-only presentation with explicit status:
- `router_mode_active`
- `router_mode_available_not_active`
- `router_mode_unavailable`
- `router_mode_degraded`
- `single_model_active`

- [ ] **Step 4: Add / update tests**

Add test cases for:
- supported-but-not-active
- unsupported binary
- reachable vs unreachable router API
- degraded disagreement between process and HTTP detection

- [ ] **Step 5: Run focused tests**

```bash
cd financial-engine_v2
pytest cockpit/tests/test_llamacpp_manager_router_mode.py cockpit/tests/test_preboot_router_mode.py -q
```

- [ ] **Step 6: Commit**

```bash
git add financial-engine_v2/cockpit/integrations/llamacpp_manager.py \
        financial-engine_v2/cockpit/ui/preboot.py \
        financial-engine_v2/cockpit/tests/test_llamacpp_manager_router_mode.py \
        financial-engine_v2/cockpit/tests/test_preboot_router_mode.py
git commit -m "milestone(cockpit): add explicit router capability state

Working: cockpit preboot now distinguishes router availability, activation, and degraded states explicitly
Tested: pytest cockpit/tests/test_llamacpp_manager_router_mode.py cockpit/tests/test_preboot_router_mode.py -q"
```

---

## Task 3: Add Explicit Cockpit Router-Mode Opt-In

**Files:**
- Modify: `financial-engine_v2/cockpit/core/config.py`
- Modify: `financial-engine_v2/cockpit/ui/preboot.py`
- Modify: `scripts/run_llama_server.sh`

The first rollout must be explicit opt-in, not an implicit default.

- [ ] **Step 1: Add cockpit config/runtime flag for router mode**

This should be cockpit-only and must not change backend routing behavior.

- [ ] **Step 2: Thread the flag into preboot and launch semantics**

Behavior:
- when off, cockpit can still report router capability but does not activate router-mode behavior automatically
- when on, cockpit may use hot-switch behavior if capability checks pass

- [ ] **Step 3: Make launcher reporting explicit**

Improve launch output so router support / active router mode / fallback to single-model mode are visible and testable.

- [ ] **Step 4: Add tests**

Cover:
- opt-in disabled on capable host
- opt-in enabled on capable host
- opt-in enabled on unsupported host gracefully degrades

- [ ] **Step 5: Run focused tests**

```bash
cd financial-engine_v2
pytest cockpit/tests/test_preboot_router_mode.py cockpit/tests/test_llamacpp_manager_router_mode.py -q
```

- [ ] **Step 6: Commit**

```bash
git add financial-engine_v2/cockpit/core/config.py \
        financial-engine_v2/cockpit/ui/preboot.py \
        scripts/run_llama_server.sh \
        financial-engine_v2/cockpit/tests/test_preboot_router_mode.py \
        financial-engine_v2/cockpit/tests/test_llamacpp_manager_router_mode.py
git commit -m "milestone(cockpit): gate router mode behind explicit opt-in

Working: cockpit router mode is now opt-in and unsupported hosts degrade predictably
Tested: pytest cockpit/tests/test_preboot_router_mode.py cockpit/tests/test_llamacpp_manager_router_mode.py -q"
```

---

## Task 4: Make Multi-Server Topology Explicit

**Files:**
- Modify: `financial-engine_v2/cockpit/integrations/llamacpp_manager.py`
- Modify: `financial-engine_v2/cockpit/ui/preboot.py`

Current process selection is too ambiguous for safe default router-mode use.

- [ ] **Step 1: Surface all discovered llama-server processes to preboot**

Use the existing multi-process discovery path as the source of truth, not just the first result.

- [ ] **Step 2: Add topology rules**

Rules:
- if there is one valid chat runtime, use it
- if multiple candidate runtimes exist, block hot-switch until the target is explicit
- do not silently attach to an arbitrary process for router mode

- [ ] **Step 3: Update UI messaging**

Preboot should clearly explain when router mode is blocked due to ambiguous topology.

- [ ] **Step 4: Add tests**

Cover:
- single server
- multiple servers with one valid target
- multiple ambiguous servers
- extraction runtime coexistence

- [ ] **Step 5: Run focused tests**

```bash
cd financial-engine_v2
pytest cockpit/tests/test_preboot_router_mode.py cockpit/tests/test_llamacpp_manager_router_mode.py -q
```

- [ ] **Step 6: Commit**

```bash
git add financial-engine_v2/cockpit/integrations/llamacpp_manager.py \
        financial-engine_v2/cockpit/ui/preboot.py \
        financial-engine_v2/cockpit/tests/test_preboot_router_mode.py \
        financial-engine_v2/cockpit/tests/test_llamacpp_manager_router_mode.py
git commit -m "milestone(cockpit): make router-mode topology explicit

Working: cockpit blocks ambiguous router-mode switching and surfaces server topology clearly
Tested: pytest cockpit/tests/test_preboot_router_mode.py cockpit/tests/test_llamacpp_manager_router_mode.py -q"
```

---

## Task 5: Harden Router Hot-Switch Outcomes

**Files:**
- Modify: `financial-engine_v2/cockpit/integrations/llamacpp_manager.py`
- Modify: `financial-engine_v2/cockpit/ui/preboot.py`

The first rollout should not silently auto-restart after a router load failure.

- [ ] **Step 1: Return structured switch outcomes from `switch_model()` / related helpers**

Include:
- success/failure
- chosen path (`router_hot_switch` or `restart`)
- target model
- reason message
- whether fallback was used

- [ ] **Step 2: Preserve first-rollout failure policy**

If router mode is chosen and `/models/load` fails:
- surface failure clearly
- offer manual retry / model change / restart-path choice
- do not silently convert the failure into a restart

- [ ] **Step 3: Improve UI logging**

Make launch logs reflect:
- hot-switch started
- load state progress
- explicit failure reason
- explicit manual restart option

- [ ] **Step 4: Add tests**

Cover:
- successful hot-switch
- stalled child-process failure
- timeout failure
- restart path still works when router mode is not active

- [ ] **Step 5: Run focused tests**

```bash
cd financial-engine_v2
pytest cockpit/tests/test_llamacpp_manager_router_mode.py cockpit/tests/test_preboot_router_mode.py -q
```

- [ ] **Step 6: Commit**

```bash
git add financial-engine_v2/cockpit/integrations/llamacpp_manager.py \
        financial-engine_v2/cockpit/ui/preboot.py \
        financial-engine_v2/cockpit/tests/test_llamacpp_manager_router_mode.py \
        financial-engine_v2/cockpit/tests/test_preboot_router_mode.py
git commit -m "milestone(cockpit): harden router hot-switch outcomes

Working: cockpit router-mode failures now surface explicit outcomes without silent restart fallback
Tested: pytest cockpit/tests/test_llamacpp_manager_router_mode.py cockpit/tests/test_preboot_router_mode.py -q"
```

---

## Task 6: Align Extraction Auto-Load with Router Capability Checks

**Files:**
- Modify: `financial-engine_v2/cockpit/core/action_runtime_guards.py`
- Create: `financial-engine_v2/cockpit/tests/test_action_runtime_guards_router_mode.py`

Extraction auto-load already depends on router-mode model loading. This path must stay coherent with the rollout.

- [ ] **Step 1: Review extraction auto-load assumptions**

Ensure the guard path is compatible with:
- explicit router capability state
- topology checks
- operator-visible failure messages

- [ ] **Step 2: Reuse capability / topology checks where appropriate**

Avoid duplicating incompatible logic between preboot and extraction runtime guards.

- [ ] **Step 3: Add tests**

Cover:
- extraction model already loaded
- extraction model available and auto-load succeeds
- router unavailable
- router ambiguous / blocked
- auto-load failure surfaces cleanly

- [ ] **Step 4: Run focused tests**

```bash
cd financial-engine_v2
pytest cockpit/tests/test_action_runtime_guards_router_mode.py -q
```

- [ ] **Step 5: Commit**

```bash
git add financial-engine_v2/cockpit/core/action_runtime_guards.py \
        financial-engine_v2/cockpit/tests/test_action_runtime_guards_router_mode.py
git commit -m "milestone(cockpit): align extraction auto-load with router capability checks

Working: cockpit extraction guards now respect router capability and topology state consistently
Tested: pytest cockpit/tests/test_action_runtime_guards_router_mode.py -q"
```

---

## Task 7: Final Validation and Documentation Pass

**Files:**
- Modify as needed: cockpit runtime files and tests only

- [ ] **Step 1: Run the complete cockpit router-mode test set**

```bash
cd financial-engine_v2
pytest cockpit/tests/test_llamacpp_manager_router_mode.py \
       cockpit/tests/test_preboot_router_mode.py \
       cockpit/tests/test_action_runtime_guards_router_mode.py -q
```

- [ ] **Step 2: Run targeted lint / syntax checks**

```bash
cd financial-engine_v2
python -m ruff check cockpit scripts
```

- [ ] **Step 3: Perform manual supported-host smoke test**

Validate:
- single-model startup still works
- router-mode opt-in shows correct capability state
- hot-switch works on supported host
- router failure path is explicit and non-destructive
- extraction auto-load still behaves correctly

- [ ] **Step 4: Commit**

```bash
git add financial-engine_v2/cockpit \
        scripts/run_llama_server.sh
git commit -m "milestone(cockpit): validate safe local router-mode rollout

Working: cockpit local router mode is available behind opt-in with capability checks, topology guards, and explicit hot-switch outcomes
Tested: pytest cockpit/tests/test_llamacpp_manager_router_mode.py cockpit/tests/test_preboot_router_mode.py cockpit/tests/test_action_runtime_guards_router_mode.py -q; python -m ruff check cockpit scripts"
```

---

## Rollout Rules

- Do not add Anthropic or any cloud provider work in this plan.
- Do not change backend `route_request()` or backend model-routing configuration.
- Do not silently auto-enable router mode on unsupported hosts.
- Do not silently auto-restart after a router-mode load failure in the first rollout.
- Keep extraction auto-load behavior aligned with the same runtime capability logic.

---

## Exit Criteria

- cockpit exposes accurate router capability and activation state
- router mode is opt-in and predictable
- multi-server ambiguity is handled explicitly
- hot-switch outcomes are structured and operator-visible
- single-model restart path still works
- extraction auto-load remains coherent with router capability checks
- focused tests exist and pass for manager, preboot, and runtime guards
