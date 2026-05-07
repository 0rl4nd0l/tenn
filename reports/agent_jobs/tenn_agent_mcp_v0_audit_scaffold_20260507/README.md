# Tenn Agent MCP V0 Audit Scaffold

## Summary

Implemented a local-first stdio MCP scaffold for Tenn agent-job orchestration under `tools/tenn_agent_mcp/`. The scaffold is intentionally bounded to task-card creation, registry reads, audit-only launch planning, status reads, and report reads.

No backend runtime, Cockpit product surface, financial truth, Qdrant, news store, memory store, holdings, gold-label, source-PDF, extraction-output, or live service was touched.

## Preflight

| Item | Result |
| --- | --- |
| Lane | Evaluation |
| Branch | `safe/tenn-agent-mcp-v0-audit-scaffold-20260507` |
| Worktree | `/mnt/sdb2/home/l4nd0/tenn-agent-mcp-v0-audit-scaffold-20260507` |
| HEAD | `b17e2bcc4b06` |
| Execution mode | SAFE EXTENSION MODE |
| Contested surfaces touched | none |
| Collision risk | LOW |
| GPU process check | not required |

Task-card validation:

```text
python3 scripts/agent_job_contract.py validate docs/agent_tasks/tenn_agent_mcp_v0_audit_scaffold_20260507.md --write-report
PASS ok=true
```

Registry:

```text
python3 scripts/agent_job_registry.py list-active --repo-root "$(pwd)"
PASS ok=true
```

One active job was present during preflight:

```text
marketplace_match_recency_contract_v1
lane: Reporting
worktree: /mnt/sdb2/home/l4nd0/tenn-marketplace-match-recency-contract-v1
```

Overlap:

```text
python3 scripts/agent_job_registry.py check-overlap docs/agent_tasks/tenn_agent_mcp_v0_audit_scaffold_20260507.md --repo-root "$(pwd)"
PASS ok=true issues=[]
```

Claim:

```text
python3 scripts/agent_job_registry.py claim docs/agent_tasks/tenn_agent_mcp_v0_audit_scaffold_20260507.md --repo-root "$(pwd)"
PASS ok=true
```

Release:

```text
python3 scripts/agent_job_registry.py release tenn_agent_mcp_v0_audit_scaffold_20260507 --repo-root "$(pwd)"
PASS ok=true
```

## Tools Exposed

- `list_capabilities`: read-only server capability and security posture summary.
- `create_task_card`: token-gated creation of validated non-production task cards under `docs/agent_tasks/`.
- `list_active_jobs`: read-only shared registry listing.
- `launch_codex_audit`: token-gated dry-run-by-default audit-only Codex launch planner.
- `get_agent_status`: read-only `status.json` plus active-registry lookup for one job id.
- `read_agent_report`: read-only bounded `README.md` read under `reports/agent_jobs/<job_id>/`.

## Security Model

- Stdio transport only in this scaffold.
- Local HTTP/SSE defaults are reserved as `127.0.0.1:8765`; no network listener is opened.
- Non-read tools require `TENN_AGENT_MCP_TOKEN`.
- `launch_codex_audit` defaults to dry-run.
- Real launch requires `dry_run=false` and `TENN_AGENT_MCP_ENABLE_LAUNCH=1`.
- Real launch uses a fixed `codex exec --cd <repo> ...` argv; callers cannot provide shell commands.
- `launch_codex_audit` only accepts task cards under `docs/agent_tasks/<job_id>.md` and refuses non-`audit_only` cards.
- Job/report reads are scoped by validated `job_id` only.
- `create_task_card` rejects absolute paths and `..` path traversal in `allowed_files`.

Hard refusals preserved:

- no production data access
- no arbitrary shell tool
- no unrestricted filesystem access
- no runtime database mutation
- no Qdrant/news/company-memory/financial-truth access
- no auto-merge
- no recursive self-launching loops

## Validation Run

| Command | Result |
| --- | --- |
| `python3 -m py_compile tools/tenn_agent_mcp/server.py tools/tenn_agent_mcp/__main__.py tools/tenn_agent_mcp/__init__.py` | PASS |
| `/mnt/sdb2/home/l4nd0/tenn/financial-engine_v2/.venv/bin/python -m pytest tests/tools/tenn_agent_mcp/test_server.py -q` | PASS: `8 passed in 0.21s` |
| `/mnt/sdb2/home/l4nd0/tenn/financial-engine_v2/.venv/bin/python -m ruff check tools/tenn_agent_mcp tests/tools/tenn_agent_mcp` | PASS: `All checks passed!` |
| `python3 -m tools.tenn_agent_mcp --help` | PASS |
| `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/tenn_agent_mcp_v0_audit_scaffold_20260507.md --repo-root "$(pwd)" --no-write-report` | PASS: `ok=true` |
| `git diff --check && git diff --cached --check` | PASS |

System Python gaps:

```text
python3 -m pytest tests/tools/tenn_agent_mcp/test_server.py -q
FAIL: /usr/bin/python3: No module named pytest

python3 -m ruff check tools/tenn_agent_mcp tests/tools/tenn_agent_mcp
FAIL: /usr/bin/python3: No module named ruff
```

The repo venv from `/mnt/sdb2/home/l4nd0/tenn/financial-engine_v2/.venv/bin/python` was used for pytest and ruff.

## Files Changed

- `docs/agent_tasks/tenn_agent_mcp_v0_audit_scaffold_20260507.md`
- `tools/tenn_agent_mcp/README.md`
- `tools/tenn_agent_mcp/__init__.py`
- `tools/tenn_agent_mcp/__main__.py`
- `tools/tenn_agent_mcp/server.py`
- `tests/tools/tenn_agent_mcp/test_server.py`
- `reports/agent_jobs/tenn_agent_mcp_v0_audit_scaffold_20260507/README.md`
- `reports/agent_jobs/tenn_agent_mcp_v0_audit_scaffold_20260507/status.json`
- `reports/agent_jobs/tenn_agent_mcp_v0_audit_scaffold_20260507/validation.json`

## DATA_MISSING

- Exact Codex CLI flags for long-running background agent orchestration were not verified by real launch; real launch is intentionally gated and was not executed.
- Whether this scaffold should later be registered in `.mcp.json` is not decided. No `.mcp.json` or `scripts/mcp/` change was made in this task.

## Remaining Risks

- `tools/` and `tests/` are ignored by `.gitignore`, and `reports/` is ignored by `.git/info/exclude`; these files must be force-added for the milestone commit.
- Real `launch_codex_audit` behavior remains a guarded V0 path and should be validated only with an explicit operator-approved dry-run-to-real-launch task.

## Next Safe Step

Review whether to add a launcher under `scripts/mcp/` and documentation under `docs/claude/mcp-servers.md` in a separate task card. This task intentionally avoided those files because they were outside the approved scope.

`/save` recommendation: yes, after the milestone commit lands, because this adds a new local agent-control scaffold.
