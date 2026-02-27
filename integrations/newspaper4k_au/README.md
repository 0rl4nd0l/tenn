# Isolated `newspaper4k` AU Finance Collector

This module is intentionally isolated from the main `financial-engine_v2` runtime.

It does not write to production databases. It only emits a JSONL artifact that can be used as an optional upstream input for research workflows.

## 1) Create an isolated virtual environment

From repo root:

```bash
python3 -m venv integrations/newspaper4k_au/.venv
integrations/newspaper4k_au/.venv/bin/pip install -r integrations/newspaper4k_au/requirements.txt
```

## 2) Run collection

```bash
integrations/newspaper4k_au/.venv/bin/python integrations/newspaper4k_au/collect_au_finance_news.py \
  --sources-file integrations/newspaper4k_au/sources_au_finance.txt \
  --output-jsonl integrations/newspaper4k_au/out/au_finance_news.jsonl \
  --manifest-json integrations/newspaper4k_au/out/au_finance_manifest.json \
  --lookback-hours 120 \
  --max-articles-per-source 25 \
  --max-total-articles 200
```

Dry-run (no file writes):

```bash
integrations/newspaper4k_au/.venv/bin/python integrations/newspaper4k_au/collect_au_finance_news.py --dry-run
```

Authenticated (for subscriber-only sources):

```bash
integrations/newspaper4k_au/.venv/bin/python integrations/newspaper4k_au/collect_au_finance_news.py \
  --sources-file integrations/newspaper4k_au/sources_afr_focus.txt \
  --output-jsonl integrations/newspaper4k_au/out/au_finance_news_afr.jsonl \
  --manifest-json integrations/newspaper4k_au/out/au_finance_manifest_afr.json \
  --http-cookie-file /path/to/afr_cookie_header.txt \
  --raw-html-dir integrations/newspaper4k_au/out/raw_html_afr
```

Notes:

- `--http-cookie` or `--http-cookie-file` lets you pass your own authenticated session cookie.
- `--raw-html-dir` stores full fetched HTML snapshots per article URL for audit/re-parsing.
- If the source still returns teaser text, the paywall is serving preview content to your session.

Source line modes (`sources_au_finance.txt`):

- `auto:<url>`: web discovery, with RSS fallback when web returns no candidates.
- `web:<url>`: web discovery only.
- `rss:<url>`: RSS/Atom feed discovery.
- `url:<url>`: direct single article URL.

Upstream `newspaper4k` FutureWarnings are suppressed by default. Use `--keep-future-warnings` to show them.

For more stable runs (less homepage discovery variance), use:

- `integrations/newspaper4k_au/sources_au_finance_rss_only.txt`

For AFR-first scraping, use:

- `integrations/newspaper4k_au/sources_afr_focus.txt`

No-subscription finance run (recommended if you do not have AFR access):

- `integrations/newspaper4k_au/sources_finance_no_sub.txt`
- `integrations/newspaper4k_au/sources_finance_no_sub_plus_capitalbrief.txt`
- `integrations/newspaper4k_au/sources_finance_no_sub_plus_capitalbrief_kalkine.txt`
- `integrations/newspaper4k_au/sources_finance_no_sub_plus_capitalbrief_kalkine_benzinga.txt`
- `integrations/newspaper4k_au/sources_finance_no_sub_plus_capitalbrief_kalkine_benzinga_australian.txt`

Capital Brief focus:

- `integrations/newspaper4k_au/sources_capitalbrief_focus.txt`

Kalkine focus:

- `integrations/newspaper4k_au/sources_kalkine_focus.txt`

Benzinga focus:

- `integrations/newspaper4k_au/sources_benzinga_focus.txt`

Market Index focus:

- `integrations/newspaper4k_au/sources_marketindex_focus.txt`

Sky News focus:

- `integrations/newspaper4k_au/sources_skynews_focus.txt`

Stockhead focus:

- `integrations/newspaper4k_au/sources_stockhead_focus.txt`

Livewire Markets focus:

- `integrations/newspaper4k_au/sources_livewire_focus.txt`

Yahoo Finance focus:

- `integrations/newspaper4k_au/sources_yahoo_finance_focus.txt`

The Australian focus (login/subscription usually required):

- `integrations/newspaper4k_au/sources_australian_focus.txt`

## Safety guardrails

- Domain allowlist: only keeps article URLs that resolve to domains from `sources_au_finance.txt`.
- Rate control: configurable `--sleep-seconds` between sources.
- Scope control: `--max-sources`, `--max-articles-per-source`, `--max-total-articles`.
- Research-only output: JSONL artifact only, no direct DB writes.
- Filtering: keeps articles matching finance keywords and minimum body length.
- URL hygiene: drops non-article section/category URLs (for example `/companies/mining`) before parse.
- Empty-run protection: zero-record runs do not overwrite an existing non-empty JSONL unless `--allow-empty-overwrite` is set.

## Output schema

Each JSONL row is compatible with `scripts/build_news_context_db.py`:

