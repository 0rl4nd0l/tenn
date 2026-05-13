# Runtime Visibility

## Confirmed Facts

- Audit timestamp: `2026-05-12T19:08:00+10:00`.
- Repo root: `/mnt/hdd-data/home/l4nd0/tenn`.
- Shell `pwd` resolved through the symlink path as `/home/l4nd0/tenn`; `git rev-parse --show-toplevel` resolved the canonical repo path as `/mnt/hdd-data/home/l4nd0/tenn`.
- Current branch: `preserve/dirty-work-20260430T065748Z`.
- Current HEAD: `dabbc456e42f737d12e6a1d979e6189e0936e865` (`dabbc456e42f`).
- Listening ports from `ss -ltnp`: `:8081` has `next-server (v16.2.0)` PID `39721`; `:8000` is listening; `:8001` has `llama-server` PID `36207`; `:3000` is not listening.
- `curl -sI http://127.0.0.1:8081` returned `HTTP/1.1 200 OK` with `X-Powered-By: Next.js`.
- `curl -sI http://127.0.0.1:3000` returned no response body/header in this audit.
- Next process command chain:
  - PID `39699`: `node .../pnpm start --port 8081`
  - PID `39720`: `sh -c next start --port 8081`
  - PID `39721`: `next-server (v16.2.0)`
- `/proc/39721/cwd` and `/proc/39699/cwd` both resolve to `/mnt/hdd-data/home/l4nd0/tenn/cockpit-ui`.
- `/proc/39721/environ` includes `NEXT_PUBLIC_API_URL=http://localhost:8000` and `PWD=/mnt/hdd-data/home/l4nd0/tenn/cockpit-ui`.
- `git -C /proc/39721/cwd rev-parse --abbrev-ref HEAD` returned `preserve/dirty-work-20260430T065748Z`.
- `git -C /proc/39721/cwd rev-parse HEAD` returned `dabbc456e42f737d12e6a1d979e6189e0936e865`.

## Inferred Facts

- The live `:8081` Cockpit runtime is serving the current preserve worktree and current preserve HEAD.
- There is no `:3000` runtime competing with `:8081` for Cockpit validation in this audit.

## DATA_MISSING

- `lsof -nP -iTCP:8081 -sTCP:LISTEN` returned no rows even though `ss` and `/proc` identified the listener. The listener identity is therefore grounded in `ss`, `ps`, `/proc`, and curl evidence, not `lsof`.
