# Implementation Discipline Skill

## Source Trace
- `docs/architecture/11_engineering_discipline.md` (Confirmed)
- `docs/entrypoints.md` (Confirmed — validation sequence)
- `docs/cloud_workflow.md` (Confirmed — cloud workflow rules)
- `docs/ops/README.md` (Confirmed — change control)
- `CLAUDE.md` (this repo) (Confirmed)

---

## The Rule: Extract → Analyze → Implement

Never write code without reading the code you are about to change.

1. **Extract** — Read the relevant files. Identify invariants and existing patterns.
2. **Analyze** — Understand the impact. Identify safety-sensitive areas. Check for conflicts.
3. **Implement** — Make the minimal change. Match existing style. Do not refactor unrelated code.

---

## Pre-Task

Before starting any implementation task:

- [ ] Read `docs/entrypoints.md` — know the correct execution path
- [ ] Read `docs/claude/safety.md` — confirm no prohibited actions
- [ ] Identify which subsystem is affected (see `docs/claude/architecture/system-map.md`)
- [ ] Read the relevant architecture doc for that subsystem
- [ ] Write a plan (even a 3-line summary) before touching code
- [ ] Confirm the scope is narrow (one subsystem per task)

---

## Pre-Write

Before writing code to a file:

- [ ] Have I read this file?
- [ ] Does this change touch a safety-sensitive area? (secrets, validation gates, vector IDs, RAG, financial rows)
- [ ] Does this change affect embeddings or RAG? → Vector baseline + RAG stability verification required post-change
- [ ] Does the diff exceed ~300 lines? → Stop and confirm scope with user
- [ ] Am I creating a new file when editing an existing one would suffice? → Prefer edit

---

## Post-Write

After any code change:

```bash
# Always run lint
python -m ruff check autodev financial-engine_v2/backend scripts

# Run affected tests
pytest financial-engine_v2/backend/tests  # or specific test file
pytest autodev/tests
pytest scripts
```

For changes affecting the financial pipeline or embeddings:
```bash
bash scripts/run_canonical_dataset_checks.sh
python scripts/check_canonical_regression.py \
  --baseline reports/baselines/canonical_eval_baseline_latest.json \
  --news-report reports/news_eval_report.json \
  --company-report reports/company_eval_report_v2.json \
  --reference-report reports/eval_queries_report.json
```

---

## Pre-Merge Checklist

- [ ] Plan written before implementation
- [ ] Invariants reviewed
- [ ] Tests executed and passing
- [ ] No architecture drift introduced
- [ ] Vector baseline verified (if embeddings changed)
- [ ] RAG stability verified (if retrieval changed)
- [ ] Lessons logged (if bug fix)

Source: `docs/architecture/11_engineering_discipline.md`

---

## Minimal Change Discipline

- Change only what the task requires.
- Do not clean up unrelated code ("while I'm here" changes).
- Do not add docstrings, comments, or type annotations to code you didn't change.
- Do not add error handling for scenarios that cannot happen.
- Do not create helpers or abstractions for one-time operations.
- Do not add feature flags for features that should just be changed.
- Three similar lines of code is better than a premature abstraction.

---

## Change Control Rules

From `docs/ops/README.md`:
- Keep ops pack additive to existing runtime docs.
- Do not replace `financial-engine_v2/docker-compose.yml` in Phase 1.
- Update acceptance criteria before changing model tiers or queue concurrency.
- Fix broken markdown links before merge (`bash scripts/check_markdown_hygiene.sh`).

---

## Large Diff Policy

If a change would touch more than ~300 lines or more than 5 files:
1. Stop.
2. Confirm scope with user.
3. Prefer splitting into smaller, independently-reviewable changes.
4. One subsystem per PR.

---

## Cloud Workflow Rules

From `docs/cloud_workflow.md`:
1. Local is source of truth — push before Cloud handoff.
2. Give Cloud a narrow task (one subsystem per PR).
3. Require deterministic start/validation before and after.
4. Bring Cloud changes back through isolated review (`prepare_cloud_worktree.sh`).
5. Never merge Cloud work directly into a dirty local checkout.

---

## Style and Consistency

- Python linter: `ruff` (configured in `ruff.toml`)
  - Target: Python 3.10
  - Ignores: legacy multi-import, some unused imports, one-liners
- Tests: `pytest` (configured in `pytest.ini`)
  - pythonpath: `.`, `financial-engine_v2/backend`, `scripts`
- Do not bypass hooks with `--no-verify`.
- Do not amend published commits; create new commits instead.
