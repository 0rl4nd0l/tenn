# Repository Audit

Full repository audit: environment preflight, branch inventory, structure analysis, and evidence-based completeness review.

## Read First

- `CLAUDE.md`
- `docs/claude/README.md`
- `docs/entrypoints.md`
- `README.md`
- This command file's workflow and output requirements

## Workflow

1. **Environment preflight** (mandatory):
   - Verify repo root, active branch, git status.
   - Check canonical entrypoint: `financial-engine_v2/scripts/run_local_backend.sh` exists.
   - Check validation scripts: `scripts/start_system.sh`, `scripts/validate_system.sh`.
   - If preflight blocked → stop functional validation, return `DATA_MISSING`.

2. **Inventory**:
   - Repository structure (top-level dirs, key files).
   - Branches: compare against default branch; identify duplicate, stale, or half-integrated work.
   - Docs: check `docs/claude/`, `docs/architecture/`, `docs/ops/` for completeness.
   - Rules and agents: `docs/architecture/SYSTEM_CONTRACT.md`, `.claude/commands/`, `.claude/agents/`, `.codex/skills/`.
   - Validation commands and feature surfaces.

3. **Run smallest real checks** the environment supports; record exact commands and outcomes.

4. **Separate claims**:
   - **CONFIRMED** — directly verified from source.
   - **INFERRED** — derived from pattern or context.
   - **UNVERIFIED** — not checked; flagged as such.

## Constraints

- Do not claim functional validation results unless preflight is `READY`.
- Do not modify functional code while auditing unless user explicitly requests it.
- Do not fabricate command outputs or system state.

## Output

Return an evidence-rich markdown report with a JSON structure covering preflight status, files inspected, validation commands, confirmed findings, inferred findings, unverified findings, and next actions.
