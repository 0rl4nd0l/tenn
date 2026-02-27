# Axon Setup (Scoped to Code)

This repo is large and data-heavy, so Axon is configured to index a scoped workspace instead of the full tree.

## Prerequisites

- Docker daemon available to your user.
- Network access for first image build (pull base image + Axon install).

## Commands

Build image:

```bash
./scripts/axon.sh install
```

Create/update scoped workspace snapshot at `.axon_scope/`:

```bash
./scripts/axon.sh prepare
```

Use full scope (includes both script trees):

```bash
AXON_SCOPE_MODE=full ./scripts/axon.sh prepare
```

Index scoped workspace:

```bash
./scripts/axon.sh analyze --full
```

Query indexed code:

```bash
./scripts/axon.sh query "Where is extraction pipeline orchestrated?"
```

Run MCP server over stdio:

```bash
./scripts/axon.sh mcp
```

Optional: pass Hugging Face auth token to reduce Hub rate limits:

```bash
HF_TOKEN=hf_xxx ./scripts/axon.sh query "Where is extraction pipeline orchestrated?"
```

## Scope Contents

Default scope (`AXON_SCOPE_MODE=core`) copies:

- `financial-engine_v2/backend`
- `financial-engine_v2/cockpit`
- `financial-engine_v2/config`
- `docs`
- root `*.py`
- `README.md`, `runbook.md`

Full scope (`AXON_SCOPE_MODE=full`) additionally copies:

- `financial-engine_v2/scripts`
- `scripts`

Axon index artifacts are stored under `.axon_scope/.axon/`.
Cache files are stored under `.axon_scope/.cache/` and preserved across `prepare` runs.
