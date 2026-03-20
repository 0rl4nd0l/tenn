# Environment audit (Cursor Cloud)

Audit date: 2026-03-19

## System

- **OS**: Linux 6.1.147 x86_64
- **Python**: 3.12.3
- **GPU**: `nvidia-smi` not present (CPU-only runtime)

## Required system tools

- **Poppler** (`pdftotext`): installed (Poppler 24.02.0)
- **Tesseract** (`tesseract`): installed (5.3.4)
- **Ghostscript** (`gs`): installed (10.02.1)
- **Java** (`java`): installed (OpenJDK 21)

## Virtual environments (strict isolation)

### Main runtime: `.venv_main/`

Purpose: non-Docling extractors and glue code.

Installed via pip:

- `pdfminer.six`
- `pymupdf`
- `camelot-py`
- `tabula-py`
- `numpy`, `pandas`
- `pytesseract`

### Docling runtime: `.venv_docling/`

Purpose: Docling-only execution via subprocess (no in-process Docling imports).

Installed via pip:

- `docling`

## Reproducibility

- `requirements.lock.txt` contains `pip freeze` output for both venvs.

