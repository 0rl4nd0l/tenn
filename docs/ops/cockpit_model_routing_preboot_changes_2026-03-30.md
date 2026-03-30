# Cockpit Model Routing And Preboot Changes

Date: 2026-03-30
Scope: read-only investigation of recent Cockpit routing and preboot changes landed on 2026-03-28 and 2026-03-29.

## What Changed

The main Cockpit routing and preboot rewrite landed in commit `6db38b09` on 2026-03-29:

- Introduced a new authoritative file for Cockpit LLM settings: `financial-engine_v2/config/cockpit_llm.yaml`.
- Expanded `financial-engine_v2/cockpit/core/config.py` so launch-time config is now built from:
  1. base defaults
  2. `config/cockpit*.yaml`
  3. `config/cockpit_llm.yaml`
  4. optional env overrides when `allow_env_override: true`
- Simplified the preboot UI in `financial-engine_v2/cockpit/ui/preboot.py` and made it validate the same effective config that Launch uses.
- Kept `financial-engine_v2/scripts/cockpit_tui.py` as the launcher that applies preboot flags into argv and env before `cockpit.main` or `cockpit_serve.py` starts.

Supporting commits around the same area:

- `fe854582` on 2026-03-28 added router-mode opt-in plumbing.
- `17037d46` on 2026-03-28 moved `.env` loading into shared config code so all Cockpit entrypoints resolve env-backed defaults consistently.
- `b37ce9df` on 2026-03-28 added the operator cheat sheet documenting the updated preboot/routing model.

## Current Source Of Truth

### 1. Cockpit LLM policy is now split out into `config/cockpit_llm.yaml`

`financial-engine_v2/cockpit/core/config.py` defines a dedicated `DEFAULT_COCKPIT_LLM_FILE` block with:

- `allow_env_override`
- `hybrid_router_policy`
- `llm_profile_label`
- `tool_debug`
- stack defaults for extraction, embeddings, and Anthropic
- the actual Cockpit chat provider/model/endpoints

Evidence:

