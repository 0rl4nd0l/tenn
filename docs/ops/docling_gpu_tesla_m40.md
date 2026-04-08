# Docling on Tesla M40 (sm_52) — GPU default

> **Status (2026-04):** Docling is the default structured extraction backend (`EXTRACTION_BACKEND=docling`).
> Use this runbook when enabling/maintaining Docling GPU execution on Tesla M40. For a
> faster local override path, set `EXTRACTION_BACKEND=pymupdf`.

The Tesla M40 has **CUDA compute capability 5.2** (Maxwell). Current **PyTorch 2.10** wheels are built for **sm_70 and above** only, so you get:

```text
CUDA error: no kernel image is available for execution on the device
```

The scripts in this repo are GPU-first by default. Use `--cpu` only as fallback.

You have two practical options.

## Option 1: Use GPU (default)

Use a CUDA-compatible PyTorch stack in a dedicated venv:

```bash
cd /home/l4nd0/tenn
python3 -m venv .venv-docling-gpu
source .venv-docling-gpu/bin/activate

# Try PyTorch 2.5 with CUDA 12.1 (some sources suggest cu121/cu124 still had Maxwell in older 2.x)
pip install torch==2.5.0 torchvision==0.20.0 torchaudio==2.5.0 --index-url https://download.pytorch.org/whl/cu121
pip install docling pandas

python3 scripts/docling_export_tables.py --pdf /path/to/file.pdf --out-dir reports/docling_tables
```

If you still see “no kernel image”, try **CUDA 11.8**:

```bash
pip install torch==2.2.2 torchvision==0.17.2 torchaudio==2.2.2 --index-url https://download.pytorch.org/whl/cu118
pip install docling pandas
```

## Option 2: CPU fallback

No PyTorch reinstall required. Force Docling to use CPU:

```bash
python3 scripts/docling_export_tables.py --cpu --pdf /path/to/file.pdf --out-dir reports/docling_tables
```

Slower but reliable. For occasional table export, this is usually enough.

If GPU still fails after these wheel combinations, use **Option 2 (`--cpu`)** or build PyTorch from source with `TORCH_CUDA_ARCH_LIST="5.2"` (advanced).

**NumPy 2.x:** PyTorch 2.2.2 was built for NumPy 1.x. If you see `RuntimeError: Numpy is not available` or "Failed to initialize NumPy: _ARRAY_API not found", downgrade with `pip install "numpy<2"` and reinstall docling/pandas if needed. The file `docs/ops/requirements-docling-gpu-m40.txt` pins `numpy<2` for this reason.

## Integrated extraction (extract_financial_metrics)

Docling is now integrated into the main financial metrics pipeline. Use `--extractor docling`:

```bash
# Single company with Docling (use .venv-docling-gpu)
source .venv-docling-gpu/bin/activate
python3 scripts/extract_financial_metrics.py \
  --pdf-dir financial-engine_v2/data/asx/docs/10X \
  --out-json reports/financial_metrics_10x_docling.json \
  --no-sqlite --extractor docling
```

Compare Docling vs pdftotext accuracy across tickers:

```bash
python3 scripts/compare_docling_accuracy.py --tickers 10X 29M
# or: --max-tickers 5
```

Document quarantine is enabled by default in `extract_financial_metrics.py` via
`financial-engine_v2/config/document_quarantine_rules.json` (currently includes
29M EMR/Golden Grove subsidiary exclusions). To bypass for a one-off review:

```bash
python3 scripts/extract_financial_metrics.py ... --no-quarantine-rules
```

Optional OCR for scanned PDFs (slower):

```bash
python3 scripts/extract_financial_metrics.py \
  --pdf-dir financial-engine_v2/data/asx/docs/10X \
  --out-json reports/financial_metrics_10x_docling.json \
  --no-sqlite --extractor docling --docling-ocr
```

Report written to `reports/docling_accuracy_comparison/comparison_report.json`.

## Summary

| Goal              | Action                                      |
|-------------------|---------------------------------------------|
| Default path      | Use GPU (no `--cpu` flag).                  |
| If GPU wheel fails| Install older torch in dedicated venv.      |
| Fallback          | Use `--cpu` or build PyTorch from source.   |