- `id`
- `date`
- `title`
- `text`
- `extra_fields.source`
- `extra_fields.url`
- `extra_fields.category`
- `extra_fields.language`
- `extra_fields.domain`
- `extra_fields.authors`
- `extra_fields.matched_keywords`
- `extra_fields.body_source` (which extractor won: `newspaper_text`, `newspaper_fulltext`, `jsonld_articleBody`)
- `extra_fields.body_lengths` (candidate lengths by extractor)
- `extra_fields.raw_html_path` (when `--raw-html-dir` is used)

## Optional follow-on

Use the artifact with your existing builder:

```bash
python3 scripts/build_news_context_db.py \
  --input-path integrations/newspaper4k_au/out/au_finance_news.jsonl \
  --db sqlite \
  --out reports/qual_context/news_newspaper4k.sqlite \
  --embed-backend hash \
  --hash-dim 64 \
  --research-only-ack
```

## Recommended strict finance run

```bash
integrations/newspaper4k_au/.venv/bin/python integrations/newspaper4k_au/collect_au_finance_news.py \
  --sources-file integrations/newspaper4k_au/sources_afr_focus.txt \
  --output-jsonl integrations/newspaper4k_au/out/au_finance_news_afr.jsonl \
  --manifest-json integrations/newspaper4k_au/out/au_finance_manifest_afr.json \
  --lookback-hours 168 \
  --min-text-chars 180 \
  --min-keyword-hits 2 \
  --max-articles-per-source 40 \
  --max-total-articles 200
```

## Recommended no-sub run

```bash
integrations/newspaper4k_au/.venv/bin/python integrations/newspaper4k_au/collect_au_finance_news.py \
  --sources-file integrations/newspaper4k_au/sources_finance_no_sub.txt \
  --output-jsonl integrations/newspaper4k_au/out/au_finance_news_no_sub.jsonl \
  --manifest-json integrations/newspaper4k_au/out/au_finance_manifest_no_sub.json \
  --lookback-hours 168 \
  --min-text-chars 180 \
  --min-keyword-hits 2 \
  --max-articles-per-source 40 \
  --max-total-articles 300
```

## Capital Brief run

```bash
integrations/newspaper4k_au/.venv/bin/python integrations/newspaper4k_au/collect_au_finance_news.py \
  --sources-file integrations/newspaper4k_au/sources_capitalbrief_focus.txt \
  --output-jsonl integrations/newspaper4k_au/out/au_finance_news_capitalbrief.jsonl \
  --manifest-json integrations/newspaper4k_au/out/au_finance_manifest_capitalbrief.json \
  --lookback-hours 168 \
  --min-text-chars 180 \
  --min-keyword-hits 2 \
  --max-articles-per-source 40 \
  --max-total-articles 200
```

## No-sub + Capital Brief run

```bash
integrations/newspaper4k_au/.venv/bin/python integrations/newspaper4k_au/collect_au_finance_news.py \
  --sources-file integrations/newspaper4k_au/sources_finance_no_sub_plus_capitalbrief.txt \
  --output-jsonl integrations/newspaper4k_au/out/au_finance_news_no_sub_plus_capitalbrief.jsonl \
  --manifest-json integrations/newspaper4k_au/out/au_finance_manifest_no_sub_plus_capitalbrief.json \
  --finance-url-gate-exempt-domains capitalbrief.com \
  --article-url-gate-exempt-domains capitalbrief.com \
  --lookback-hours 168 \
  --min-text-chars 180 \
  --min-keyword-hits 2 \
  --max-articles-per-source 40 \
  --max-total-articles 300
```

## Kalkine run

```bash
integrations/newspaper4k_au/.venv/bin/python integrations/newspaper4k_au/collect_au_finance_news.py \
  --sources-file integrations/newspaper4k_au/sources_kalkine_focus.txt \
  --output-jsonl integrations/newspaper4k_au/out/au_finance_news_kalkine.jsonl \
  --manifest-json integrations/newspaper4k_au/out/au_finance_manifest_kalkine.json \
  --finance-url-gate-exempt-domains kalkinemedia.com,kalkinemedia.com.au \
  --article-url-gate-exempt-domains kalkinemedia.com,kalkinemedia.com.au \
  --lookback-hours 168 \
  --min-text-chars 180 \
  --min-keyword-hits 2 \
  --max-articles-per-source 40 \
  --max-total-articles 200
```

## No-sub + Capital Brief + Kalkine run

```bash
integrations/newspaper4k_au/.venv/bin/python integrations/newspaper4k_au/collect_au_finance_news.py \
  --sources-file integrations/newspaper4k_au/sources_finance_no_sub_plus_capitalbrief_kalkine.txt \
  --output-jsonl integrations/newspaper4k_au/out/au_finance_news_no_sub_plus_capitalbrief_kalkine.jsonl \
  --manifest-json integrations/newspaper4k_au/out/au_finance_manifest_no_sub_plus_capitalbrief_kalkine.json \
  --finance-url-gate-exempt-domains capitalbrief.com,kalkinemedia.com,kalkinemedia.com.au \
  --article-url-gate-exempt-domains capitalbrief.com,kalkinemedia.com,kalkinemedia.com.au \
  --lookback-hours 168 \
  --min-text-chars 180 \
  --min-keyword-hits 2 \
  --max-articles-per-source 40 \
  --max-total-articles 300
```