- `DEFAULT_COCKPIT_LLM_FILE` is defined at [financial-engine_v2/cockpit/core/config.py](/home/l4nd0/tenn/financial-engine_v2/cockpit/core/config.py#L99).
- The committed YAML lives at [financial-engine_v2/config/cockpit_llm.yaml](/home/l4nd0/tenn/financial-engine_v2/config/cockpit_llm.yaml).
- The file is merged by `merge_cockpit_llm_file()` at [financial-engine_v2/cockpit/core/config.py](/home/l4nd0/tenn/financial-engine_v2/cockpit/core/config.py#L455).

### 2. Env overrides are no longer always authoritative

`apply_runtime_flags()` now checks `cockpit_llm.allow_env_override` before accepting `COCKPIT_*` model/provider env overrides.

- When `allow_env_override: false`, YAML stays authoritative and env only syncs tool-debug plus non-LLM settings.
- When `allow_env_override: true`, `_apply_llm_env_overrides()` can replace provider, URLs, model, API key, and `router_mode_opt_in`.

Evidence:

- Gate is in [financial-engine_v2/cockpit/core/config.py](/home/l4nd0/tenn/financial-engine_v2/cockpit/core/config.py#L556).
- Actual env override logic is in [financial-engine_v2/cockpit/core/config.py](/home/l4nd0/tenn/financial-engine_v2/cockpit/core/config.py#L481).
- The default committed policy is `allow_env_override: false` in [financial-engine_v2/config/cockpit_llm.yaml](/home/l4nd0/tenn/financial-engine_v2/config/cockpit_llm.yaml#L5).

### 3. Cockpit now exports stack-wide model defaults from the same routing file

`apply_stack_defaults_to_environ()` seeds:

- `EXTRACT_MODEL`
- `EMBED_MODEL`
- `EMBEDDING_MODEL`
- `ANTHROPIC_MODEL`
- `COCKPIT_LLM_PROFILE`

when those env vars are not already set.

Evidence:

- Default propagation is implemented at [financial-engine_v2/cockpit/core/config.py](/home/l4nd0/tenn/financial-engine_v2/cockpit/core/config.py#L133).
- Current committed defaults are in [financial-engine_v2/config/cockpit_llm.yaml](/home/l4nd0/tenn/financial-engine_v2/config/cockpit_llm.yaml#L16).

### 4. Runtime routing now resolves separately from config merge

After config is resolved, chat constructs a `HybridRouter` with a local llama.cpp client and an optional Anthropic client. The active routing policy is chosen by `resolve_hybrid_router_policy()`, which now treats `cockpit_llm.hybrid_router_policy` as authoritative when `allow_env_override` is false.

Evidence:

- Chat wiring is in [financial-engine_v2/cockpit/core/chat.py](/home/l4nd0/tenn/financial-engine_v2/cockpit/core/chat.py#L161).
- Policy resolution logic is in [financial-engine_v2/cockpit/core/llm_profile.py](/home/l4nd0/tenn/financial-engine_v2/cockpit/core/llm_profile.py#L77).

## Preboot Behavior After The Rewrite

### 1. Preboot profiles are intentionally smaller

The preboot screen now centers around two launch profiles:

- `full`
- `testing`

with fixed profile defaults for read-only, web, verbosity, RAG, and profile-specific env vars.

Evidence:

- Profile table is defined at [financial-engine_v2/cockpit/ui/preboot.py](/home/l4nd0/tenn/financial-engine_v2/cockpit/ui/preboot.py#L141).

### 2. Preboot validates the same effective config used at launch

The preboot screen recomputes the effective config via `compute_effective_cockpit_config()` and blocks Launch if config validation fails or if the runtime model mismatches the configured llama.cpp model.

Evidence:

- UI sync path is in [financial-engine_v2/cockpit/ui/preboot.py](/home/l4nd0/tenn/financial-engine_v2/cockpit/ui/preboot.py#L369).
- Launch blocking is enforced at [financial-engine_v2/cockpit/ui/preboot.py](/home/l4nd0/tenn/financial-engine_v2/cockpit/ui/preboot.py#L412).
- Launch exits early when config or runtime verification fails at [financial-engine_v2/cockpit/ui/preboot.py](/home/l4nd0/tenn/financial-engine_v2/cockpit/ui/preboot.py#L693).

### 3. `cockpit_tui.py` applies preboot state by mutating argv and env

The launcher:

- infers initial preboot state from existing CLI flags
- runs the preboot UI unless `--no-setup` is set
- injects `--read-only`, `--no-web`, and `--profile` into argv when chosen in UI
- exports `COCKPIT_PREBOOT_PROFILE`, `COCKPIT_PREBOOT_READ_ONLY`, and `COCKPIT_PREBOOT_NO_WEB`
- applies profile env vars only when the key is not already present

Evidence:

- Initial flag resolution is in [financial-engine_v2/scripts/cockpit_tui.py](/home/l4nd0/tenn/financial-engine_v2/scripts/cockpit_tui.py#L322).
- Flag and env merge logic is in [financial-engine_v2/scripts/cockpit_tui.py](/home/l4nd0/tenn/financial-engine_v2/scripts/cockpit_tui.py#L358).
- Preboot launch path is in [financial-engine_v2/scripts/cockpit_tui.py](/home/l4nd0/tenn/financial-engine_v2/scripts/cockpit_tui.py#L466).

### 4. Startup defaults in `cockpit_tui.py` still shape behavior before preboot merges

The launcher still seeds operational defaults such as:

- `COCKPIT_BACKEND_API_URL=http://localhost:8000`
- `COCKPIT_NEWS_CORPUS_FILTER=news`
- `COCKPIT_NEWS_TICKER_MATCH_MODE=soft`
- `COCKPIT_FORCE_LOCAL_OPERATIONAL_BRIEF=0`
- `COCKPIT_CONTEXT_GATHER_TIMEOUT_SECONDS=60`
- `COCKPIT_MAX_USER_MESSAGE_CHARS=8000`
- `COCKPIT_NPX_PATH=npx`

Evidence:

- These defaults are set in [financial-engine_v2/scripts/cockpit_tui.py](/home/l4nd0/tenn/financial-engine_v2/scripts/cockpit_tui.py#L100).

## Tests Added Or Updated With The New Model

The rewrite added or updated tests around provider precedence and preboot behavior.

Evidence:

- Env override tests for `allow_env_override: true` live at [financial-engine_v2/scripts/test_cockpit_llm_provider_config.py](/home/l4nd0/tenn/financial-engine_v2/scripts/test_cockpit_llm_provider_config.py#L18).
- Commit `6db38b09` also reports changes to:
  - `financial-engine_v2/cockpit/tests/test_preboot_router_mode.py`
  - `financial-engine_v2/cockpit/tests/test_config_router_mode.py`
  - `financial-engine_v2/cockpit/tests/test_llm_backend_readonly_format.py`
  - `financial-engine_v2/cockpit/tests/test_llm_profile.py`

One stale-looking expectation remains in the script-level preboot tests:

- [financial-engine_v2/scripts/test_cockpit_preboot.py](/home/l4nd0/tenn/financial-engine_v2/scripts/test_cockpit_preboot.py#L95) still expects `_merge_preboot_flags()` to export `COCKPIT_LLM_PROVIDER` and `COCKPIT_LLM_MODEL`.
- Current `cockpit_tui.py` no longer sets those env vars in `_merge_preboot_flags()`, and instead only exports preboot profile/read-only/no-web plus profile env values. See [financial-engine_v2/scripts/cockpit_tui.py](/home/l4nd0/tenn/financial-engine_v2/scripts/cockpit_tui.py#L358).

## Operator Impact

- Editing `config/cockpit.local.yaml` alone no longer describes the full Cockpit LLM setup. `config/cockpit_llm.yaml` is now part of the launch contract.
- The preboot screen is less about directly editing every routing field and more about selecting safe launch profiles while showing the resolved effective config.
- The repo default is now local-first llama.cpp chat with `hybrid_router_policy: local_preferred`, plus centralized defaults for extraction, embeddings, and Anthropic fallback.
- Host envs are safer by default because `allow_env_override` is committed as `false`, but operators can still opt into env-driven overrides explicitly.
- Runtime routing has moved further away from ad hoc preboot model overrides and closer to a fixed YAML policy plus `HybridRouter` policy resolution during chat startup.

## Commit Timeline

| Date | Commit | Summary |
|---|---|---|
| 2026-03-28 | `fe854582` | Added router-mode opt-in plumbing in config and preboot |
| 2026-03-28 | `17037d46` | Centralized `.env` loading in shared config for all Cockpit entrypoints |
| 2026-03-28 | `b37ce9df` | Added operator cheat sheet covering preboot and routing |
| 2026-03-29 | `6db38b09` | Landed config expansion, LLM profiles, and preboot simplification |

## Investigation Limits

- I could not read Claude's shared project memory index because the sandbox denied access to `/home/l4nd0/.claude/projects/-home-l4nd0-tenn/memory/MEMORY.md`.
- I therefore verified changes from git history, current code, and repo docs only.
- I cannot prove which edits were made specifically by Cursor agents versus other local agents; the evidence supports "recent repo changes" more strongly than exact agent attribution.

## Known Mismatches Worth Following Up

- `docs/ops/cockpit_functionality_limits.md` still describes environment variables as broad routing controls without clearly documenting the new `allow_env_override` gate.
- `financial-engine_v2/scripts/test_cockpit_preboot.py` still expects preboot to export explicit LLM provider/model env vars, but current launcher code no longer does that.
- `financial-engine_v2/cockpit/core/config.py` falls back from `COCKPIT_LLM_MODEL` to `EXTRACT_MODEL` inside `_apply_llm_env_overrides()`, which couples chat model fallback to extraction-model env state.
