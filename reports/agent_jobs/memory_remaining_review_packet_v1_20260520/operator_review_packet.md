# Operator Review Packet

Verdict: `REVIEW_PACKET_READY`.

This packet consolidates the remaining narrow company-memory review surface from prior read-only artifacts only. It does not decide or perform cleanup.

## Review Counts

- Review items: `18` including separate manual-review manifest views.
- Distinct underlying entry IDs represented: `19`.
- Source-fanout threshold clusters: `1`.
- Known historical source rows: `14`.
- Manual-review manifest rows: `3`; these overlap known historical entry IDs `283, 310, 1129`.

## Recommended Operator Actions

- `insufficient_evidence`: `1`
- `likely_legitimate`: `13`
- `review_source`: `4`

## Rows

| review_item_id | category | entry_id(s) | company_id(s) | source_id | preview | recommended action | confidence |
| --- | --- | --- | --- | --- | --- | --- | --- |
| source_fanout_threshold_cluster_001 | source_fanout_threshold_cluster | 2362, 2363, 2361, 2359, 2360 | CBA, MIN, MP1, XRO, XRO | `news:art_c0195feddb42ee1a1f11268d` | Commonwealth Bank (ASX:CBA) extending its rebound from Wednesday’s sell-off | `review_source` | `medium` |
| known_historical_source_row_0283 | known_historical_source_row | 283 | A2M | `youtube_transcript:asx-daily-rundown-atlassian-lifts-tech-a2-milk-recall-shock-accent-group-all-time-lows:88e960386e503796` | A2 MILK's share price dropped 10% due to a product recall | `likely_legitimate` | `medium` |
| known_historical_source_row_0310 | known_historical_source_row | 310 | A2M | `youtube_transcript:asx-daily-rundown-atlassian-lifts-tech-a2-milk-recall-shock-accent-group-all-time-lows:88e960386e503796` | A2 MILK's share price has dropped from almost $10 back to $6.59 in a few months | `likely_legitimate` | `medium` |
| known_historical_source_row_0717 | known_historical_source_row | 717 | NAB | `youtube_transcript:asx-daily-rundown-atlassian-lifts-tech-a2-milk-recall-shock-accent-group-all-time-lows:88e960386e503796` | DATA_MISSING: statement preview not present in artifact cap | `insufficient_evidence` | `low` |
| known_historical_source_row_1129 | known_historical_source_row | 1129 | A2M | `youtube_transcript:asx-daily-rundown-atlassian-lifts-tech-a2-milk-recall-shock-accent-group-all-time-lows:88e960386e503796` | Potential overreaction by the market to the recall announcement for A2 MILK | `likely_legitimate` | `medium` |
| known_historical_source_row_1273 | known_historical_source_row | 1273 | EZZ | `news:art_e4faef3c4644fe5bb3b66e32` | EZZ enters the wellness market with its MeTime range | `likely_legitimate` | `medium` |
| known_historical_source_row_1301 | known_historical_source_row | 1301 | CSL | `news:art_e4faef3c4644fe5bb3b66e32` | CSL faces renewed scrutiny over valuation gaps and growth expectations | `likely_legitimate` | `medium` |
| known_historical_source_row_1310 | known_historical_source_row | 1310 | RESMED | `news:art_e4faef3c4644fe5bb3b66e32` | RESMED delivers strong quarterly growth | `likely_legitimate` | `medium` |
| known_historical_source_row_1341 | known_historical_source_row | 1341 | CSL | `news:art_e4faef3c4644fe5bb3b66e32` | CSL's renewed scrutiny over valuation gaps and growth expectations | `likely_legitimate` | `medium` |
| known_historical_source_row_1493 | known_historical_source_row | 1493 | A2M | `news:art_aa13edd261034dba97055d8a` | A2 Milk has recalled three batches of its USA label infant formula due to the presence of cereulide toxin | `likely_legitimate` | `medium` |
| known_historical_source_row_1495 | known_historical_source_row | 1495 | A2M | `news:art_aa13edd261034dba97055d8a` | Shares in A2 Milk plunged 11.35% to $6.44 in afternoon trade | `likely_legitimate` | `medium` |
| known_historical_source_row_1829 | known_historical_source_row | 1829 | A2M | `youtube_transcript:asx-daily-rundown-atlassian-lifts-tech-a2-milk-recall-shock-accent-group-all-time-lows:88e960386e503796` | A2 MILK's voluntary recall of three batches of A2 Platinum USA label infant milk formula | `likely_legitimate` | `medium` |
| known_historical_source_row_1961 | known_historical_source_row | 1961 | A2M | `youtube_transcript:asx-daily-rundown-atlassian-lifts-tech-a2-milk-recall-shock-accent-group-all-time-lows:88e960386e503796` | A2 MILK's potential overreaction from the market due to the product recall | `likely_legitimate` | `medium` |
| known_historical_source_row_2425 | known_historical_source_row | 2425 | CSL | `news:art_ffe96e73baccb32f600ec187` | CSL's share price dropped due to chaotic trading after CEO resignation announcement | `likely_legitimate` | `medium` |
| known_historical_source_row_2427 | known_historical_source_row | 2427 | CSL | `news:art_ffe96e73baccb32f600ec187` | CSL's share price dropped amid chaotic trading after CEO resignation announcement | `likely_legitimate` | `medium` |
| manual_review_manifest_row_0283 | manual_review_manifest_row | 283 | A2M | `youtube_transcript:asx-daily-rundown-atlassian-lifts-tech-a2-milk-recall-shock-accent-group-all-time-lows:88e960386e503796` | A2 MILK's share price dropped 10% due to a product recall | `review_source` | `medium` |
| manual_review_manifest_row_0310 | manual_review_manifest_row | 310 | A2M | `youtube_transcript:asx-daily-rundown-atlassian-lifts-tech-a2-milk-recall-shock-accent-group-all-time-lows:88e960386e503796` | A2 MILK's share price has dropped from almost $10 back to $6.59 in a few months | `review_source` | `medium` |
| manual_review_manifest_row_1129 | manual_review_manifest_row | 1129 | A2M | `youtube_transcript:asx-daily-rundown-atlassian-lifts-tech-a2-milk-recall-shock-accent-group-all-time-lows:88e960386e503796` | Potential overreaction by the market to the recall announcement for A2 MILK | `review_source` | `medium` |

## Operator Notes

- `candidate_expire_later` is intentionally unused because the prior artifacts do not prove any row is ready for mutation without source review.
- `likely_legitimate` means the capped preview appears tied to the scoped company, not that the row has been approved for preservation.
- `review_source` means the source article or transcript should be inspected before preserve/expire-later decisions.
- `insufficient_evidence` means the artifacts do not include enough row-level text/source context for a responsible classification.
- `mutation_allowed` is false for every item in `operator_review_rows.json` and `operator_review_rows.csv`.
