# Tenn Agent Setup Docs V1

State: `DONE_WITH_RISK`

## Objective

Add Tenn-specific `docs/agents/` configuration for generic engineering skills
that expect issue tracker, triage label, and domain-doc setup, without importing
Matt Pocock's default labels or generic GitHub mutation posture.

## Evidence Used

- Current canonical base: `origin/migration/clean-runtime-baseline-reconstruct-v1`
  at `9973f508e45bc71c3911532c79874f8c1e690cc9`.
- Issue #78 is open and covers agent markdown / Codex repo documentation.
- Local Matt setup skill copy exists under
  `/home/l4nd0/.codex/skills.disabled/context-bloat-20260529T154516/setup-matt-pocock-skills/`.
- Public skill documentation describes the setup as prompt-driven and focused on
  issue tracker, triage labels, and domain-doc layout.
- Live Tenn labels use `lane:*`, `mode:*`, `risk:*`, `type:*`, `state:*`, and
  related Tenn labels rather than Matt's defaults.

## Files Touched

- `AGENTS.md`
- `docs/agent_tasks/tenn_agent_setup_docs_v1_20260608.md`
- `docs/agents/issue-tracker.md`
- `docs/agents/triage-labels.md`
- `docs/agents/domain.md`
- `reports/agent_jobs/tenn_agent_setup_docs_v1_20260608/README.md`

## Files Intentionally Not Touched

- Product, backend, frontend, runtime, extraction, parser, prompt, gold-label,
  DB, Qdrant, Redis, news, memory, source-PDF, backfill, service, model, and GPU
  surfaces.
- `.codex/config.toml`, `.codex/hooks.json`, and host skill directories.
- GitHub issues and labels, unless a later approved PR/open action is performed.

## Validation

| Command | Exit | Result |
| --- | ---: | --- |
| `python3 scripts/agent_job_contract.py validate docs/agent_tasks/tenn_agent_setup_docs_v1_20260608.md` | 0 | Passed; no validation issues. |
| `python3 scripts/agent_job_registry.py list-active --read-only` | 0 | Passed; returned no active jobs, `read_only: true`, `lock_acquired: false`. |
| `git diff --check` | 0 | Passed. |
| `git diff --cached --check` | 0 | Passed after staging allowlisted files. |
| `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/tenn_agent_setup_docs_v1_20260608.md --no-write-report` | 0 | Passed after force-adding the ignored report artifact; no disallowed files. |

No runtime or extraction tests were run because this is a docs/control-plane
configuration slice only.

## Unsafe Actions Avoided

- No extraction sample, count-24, count-32, broad extraction, or backfill.
- No DB, Qdrant, Redis, news, memory, source-PDF, gold-label, prompt, runtime,
  service, model, GPU, or production-data mutation.
- No dependency install.

## Remaining Risk

- `reports/` is ignored by repo rules and must be force-added for preservation.
- Generic engineering skills may still have their own default behavior; Tenn
  docs now tell them to use existing Tenn labels and fail closed on GitHub
  writes unless explicitly approved.

## Next Recommended Prompt

```text
Review the Tenn agent setup docs PR. Confirm that docs/agents maps Matt-style
setup concepts to Tenn issue/task/report conventions without importing generic
labels or write behavior. If checks are green and scope is clean, merge it into
origin/migration/clean-runtime-baseline-reconstruct-v1.
```
