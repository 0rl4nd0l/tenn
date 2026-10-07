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
- Delegates to `financial-engine_v2/run.py`.
- Default `CONFIG["workflow"]` is `both`: ticker full-history, then the daily MarketIndex scrape.
- `daily_asx_marketwide` is a separate workflow. It runs `scripts/daily_asx_marketwide_action.py`. The cockpit action with that same id runs `scripts/daily_asx_all_announcements_action.py` instead.
- Command shapes, fallbacks, and exit rules: `financial-engine_v2/README.md` (Production CLIs).

## Legacy scripts
Old root scripts are archived under:
- `scripts/archive/legacy_root_20260218/`
