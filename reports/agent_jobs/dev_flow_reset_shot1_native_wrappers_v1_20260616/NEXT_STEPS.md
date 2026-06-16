# Next Steps

## After This PR

1. Review and merge the instruction-only wrappers if CI and review are clean.
2. Run a report-only trial `/issue` against issue #78 or #291.
3. Use the trial to decide whether Shot 2 should add a report-only Git guard
   helper script.
4. Keep cleanup, worker spawning automation, and hook behavior changes in
   separate approved workstreams.

## Next Recommended Prompt

```text
/goal Trial the new Tenn /issue wrapper report-only on one existing control-plane issue. Do not mutate GitHub or product/runtime/extraction files. Produce ISSUE.md, MILESTONES.md, a context pack, and NEXT_GOAL.md, then evaluate whether Shot 2 needs a report-only git-guard helper.
```