## Benzinga run

```bash
integrations/newspaper4k_au/.venv/bin/python integrations/newspaper4k_au/collect_au_finance_news.py \
  --sources-file integrations/newspaper4k_au/sources_benzinga_focus.txt \
  --output-jsonl integrations/newspaper4k_au/out/au_finance_news_benzinga.jsonl \
  --manifest-json integrations/newspaper4k_au/out/au_finance_manifest_benzinga.json \
  --finance-url-gate-exempt-domains benzinga.com \
  --article-url-gate-exempt-domains benzinga.com \
  --lookback-hours 168 \
  --min-text-chars 180 \
  --min-keyword-hits 2 \
  --max-articles-per-source 40 \
  --max-total-articles 200
```

## No-sub + Capital Brief + Kalkine + Benzinga run

```bash
integrations/newspaper4k_au/.venv/bin/python integrations/newspaper4k_au/collect_au_finance_news.py \
  --sources-file integrations/newspaper4k_au/sources_finance_no_sub_plus_capitalbrief_kalkine_benzinga.txt \
  --output-jsonl integrations/newspaper4k_au/out/au_finance_news_no_sub_plus_capitalbrief_kalkine_benzinga.jsonl \
  --manifest-json integrations/newspaper4k_au/out/au_finance_manifest_no_sub_plus_capitalbrief_kalkine_benzinga.json \
  --finance-url-gate-exempt-domains capitalbrief.com,kalkinemedia.com,kalkinemedia.com.au,benzinga.com \
  --article-url-gate-exempt-domains capitalbrief.com,kalkinemedia.com,kalkinemedia.com.au,benzinga.com \
  --lookback-hours 168 \
  --min-text-chars 180 \
  --min-keyword-hits 2 \
  --max-articles-per-source 40 \
  --max-total-articles 300
```

## The Australian run (authenticated)

```bash
integrations/newspaper4k_au/.venv/bin/python integrations/newspaper4k_au/collect_au_finance_news.py \
  --sources-file integrations/newspaper4k_au/sources_australian_focus.txt \
  --output-jsonl integrations/newspaper4k_au/out/au_finance_news_australian.jsonl \
  --manifest-json integrations/newspaper4k_au/out/au_finance_manifest_australian.json \
  --http-cookie-file /path/to/the_australian_cookie_header.txt \
  --finance-url-gate-exempt-domains theaustralian.com.au \
  --article-url-gate-exempt-domains theaustralian.com.au \
  --lookback-hours 168 \
  --min-text-chars 180 \
  --min-keyword-hits 2 \
  --max-articles-per-source 40 \
  --max-total-articles 200
```

## No-sub + Capital Brief + Kalkine + Benzinga + The Australian + Market Index + Sky News + Stockhead + Livewire + Yahoo Finance run

```bash
integrations/newspaper4k_au/.venv/bin/python integrations/newspaper4k_au/collect_au_finance_news.py \
  --sources-file integrations/newspaper4k_au/sources_finance_no_sub_plus_capitalbrief_kalkine_benzinga_australian.txt \
  --output-jsonl integrations/newspaper4k_au/out/au_finance_news_no_sub_plus_capitalbrief_kalkine_benzinga_australian.jsonl \
  --manifest-json integrations/newspaper4k_au/out/au_finance_manifest_no_sub_plus_capitalbrief_kalkine_benzinga_australian.json \
  --http-cookie-file /path/to/the_australian_cookie_header.txt \
  --finance-url-gate-exempt-domains capitalbrief.com,kalkinemedia.com,kalkinemedia.com.au,benzinga.com,theaustralian.com.au,marketindex.com.au,skynews.com.au,stockhead.com.au,stockhead.com,livewiremarkets.com,finance.yahoo.com \
  --article-url-gate-exempt-domains capitalbrief.com,kalkinemedia.com,kalkinemedia.com.au,benzinga.com,theaustralian.com.au,marketindex.com.au,skynews.com.au,stockhead.com.au,stockhead.com,livewiremarkets.com,finance.yahoo.com \
  --lookback-hours 168 \
  --min-text-chars 180 \
  --min-keyword-hits 2 \
  --max-articles-per-source 40 \
  --max-total-articles 300
```

If AFR returns `seen: 0`, the collector now also tries HTML link extraction fallback on the section page. In the manifest, check:

- `html_links_seen`
- `url_filtered_non_finance_path`
- `insufficient_keyword_hits`

For AFR specifically, `auto:` mode now also probes common AFR RSS endpoints as fallback when section discovery is empty.
