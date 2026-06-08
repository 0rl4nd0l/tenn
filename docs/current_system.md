# Current System

The active system is `financial-engine_v2`.

## Quick Start (after `git pull`)
1. Create/activate your main venv at repo root.
2. Install dependencies:
   - `pip install -r requirements.txt`
   - `python -m playwright install chromium`
3. Run:
   - `python run.py`

## What `python run.py` does
- Delegates to `financial-engine_v2/run.py`
- Runs the configured workflows from one command:
  - `both` (full history + daily MarketIndex)
  - `full_history`
  - `daily_marketindex`
  - `daily_asx_marketwide`

## Core ingestion entrypoints
- `financial-engine_v2/scripts/full_history_ticker_sync.py`
- `financial-engine_v2/scripts/daily_marketindex_action.py`
- `financial-engine_v2/scripts/daily_asx_all_announcements_action.py` (single explicit date)
- `financial-engine_v2/scripts/daily_asx_marketwide_action.py` (lookback window)
- `financial-engine_v2/scripts/asx_enrichment_sweep_action.py` (bulk daily/historical sweep)
- `financial-engine_v2/scripts/run_asx_enrichment_chunked.py` (chunked multi-window runner)
- `financial-engine_v2/scripts/probe_all_system_tickers.py` (DB-known ticker probe)

For operational details (health gate, marker states, recovery workflow, API list), see:
- `financial-engine_v2/README.md`

## Legacy scripts
Old root scripts are archived under:
- `scripts/archive/legacy_root_20260218/`
