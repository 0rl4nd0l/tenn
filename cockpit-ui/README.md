# TENN Cockpit UI

This directory contains restored minimal source for the local TENN Cockpit shell.

The previous checkout contained only `.next/`, `node_modules/`, and build artifacts. This source restores a small Next.js app with:

- `/` local status page
- `/api/cockpit/config`
- `/api/cockpit/health`
- `/api/cockpit/watchlist`
- `/api/cockpit/holdings`

The full historical cockpit surface shown in `.next/server/app-paths-manifest.json` is not fully reconstructed here. Treat this as a safe source baseline and expand route-by-route with tests.

## Commands

```bash
pnpm install
pnpm route:check
pnpm test
pnpm build
```

Set `NEXT_PUBLIC_API_URL`, `TENN_API_KEY`, or `API_KEY` to connect to the backend.
