# News Ticker Identity

Cockpit news retrieval labels each hit with `ticker_identity_strength` and, when signal weighting is on, uses that label as the ticker boost. The matcher lives in `financial-engine_v2/cockpit/integrations/qual_context.py` (`evaluate_ticker_identity_strength`, `compute_news_weighted_score`, `QualContextReader.query`).

The checked-in map is `financial-engine_v2/config/ticker_identity_map.json` (375 tickers). Cockpit starts with `repo_root` at `financial-engine_v2` (`cockpit/main.py`), and `rag.news_context` in `config/cockpit.yaml` points at `config/ticker_identity_map.json` under that root.

## What a hit means

Strength is one of `strong`, `medium`, `weak`, `ambiguous`, or `none`.

Phrases in `canonical_names` and `aliases` are equal. The loader keeps only those two lists, uppercases the ticker key, and drops every other field. Names are tried first, then aliases. The first phrase that hits decides the label; later phrases are not examined.

| Evidence | Strength |
| --- | --- |
| Phrase in the body | `strong` |
| Phrase in the title, and the headline-only exception below does not apply | `strong` |
| Phrase in the title only, body shorter than 120 characters, AU source | `medium` |
| `ASX:TICKER`, `ASX-TICKER`, or `TICKER.AX` in the title plus the first 3500 body characters | `medium` |
| Bare ticker, and the map has phrases for that ticker, while `canonical_name_required_for_acronym` is true | `ambiguous` |
| Bare ticker, no phrases stored, ticker shorter than `acronym_min_length` (default 4) | `weak` |
| Bare ticker, no phrases stored, ticker length at least 4, canonical name still required | `ambiguous` |
| No phrase and no ticker token in the scanned text | `none` |

Setting `canonical_name_required_for_acronym` to false makes every bare ticker `weak`, including tickers that have phrases and tickers of length 4 or more. The cockpit file leaves the flag true, so a mapped acronym such as `BHP` or `CSL` stays `ambiguous`.

Phrase checks use the full title and the full body. `ASX:` / `.AX` / bare-ticker checks use the title plus the first 3500 body characters. A ticker that appears only after that cutoff does not count. A company phrase after that cutoff still counts.

Matching is case-insensitive. A phrase must sit on non-alphanumeric boundaries, so `Orica` does not match inside `Historical`, and `CSL` does not match inside a longer token. Internal spaces may be any whitespace.

The headline-only exception needs all three: `allow_headline_only_medium`, a stripped body shorter than the threshold, and an AU source. Length 119 is `medium`. Length 120 is `strong`. `config/cockpit.yaml` omits `headline_only_body_chars`; the evaluator default is 120. The reader treats a source domain that ends with `.au` (after removing a leading `www.`) as AU. It does not set `feed_is_au`.

With the checked-in map, a short Australian headline `BHP Group Limited note` is `medium` even when the body contains a later BHP alias such as `court of appeal rules`. That alias is never reached because `BHP Group Limited` already matched the title.

## How the label changes ranking

`config/cockpit.yaml` turns weighting on for news (`enable_signal_weighting: true`) and turns identity hardening on. Hardening replaces the rank-based ticker boost:

| Strength | Boost field | Cockpit value |
| --- | --- | --- |
| `strong` | `ticker_match_boosts.exact` | `0.24` |
| `medium` | `ticker_match_boosts.strong` | `0.14` |
| `weak` | `ticker_match_boosts.weak` | `0.06` |
| `ambiguous` | `downgrade_ambiguous_acronym_boost` | `0.02` |
| `none` | none | `0` |

A semantic score of `0.50` therefore becomes `0.74` for `strong`, `0.52` for `ambiguous`, and stays `0.50` for `none`. Recency, `.au` domain (`au_domain_boost` `0.05`), and title keywords (`earnings`, `guidance`, `downgrade`, `upgrade`, `dividend`, `profit`, `rba`, `asx`, each `0.05`) still add on top when weighting is on.

`ticker_match_boosts` is merged key by key with the code defaults. The nested `ticker_identity` object is replaced as a whole. A partial `ticker_identity` block drops keys you leave out, and the evaluator's own defaults fill those gaps (`headline_only_body_chars` 120, `allow_headline_only_medium` false when the key is absent).

