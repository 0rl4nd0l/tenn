# Retrieval Impact Approximation

This approximation does not run live chat and does not change retrieval/ranking. It estimates scope impact by active company-memory row counts before and after copied-DB status expiry.

## Removed Active Contamination

- Active company-memory rows before: 1997
- Candidate active rows removed from active retrieval scope: 1212
- Active rows after: 785
- Overall active-row reduction: 60.69%

## Ticker Scopes Changing Most

|entity|active_before|expire_candidate_count|active_after|active_reduction_pct|
|---|---|---|---|---|
|COH|68|39|29|57.35|
|ASX|58|33|25|56.9|
|BHP|58|33|25|56.9|
|INDE|44|33|11|75.0|
|TXT|44|33|11|75.0|
|XTX|44|33|11|75.0|
|NAB|50|32|18|64.0|
|SKT|37|30|7|81.08|
|VCE|37|30|7|81.08|
|WBC|41|30|11|73.17|
|WES|37|30|7|81.08|
|WIN|37|30|7|81.08|
|ACCENT GROUP|44|29|15|65.91|
|C79|44|28|16|63.64|
|PETT|44|28|16|63.64|


## Nearly Emptied / Floor Check

No ticker scope drops below the strict retrieval floor of 3 active rows, and no scope is nearly emptied by this action. Using a conservative watch floor of 5 active rows, changed scopes below 5 are: CLAR (27->4), KEYP (27->4), LION (27->4), LIVN (27->4), MARINO (27->4), SN (27->4).

Unchanged scopes below 5 already existed before this cleanup: GOLD (4), NAVIG (3), RETAIL (4), UGL (4).
