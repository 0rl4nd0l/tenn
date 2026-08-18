# Preservation Recommendation

## Verdict

Preserve the prior issue #105 audit result, but do not commit, merge, park in
the registry, or update GitHub from this task. The current task card only allows
this preservation-review report bundle, and registry check-overlap already
proved there is dirty work outside this task allowlist.

## Recommended Handling

- Leave the prior report local until dirty work clears or a separate approved
  preservation task explicitly allows the prior task card and prior report
  directory.
- Commit only the prior task card/report under a separate approved task that
  allows:
  - `docs/agent_tasks/pr39_lint_and_test_failure_cluster_split_v1_20260526.md`
  - `reports/agent_jobs/pr39_lint_and_test_failure_cluster_split_v1_20260526/**`
  - any preservation-review report files the operator wants included.
- Create merge-parking entries only under a separate approved task if the
  parking registry paths are included in that task's `allowed_files`.
- Update issue #105 only by explicit separate approval. A safe comment would
  summarize: 13 clusters, PR #39 remains draft/not merge-ready, child tasks
  required, and prior run `26439822448` remains the current failing CI evidence.
- Mark GitHub mutation and production data access as not performed for this
  review.

## Parkability

The prior audit is parkable as evidence because required artifacts exist, JSON
parses, GitHub PR/check state still matches, and the failure clusters are
actionable. It is not merge approval and not root-cause remediation.

The parking recommendation should remain report-local until a task card
explicitly permits either:

- committing the prior task card/report bundle; or
- writing merge parking entries such as `docs/agent_registry/merge_parking/**`.

## Exact Next Prompt Recommendation

Use this as the next operator prompt if preservation is desired:

```text
/goal Preserve the completed PR #39 issue #105 CI failure-cluster audit artifacts in git without touching unrelated dirty work. Create or validate a new Repo Hygiene task card that explicitly allows docs/agent_tasks/pr39_lint_and_test_failure_cluster_split_v1_20260526.md, reports/agent_jobs/pr39_lint_and_test_failure_cluster_split_v1_20260526/**, and the preservation-review report bundle. Do not edit product/runtime/test/dependency/workflow files, do not clean/stash/reset unrelated work, do not mutate GitHub, and do not implement any PR39 cluster fixes. Validate task-card, registry overlap, JSON parse, git diff --check, task-card check-diff, and release any claim before closeout.
```

Use this as the next remediation prompt after preservation is accepted:

```text
/goal Create a child task card for PR #39 cluster C01, [CI] Reconcile backend sqlite3/uuid4/vector invariant failures for PR #39. Start audit-first, preserve architecture invariants, do not touch production DB/Qdrant/news/memory, canonical financial truth, parser routing, extraction prompts, gold labels, runtime/model/GPU/service config, or unrelated dirty work. Validate with focused architecture invariant tests and architecture-check before proposing any remediation.
```

## DATA_MISSING

- Whether the operator wants a separate commit-preservation task or only
  report-local parking.
- Whether merge parking registry paths should be used; this task did not allow
  those paths.
- Which external job owned the transient Cockpit/news dirty files observed by
  registry check-overlap.
