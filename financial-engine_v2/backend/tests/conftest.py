"""
conftest.py — ensure the backend package is importable from the tests directory.

The backend `app` package lives one level up from this tests/ directory.
Without this, `from app.services.extraction import ...` fails unless tests
are run with PYTHONPATH=backend or `pip install -e .` is used.
"""
import sys
from pathlib import Path

# Add backend/ to sys.path so `import app` resolves correctly.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
# Add financial-engine_v2/ so shared/* modules resolve consistently as well.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
