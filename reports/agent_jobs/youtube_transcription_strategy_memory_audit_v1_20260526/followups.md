# Follow-Ups

## Linked Existing Issues

1. #101 - Persist YouTube source metadata and transcript timing through
   commentary chunks.
   - Lane: Provenance.
   - Validation: staged chunk payloads preserve video URL, channel, published
     time, transcript method, and timestamp/chunk citations.

2. #102 - Add YouTube intake quality gates for low-signal and speculative
   transcripts.
   - Lane: Evaluation.
   - Validation: fixtures for low-signal, incomplete, off-domain, speculative,
     and factual transcript cases.

3. #103 - Add Home memory-candidate queue for commentary takeaways.
   - Lane: Reporting and Memory.
   - Validation: Home shows pending candidates without applying memory writes;
     confirm/reject/edit/downgrade/apply actions route through backend-owned
     proposal APIs.

## New Follow-Up Recommended, Not Created

4. Reconcile YouTube channel-watch runtime docs after proving service ownership.
   - Lane: Runtime and Reporting.
   - Reason not created here: this audit task card permits report artifacts only
     and does not authorize new GitHub issue creation.
   - DATA_MISSING: durable tracker for this docs/runtime reconciliation.

## Implementation Sequencing

1. Execute #102 first to define quality and speculation gates.
2. Execute #101 next so all candidates carry durable provenance and timing.
3. Execute #103 after #101/#102 so Home displays evidence-bound candidates.
4. Update channel-watch runbook once runtime service/process ownership is proven.
