# Data Missing

- The issue scan used open `state:ready` issues with the requested risk filter,
  not the entire Tenn backlog.
- The script uses deterministic local scoring, not DeepSeek or another external
  planner model.
- No closed issues/PRs were searched for every ranked candidate.
- No registry claim was taken because this run is read-only/report-local.
- No product/runtime/extraction validation was run.
- No GitHub write capability was tested.
