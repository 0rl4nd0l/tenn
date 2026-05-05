# Approval Gates

Gate 1: operator reviews candidate CSVs.

Gate 2: operator approves action types allowed.

Gate 3: operator approves maximum row count to mutate.

Gate 4: operator approves backup path and checksum.

Gate 5: future Codex run performs dry run against copied DB.

Gate 6: live mutation only after explicit user approval in a separate prompt.

No gate is satisfied by this report alone.
