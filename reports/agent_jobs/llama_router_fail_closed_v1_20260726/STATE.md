# State

- target_identity: `/home/l4nd0/tenn`, `deploy/canonical-runtime-v1`,
  `4248d947a22203d8c415060884337e06a3ffa262`, clean, guard `pass`
- alleged_old_fix: PR #520 / `a144a69f` fixed resolved-binary execution; it did
  not address router capability fallback
- canonical_lineage: PR #520 is an ancestor of current canonical
- current_repro: preserved `/tmp/llama-server-8001.log` shows router requested,
  capability declared unsupported, single-model GPT-OSS selected, then nine
  structured-output parser 500s
- scope_comparison: different failure class from PR #520
- permanent_gate: added in `scripts/test_llama_server_launchers.py`; red before
  repair and green after repair
- runtime_functionality_proof: `DATA_MISSING` by explicit no-activation boundary
- classification: `NEW_FAILURE_CLASS` with contributing `TEST_GAP`
- next_action: local commit; runtime activation remains separately authorized
- duplicate_work_classification: `NO_MATCHING_ACTIVE_WORK_FOUND`
- ledger_status: `PASS`; live append skipped because V2 is not required and
  shared ledger mutation is not authorized
- docs_impact: `DOCS_UPDATED`
- docs_checked: `docs/setup/environment.md` and repository router references
- docs_changed: `docs/setup/environment.md`
- docs_followup: none
- docs_reason: router capability failure is now an explicit fatal safety
  boundary and single-model mode must be selected explicitly
- task_tier: medium
- recommended_model: standard coding model
- actual_model: Codex
- why_this_model: two-file launcher correctness repair with targeted regression
- worker_model_allowed: false
- worker_decision_limit: none
- escalation_needed: false
