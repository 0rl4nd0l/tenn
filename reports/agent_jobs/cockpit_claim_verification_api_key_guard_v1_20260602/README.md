# Cockpit Claim Verification API Key Guard

## Summary

GitHub issue: #224

This safe-extension task adds the canonical backend `require_api_key` dependency to `POST /api/cockpit/claims/verify`.

## Scope

Changed files:

- `financial-engine_v2/backend/app/routes/cockpit_claims.py`
- `financial-engine_v2/backend/tests/test_claim_verification.py`
- `financial-engine_v2/backend/tests/test_local_api_key.py`
- `docs/agent_tasks/cockpit_claim_verification_api_key_guard_v1_20260602.md`

No Cockpit UI, BFF, runtime, memory, data-store, parser, extraction, Qdrant, model, or financial-truth files were changed.

## Red Phase

Command:

```bash
/home/l4nd0/tenn-nvme-clean-baseline-reconstruct-v1/financial-engine_v2/.venv/bin/python -m pytest financial-engine_v2/backend/tests/test_claim_verification.py financial-engine_v2/backend/tests/test_local_api_key.py -q
```

Result before the route guard:

- `test_claim_verification_endpoint_rejects_missing_api_key_when_configured` failed because the endpoint returned `200` instead of `401`.
- `test_claim_verification_endpoint_rejects_wrong_api_key_when_configured` failed because the endpoint returned `200` instead of `401`.
- `test_protected_routes_register_api_key_dependency[/api/cockpit/claims/verify-POST]` failed because the route had no canonical API-key dependency.

## Green Phase

Command:

```bash
/home/l4nd0/tenn-nvme-clean-baseline-reconstruct-v1/financial-engine_v2/.venv/bin/python -m pytest financial-engine_v2/backend/tests/test_claim_verification.py financial-engine_v2/backend/tests/test_local_api_key.py -q
```

Result after the route guard:

- `25 passed`
- Warnings were pre-existing pydantic/FastAPI deprecation warnings from imported backend app setup.

Additional validation:

```bash
/home/l4nd0/tenn-nvme-clean-baseline-reconstruct-v1/financial-engine_v2/.venv/bin/python -m ruff check financial-engine_v2/backend/app/routes/cockpit_claims.py financial-engine_v2/backend/tests/test_claim_verification.py financial-engine_v2/backend/tests/test_local_api_key.py
```

Result: `All checks passed!`

## Contract Notes

- The backend remains the route guard authority.
- Authenticated claim verification behavior remains covered by the structured verdict test.
- Empty `assistant_text` still returns `400` after a valid API key is provided.
- No unauthenticated fallback path was introduced.
