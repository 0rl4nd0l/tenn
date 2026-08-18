# Data Missing

- The broad `state:ready` issue scan was intentionally byte-capped/noise-capped.
  The ranking uses bounded label scans and focused issue bodies, not an
  exhaustive full backlog export.
- The keyword issue search returned no additional JSON rows in this run. Label
  scans were treated as more authoritative for this Phase 1 surface.
- Issue bodies were not fetched for every potentially relevant issue in the
  backlog.
- No PR checks, CI state, or branch diffs were inspected because Phase 1 is an
  issue/milestone planner only.
- No product/runtime/extraction validation was run by instruction.
- No GitHub write capability was tested by instruction.
- No executable auto-progress script was implemented in Phase 1.
