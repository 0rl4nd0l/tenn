# Verification Source PDF BFF Auth Parity V1

Implemented GitHub issue #155 for Verification source-PDF opening.

## What changed

- Added `cockpit-ui/app/api/extraction-eval/confirmed-metric-coverage/source/route.ts`.
- The route forwards an explicit `X-API-Key` request header or the configured `NEXT_PUBLIC_API_KEY` to the existing backend source-PDF route.
- The backend route remains protected and remains responsible for source resolution and allowlist enforcement.
- The route preserves backend PDF content headers and fails closed with `DATA_MISSING` when no API key can be forwarded.
- The Verification source detail panel now disables source opening with a visible `DATA_MISSING` reason when no Cockpit API key is available.

## Evidence

- Focused UI and BFF route tests passed.
- Targeted ESLint passed.
- TypeScript passed.
- Next build passed and listed the BFF route.
- Authenticated route forwarding was tested without printing any secret value.
