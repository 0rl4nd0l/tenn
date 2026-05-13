# Validation Matrix

## Checks run

| check | command | result | proves | does not prove |
| --- | --- | --- | --- | --- |
| Date/time | `date -Iseconds` | `2026-05-13T11:03:40+10:00` | Audit timestamp | Runtime freshness after this point |
| Working directory | `pwd`; `git rev-parse --show-toplevel` | `/home/l4nd0/tenn`; git root `/mnt/hdd-data/home/l4nd0/tenn` | Symlink/logical cwd and true repo root | Files outside repo |
| Branch/HEAD | `git branch --show-current`; `git rev-parse HEAD`; `git rev-parse --short=12 HEAD` | `preserve/dirty-work-20260430T065748Z`; `5295d5cbd7fcaec626d8a99dd006c4663a682372`; `5295d5cbd7fc` | Current checkout | Remote state |
| Git status | `git status --short --untracked-files=all` | Five untracked task cards | Dirty visible state | Ignored report artifacts |
| Worktrees | `git worktree list` | Large multi-worktree estate | Current and nearby worktrees | Active human intent |
| Recent log | `git log --oneline --decorate -20` | Recent Cockpit/runtime/news/memory commits | HEAD context | Test health |
| Task card validation | `python3 scripts/agent_job_contract.py validate ...` | `ok: true` | Task-card schema valid | Collision safety |
| Registry active list | `python3 scripts/agent_job_registry.py list-active` | no active jobs | No registry claim currently active | Unregistered live work |
| Registry overlap | `python3 scripts/agent_job_registry.py check-overlap ...` | `ok: false` | Dirty task cards block clean claim | Whether files should be kept |
| Registry claim | `python3 scripts/agent_job_registry.py claim ...` | failed | No claim acquired | Future claim after cleanup |
| Diff whitespace | `git diff --check` | no output, exit 0 | No whitespace conflict in tracked diff | Ignored files/tests |
| Check-diff | `python3 scripts/agent_job_contract.py check-diff ...` | `ok: false` | Four dirty files outside allowlist | Whether those files are bad |
| Frontend route count | `find cockpit-ui/app -path '*/page.tsx' | wc -l` | 19 | Page route count | Runtime rendering |
| BFF route count | `find cockpit-ui/app -name route.ts | wc -l` | 52 | Route-handler count | Contract correctness |
| Backend route count | `rg '@router|@app' ... | wc -l` | 162 | Backend route decorator count | Mounted reachability of every route |
| Port scan | `ss -ltnp | rg ...` | 8000, 8001, 6333, 6379, 5050, 8081 listening | Services present | Deep service health |
| Backend health GET | `curl http://127.0.0.1:8000/api/health` | `{"status":"ok"}` | Backend responds | Authenticated routes |
| Llama health GET | `curl http://127.0.0.1:8001/health` | `{"status":"ok"}` | llama.cpp responds | Inference stability |
| Cockpit health GET | `curl http://127.0.0.1:8081/api/cockpit/health` | healthy service summary | Frontend BFF health path works | All UI pages |
| Chorus GET | `curl http://127.0.0.1:5050` | HTML returned | Chorus UI running | Chorus task correctness |

## Checks not run

| check | reason not run | recommended condition |
| --- | --- | --- |
| `pnpm -C cockpit-ui test` | Audit-only and dirty registry/check-diff blockers | Run after task-card cleanup and claim |
| `pnpm -C cockpit-ui lint` | Could be safe, but broad and not necessary for audit-only report | Run after cleanup |
| Playwright | Browser automation can accidentally touch mutating controls | Run read-only scripted smoke after explicit plan |
| Backend pytest | Broad tests may invoke runtime/data paths | Run selected collection after cleanup |
| Extraction eval POST | Mutating/heavy workload | Only under Evaluation/Financial Truth task |
| Marketplace scan/sync/calibration | Mutating external/runtime operations | Only under explicit Marketplace task |
| Memory add/expire/thesis mutation | Memory writes prohibited by this audit | Only under Memory task with confirmation |
| Qdrant/database sync/backfill | Explicitly forbidden | Separate approved task only |

## Available scripts and dependencies

| surface | evidence |
| --- | --- |
| Frontend package scripts | `dev`, `build`, `start`, `lint`, `test`, `test:e2e`, `test:e2e:ui` in `cockpit-ui/package.json` |
| Package manager/runtime | `pnpm 10.33.0`, `node v22.22.0` |
| Python | `python3 3.10.12`; venv pytest `8.3.5` |
| Backend start | README canonical isolated backend: `LOCAL_BACKEND_PROFILE=isolated financial-engine_v2/scripts/run_local_backend.sh` |
| Frontend start | README/Cockpit conventions point to `cockpit start new`; Next server observed on `:8081` |

## Freshness

| evidence | freshness |
| --- | --- |
| Git/registry/route counts/health probes | Fresh, current turn |
| Current report files | Fresh, current turn |
| Prior report `status.json` files | Stale unless verified against current code |
| Claude memory and HANDOFF docs | Background only, not current truth without code verification |

