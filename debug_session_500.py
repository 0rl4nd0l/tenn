import os
import sys
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path("/mnt/sdb2/home/l4nd0/tenn/financial-engine_v2").resolve()
sys.path.append(str(PROJECT_ROOT))
sys.path.append(str(PROJECT_ROOT / "backend"))

# Mock environment
os.environ["DATABASE_URL"] = "postgresql://fe:fe@localhost:5432/fe"

from app.core.db import SessionLocal
from app.services.extraction_review import create_review_session

def test_session():
    db = SessionLocal()
    try:
        run_ids = ["38414530-d2d3-4315-b9e2-8b7fd1580bb6"]
        print(f"Creating session for {run_ids}...")
        session = create_review_session(db, [], run_ids=run_ids)
        print("Success!")
        print(f"Session ID: {session['session_id']}")
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    test_session()
