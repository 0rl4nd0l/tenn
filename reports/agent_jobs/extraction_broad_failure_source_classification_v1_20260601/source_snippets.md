# Source Snippets

Evidence source: `pdftotext -layout` output in `/tmp/tenn_broad_failure_source_classification_v1/`.

## GTE

- Lines 670-672: Directors present the annual report for the consolidated group for the year ended 30 June 2025.
- Lines 1334-1341: consolidated profit-or-loss statement, year ended 30 June 2025, with `$` column headers.
- Lines 1361-1363: source label is loss before income tax and loss for the period, not EBIT.
- Lines 1503-1508: consolidated cash-flow statement, year ended 30 June 2025, with `$` column headers.
- Lines 2911-2916: ordinary shares on issue are stated as `567,757,925`.

Assessment: eligible annual financial report; unit scale is source dollars/units; failure is EBIT label semantics, not source eligibility or scale.

## ARL

- Lines 9-17: document is results of the 2022 Annual General Meeting held 28 October 2022.
- Lines 20-21: announcement says all AGM resolutions passed and the attached table lists AGM results.
- Lines 42-81: content is proxy/poll vote results.

Assessment: AGM results notice; not eligible for canonical financial metric extraction.

## HNG

- Lines 8-15: financial update for the half year ended 31 March 2021, ahead of planned release, subject to audit.
- Lines 25-32: headline values are expressed in millions, but no formal statements are present.

Assessment: unaudited headline update without formal statements; exclude from canonical financial-row extraction or route separately as non-canonical announcement signal.

## CAF

- Lines 6-7: Appendix 4E for the year ended 30 June 2021.
- Lines 14-18: revenue and attributable profit are explicit full-dollar values with dollar signs.
- Line 54: prose summary uses `$1.8m`, but the extractable table rows above are full-dollar values.

Assessment: eligible Appendix 4E; failure points to source-unit detection for full-dollar summary rows.

## TLS

- Lines 22-25: document is results of the 2022 Annual General Meeting and poll results.
- Lines 82-88: attached report is annual general meeting voting statistics.
- Lines 91-142: content is proxy/direct-vote/poll table, not financial statements.

Assessment: AGM results notice; not eligible for canonical financial metric extraction.
