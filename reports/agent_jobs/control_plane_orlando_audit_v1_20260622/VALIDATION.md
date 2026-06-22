# Validation

Status: final validation passed for the docs/report audit branch. Runtime Functionality Proof is not applicable to docs-only output, but all monitor/worker claims in the docs are backed by command evidence and classified with `IMPLEMENTED`, `PARTIAL`, `HOST_ONLY`, `NOT_FOUND`, `STALE`, or related status terms.

## Final Results

Task card validate:

```bash
python3 scripts/agent_job_contract.py validate docs/agent_tasks/control_plane_orlando_audit_v1_20260622.md
```

Result: `ok: true`.

Ledger path:

```bash
python3 scripts/agent_task_ledger.py resolve-path
```

Result: `/mnt/sdb2/home/l4nd0/tenn/.git/tenn-agent-registry/task-ledger.jsonl`.

Registry read-only:

```bash
python3 scripts/agent_job_registry.py list-active --read-only --repo-root .
```

Result: `ok: true`, no active jobs, read-only, no lock acquired.

Ledger validate:

```bash
python3 scripts/agent_task_ledger.py validate
```

Result: `ok: true`, 15 live entries, no issues, no data missing.

OpenCode probe:

```bash
python3 scripts/opencode_worker_bridge.py probe
```

Result: exit 0; OpenCode available.

Probe summary: command `/home/l4nd0/.opencode/bin/opencode`, version `1.3.17`, visible agent `build (primary)`, DeepSeek available.

OpenCode bridge tests:

```bash
python3 -m unittest tests.test_opencode_worker_bridge
```

Result: 26 tests passed.

Runtime proof docs check:

```bash
python3 scripts/check_runtime_functionality_proof_docs.py
```

Result: `runtime_functionality_proof_docs_ok`.

Codex hooks JSON parse:

```bash
python3 -m json.tool .codex/hooks.json
```

Result: parsed successfully.

Skill count:

```bash
find .agents/skills -maxdepth 2 -name SKILL.md | sort
```

Result: 10 visible repo-backed skill files.

Skill frontmatter/H1 check:

```bash
for f in $(find .agents/skills -maxdepth 2 -name SKILL.md | sort); do ...; done
```

Result: all 10 files start with YAML frontmatter and have an H1.

Markdown path/link hygiene:

```bash
scripts/check_markdown_hygiene.sh
```

Result: internal markdown link scan passed.

Diff whitespace check:

```bash
git diff --check
```

Result: passed.

Allowed-diff check:

```bash
python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/control_plane_orlando_audit_v1_20260622.md --no-write-report
```

Result: `ok: true`, no disallowed files.

Report artifacts check:

```bash
python3 scripts/agent_job_contract.py check-report-artifacts docs/agent_tasks/control_plane_orlando_audit_v1_20260622.md
```

Result: `ok: true`, all required report artifacts exist and are non-empty.

Forbidden path guards:

```bash
product/runtime/data/extraction/count-24 guard
host-global guard
```

Result: both passed.

Git hooks check:

```bash
python3 scripts/check_agent_hooks.py --repo-root .
```

Result: `ok: false`; configured hooks path was stale/missing in this worktree. Classified as PARTIAL in the docs.

This hook check is an audited control-plane gap, not a validation failure for the docs/report change.
