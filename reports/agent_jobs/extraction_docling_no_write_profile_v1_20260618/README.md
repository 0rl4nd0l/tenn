# Certified Docling No-Write Profile

State: DONE_WITH_RISK

Implemented a `docling-no-write` profile for
`scripts/extraction_no_write_replay.py`.

The default `baseline-no-write` profile remains unchanged. The new profile is
approval-free only for certified manifest cases and approved existing venv
paths:

```bash
python3 scripts/extraction_no_write_replay.py \
  --profile docling-no-write \
  --venv-python financial-engine_v2/.venv/bin/python \
  --case HUB \
  --case-manifest financial-engine_v2/data/extraction_no_write_cases/guard_cases_v1.json \
  --report-dir reports/agent_jobs/<job_id>/docling_preflight
```

## Contract

- Uses only approved existing repo/backend venv Python paths:
  - `financial-engine_v2/.venv/bin/python`
  - `financial-engine_v2/.venv/bin/python3`
  - `.venv/bin/python`
  - `.venv/bin/python3`
- Does not install dependencies or repair environments.
- Re-execs under the approved venv before importing extraction runtime modules.
- Requires `docling` to import successfully before extraction starts.
- Refuses manifest cases pinned to a non-docling parser backend.
- Preserves the existing no-write runtime contract: isolated `DATA_ROOT`,
  `HOME`, `TMPDIR`, XDG roots, loopback LLM URL, in-memory DB/Redis settings,
  disabled embeddings/Qdrant/session memory/router feedback, report-only
  durable writes, and side-effect audit artifacts.

## Validation Result

Focused unit validation passed: `15 tests`.

`docling-no-write --preflight-only --case HUB` returned `DATA_MISSING`, which is
the expected safe result on this host because no approved docling-capable venv
exists in this worktree:

```json
{
  "profile": "docling-no-write",
  "status": "DATA_MISSING",
  "reason": "approved_docling_venv_python_missing",
  "side_effect_pass": true
}
```

No extraction was run by the docling profile in this closeout.

## Remaining Risk

The profile is implemented and fail-closed, but a real docling-backed replay is
still `DATA_MISSING` until an approved existing venv is present. Creating or
repairing that venv remains a separate explicit environment task.
