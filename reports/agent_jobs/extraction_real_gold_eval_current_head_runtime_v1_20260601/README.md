# Extraction Real-Gold Eval Current-Head Runtime V1

Status: complete, with residual extraction blockers.

Started: 2026-06-01T09:16:47Z.

Finished: 2026-06-01T10:04:00Z.

Scope: bounded backend real-gold eval on current HEAD after the source-path
resolver fix. This report bundle records preflight, runtime, eval, and shutdown
evidence. It does not claim full ticker-universe extraction graduation.

## Result

- Eval mode: canonical, KPI eligible.
- Documents: 15.
- Metric checks: 39.
- Correct metrics: 34.
- Metric accuracy: 87.18%.
- Context accuracy: 14/15.
- Trust distribution: 12 trusted, 2 abstain, 1 quarantine.
- Trust matched expected for 12/15 documents.

Residual blockers:

- `14d_q_2021-03-31`: context mismatch, missing period end, trust quarantined.
- `29m_a_2025-12-31`: `net_debt` missing, trust abstained.
- `a2m_h_2025-12-31`: `net_debt` wrong because expected null but runtime extracted `-397878000`, trust abstained.

External backend review artifacts were created under
`/data/reports/extraction_review`: file count changed from 1162 to 1183,
session JSON count from 5 to 7, and snippet count from 24 to 43. These are
backend-owned diagnostic artifacts, not canonical financial truth.

Shutdown evidence: backend/router units stopped, ports `8000` and `8001`
closed, GPU-exclusive activity cleared, GPU guard clean, and Tesla M40 memory
returned to `0 / 24576 MiB`.
