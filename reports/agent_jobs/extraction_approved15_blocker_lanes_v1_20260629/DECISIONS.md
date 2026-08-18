# Decisions

1. Select Lane A RMS as the only implementation lane.
   - Reason: source-proven, narrow, one marker expansion, directly explains
     the four `missing_expected_metric` rows.

2. Park Lane B QBE.
   - Reason: source-proven but separate failure class; needs formal statement
     revenue precedence without weakening magnitude gates.

3. Park Lane C DXS.
   - Reason: fail-closed gate is catching mixed source-scale payloads; raw
     table candidate evidence is still insufficient for one safe fix.

4. Park Lane D BHP/MIN.
   - Reason: source-proven and likely valuable, but owner-attributable
     precedence is a separate fix class.

5. Park Lane E ambiguous quarantine.
   - Reason: policy/source-evidence review lane, not an extractor fix.

6. Keep Lane F gate strict.
   - Reason: scorecard gate remains blocked after RMS; status must remain
     `PARTIAL`.

7. Do not rebase or merge.
   - Reason: current origin advanced after the PR #461 base. The drift is
     control-plane/docs-only for inspected extraction allowlist, but branch
     refresh is a separate owner action.
