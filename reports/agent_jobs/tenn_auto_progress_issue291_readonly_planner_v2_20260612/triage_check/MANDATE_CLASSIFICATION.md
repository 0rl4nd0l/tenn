# Mandate Classification

| Mandate | Applies | Boundary |
| --- | --- | --- |
| `REPORT_AUTONOMY` | read-only scans, rankings, context packs, draft packets | stop before source/product/runtime/data/GitHub mutation |
| `ISSUE_291_READONLY_PLANNER` | issue #291 planner and dry-run script | stop before execution |
| `OWNER_APPROVAL_REQUIRED` | commits, pushes, GitHub writes, runtime/data/source changes | explicit owner approval only |
