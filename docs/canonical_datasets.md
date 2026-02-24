# Canonical Datasets (2026-02-23)

This file defines the canonical dataset artifacts to use for retrieval and extraction checks.

## Canonical DB Aliases

- `reports/qual_context/company.sqlite` -> `reports/qual_context/company_bge_v2.sqlite`
- `reports/qual_context/news_eval.sqlite` -> `reports/qual_context/news_eval_hash.sqlite`
- `reports/qual_context/news.sqlite` (full research news corpus)
- `reports/qual_context/reference.sqlite` -> `reports/usb_qual_context/reference_fulltext.sqlite`
- `reports/financial_metrics.sqlite`

## Purpose

- `company.sqlite`: primary company RAG dataset for filing/announcement retrieval.
- `news_eval.sqlite`: deterministic fixture dataset for news benchmark tests.
- `news.sqlite`: large research news corpus dataset (not used for deterministic benchmark).
- `reference.sqlite`: textbook/research/announcement reference corpus.
- `financial_metrics.sqlite`: structured extracted metric rows.

## Source Of Truth

- Primary document source: `financial-engine_v2/data/asx/docs` (ASX architecture).
- MarketIndex PDFs are fallback-only ingestion input.

## Canonical Eval Backends

- News fixture eval: `hash`
- Company eval: `sentence-transformers` with `BAAI/bge-large-en-v1.5`
- Reference eval: `hash`

## Canonical Check Command

```bash
scripts/run_canonical_dataset_checks.sh
```

GPU default:
- Company eval runs with `ST_DEVICE=cuda` by default.
- Override explicitly when needed, for example: `ST_DEVICE=cpu scripts/run_canonical_dataset_checks.sh`.
- CUDA is enforced by default (`REQUIRE_CUDA=1`), so the check script exits if no GPU is visible.
- To intentionally allow CPU fallback: `REQUIRE_CUDA=0 scripts/run_canonical_dataset_checks.sh`.

Outputs:

- `reports/news_eval_report.json`
- `reports/company_eval_report_v2.json`
- `reports/eval_queries_report.json`

## Canonical Regression Gate

Optional strict gate against a baseline snapshot:

```bash
CHECK_BASELINE=1 \
BASELINE_PATH=reports/baselines/canonical_eval_baseline_latest.json \
scripts/run_canonical_dataset_checks.sh
```

Direct gate command:

```bash
python3 scripts/check_canonical_regression.py \
  --baseline reports/baselines/canonical_eval_baseline_latest.json
```

## Baseline Snapshot

Create a dated baseline from current passing reports and also refresh `latest`:

```bash
python3 scripts/snapshot_canonical_baseline.py \
  --out reports/baselines/canonical_eval_baseline_2026-02-23.json \
  --latest-out reports/baselines/canonical_eval_baseline_latest.json
```

## Environment Note

News ingestion and sentence-transformers retrieval require a compatible Hugging Face stack.

Current repo runtime observed:
- `datasets==4.5.0` needs `huggingface-hub>=0.25.0`
- `sentence-transformers==2.2.2` imports `cached_download` (removed in `huggingface-hub>=0.26`)

Recommended compatibility pin:

```bash
financial-engine_v2/.venv/bin/pip install --upgrade "huggingface-hub>=0.25,<0.26"
```

If sentence-transformers model load fails with `No module named 'pkg_resources'`,
pin setuptools to retain that compatibility shim used by the current accelerate/transformers stack:

```bash
financial-engine_v2/.venv/bin/pip install --upgrade "setuptools<81"
```

Then verify:

```bash
financial-engine_v2/.venv/bin/python - <<'PY'
import datasets, huggingface_hub
from sentence_transformers import SentenceTransformer
print("datasets", datasets.__version__)
print("huggingface_hub", huggingface_hub.__version__)
print("sentence_transformers import OK")
PY
```
