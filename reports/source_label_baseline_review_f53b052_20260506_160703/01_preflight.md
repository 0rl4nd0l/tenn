# Preflight

## Required Command Results

`pwd`

```text
/home/l4nd0/tenn
```

`git branch --show-current`

```text
preserve/dirty-work-20260430T065748Z
```

`git rev-parse HEAD`

```text
f53b0526a6a483c350f8ee74434b95ed3f0dc06a
```

`git status --short`

```text
?? tenn_prompt_contracts_response_guidelines.zip
```

`git diff --cached --name-status`

```text

```

Active job registry:

```json
{
  "active_jobs": [],
  "registry_scope": "shared",
  "repo_root": "/mnt/sdb2/home/l4nd0/tenn"
}
```

## Recent HEAD

```text
f53b052 fix(provenance): preserve source labels across reload and drawer
51ccfd8 milestone(reporting): inject metric coverage git provenance
ffffb2f milestone(reporting): add commentary recent route parity
cf4701f milestone(agent-registry-docs): document shared registry workflow
af5f9c6 wip(reporting): add metric coverage provenance flags
2d09b67 milestone(agent-registry): share job claims across worktrees
3c147f7 fix(provenance): classify source labels by evidence role
906593b milestone(agent-registry): add dev-agent lane locks
3837263 milestone(reporting): add watchlist route parity
b9ace36 fix(query): include ticker-filtered news evidence for company chat
8d3d588 milestone(reporting): add ebay sync bff route parity
3e7187e milestone(news): align nightly memo diagnostics path
dd05503 milestone(marketplace): checkpoint requirement-driven match payloads
93e91cc milestone(agent-jobs): activate dev-agent task-card hooks
518c363 ops(memory): remove tracked cleanup backup artifact
8d7ee27 milestone(reporting): wrap metric coverage review table text
46ba99f milestone(agent-jobs): enforce task card diff scope
92630d2 milestone(reporting): fix confirmed coverage fixture path
0669030 milestone(reporting): harden cockpit web contract gaps phase 1
c907cb8 milestone(reporting): add confirmed metric coverage verification UI
```

## Ancestor Check

All requested commits were present ancestors of `HEAD`:

```text
f53b0526a6a
51ccfd8
ffffb2f2aeb8
383726323353
8d3d58811cf1
dd055038a045
0669030bd468
165be97d7e45632abd42fdebd2ef9b27805332d8
fb880c6ec0e2451855e80fbd203b924f14270ebc
22356f2139aa
a48c2e1a6389
```

## Collision Result

Dirty state matched the expected untracked zip only. No implementation file was dirty, and no active registry job was present. Audit proceeded.
