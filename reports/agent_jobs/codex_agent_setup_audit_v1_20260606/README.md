# Codex Agent Setup Audit V1

Audit date: 2026-06-06
Primary Tenn audit target: `/home/l4nd0/tenn-nvme-clean-baseline-reconstruct-v1`
Secondary comparison target: `/home/l4nd0/tenn-fast-dev-storage-v1`
Original shell cwd: `/mnt/tenn-nvme2/tenn/offloaded-home/l4nd0/greyhound_racing_collector`

## Executive Verdict

What is working:

- Tenn has a strong operating model in practice: task cards, exact allowed-file thinking, reports as evidence, merge parking, issue labels/milestones, and shared active-job records.
- The current GitHub backlog already tracks the broad agent/Codex documentation refresh (#78), Codex-native auto-progress workflow (#291), and the main financial extraction blockers (#73, #96, #97, #286).
- The current Financial Truth active registry entry is visible in the shared registry and points to a bounded post-PR297 extraction failure-taxonomy job.

What is hurting us:

- There is no single current repo-backed Codex setup. The newer NVMe baseline has a short stale `AGENTS.md`, an empty repo-local `.codex/`, untracked agent scripts, and untracked `.gemini/skills` symlinks into host-level skills. The older fast-dev tree has the richer `.codex` setup, but it is on an older branch and embeds stale skill inventory in `AGENTS.md`.
- `AGENTS.md` is split between two bad shapes: too short and stale in the newer baseline, too long and partly stale in the older tree. It is not yet acting as a stable repo constitution.
- Useful Tenn skills live under `/home/l4nd0/.codex/skills`, not in the repo. Fresh worktrees/clones cannot discover the real workflow set from repo state alone.
- The registry script lacks the expected `list-active --read-only` flag. The implemented `list-active` path acquires a filesystem lock and writes transient `.lock/owner.json`, so I did not run it in this read-only audit.
- Reports are ignored by `.gitignore` and `.git/info/exclude`, so evidence bundles are easy to create locally but easy to leave unpreserved unless force-added or explicitly committed.

Highest-leverage next move:

> Use issue #78 as the approval vehicle to rewrite `AGENTS.md` into a short stable constitution and create a repo-backed Tenn skill skeleton. Do not start with #291 automation. First remove instruction drift, define the skill boundaries, and add/readjust the registry read-only guard.

## Current Inventory

| Surface | Current evidence | Classification | Impact |
| --- | --- | --- | --- |
| Original cwd | `greyhound_racing_collector`, branch `feature/dog-odds-snapshot-readiness`, origin `0rl4nd0l/greyhound-racing-collector`; required `find` probe returned no `AGENTS.md` or `.codex` | Not Tenn target | The shell started in the wrong repo for this Tenn audit. No greyhound files were modified. |
| Tenn NVMe baseline | `/home/l4nd0/tenn-nvme-clean-baseline-reconstruct-v1`, branch `tmp/sloppy-fix-demo`, HEAD `dfa313aaa6c1b34696f4bf9a8bd430636e5792ce` | Current audited target, dirty | Most current reports/task cards are here, but this is not clean and is not the remote extraction canonical. |
| Tenn fast-dev | `/home/l4nd0/tenn-fast-dev-storage-v1`, branch `migration/clean-runtime-baseline-20260517`, HEAD `6c6748fe87e57b9d3b6c890e8551e7c288bc51b0` | Older setup reference | Contains tracked `.codex/config.toml`, hooks, and one repo skill, but is stale relative to current extraction work. |
| Remote branches | `origin/main` = `c2609429...`; `origin/migration/clean-runtime-baseline-reconstruct-v1` = `3749270c...`; `origin/tmp/sloppy-fix-demo` = `1938535a...` | Requires explicit target choice | Current local branch and remote extraction canonical differ. AGENTS should say to verify branch/remote before acting. |
| `AGENTS.md` in NVMe baseline | 53 lines; Cursor Cloud `/workspace` paths; no task-card/registry/GitHub issue constitution | Stale/too thin | Not sufficient for current Codex operation. |
| `AGENTS.md` in fast-dev | 348 lines; includes skill inventory, task-card model, live repo rules, stale sprint snapshot | Useful but too broad/stale | Good source material, but should be split into AGENTS constitution plus skills. |
| Repo `.codex` in NVMe baseline | `.codex/` exists but `find .codex -maxdepth 4 -type f` returned no files | Missing | No repo-local Codex hooks or skills in current baseline. |
| Repo `.codex` in fast-dev | `.codex/config.toml`, `.codex/hooks.json`, `.codex/skills/cockpit-flag-orchestrator/SKILL.md` tracked | Useful but stale/narrow | Reusable pattern, but not enough for Financial Truth work. |
| `.gemini/skills` in NVMe baseline | Untracked symlinks into `/home/l4nd0/.codex/skills` and some Claude skills; one points to absent repo-local cockpit skill | Non-portable/partly broken | Useful locally, but should not be treated as repo-backed truth. |
| Host Codex skills | 36 host-level skills under `/home/l4nd0/.codex/skills` plus plugin cache skills | Useful but not repo-backed | Current session uses them, but new agents need a repo pointer or mirror. |
| Agent scripts in NVMe baseline | `scripts/agent_job_contract.py`, `scripts/agent_job_registry.py`, `scripts/agent_job_hook.py` exist but are untracked | Useful but preservation gap | Hooks/task-card workflow depends on untracked scripts. |
| Agent scripts in fast-dev | Same scripts are tracked | Useful older source | Candidate source for clean integration into current target. |
| Shared registry | `/mnt/sdb2/home/l4nd0/tenn/.git/tenn-agent-registry/active/extraction_post_pr297_failure_taxonomy_v1_20260605.json` | Useful | Active Financial Truth work is visible via shared Git common dir. |
| Repo-local `.tenn` | `.tenn/active_agent_task.stale_query_orchestration...` and `.tenn/agent_jobs/TENN-ARCH-001-inference-engine.md` | Stale/fragmented | Old local markers can confuse task selection. |
| Task cards | 22 visible files under `docs/agent_tasks` in NVMe baseline | Useful, fragmented | Current task cards are strong but too verbose and sometimes broad-globbed. |
| Reports | Many `reports/agent_jobs/*` directories; reports ignored by git | Useful, preservation-sensitive | Evidence exists locally, but must be explicitly preserved. |
| GitHub issues | `gh` authenticated. Open issue #78 covers agent docs refresh; #291 covers auto-progress; #96/#97/#286 cover financial extraction blockers | Useful | Do not create broad duplicate issues. |
| GitHub workflows | Only `.github/workflows/sloppy-scan.yml` and `sloppy-fix.yml` in current checkout | Partial | No repo-native task-card/skill/report validation CI. |

## AGENTS.md Audit

| Finding | Evidence | Classification | Recommendation |
| --- | --- | --- | --- |
| NVMe AGENTS hard-codes Cursor Cloud `/workspace` paths | `AGENTS.md:3-24` in NVMe baseline | Stale local fact | Replace with a "runtime paths are environment-specific; verify cwd/venv" section. Keep `/workspace` only under a Cloud-specific note. |
| NVMe AGENTS omits current Tenn control-plane rules | NVMe `AGENTS.md` has no GitHub issue hierarchy, task-card contract, registry, merge parking, reports, handoff, or subagent policy | Missing constitution | Rewrite from fast-dev constitutional sections and current evidence. |
| NVMe AGENTS says no lint tooling is configured | `AGENTS.md:51-52`; current open #281 asks for lint/type gates | Possibly stale | Replace with "verify current CI/tooling; do not assume lint/type gates." |
| NVMe AGENTS points to test ignores and "12 additional failures" | `AGENTS.md:28-40` | Stale/time-sensitive | Move old test status out of AGENTS. Tests should be per-task validation, not static constitution. |
| Fast-dev AGENTS embeds full skill inventory | `AGENTS.md:7-50` in fast-dev | Token waste/stale | AGENTS should point to `.codex/skills/` and `~/.codex/skills`; it should not list every skill and absolute path. |
| Fast-dev skill paths are stale/non-portable | `/home/l4nd0/tenn/.codex/skills/...` in `AGENTS.md:10-29`; actual audited paths are `/home/l4nd0/tenn-nvme-clean-baseline-reconstruct-v1`, `/home/l4nd0/tenn-fast-dev-storage-v1`, and `/home/l4nd0/.codex/skills` | Stale facts | Remove absolute skill path inventory. |
| Fast-dev AGENTS has strong truth/contract rules | `AGENTS.md:59-75` | Useful constitution | Keep short version: current-turn evidence, SYSTEM_CONTRACT, no fallbacks that violate invariants. |
| Fast-dev AGENTS has strong lane/mode/collision model | `AGENTS.md:91-218` | Useful constitution | Keep compressed. Include Repo Hygiene mismatch note or use accepted primary lanes plus `supporting_lanes`. |
| Fast-dev AGENTS has useful task-card contract | `AGENTS.md:259-271` | Useful but needs update | Keep, but update registry command to a real safe read-only path once implemented. |
| Fast-dev AGENTS has stale sprint snapshot | `AGENTS.md:273-287`, dated 2026-04-14 | Stale/token waste | Remove from AGENTS. Put current status in reports/issues/handoffs only. |
| Fast-dev AGENTS has milestone/flag protocols | `AGENTS.md:309-338` | Useful but workflow-specific | Move detailed flagged-report resolution to a skill. Keep only "follow issue/report closeout protocol." |
| Graphify section forces broad context work | `AGENTS.md:340-348` | Token-risk | Move to an optional `tenn-codebase-map` or graphify skill; do not require for every architecture/codebase answer. |
| Missing canonical path/branch guidance | Current audit found greyhound cwd, NVMe baseline, fast-dev, remote canonical mismatch | Missing | Add "Tenn target selection" section: verify cwd, origin, branch, HEAD, and whether remote extraction canonical is required. |
| Missing financial extraction priority pointer | Active registry and issues #73/#96/#97/#286 show Financial Truth priority | Missing | Add a brief "Current priority is issue-backed and must be verified from GitHub/registry, not hard-coded." |
| Missing reporting expectations for unverified facts | Reports use `DATA_MISSING`, but NVMe AGENTS does not | Missing | Add "mark unverified/current-state gaps as DATA_MISSING; include commands/evidence." |

## Skills Audit

Repo-local and host-level skill inventory:

| Skill/surface | Location | Classification | Notes |
| --- | --- | --- | --- |
| `.codex/skills` in NVMe baseline | `/home/l4nd0/tenn-nvme-clean-baseline-reconstruct-v1/.codex` | Missing | Directory exists but contains no skill files. |
| `cockpit-flag-orchestrator` | Fast-dev `.codex/skills/cockpit-flag-orchestrator/SKILL.md` | Useful but stale/narrow | Good pattern for flag triage, but not in current baseline and not Financial Truth-focused. |
| `.gemini/skills` symlink farm | NVMe `.gemini/skills/*` | Too broad/non-portable | Symlinks point to host Codex/Claude skills; useful locally, but untracked and not repo truth. |
| `architecture-check` | Host `/home/l4nd0/.codex/skills` | Useful | Keep host-level; use before RAG/vector/backend invariant changes. |
| `architecture-cleanup-steward` | Host | Useful but broad | Use for architecture cleanup only; not default for extraction work. |
| `caveman` | Host | Useful for token reduction | Keep host-level; do not repo-mirror unless desired. |
| `code-fixer` | Host | Useful | Good downstream implementer after review/function-quality. |
| `code-reviewer` | Host | Useful | Keep for post-fix review; not a task orchestrator. |
| `diagnose` | Host | Useful | Good for bugs/performance regressions. |
| `function-quality` | Host | High-value | Best current deep-analysis tool for metric extraction. Should be wrapped by a Tenn Financial Truth skill. |
| `grill-me`, `grill-with-docs` | Host | Useful but optional | Planning/design tools; keep out of AGENTS. |
| `handoff` | Host | Useful | Formalizes `/save`-style current-state compression. |
| `hatch-pet` | Host | Irrelevant to Tenn | Do not mention in Tenn AGENTS. |
| `improve-codebase-architecture` | Host | Useful but broad | Use for architecture improvement, not financial truth mutation by default. |
| `intelligence-pack-review` | Host | Useful narrow | Keep for weekly reports only. |
| `news-pipeline-remaining-fixes` | Host | Useful but narrow | Current issue #123/news work only; not priority for metric extraction. |
| `pdf` | Host | Useful | Important for PDF review, but extraction truth still needs source-bound gates. |
| `performance-check` | Host | Useful read-only | Keep for runtime/GPU/retrieval checks. |
| `playwright`, `playwright-interactive` | Host | Useful | UI/runtime debugging; not core Financial Truth. |
| `prompt-crafter`, `prompt-structure-reference` | Host | Useful | Good for subagent prompt generation and issue-to-card work. |
| `prototype` | Host | Useful optional | Avoid on production extraction surfaces unless explicitly requested. |
| `rag-stability-eval` | Host | Useful read-only | For retrieval drift only. |
| `tdd` | Host | Useful | Use for strict bounded implementation slices. |
| `tenn-issue-closeout` | Host | High-value | Keep; should be one of the canonical Tenn skills. |
| `tenn-issue-finder` | Host | High-value | Used for this audit's GitHub duplicate/read-only workflow. |
| `tenn-issue-resolution-reviewer` | Host | High-value | Needed before closing high-risk Tenn issues. |
| `to-issues`, `to-prd`, `triage` | Host | Useful but generic | Use after issue-system setup, not as default Tenn executor. |
| `vast-gpu-operator` | Host | Useful but high-risk | Runtime/GPU only; must require spending/destruction confirmation. |
| `zoom-out` | Host | Useful/token-efficient | Good for codebase map questions. |
| System skills (`imagegen`, `openai-docs`, `plugin-creator`, `skill-creator`, `skill-installer`) | Host `.system` | Useful platform tools | Do not mirror into Tenn unless building skills/plugins. |
| Plugin cache skills | `/home/l4nd0/.codex/plugins/cache/...` | Mostly irrelevant to Tenn control plane | Investment/public-equity plugins are useful only for explicit investing workflows, not repo safety. |

## Missing Skills Recommendations

Top 5 Tenn skills to add next:

| Proposed skill | Responsibility | Why now |
| --- | --- | --- |
| `tenn-financial-metric-extraction` | Route issue-backed Financial Truth work (#73/#96/#97/#286), require current registry/GitHub checks, classify report-local vs safe extension, forbid DB/Qdrant/news/memory/backfill unless explicitly approved, and require source-bound validation. | Financial metric extraction is the highest-priority blocker. This should be the first new skill. |
| `tenn-task-card-registry-safety` | Validate/create task cards, check dirty state, resolve registry root, inspect active jobs read-only, enforce exact allowlists, recommend clean sibling worktrees, and report collision risk. | Current task-card/registry knowledge is scattered across AGENTS, scripts, memory, and reports. |
| `tenn-merge-parking-review` | Read merge parking registry and latest report bundles, classify parked branches, identify latest decision surface, forbid merge/cherry-pick/cleanup unless approved. | Merge parking is useful but fragmented and currently requires too much context rereading. |
| `tenn-agent-docs-refresh` | Rewrite AGENTS.md, sync repo-local `.codex/skills`, update issue/workflow docs, and validate no product/runtime changes. | Directly maps to GitHub issue #78 and this audit's main next move. |
| `tenn-auto-progress` | Phase-gated workflow from issue/milestone intent to candidate ranking, context pack, draft task card, one executor, verifier, report, optional GitHub writes. | Already tracked by #291, but should start only after the constitution/skills base is corrected. |

Useful later:

- `tenn-report-closeout-handoff`: standardize `/save` handoffs, status.json, validation.json, README closeout, and memory-save recommendations without mutating memory.
- `tenn-cockpit-answer-readiness`: focus on DATA_MISSING and backend-backed usefulness for Cockpit, separate from financial truth.
- `tenn-runtime-readiness`: local service/GPU/port/env checks with no production mutation.

## Orchestration And Task Workflow Audit

| Surface | Evidence | Verdict | Recommendation |
| --- | --- | --- | --- |
| Agent registry | Active shared record exists for `extraction_post_pr297_failure_taxonomy_v1_20260605`; active job lane `Financial Truth`, worktree `/home/l4nd0/tenn-post-pr297-failure-taxonomy-v1-20260605` | Working but read-only gap | Add `list-active --read-only` that does not lock/write. |
| Registry root resolution | Both Tenn worktrees resolve Git common dir to `/mnt/sdb2/home/l4nd0/tenn/.git` | Good | AGENTS should state registry root is resolved, not hard-coded. |
| Repo-local `.tenn` | Contains stale active-agent marker and old inference-engine card | Fragmented | Treat repo-local `.tenn` as fallback/stale unless shared registry says otherwise. |
| Task-card convention | Recent task cards contain frontmatter, allowed files, hard stops, validation | Strong | Keep, but move repeated hard-stop boilerplate into skills/prompts. |
| Task-card validator | Accepted primary lanes exclude `Repo Hygiene`; supporting lanes are not validated | Restrictive/mismatch | Either add `Repo Hygiene` as valid primary lane or document it as supporting-only. |
| Allowed-file handling | Reports show broad `**` patterns sometimes conflict with exact `check-diff` behavior | Fragmented | Prefer exact report files for closeout or update validator to support globs consistently. |
| Reports | Good evidence bundles under `reports/agent_jobs`; ignored by git | Useful but preservation-risky | Require final report to say whether artifacts are ignored/untracked/staged/committed. |
| Merge parking | Registry exists with statuses and parked entries | Useful | Add "latest decision surface" pointer and skill wrapper. |
| `/goal`/auto-progress | Issue #291 exists with detailed design | Too broad for immediate implementation | Split into Phase 1 read-only planner after #78/skills cleanup. |
| `/save`/handoff | Host `handoff` skill exists; no repo-local handoff convention found in current baseline | Missing | Add a short handoff convention to AGENTS and a skill/report template later. |
| Subagents | Fast-dev AGENTS has policy; cockpit skill has subagent prompts | Useful | Keep parent reconciliation requirement; forbid parallel writers by default. |
| Hooks | Fast-dev `.codex/hooks.json` checks graphify before Bash and task-card hook on Stop | Useful but stale location | Restore repo-local hooks in current baseline only after scripts are tracked and read-only registry gap is fixed. |
| Automation hooks | Sloppy workflows use `gpt-5.2-codex` and auto comment on PRs | Powerful but separate | AGENTS should not rely on Sloppy for local task-card safety. |

## GitHub Issue Workflow

Existing relevant open issues:

| Issue | Coverage | Audit decision |
| --- | --- | --- |
| #78 `[Repo Hygiene] Refresh agent markdown and Codex repo documentation` | Directly covers AGENTS/Codex docs/task-card/registry/merge-parking docs refresh | Use this for the next AGENTS + skills documentation slice. Do not create a duplicate broad docs issue. |
| #291 `[Control Plane] Build Codex-native auto-progress skill workflow` | Covers auto-progress, issue-to-card, Codex executor, verifier, token control | Keep open. Do not implement before #78 and registry read-only safety. |
| #96 `[Query Orchestration] Most PDF-path documents lack terminal extraction` | Main runtime coverage blocker for metric extraction | Treat as current Financial Truth priority surface with live re-checks. |
| #97 `[Evaluation] Generate extracted-payload scorecard for confirmed metric coverage` | Evaluation/scorecard blocker for confirmed metrics | Use for scoring skill workflows. |
| #286 `[Financial Truth] Add field-level provenance and accounting number parsing to extraction outputs` | Field-level provenance/accounting number parsing | Relevant to metric-extraction skill. |
| #73 `[Financial Truth] ASX evidence-bound extraction redesign parent tracker` | Parent tracker | Link child work; do not collapse all extraction work into a new meta-issue. |
| #234 `[Repo Hygiene] Classify stale extraction contract parity diff-check dirt` | One stale report-artifact dirt issue | Adjacent but not a registry/read-only fix. |

Duplicated or stale issue risk:

- #78 and #291 overlap in "Codex workflow" language, but are not duplicates. #78 is docs/control-plane alignment; #291 is automation.
- Creating a new broad "Codex agent setup" issue would duplicate #78. Prefer a comment/update to #78 with this report path, or use #78 as the implementation tracker.
- Financial extraction is already covered by #73/#96/#97/#286. New extraction issues should be narrow root-cause slices only.

Missing issue recommendations:

### Issue A

Title: `[Control Plane] Add read-only registry inspection and align task-card hook commands`

Body:

```markdown
## Finding
Current Tenn workflow expects safe read-only registry inspection, but `scripts/agent_job_registry.py list-active --read-only` is not implemented. The existing `list-active` path acquires `RegistryLock`, creates the registry root if needed, and writes transient `.lock/owner.json`.

## Evidence
- `python3 scripts/agent_job_registry.py list-active --read-only` exits with `unrecognized arguments: --read-only`.
- `list_active_jobs()` enters `RegistryLock(location.root)`.
- Current task cards and reports still ask for final `list-active`.

## Acceptance
- Add `list-active --read-only` that does not create lock dirs, owner files, registry roots, or status files.
- Update hook/task-card docs to use the real safe command.
- Add focused tests proving mtimes/contents do not change.
- No product/runtime/data changes.
```

Suggested labels: `lane:repo-hygiene`, `lane:evaluation`, `mode:safe-extension`, `priority:p1`, `risk:medium`, `state:ready`, `type:control-plane`, `type:validation-gap`; milestone `M0 - Control Plane Hardening`.

### Issue B

Title: `[Repo Hygiene] Version repo-local Tenn Codex skills and remove stale AGENTS skill inventory`

Recommendation: do not create yet if #78 will own it. Use as a subtask/comment under #78 unless the implementation needs its own tracker.

Body:

```markdown
Repo-local Codex skills are missing from the current NVMe baseline, while host-level Tenn skills exist under `/home/l4nd0/.codex/skills` and the older fast-dev tree contains one tracked `.codex/skills/cockpit-flag-orchestrator`. AGENTS in the older tree embeds stale absolute skill paths.

Acceptance: repo-local skill skeleton or documented host-skill policy exists, AGENTS points to discovery rather than listing every skill, and at least `tenn-financial-metric-extraction`, `tenn-task-card-registry-safety`, and `tenn-merge-parking-review` have clear responsibilities.
```

### Issue C

Title: `[Financial Truth] Create Codex skill for bounded financial metric extraction work`

Recommendation: create only if #73/#96/#97/#286 owners agree this belongs as control-plane work rather than extraction implementation.

Body:

```markdown
Create `tenn-financial-metric-extraction` as a repeatable workflow skill for issue-backed financial metric extraction tasks. It must preserve canonical truth boundaries, require current GitHub/registry/task-card checks, support report-local audit first, and allow only narrow source-bound safe extensions with tests.
```

## Proposed Lean AGENTS.md Outline

```markdown
# AGENTS.md - Tenn Repo Constitution

## Purpose
- Tenn is an ASX financial data, extraction, provenance, query, and Cockpit system.
- Current facts must be verified from repo/GitHub/runtime evidence in the current turn.

## Target Selection
- First verify cwd, origin, branch, HEAD, worktree, dirty state, and whether the user intended the Tenn repo.
- Preferred local roots may exist, but are not truth until verified.

## Source Of Truth Hierarchy
1. GitHub issues/PRs/milestones for backlog and coordination.
2. Task cards for execution contract.
3. Shared registry for active job/collision state.
4. Reports for evidence and closeout.
5. Merge parking for parked branch visibility.
6. Memory/handoffs as search hints, never current proof.

## Safety Boundaries
- No production DB/Qdrant/news/memory/backfill/extraction/runtime/gold-label/prompt/canonical financial truth mutation without explicit approval and a task card.
- Financial truth remains source-bound, deterministic, auditable, and provenance-linked.
- Mark missing current evidence as DATA_MISSING.

## Work Modes And Lanes
- Lanes: Financial Truth, Evaluation, Provenance, Query Orchestration, Memory, Reporting, Repo Hygiene, Runtime.
- Modes: audit_only, safe_extension, blocked.
- High collision risk stops implementation.

## Task-Card Contract
- Validate task card before edits.
- Inspect registry safely.
- Claim only when implementation is approved and overlap is acceptable.
- Keep changes inside allowed_files.
- Release or report blocked status.

## Skills
- AGENTS is the constitution, not the workflow cookbook.
- Repeatable workflows live under `.codex/skills` or documented host skills.
- Use the smallest applicable skill.

## Validation And Reporting
- Report files changed, files inspected, validation commands/results, unsafe actions avoided, unresolved blockers, and next safe step.
- Reports under `reports/agent_jobs/<job_id>/` are evidence; GitHub issues remain live backlog.

## Subagents And Handoffs
- Parallel read-only scouts are allowed when bounded.
- One writer at a time.
- Parent reconciles findings.
- `/save`/handoff captures current state but does not replace issue/task/report truth.
```

## Proposed `.codex/skills` Structure

```text
.codex/
  config.toml
  hooks.json
  skills/
    tenn-financial-metric-extraction/
      SKILL.md
    tenn-task-card-registry-safety/
      SKILL.md
    tenn-merge-parking-review/
      SKILL.md
    tenn-agent-docs-refresh/
      SKILL.md
    tenn-auto-progress/
      SKILL.md
    cockpit-flag-orchestrator/
      SKILL.md
      references/subagent-prompts.md
```

Keep host-level general skills (`function-quality`, `code-reviewer`, `tdd`, `pdf`, `playwright`, etc.) outside repo unless Tenn needs a stable wrapper.

## Do Now / Do Next / Later

Do now:

1. Approve a bounded issue #78 implementation task: rewrite AGENTS and create/update repo-local Tenn skill skeletons.
2. Add or approve a separate task for `list-active --read-only`; do not rely on the current lock-writing path for read-only audits.
3. Create `tenn-financial-metric-extraction` first, because it reduces repeated prompt boilerplate for #96/#97/#286.

Do next:

1. Normalize task-card lane vocabulary, especially `Repo Hygiene`.
2. Add a latest-decision pointer to merge parking so agents do not re-read stale report chains.
3. Decide whether `.gemini/skills` symlinks should be ignored, removed, or documented as local-only.

Later:

1. Add changed-file-scoped CI for task cards, report schemas, and hooks.
2. Implement #291 Phase 1 read-only planner only after the constitution and skill wrappers exist.
3. Build a compact `/save` handoff/report schema and issue-link policy.

## Suggested Codex Prompts For Next 3 Tasks

### Prompt 1 - Rewrite AGENTS and create skills skeleton

```text
Use issue #78 as the tracker. Create or validate a task card first for a docs/control-plane-only safe extension. Rewrite Tenn `AGENTS.md` into a lean stable constitution using `reports/agent_jobs/codex_agent_setup_audit_v1_20260606/README.md` as the evidence source. Do not modify product/backend/frontend/runtime/data files. Create repo-local skill skeletons for `tenn-financial-metric-extraction`, `tenn-task-card-registry-safety`, and `tenn-merge-parking-review` with responsibilities only, no implementation scripts yet. Preserve unrelated dirt. Validate markdown, task card, git diff check, and final status.
```

### Prompt 2 - Add read-only registry inspection

```text
Implement exactly one bounded Repo Hygiene safe extension: add `python3 scripts/agent_job_registry.py list-active --read-only` that performs active-job inspection without creating lock dirs, owner files, registry roots, status files, or timestamp changes. Start with failing tests proving the current command is missing and that read-only mode does not mutate filesystem state. Do not touch product/runtime/data surfaces. Update hook/task-card docs only where necessary. Validate with focused tests, task-card validate/check-diff, git diff --check, and final status.
```

### Prompt 3 - Financial metric extraction skill

```text
Create `tenn-financial-metric-extraction` as a Codex skill for issue-backed Financial Truth work. Use live GitHub issues #73, #96, #97, and #286 plus the active registry entry as current evidence, but do not mutate extraction code. The skill must enforce audit-first, source-bound validation, no DB/Qdrant/news/memory/backfill/runtime/gold-label/prompt mutation without explicit approval, and one narrow safe extension at a time. Include exact report output expectations and validation gates for post-PR297/count16 work. Validate the skill markdown and produce a report-only closeout.
```

## Command Log

Read-only/safe commands run:

- `git status --short --untracked-files=all` in original greyhound cwd and both Tenn targets.
- `find . -maxdepth 3 -iname 'AGENTS.md' -o -path './.codex/*'` in original cwd and Tenn targets.
- `git branch --show-current`, `git rev-parse HEAD`, `git remote -v`, `git log -1 --oneline --decorate`.
- `rg --files ...` to list docs, reports, registry, task, and agent files.
- `ls -ld` on known Tenn roots and orchestration directories.
- `nl -ba AGENTS.md`, `.codex/config.toml`, `.codex/hooks.json`, task cards, reports, registry files, and scripts.
- `find .codex`, `.gemini`, `.tenn`, `docs/agent_tasks`, `docs/agent_registry`, `reports/agent_jobs`.
- `python3 scripts/agent_job_registry.py list-active --read-only` was attempted and failed with `unrecognized arguments: --read-only`.
- `python3 scripts/agent_job_contract.py --help` and `python3 scripts/agent_job_registry.py --help`.
- `git rev-parse --git-common-dir` and direct read-only `find /mnt/sdb2/home/l4nd0/tenn/.git/tenn-agent-registry`.
- `gh auth status`, `gh repo view 0rl4nd0l/tenn`, `gh issue list`, `gh issue view`, `gh pr list`.
- `git ls-remote --heads origin main migration/clean-runtime-baseline-reconstruct-v1 tmp/sloppy-fix-demo`.
- `git ls-files` for AGENTS, agent scripts, and `.codex` files.

Unsafe or mutating actions avoided:

- No DB mutation.
- No Qdrant, news, memory, backfill, extraction, source-PDF, prompt, gold-label, runtime/model/GPU/service config mutation.
- No dependency install.
- No GitHub issue/PR creation, edit, close, comment, label, milestone, push, merge, rebase, reset, stash, clean, prune, or checkout.
- Did not run non-read-only `agent_job_registry.py list-active` because code inspection showed it takes `RegistryLock` and writes transient `.lock/owner.json`.

## Evidence References

- NVMe `AGENTS.md:3-53`: short Cursor Cloud-oriented instructions with `/workspace` paths and no current task-card/registry issue constitution.
- Fast-dev `AGENTS.md:7-50`: embedded skill inventory with absolute stale paths.
- Fast-dev `AGENTS.md:59-75`: useful current-evidence and system-contract rules.
- Fast-dev `AGENTS.md:91-271`: useful live repo, lane, collision, subagent, and task-card model.
- Fast-dev `AGENTS.md:273-287`: stale sprint snapshot.
- Fast-dev `.codex/hooks.json:1-26`: hook shape.
- Fast-dev `.codex/skills/cockpit-flag-orchestrator/SKILL.md:1-120`: existing repo-local skill pattern.
- NVMe `scripts/agent_job_registry.py`: `list-active` help lacks `--read-only`; `list_active_jobs()` uses `RegistryLock`.
- Shared registry active record: `/mnt/sdb2/home/l4nd0/tenn/.git/tenn-agent-registry/active/extraction_post_pr297_failure_taxonomy_v1_20260605.json`.
- Merge parking registry: `docs/agent_registry/merge_parking/REGISTRY.md:1-53`.
- Recent extraction preflight report: `reports/agent_jobs/extraction_preflight_consolidation_before_next_work_v1_20260604/README.md`.
- GitHub issues inspected: #78, #291, #96, #97, #286, #234.

## Unverified / DATA_MISSING

- I did not fetch or mutate refs. Remote state is from `git ls-remote` and `gh`, not from a local `git fetch`.
- I did not run live extraction, tests, canaries, backfills, or services.
- I did not validate whether host-level skills are the latest intended versions beyond reading their current local `SKILL.md` headers.
- I did not inspect every plugin-cache skill body; plugin cache was inventoried only to classify it as mostly irrelevant to Tenn repo control.
- I did not inspect GitHub Projects fields/schema.
- I did not decide whether the report should be force-added; `reports/` is ignored in this repo and this artifact is currently a local report file unless separately preserved.

## Final Audit Status

Files created:

- `reports/agent_jobs/codex_agent_setup_audit_v1_20260606/README.md`

Files intentionally not modified:

- `AGENTS.md`
- `.codex/*`
- `.gemini/*`
- `scripts/agent_job_contract.py`
- `scripts/agent_job_registry.py`
- `scripts/agent_job_hook.py`
- GitHub issues/PRs
- Product/runtime/data/extraction surfaces

Recommended next prompt:

Use Prompt 1 above: rewrite AGENTS.md and create/update repo-local skills under issue #78, with a task card and docs/control-plane-only allowlist.

---

# Amendment - External Workflow Patterns And `.agents/skills`

Amendment date: 2026-06-06
Scope: report-only extension requested after external Codex workflow research. No repo operating files were changed.

## Amendment Executive Delta

The main audit verdict still holds, but the skill-location recommendation changes:

- Official current Codex documentation says repo skills are discovered from `.agents/skills`, not `.codex/skills`.
- Tenn current NVMe baseline has empty `.agents/` and empty `.codex/` directories.
- The older fast-dev tree has a tracked `.codex/skills/cockpit-flag-orchestrator`, plus `AGENTS.md` text that explicitly describes `.codex/skills` as Codex-only. That is local legacy/custom evidence, but not enough to keep new repo skills there.
- Recommendation: migrate repo-authored Tenn skills to `.agents/skills`; keep `.codex/config.toml` and `.codex/hooks.json` for Codex configuration and hooks; treat existing `.codex/skills` references as stale or legacy unless a compatibility note is deliberately added.

Highest-leverage next move after this amendment:

1. Use issue #78 to rewrite `AGENTS.md` as a short constitution.
2. Create a repo-local `.agents/skills` skeleton for repeatable Tenn workflows.
3. Leave `.codex/skills` only as a migration source or compatibility alias if an explicit Codex-version reason is documented.

## `.agents/skills` And `.codex/skills` Evidence

| Surface | Evidence | Verdict | Recommendation |
| --- | --- | --- | --- |
| Official Codex skills location | Fetched OpenAI Codex manual says repo skills are scanned from `.agents/skills` up to repo root, and user skills from `$HOME/.agents/skills`. | `.agents/skills` is the current official convention. | Use `.agents/skills` for new Tenn repo skills. |
| Official Codex config/hooks location | OpenAI Codex manual says MCP/config is in `config.toml`; project-scoped config may be `.codex/config.toml`; hooks are discovered next to active config layers as `hooks.json` or inline `[hooks]`. | `.codex` remains correct for project Codex config/hooks. | Keep `.codex/config.toml` and `.codex/hooks.json` when hooks are restored. |
| NVMe baseline `.agents` | `ls -la .agents` shows an empty directory. | Missing skills. | Create `.agents/skills` only when implementing issue #78. |
| NVMe baseline `.codex` | `ls -la .codex` shows an empty directory. | No current repo-local Codex config/skills. | Do not infer an active `.codex/skills` convention from this checkout. |
| Fast-dev `.agents` | Empty directory. | Missing official repo skills. | Migration target. |
| Fast-dev `.codex/skills` | Contains tracked `cockpit-flag-orchestrator/SKILL.md` and `agents/openai.yaml`. | Useful legacy/custom pattern. | Move or mirror to `.agents/skills/cockpit-flag-orchestrator` during docs refresh if still wanted. |
| Fast-dev `AGENTS.md` skill block | Lines 4-50 say skills use `.codex/skills` and list absolute `/home/l4nd0/tenn/.codex/skills/...` paths. | Stale/custom/token-wasteful. | Remove inventory from AGENTS; replace with "Codex discovers repo skills from `.agents/skills`; use `/skills` or explicit `$skill`." |

## Context Discipline Audit

| Check | Current evidence | Risk | Recommendation |
| --- | --- | --- | --- |
| Does NVMe `AGENTS.md` tell Codex to avoid huge command output? | No. It includes full commands and broad test commands, but no output discipline. | High token waste, especially from `git status`, test logs, Playwright logs, JSON, and one-line minified output. | Add exact "Command Output Discipline" wording below. |
| Does fast-dev `AGENTS.md` tell Codex to keep context small? | Yes, but only inside the embedded skill instructions: "summarize long sections" and "avoid deep reference-chasing". | Good idea, wrong location and too weak for shell output. | Keep as general policy, but add byte-cap rules to AGENTS constitution. |
| Does current workflow rely on line caps? | GitHub workflow uses `sed -n '1,220p'`; local habits often use `head`. | Line caps alone are unsafe because one very long line can still flood context. | Use byte caps for unknown/noisy output: `head -c 4000` or `tail -c 4000`. |
| Are there exceptions for full reads? | Not clearly stated in AGENTS. | Over-compression can hide the actual instruction or policy. | Full-read instruction/policy/skill files and intentionally selected small source sections when relevant. |
| Are scoped searches preferred before full reads? | Developer/user preference and some fast-dev guidance imply it, but NVMe AGENTS does not. | Agents may read large files before locating relevant sections. | Add "search first, then read targeted sections" rule. |

### Exact `Command Output Discipline` Wording

Recommended AGENTS section:

```markdown
## Command Output Discipline

Before running commands that may emit large output, scope the command or cap bytes.

- Prefer scoped searches before full file reads: `rg`, `rg --files`, `git diff --name-only`, `git status --short`, and targeted `sed -n` ranges.
- For unknown or potentially noisy output, cap bytes, not just lines:
  - `COMMAND 2>&1 | head -c 4000`
  - `COMMAND 2>&1 | tail -c 4000`
- Line caps alone are not safe because one giant line can still flood context.
- Use `tail -c 4000` for failing commands when the useful error is likely at the end.
- Use `head -c 4000` for inventory commands where the beginning is enough.
- Do not pipe away exit status when the exit code matters; if using a pipe, capture and report the real command status or rerun a focused command.
- Read these fully when relevant: instruction files, policy files, skill files, task cards, small config files, and intentionally selected small source sections.
- For tests/builds that produce long logs, prefer repo summarizer targets or write full raw output to a report artifact and show only the short summary plus artifact path.
```

Implementation note: plain shell pipelines can mask non-zero exit status unless `set -o pipefail` or explicit status capture is used. A future summarizer helper should preserve command exit codes.

## Validation Discipline Audit

| Check | Current evidence | Risk | Recommendation |
| --- | --- | --- | --- |
| NVMe AGENTS validation | Hard-codes broad `pytest scripts/ -v` with stale ignore notes and "12 additional failures". | Stale validation claims and over-testing by default. | Remove static test state from AGENTS. |
| Fast-dev master prompt validation | `docs/prompts/CODEX_MASTER_PROMPT.md` requires ruff plus three test suites after any change. | Over-testing for docs/report-only changes, token waste, and false blockers. | Replace with risk-based matrix. |
| Repo summarizer targets | `financial-engine_v2/Makefile` has `logs`, `context-check`, `hooks-install`, but no focused test-output summarizer target. Some scripts store tails internally. | Agents will stream noisy test output directly. | Add future `make test-summary` or `scripts/run_with_summary.py`; do not implement in this audit. |
| Current extraction tests | Many focused `scripts/test_*` files exist for financial metric parsing. | Good targeted gate surface. | Financial extraction skill should select the cheapest relevant focused tests first. |

### Exact `Risk-Based Validation` Wording

Recommended AGENTS section:

```markdown
## Risk-Based Validation

Choose validation by blast radius and explain the choice.

- Tiny docs, comments, report-only artifacts, or prompt text changes: no runtime validation required. Say why validation was skipped.
- Narrow code change in one module: run the cheapest relevant focused test, typecheck, lint, or import check that exercises the changed behavior.
- Shared extraction, parser, runtime, RAG, registry, hook, or orchestration change: run a targeted regression or smoke test tied to the affected contract.
- Broad behavior change, cross-layer change, or release/merge candidate: run the broader suite only when justified by the changed surface.
- Do not run broad tests just to look diligent. Prefer evidence that is relevant, reproducible, and cheap enough to repeat.
- For noisy test/build commands, use a summarizer target or write full raw output to a report artifact, then show the exit code, short summary, and raw-output path.
- Never claim validation passed unless the command, exit status, and relevant output are recorded.
```

Recommended future helper, not implemented here:

```text
scripts/run_with_summary.py --out reports/agent_jobs/<job>/raw/<name>.log -- COMMAND ...
```

Required behavior:

- Preserve the original command exit code.
- Print only the first/last bounded bytes plus a concise failure summary.
- Record the raw log path in the report.
- Never summarize away failure details for Playwright/E2E/debug-heavy runs unless the raw log path is available.

## RTK / Command-Output Compression

Local investigation:

- `command -v rtk` produced no path.
- `rtk --version` produced no output.
- `rg` found no Tenn repo references to `RTK`, `Rust Token Killer`, `rtk-ai`, `rtk init`, `head -c 4000`, or `tail -c 4000` outside the current prompt stored in Codex history, which was intentionally excluded from the repo scan.

External evidence considered:

- OpenAI Codex issue #19001 proposes RTK-like shell-output filtering for Codex because verbose commands can fill context quickly. The issue is open, so this is not built-in accepted behavior.
- RTK's own README describes command rewriting, compact `git`/file/log commands, and a tee mode that can save raw output on failures.

Recommendation:

- Do not make RTK a default Tenn dependency yet.
- Trial RTK only as an explicit, reversible operator experiment after issue #78's AGENTS/skills cleanup, not as a hidden hook in the repo.
- Prefer manual byte caps first because they are transparent, dependency-free, and easy to audit.

Trial plan, if approved later:

1. Create a control-plane-only issue: `[Control Plane] Trial RTK-style output compression for low-signal Codex shell output`.
2. Do not install globally during the trial. Use an explicit command strategy or isolated environment.
3. Trial on low-risk commands only: `git status`, `git log`, dependency listings, directory inventories, success logs, and long low-signal output.
4. Do not use compression by default for failing Playwright, E2E, extraction-debug, parser-debug, traceback-heavy, or report-diff commands.
5. Preserve non-zero exit codes.
6. When summaries are used, write full raw output to `reports/agent_jobs/<job>/raw/` and include that path in the final report.
7. Success criteria: lower context footprint without hiding the exact failing assertion, traceback, changed file, or unsafe mutation signal.

Escape hatch:

```markdown
Use raw output when debugging failures, Playwright/E2E runs, parser traces, extraction score regressions, hook failures, and any command where the exact line matters. Compact only success logs and low-signal inventories unless a raw log artifact is saved.
```

## Blocked, Waiting, And Approval States

Current audit:

- Fast-dev AGENTS has `BLOCKED MODE` and `DATA_MISSING`, but it does not define a visible waiting protocol.
- NVMe AGENTS has no waiting/approval protocol.
- This is a real Tenn gap because many safe outcomes require explicit approval gates: DB mutation, backfill, GitHub mutation, merge/rebase, live service, secret/env var, GPU/runtime, and product decisions.

### Exact `Blocked, Waiting, and Approval States` Wording

Recommended AGENTS section:

````markdown
## Blocked, Waiting, and Approval States

Never silently continue low-value work when the next meaningful step requires an approval, flag, permission, credential, service, or decision.

Declare `WAITING_ON_USER` when work cannot safely continue because it needs:

- user approval
- a permission flag
- a sandbox, network, filesystem, or runtime capability
- a secret or environment variable
- a live service
- database mutation or backfill approval
- GitHub authentication or write permission
- merge, rebase, branch, or parking decision
- product, design, or architecture decision

When waiting, emit this block in the current update or final report:

```text
WAITING_ON_USER
Needed: <exact approval/flag/input>
Why: <what this unlocks>
Current safe state: <what has been done>
Options: <A/B/C>
Recommended: <one option>
```

If approval is optional, continue only with clearly labeled safe read-only work.
If approval is required for the next meaningful step, stop and ask directly instead of pretending progress is possible.
If the task is a `/goal`, write the same wait state to the goal report or handoff file before stopping.
````

## `/goal` Runner Protocol

Recommended operating model:

```markdown
## Goal Runner Protocol

For `/goal` work, start by recording:

- Objective
- Constraints
- Unsafe actions
- Required approvals
- Done criteria
- Initial state

Maintain one visible state:

- `RUNNING`: executing safe planned work.
- `WAITING_ON_USER`: user input or approval is required for the next meaningful step.
- `BLOCKED_EXTERNAL`: blocked by external service, auth, runtime, filesystem, or unavailable data.
- `VALIDATING`: implementation is complete and checks are running.
- `DONE_WITH_RISK`: useful work completed, but explicit residual risk or unverified evidence remains.
- `DONE`: done criteria met and validation/reporting are complete.

For each goal, create or update `reports/agent_jobs/<goal_id>/README.md` with:

- current state
- files touched
- commands run
- approvals needed
- blocked items
- validation status
- next recommended prompt
```

Recommendation: make this a skill, not only AGENTS text. AGENTS should define the state machine; `.agents/skills/tenn-goal-report` should provide templates and steps.

## AGENTS.md Vs Skills Split

Target split after the correction:

| Belongs in AGENTS.md | Belongs in `.agents/skills` |
| --- | --- |
| Repo map and current target-selection checks | Extraction investigation |
| Safety boundaries and forbidden mutation classes | Extraction fix and validate |
| Command-output discipline | GitHub issue triage |
| Blocked/waiting/approval protocol | PR review closeout |
| Risk-based validation policy | Merge parking review |
| Done criteria and evidence rules | Runtime smoke |
| Status/reporting format | Goal report generation |
| Skill discovery policy | Stop-slop report writing |

Conclusion:

- AGENTS should be a stable constitution under roughly 150-220 lines.
- Skills should hold repeatable job procedures and long checklists.
- GitHub issues should own backlog/coordination.
- Reports should own evidence/closeout.
- Registry should own multi-agent safety/parking.
- Subagents should be opt-in and summary-returning.
- `/save` or goal handoffs should compress current state, not duplicate all history.

## Subagent Discipline

Current audit:

- Fast-dev AGENTS already says subagents may be used only for parallel inspection, documentation gathering, or evidence collection, and parent agent owns reconciliation.
- Official Codex docs support subagents for parallel exploration, tests, triage, and summarization, while warning that parallel write-heavy work can create conflicts and coordination overhead.

Recommendation:

- Use subagents only when they save main-thread context, increase independent verification, or allow genuinely parallel specialist review.
- Do not use subagents for trivial tasks, one-file edits, or tasks where a single focused search is cheaper.
- For Tenn, default subagents should be read-only unless the parent explicitly assigns a bounded write and owns the final diff.

Proposed Tenn subagents:

| Subagent | Purpose | Write access |
| --- | --- | --- |
| `extraction-auditor` | Inspect financial extraction evidence, scorecards, PDFs, parser behavior, and issue links. | Read-only by default. |
| `validation-runner` | Run focused validation commands and summarize exit status plus raw-log paths. | Read-only except report artifacts. |
| `issue-triager` | Inspect GitHub issue/PR duplicates, labels, milestones, and existing trackers. | Read-only unless user approves GitHub mutation. |
| `diff-reviewer` | Review current diff for unsafe broad mutation, missing tests, or contract violations. | Read-only. |
| `report-writer` | Assemble evidence into `reports/agent_jobs/...` from parent-approved facts. | Report writes only. |

Each subagent must report:

```text
Files inspected:
Findings:
Uncertainty / DATA_MISSING:
Commands run:
Files changed, if any:
Recommended next action:
```

## External Workflow Patterns Considered

Sources used:

- OpenAI Codex manual fetched locally to `/tmp/openai-docs-cache/codex-manual.md`.
- Official OpenAI Codex docs pages: `https://developers.openai.com/codex/skills`, `https://developers.openai.com/codex/guides/agents-md`, `https://developers.openai.com/codex/mcp`, `https://developers.openai.com/codex/concepts/subagents`, `https://developers.openai.com/codex/hooks`.
- OpenAI Codex GitHub issue #19001: `https://github.com/openai/codex/issues/19001`.
- RTK repository: `https://github.com/rtk-ai/rtk`.
- Reddit workflow discussions:
  - `https://www.reddit.com/r/codex/comments/1t6iulo/i_cut_codex_token_usage_50_with_one_agentsmd_rule/`
  - `https://www.reddit.com/r/codex/comments/1r9y1uq/how_do_you_guys_handle_done_but_not_really_done/`
  - `https://www.reddit.com/r/codex/comments/1suke52/how_could_people_exhaust_all_tokens_with_the_pro/`

Synthesis:

| Pattern | Source signal | Tenn conclusion |
| --- | --- | --- |
| Byte-cap command output | External Codex workflow advice and RTK/Codex issue both focus on raw shell output as a major token sink. | Add byte caps to AGENTS. Use `head -c 4000` / `tail -c 4000` before installing tools. |
| Keep AGENTS short | Official docs say AGENTS has a 32 KiB default project-doc cap; skills use progressive disclosure and the initial skills list is budgeted. Reddit users also report shorter AGENTS plus scoped task packs working better. | Move skill inventory and long procedures out of AGENTS. |
| Skills for repeatable workflows | Official docs: skills package instructions, resources, optional scripts, and progressive disclosure. | Put Tenn procedures in `.agents/skills`, especially financial metric extraction. |
| MCP for live external systems | Official docs: MCP connects Codex to external tools/context and uses `config.toml`. | Keep GitHub/web/local shell as current tools; add MCP only when it removes manual evidence collection, not by default. |
| Subagents for context isolation | Official docs: subagents help keep noisy exploration/test/log work off the main thread, but write-heavy parallelism has conflict risk. | Use read-only subagents for audit, validation, issue triage, diff review, and report writing. |
| RTK-style compression | RTK and Codex issue claim large token savings on common commands; RTK can save raw failed output. | Trial cautiously, explicitly, and only after AGENTS/skills cleanup. Do not hide failing extraction details. |
| Done criteria and verifier loops | Reddit discussions emphasize acceptance criteria, invariants, reviewer agents, and one milestone at a time. | Tenn already has task cards and reports; formalize `/goal` states and independent diff/validation review. |
| Avoid over-plugin/token-burn setups | Reddit advice warns against too much plugin/subagent/process overhead. | Keep first implementation to AGENTS + 3-5 repo skills. Defer automation #291 until the base is stable. |

## Recommended Lean AGENTS.md Sections - Revised

Recommended AGENTS shape after this amendment:

```markdown
# AGENTS.md - Tenn Repo Constitution

## Repo Map And Target Selection
## Current Evidence And Truthfulness
## Safety Boundaries
## Financial Truth Priority
## Multi-Agent Live Repo Control
## Task Cards, Registry, And Merge Parking
## Command Output Discipline
## Blocked, Waiting, And Approval States
## Risk-Based Validation
## Done Criteria And Reporting
## Skill And Subagent Policy
## GitHub Issue Workflow
```

Keep AGENTS stable and short. It should not list every skill, stale sprint state, old test failures, or absolute host paths.

## Proposed `.agents/skills` Tree

Recommended initial repo tree:

```text
.agents/
  skills/
    tenn-financial-metric-extraction/
      SKILL.md
      references/
        financial_truth_boundaries.md
        validation_matrix.md
    tenn-task-card-registry-safety/
      SKILL.md
      references/
        task_card_schema.md
        registry_readonly_checks.md
    tenn-merge-parking-review/
      SKILL.md
      references/
        merge_parking_statuses.md
    tenn-github-issue-triage/
      SKILL.md
      references/
        issue_labels_and_milestones.md
    tenn-goal-report/
      SKILL.md
      templates/
        README.md
        status.json
    tenn-runtime-smoke/
      SKILL.md
      references/
        smoke_matrix.md
    tenn-pr-review-closeout/
      SKILL.md
      references/
        closeout_decision_tree.md
    tenn-stop-slop-report/
      SKILL.md
      templates/
        report.md
```

First three to implement:

1. `tenn-financial-metric-extraction`
2. `tenn-task-card-registry-safety`
3. `tenn-goal-report`

Migration note:

- Move `cockpit-flag-orchestrator` from fast-dev `.codex/skills` to `.agents/skills/cockpit-flag-orchestrator` only if it is still operationally wanted.
- Keep any `agents/openai.yaml` metadata with the skill if still valid.
- Do not mirror all host skills into Tenn. Repo skills should be Tenn-specific wrappers, not a dump of personal/global tools.
- Do not preserve stale absolute paths from fast-dev `AGENTS.md`.

## GitHub Issue Recommendation Delta

Do not create a new broad audit issue. Use #78.

Add these recommendations to #78 or convert into narrow child issues only if needed:

### Issue D

Title: `[Repo Hygiene] Migrate repo Codex skills to official .agents/skills layout`

Body:

```markdown
## Finding
Current OpenAI Codex documentation says repository skills are discovered from `.agents/skills`. Tenn's current NVMe baseline has empty `.agents/` and `.codex/`, while an older fast-dev tree has tracked `.codex/skills/cockpit-flag-orchestrator` and AGENTS text listing stale `.codex/skills` paths.

## Acceptance
- New repo skills live under `.agents/skills`.
- AGENTS.md no longer embeds a full skill inventory or stale absolute skill paths.
- `.codex/config.toml` / `.codex/hooks.json` remain reserved for config/hooks.
- Any retained `.codex/skills` compatibility path is explicitly documented as legacy/custom with a migration plan.
- No product/runtime/data changes.
```

### Issue E

Title: `[Control Plane] Add command-output discipline and risk-based validation policy to AGENTS`

Body:

```markdown
## Finding
Current AGENTS guidance does not cap noisy command output by bytes and older prompts encourage broad validation after any change.

## Acceptance
- AGENTS includes byte-cap guidance using `head -c 4000` / `tail -c 4000`.
- AGENTS warns that line caps alone are unsafe.
- AGENTS includes exceptions for instruction, policy, skill, task-card, and targeted small source reads.
- AGENTS includes risk-based validation categories.
- Future summarizer helper is documented but not required in this slice.
- No product/runtime/data changes.
```

## Next Implementation Prompt - Revised

```text
Use GitHub issue #78 as the tracker. Create or validate a task card first for a Repo Hygiene documentation/control-plane slice only. Do not touch product/runtime/data/extraction code.

Rewrite AGENTS.md into a lean Tenn repo constitution using the amended audit at reports/agent_jobs/codex_agent_setup_audit_v1_20260606/README.md. Include exact sections for Command Output Discipline, Blocked/Waiting/Approval States, Risk-Based Validation, done criteria, task-card/registry safety, GitHub issue workflow, and skill/subagent policy.

Create repo-local `.agents/skills` skeletons for:
- tenn-financial-metric-extraction
- tenn-task-card-registry-safety
- tenn-goal-report

Do not migrate all host skills. Do not create GitHub issues. Do not modify `.codex/hooks.json` unless the chosen Tenn target already tracks it and the task card allowlist explicitly permits it. Validate with markdown review, `git diff --check`, task-card validation/check-diff if the scripts are available, and final git status. Report any ignored/untracked artifacts explicitly.
```

## Amendment Command Log

Additional read-only/safe commands run for this amendment:

- `find . -maxdepth 4 \( -path './.codex*' -o -path './.agents*' -o -iname 'AGENTS.md' \) -print | sort` in NVMe and fast-dev Tenn targets.
- `find .agents .codex -maxdepth 4 ...` and `ls -la .agents .codex` in both Tenn targets.
- `rg -n "RTK|rtk|head -c|tail -c|output|validation|waiting|approval|blocked|subagent|\.agents/skills|\.codex/skills" ...` in Tenn targets.
- `command -v rtk` and `rtk --version`; no local RTK binary/version was found.
- `node /home/l4nd0/.codex/skills/.system/openai-docs/scripts/fetch-codex-manual.mjs` to fetch current official Codex manual.
- Targeted `nl -ba /tmp/openai-docs-cache/codex-manual.md` reads for skills, AGENTS.md, MCP, subagents, and hooks.
- Targeted reads of NVMe `AGENTS.md`, fast-dev `AGENTS.md`, fast-dev `.codex/hooks.json`, `.codex/config.toml`, `.codex/skills/cockpit-flag-orchestrator/SKILL.md`, `docs/prompts/CODEX_MASTER_PROMPT.md`, `financial-engine_v2/Makefile`, and `.github/workflows/sloppy-*.yml`.
- Web reads for official/OpenAI/RTK/Reddit external-source synthesis; no GitHub or Reddit mutation.

## Amendment Evidence References

- Official Codex manual, skills: `/tmp/openai-docs-cache/codex-manual.md:6530-6542`, `6576-6594`.
- Official Codex manual, AGENTS.md: `/tmp/openai-docs-cache/codex-manual.md:6768-6778`.
- Official Codex manual, MCP/config: `/tmp/openai-docs-cache/codex-manual.md:7111-7128`.
- Official Codex manual, subagents: `/tmp/openai-docs-cache/codex-manual.md:9715-9746`.
- Official Codex manual, hooks: `/tmp/openai-docs-cache/codex-manual.md:10205-10252`.
- NVMe `AGENTS.md:3-53`: no output discipline, wait-state protocol, or risk-based validation.
- Fast-dev `AGENTS.md:4-50`: stale `.codex/skills` inventory and host paths.
- Fast-dev `AGENTS.md:211-217`: useful but narrow subagent policy.
- Fast-dev `AGENTS.md:237-257`: useful final report and DATA_MISSING rules.
- Fast-dev `docs/prompts/CODEX_MASTER_PROMPT.md`: broad validation after any change.
- Fast-dev `.codex/hooks.json:1-26`: tracked legacy hook shape.
- Fast-dev `.codex/skills/cockpit-flag-orchestrator/SKILL.md:1-70`: legacy repo-local skill pattern.
- NVMe `financial-engine_v2/Makefile:1-24`: no test/build summarizer target.
- OpenAI Codex issue #19001: RTK-style output compression is proposed but open, not proven built-in.
- RTK README: compact command wrappers and raw-output tee behavior.
- Reddit r/codex discussions: informal signals for byte caps, acceptance criteria, reviewer loops, scoped task packs, and token-burn caution. These are not authoritative.

## Amendment Final Status

Files modified:

- `reports/agent_jobs/codex_agent_setup_audit_v1_20260606/README.md`

Files intentionally not modified:

- `AGENTS.md`
- `.agents/*`
- `.codex/*`
- GitHub issues/PRs
- Product/runtime/data/extraction surfaces

Unsafe actions avoided:

- No RTK install.
- No dependency install.
- No DB, Qdrant, news, memory, backfill, runtime, service, source-PDF, prompt, or gold-label mutation.
- No GitHub write action.
- No AGENTS.md or skill implementation yet.
