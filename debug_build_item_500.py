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
from app.services.extraction_review import build_review_item
from app.models.extractions import ExtractionRun
from app.models.documents import Document

def test_build_item():
    db = SessionLocal()
    try:
        run_id = "38414530-d2d3-4315-b9e2-8b7fd1580bb6"
        run = db.query(ExtractionRun).filter(ExtractionRun.run_id == run_id).first()
        if not run:
            print(f"Run {run_id} not found")
            return
        
        document = db.query(Document).filter(Document.document_id == run.document_id).first()
        if not document:
            print(f"Document {run.document_id} not found")
            return
            
        print(f"Building review item for revenue...")
        item = build_review_item(db, document, run, "revenue")
        print("Success!")
        print(f"Item ID: {item['item_id'] if item else 'None'}")
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    test_build_item()
