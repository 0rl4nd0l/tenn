# Dirty worktree classification

## Method

For each worktree with working-tree deltas, collected from:
- `git -C <path> status --short --untracked-files=all`
- `git -C <path> diff --name-status`
- `git -C <path> diff --stat`
- `git -C <path> log --oneline --decorate -10`

## Dirty worktrees (non-exhaustive by design: all reported at collection time)

| Path | Branch | Head | Tracked mods | Untracked | Lane (inferred) | Likely value | Risk if lost | Preserve / review | Blocks cleanup |
|---|---|---|---|---|---|---|---|---|---|
| `/mnt/sdb2/home/l4nd0/tenn` | `preserve/dirty-work-20260430T065748Z` | `13fd78de` | `docs/agent_tasks/cockpit_runtime_worktree_visibility_audit_20260507.md` | 6 task-card files | Reporting / Evaluation | Contains current audit/task decision points and new task card | Medium: lose provenance notes | Preserve then archive by policy | No |
| `/mnt/sdb2/home/l4nd0/tenn-ab-isolation-20260421` | `audit/ab-isolation-real-gold-cap-timeout` | `ae86d6` | none | `scripts/run_docling_determinism_audit.py` | Evaluation | Experimental one-off extraction harness | Low (single file), but could represent unique test setup | Preserve if work intended; else archive | No |
| `/mnt/sdb2/home/l4nd0/tenn-agent-mcp-auth-design-before-chatgpt-20260507` | `audit/tenn-agent-mcp-auth-design-before-chatgpt-20260507` | `e387e9c` | none | `docs/agent_tasks/tenn_agent_mcp_auth_design_before_chatgpt_20260507.md` | Query Orchestration | Agent-control prep + task planning card | Low/Medium | Preserve as task artifact | No |
| `/mnt/sdb2/home/l4nd0/tenn-agent-mcp-connector-dry-run-plan-20260507` | `audit/tenn-agent-mcp-connector-dry-run-plan-20260507` | `dd903ca` | none | `docs/agent_tasks/tenn_agent_mcp_connector_dry_run_plan_20260507.md` | Query Orchestration | Agent-control dry-run planning card | Low/Medium | Preserve as task artifact | No |
| `/mnt/sdb2/home/l4nd0/tenn-agent-mcp-http-adapter-v0-20260507` | `safe/tenn-agent-mcp-http-adapter-v0-20260507` | `e387e9c` | none | `docs/agent_tasks/tenn_agent_mcp_http_local_smoke_readiness_20260507.md` | Query Orchestration | Agent-control readiness check card | Low/Medium | Preserve as task artifact | No |
| `/mnt/sdb2/home/l4nd0/tenn-agent-mcp-oauth-local-smoke-20260507` | `audit/tenn-agent-mcp-oauth-local-smoke-20260507` | `dd903ca` | none | `docs/agent_tasks/tenn_agent_mcp_oauth_local_smoke_20260507.md` | Query Orchestration | Agent-control smoke prep card | Low/Medium | Preserve as task artifact | No |
| `/mnt/sdb2/home/l4nd0/tenn-cockpit-home-bff-audit-v1` | `audit/cockpit-home-backend-bff-contract-v1` | `4f9736c` | none | `docs/agent_tasks/cockpit_home_backend_bff_contract_audit_v1.md` | Reporting | Contract audit note for cockpit home BFF | Low/Medium | Preserve as lane artifact | No |
| `/mnt/sdb2/home/l4nd0/tenn-cockpit-home-live-wiring-v1` | `safe/cockpit-home-live-wiring-v1` | `bae8b8f` | `cockpit-ui/next-env.d.ts` | none | Reporting | Small `cockpit-ui` type shim tweak | Medium: could affect local wiring diff continuity | Preserve pending branch review | No |
| `/mnt/sdb2/home/l4nd0/tenn-eval-instrumentation-20260421` | `audit/eval-instrumentation-bounded-20260421` | `49a5d34` | backend extraction + eval scripts/tests (8 files) | none | Evaluation | Active extraction evaluation instrumentation and test adjustments | **High**: high-value evaluation/finance-workflow surface | Preserve and review before merge/archive | **Yes** if cleanup is gated by audit confidence |
| `/mnt/sdb2/home/l4nd0/tenn-shared-router-strict-eval-gate-v1` | `codex/shared-router-strict-eval-acceptance-gate-v1` | `570ea57` | none | `docs/agent_tasks/shared_router_canonical_core_rerun_v1.md` | Evaluation | Active shared-router rerun artifact | Low/Medium: tied to active registry job | Preserve because active job overlap | **Yes** (active registry overlap) |
| `/mnt/sdb2/home/l4nd0/tenn-source-label-998d68e-integrate` | `codex/source-label-998d68e-clean-integration-20260506` | `4f9736c` | none | `docs/agent_tasks/source_label_998d68e_clean_integration_20260506.md` | Reporting | Source-label integration follow-up card | Low/Medium | Preserve as reporting artifact | No |

## Notes

- `git` merge-ancestor checks show most dirty-worktree branch tips are not in `preserve/dirty-work-20260430T065748Z` except:
  - `/mnt/sdb2/home/l4nd0/tenn-cockpit-home-bff-audit-v1`
  - `/mnt/sdb2/home/l4nd0/tenn-eval-instrumentation-20260421`
  - `/mnt/sdb2/home/l4nd0/tenn-cockpit-home-live-integration-final`
  - `/mnt/sdb2/home/l4nd0/tenn-source-label-998d68e-integrate`
  - `/mnt/sdb2/home/l4nd0/tenn-main-reconcile`
  - `/mnt/sdb2/home/l4nd0/tenn-main-reconcile` etc

