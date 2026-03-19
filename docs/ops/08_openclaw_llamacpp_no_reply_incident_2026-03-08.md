# OpenClaw + llama.cpp NO_REPLY Incident (2026-03-08)

## Summary

OpenClaw local/TUI sessions were returning `NO` / `NO_REPLY` for normal prompts even though llama.cpp was healthy and reachable.

Current default profile note as of 2026-03-09:

- Tenn now keeps the checked-in llama.cpp startup profile in `scripts/run_llama_server.sh` and `systemd/llama-cpp-qwen25.service`.
- The checked-in launcher default remains `http://127.0.0.1:8000/v1`, but the current host override and OpenClaw providers are pinned to `http://127.0.0.1:8001/v1`.
- The default model slot is `models/model.gguf`, with optional host overrides in `~/.config/tenn/llama-server.env`.

## What Happened

- User-visible symptom:
  - `openclaw tui` and `openclaw agent --local` often returned `NO`/`NO_REPLY` or `No reply from agent.`
- Service state:
  - `llama-cpp-qwen25.service` was active and serving `qwen2.5-coder-7b`.
  - OpenClaw gateway was active.
- Validation:
  - Direct request to cpp endpoint produced normal text:
    - `/v1/chat/completions` returned `Hello from model`.

Inference: model/server path was functional; the suppression happened in OpenClaw orchestration/prompting.

## Root Cause

- OpenClaw interactive sessions used prompt mode `"full"`.
- Full mode includes a global silent-reply instruction section centered on `NO_REPLY`.
- With this local model/profile, that instruction dominated normal chat turns.

Secondary noise during debugging:
- Stale session lockfiles and orphaned `openclaw-agent` workers caused intermittent lock timeout errors.
- Attempted GLM blob swap in cpp failed because current llama.cpp build did not support architecture `glm4moelite`.

## Fix Applied

1. Stabilization:
- Cleared stale `openclaw-agent` processes and session lockfiles.
- Restarted `openclaw-gateway.service`.

2. Workspace prompt hardening:
- Updated workspace files to prefer direct visible replies:
  - `/home/l4nd0/tenn/AGENTS.md`
  - `/home/l4nd0/tenn/BOOTSTRAP.md`

3. Runtime behavior fix (effective):
- Patched OpenClaw local dist runtime to force `resolvePromptModeForSession(...)` to return `"minimal"`:
  - `/home/l4nd0/.nvm/versions/node/v22.22.0/lib/node_modules/openclaw/dist/reply-DhtejUNZ.js`
  - `/home/l4nd0/.nvm/versions/node/v22.22.0/lib/node_modules/openclaw/dist/pi-embedded-DgYXShcG.js`
  - `/home/l4nd0/.nvm/versions/node/v22.22.0/lib/node_modules/openclaw/dist/pi-embedded-CtM2Mrrj.js`
  - `/home/l4nd0/.nvm/versions/node/v22.22.0/lib/node_modules/openclaw/dist/subagent-registry-CkqrXKq4.js`
  - `/home/l4nd0/.nvm/versions/node/v22.22.0/lib/node_modules/openclaw/dist/plugin-sdk/reply-DFFRlayb.js`

4. Runtime config pinned for this host:
- `agents.defaults.model.primary = llamacpp/qwen2.5-coder-14b` (current host default)
- `tools.profile = minimal` + `tools.alsoAllow` for required coding/runtime tools
- `agents.defaults.compaction.memoryFlush.enabled = false`
- Current caveat: if `tools.profile = coding`, some builds warn that `apply_patch` / `image` are unknown unless matching plugin tools are enabled.

## Verification

- Smoke test passed:
  - `openclaw agent --local --session-id quick-hi -m "hi"`
  - Returned normal assistant text (not `NO`/`NO_REPLY`).
- cpp model path remained functional.

## Future Impact

- Upgrade risk:
  - The effective fix is a local patch under `node_modules`; OpenClaw updates/reinstall can overwrite it.
- Operability risk:
  - If patch is lost, symptom can recur immediately in local/TUI.
- Model portability risk:
  - Not all Ollama blobs are loadable by current llama.cpp build (example: GLM `glm4moelite` unsupported).
- Maintenance implication:
  - Post-update validation must include a local chat sanity check, not only service health.

## Recommended Ongoing Checks

- After any OpenClaw update:
  - Run `openclaw agent --local --session-id health-chat -m "hi"`.
  - Confirm output is normal text and not `NO`/`NO_REPLY`.
- Keep one direct cpp endpoint test:
  - Call `/v1/chat/completions` against the live host endpoint from `~/.openclaw/openclaw.json` (`127.0.0.1:8001` on this machine) with API key.
- If lock errors reappear:
  - Stop stale workers, remove stale `*.lock`, restart gateway.
