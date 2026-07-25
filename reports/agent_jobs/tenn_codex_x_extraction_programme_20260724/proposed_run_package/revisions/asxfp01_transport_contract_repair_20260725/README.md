# ASXFP Ticket 01 Transport Contract Repair

## Incident disposition

The failed launch is classified as
`ORCHESTRATION_TRANSPORT_FAILURE_NOT_IMPLEMENTATION_ATTEMPT`. It made no Tenn
product changes and produced no implementation commit or patch. Ticket
`ASXFP_01_SCORECARDS` therefore remains `READY`, represented by schema state
`PLANNED`, with `implementation_attempts=0`, `retry_count=0`, and no consumed
implementer session.

The earlier attempt revision remains immutable audit evidence. This revision
supersedes only its attempt accounting and state conclusion.

## Corrected transport

The launcher now keeps the writable checkout at exact canonical commit
`107c926930ef5a14783a8293bac9b47c9046bfed` and tree
`9e43e6380c357e1a40a23bff6d4a07522c86ff98`. It records
`/home/l4nd0/tenn` as read-only evidence only and ignores that checkout's
identity for implementation admission.

`run_id` comes from the launcher-owned run directory. `session_id` comes only
from the Codex `thread.started.thread_id` event. The model returns neither.
After exit, the launcher/supervisor injects and validates both fields in the
child-result envelope.

## Prepared retry

- Run ID: `20260725T032937Z-107c926930-fb7928`
- Session ID: `null` until a separately authorized child actually starts
- Writable checkout:
  `/home/l4nd0/codex-x-pilot/.state/runs/20260725T032937Z-107c926930-fb7928/workspace/source`
- Corrected prompt sha256:
  `fc87a7be4c52ecd4fd501e7810581bda1e344a0b0bdb6961303a80f582ed728d`
- Launcher repair commit:
  `4a16a59d619bbc195e457a3cb573b19735229d52`

The prepared run and full proposed command were validated in dry-run mode.
No child, reviewer, integration, GitHub, runtime, data, merge, or deployment
action was started.

## Hold

Do not execute `proposed_retry_command.sh` without separate owner
authorization. Reviewer launch remains prohibited.
