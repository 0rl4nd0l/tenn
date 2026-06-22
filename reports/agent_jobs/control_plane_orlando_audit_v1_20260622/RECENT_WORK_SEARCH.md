# Recent Work Search

## GitHub PR Evidence

Relevant current PR states from safe reads:

| PR | State | Finding |
| --- | --- | --- |
| #382 | MERGED | Runtime Functionality Proof requirement merged into canonical Tenn branch at `154888ecca6220ab598efcd140a2c2b62fca3da7`. |
| #380 | MERGED | Handoff orchestration and zoom-out modes merged at `4d62fec4e855b313ae89136e947510c627b9bcde`. |
| #378 | MERGED | Skill surface trim merged; old report still says ready/pending. |
| #377 | MERGED | Ledger append flow merged. |
| #375 | MERGED | Ledger runtime handoff replay merged; superseded PR #367. |
| #373 | MERGED | OpenCode bridge safety fixes merged; old report still says validating. |
| #370 | MERGED | Initial OpenCode worker bridge merged. |
| #367 | CLOSED | Superseded by PR #375. |
| #345 | MERGED | Stop-hook terminal loop fix merged. |

No open core `control-plane/*` PRs were found in the broad control-plane search. A broader search surfaced open issue/PR work outside this audit's core control-plane surface, including Prompt Lab reporting work.

## Report Evidence

| Report | Current classification | Reason |
| --- | --- | --- |
| `reports/agent_jobs/dev_flow_ground_up_reset_audit_v1_20260616/README.md` | STALE snapshot | Useful historical audit, but worktree counts and states are old. |
| `reports/agent_jobs/dev_flow_skills_bloat_audit_v1_20260617/SKILL_RECOMMENDATIONS.md` | HISTORICAL | Explains skill surface consolidation. |
| `reports/agent_jobs/dev_flow_skill_surface_trim_v1_20260618/README.md` | STALE | Says `READY_FOR_PR`; live PR #378 is merged. |
| `reports/agent_jobs/control_plane_handoff_orchestration_modes_v1_20260619/README.md` | STALE | Says merge gate required; live PR #380 is merged. |
| `reports/agent_jobs/control_plane_runtime_functionality_proof_v1_20260622/VALIDATION.md` | CURRENT SNAPSHOT | Canonical through PR #382; old ledger data-missing note no longer matches current ledger validation. |
| `reports/agent_jobs/dev_flow_opencode_worker_bridge_v1_20260617/README.md` | CURRENT WITH RISK | Bridge exists; each worker still requires validation. |
| `reports/agent_jobs/dev_flow_opencode_worker_bridge_safety_fix_v1_20260618/README.md` | STALE | Says validating; live PR #373 is merged. |
| `reports/agent_jobs/dev_flow_ledger_runtime_handoff_v1_20260617/README.md` | SUPERSEDED | PR #367 was superseded by #375. |
| `reports/agent_jobs/dev_flow_ledger_runtime_handoff_replay_v1_20260618/README.md` | CURRENT SNAPSHOT | Captures replay lineage for PR #375. |
| `reports/agent_jobs/goal_monitor_stop_loop_audit_v1_20260613/*` | CURRENT CONCEPTUAL | Accurately distinguishes repo Stop hook from host-only goal monitor, but predates current PRs. |

## Issue Evidence

Issue #78 remains open as a control-plane/docs backlog anchor for agent markdown refresh. No GitHub issue writes were performed.

## Search Conclusion

The current control-plane implementation after PR #382 is real but uneven:

- skills and scripts are present;
- task-card/registry/ledger/report contracts exist;
- OpenCode bridge is probeable and tested;
- `/goal monitor` is not repo-backed;
- stale report and ledger states need cleanup;
- some automatic behavior depends on host Codex hook loading.