When `enable_identity_hardening` is false, the boost follows the rank signal (`exact` / `rank_1`, `strong` / `rank_2`, `weak` / `rank_3`) and the identity label is ignored for scoring. When `enable_signal_weighting` is false, `final_score` stays equal to the semantic score. The label is still computed and still returned on the hit.

## Soft mode keep rule

News uses `ticker_match_mode: soft` and `recall_top_k_multiplier: 20`. With news `top_k: 4`, the vector query asks for 80 rows and is called with an empty ticker filter. Local ranking then assigns:

| Rank | Evidence, scanned on the title plus the first 2500 body characters |
| --- | --- |
| 1 | Ticker column blob contains the symbol |
| 2 | `ASX:TICKER`, `ASX-TICKER`, or `TICKER.AX` |
| 3 | Bare ticker token |
| 0 | None of the above |

Soft mode drops rank `0` unless strength is `strong`. `medium`, `ambiguous`, `weak`, and `none` do not keep a rank-0 row. A phrase that does not contain the ticker can still be `strong` at rank `0` and stay in the result. On the checked-in map, the title `BMO Global Metals, Mining published a note` is a BHP `strong` hit at rank `0`.

Hits sort by `final_score`, then semantic score, then rank ascending. A high semantic `ambiguous` acronym hit can finish above a lower semantic `strong` name hit. `ASX-BHP` at semantic `0.55` (final `0.69`) outranks a rank-0 name hit at semantic `0.30` (final `0.54`).

Strict mode (the company corpus default, and any caller that does not pass `soft`) sends the ticker filter into the vector query, does not multiply recall, keeps every returned row, and sets `ticker_match_rank` to null. Strength is still attached when a ticker filter was passed.

Company retrieval (`rag.qualitative_context`, `corpus_filter: company`) leaves weighting off and stays strict. It still loads the same map. Hardening in that default config is true, and `headline_only_body_chars` stays `120` because the news yaml block is not applied.

## Map file

```json
{
  "BHP": {
    "canonical_names": ["BHP Group Limited"],
    "aliases": ["BHP Group"]
  }
}
```

`QualContextReader` resolves a relative `ticker_identity_map_path` from `repo_root`, then loads it. A missing file, unreadable JSON, or a non-object payload becomes an empty map and does not raise. `load_ticker_identity_map` on its own resolves a relative path from the process cwd, which is a different rule than the reader.

An empty map removes every `strong` phrase. Bare `BHP` (length 3) is then `weak`. Bare `CSL` is also `weak` for the same reason. A ticker of length 4 or more with no stored phrases is `ambiguous` while canonical names are required. Soft mode can no longer rescue a rank-0 row.

The checked-in BHP entry includes `BHP Group Limited` and also unrelated phrases such as `BMO Global Metals, Mining`, `court of appeal rules group`, and the alias `court of appeal rules`. Those phrases are trusted. A long article whose title is `The court of appeal rules today` is `strong` for BHP. Edit the JSON when a phrase is too broad; there is no separate confidence field.

## Pitfalls

- A ticker stored only in the row's ticker column is rank `1` and strength `none` when the title and body never say the name or the symbol. With hardening on, that hit gets no ticker boost. The `.au` domain boost can still apply.
- Acronym-only copy for a mapped ticker is `ambiguous` (`0.02`), including short codes such as `BHP` and `CSL`. `ASX:BHP` and `BHP.AX` are `medium` (`0.14`).
- Disabling identity hardening changes the boost. It does not change the soft-mode drop. Rank `0` is still kept only for `strong`.
- The rank window is the first 2500 body characters. The identity token window is the first 3500. A symbol between those two cutoffs can be `medium` or `ambiguous` at rank `0`, and soft mode then keeps it only when the label is `strong`.
- A source host with a port (`afr.com.au:443`) does not end with `.au`, so the AU headline exception and the domain boost both miss.

## Check

```bash
cd financial-engine_v2
PYTHONPATH=. python3 -m unittest \
  scripts/test_ticker_identity_hardening.py \
  scripts/test_news_weighted_ranking.py
```

`test_ticker_identity_hardening.py` covers canonical-name `strong`, acronym-only `ambiguous`, `ASX:BHP` `medium`, the AU headline-only rule, substring collisions, and the legacy boost when hardening is off. `test_news_weighted_ranking.py` covers recency order, domain and keyword boosts, and a disabled weighting switch.
