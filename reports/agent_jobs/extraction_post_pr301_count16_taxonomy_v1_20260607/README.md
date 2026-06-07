# Post-PR301 Count-16 Failure And Accepted-Output Taxonomy

Generated: 2026-06-07T05:00:57Z

Input: `reports/agent_jobs/extraction_post_pr301_count16_validation_v1_20260607/`.
No additional sample, count-24/count-32, broad extraction, backfill, or full
ticker-universe extraction ran in this phase.

## Result

- Failed documents classified: 9
- Low-confidence documents classified: 0
- Suspicious accepted documents classified: 2
- True noncandidate failures: 5
- Accepted-output risk: HUB and LBL

## Key Findings

DXC failed closed with
`validation_gate:metric_label_mismatch:ebit:net_operating_income`.

LBL remained accepted. Source evidence shows A$000 five-year tables were used
for several accepted values while the payload scale was `millions`; its
accepted `period_end` also matched the filename announcement date.

HUB also remained accepted with `period_end=2024-02-20`, but source text says
the Appendix 4D half-year ended 31 December 2023.

## Repair Decision

One narrow follow-up repair is justified: add a stricter accepted-output guard
that fails half-year outputs when `period_end` equals a leading announcement
date in the source title/filename. This is an abstain/quarantine guard; it does
not infer a corrected period, loosen validation, expand metrics, or backfill.

## Count-24 Decision

Count-24 approval is premature until the narrow half-year announcement-date
guard is implemented and focused tests pass.

## DATA_MISSING

- Reliable GPU memory telemetry from Milestone 3: `nvidia-smi` failed.
- `pdfplumber`/`pypdf` were unavailable; Poppler text extraction and one visual
  render were used instead.
- WHC 2022 scale root cause is not narrow enough for this repair.
