# Real-Gold Source PDF Placement Runbook

This runbook restores reviewability in a clean checkout without committing raw filings.

## Inputs

- Committed metadata manifest: `financial-engine_v2/backend/tests/eval_source_assets/real_gold_review_source_assets.json`
- Optional approved off-git raw-PDF bundle: not created by this task.

## Placement Targets

Use one of these roots, preserving every path below `data/asx/docs/` exactly:

- Workspace target: `financial-engine_v2/data/asx/docs/`
- Mounted runtime target: `/data/asx/docs/`

## Restore Steps

1. Obtain the explicit off-git bundle from the operator-approved storage location.
2. Extract or copy each PDF so its relative path matches the manifest `source_file`.
3. Do not add raw PDFs to git. They are expected to remain ignored/off-git.
4. Validate identity by resolving the manifest and checking `present_verified` for every asset.
5. Run the focused corpus asset test with `TENN_REQUIRE_REAL_GOLD_SOURCE_ASSETS=1`.

## Validation Commands

```bash
PYTHONPATH=financial-engine_v2/backend python3 - <<'PY'
from pathlib import Path
from app.services.extraction_gold_eval_scorecard import resolve_source_asset_manifest
payload = resolve_source_asset_manifest(
    'financial-engine_v2/backend/tests/eval_source_assets/real_gold_review_source_assets.json',
    workspace_root=Path.cwd(),
)
print(payload['status_counts'])
PY
TENN_REQUIRE_REAL_GOLD_SOURCE_ASSETS=1 PYTHONPATH=financial-engine_v2/backend \
  uv run --python 3.10 --with pytest --with pydantic-settings==2.6.1 --with pydantic==2.9.2 \
  python -m pytest financial-engine_v2/backend/tests/test_extraction_gold_eval.py \
  -q -k load_real_gold_corpus_accepts_operating_cash_flow_alias_and_source_paths
```

## Current Host Result

Current resolver counts: `present_verified=15`, `missing=0`, `present_metadata_mismatch=0`.

Source reviewability does not prove extracted metric correctness; #97 remains the extracted-payload scoring gate.
