# Cleanup Decision

Decision: `DEFER_CLEANUP_ACTIVE_JOB`

The root-owned cache directories are generated and ignored, but the shared checkout is currently owned by active registry job `extraction_real_gold_eval_current_head_runtime_v1_20260601` in lane Financial Truth.

Because this issue's remediation would mutate generated directories in that same checkout, this job preserves the inventory and stops before cleanup.

## Safe Cleanup Contract

The follow-up cleanup task should:

1. Re-check `python3 scripts/agent_job_registry.py list-active --read-only`.
2. Proceed only when no active job owns the same shared checkout, or when the owning job explicitly authorizes the generated-state cleanup.
3. Remove or owner-repair only the inventoried ignored `__pycache__` directories.
4. Avoid `git clean -X` and broad recursive cleanup.
5. Prove tracked files are unchanged with `git status --short --untracked-files=all`.
6. Run focused compile/write validation:

```bash
python3 -m compileall financial-engine_v2/backend/app financial-engine_v2/cockpit financial-engine_v2/shared
```

## Closeout Status

#140 should remain open until cleanup or owner repair has actually run and focused compile/write validation passes.
