import json
from pathlib import Path

from app.services.asx_appendix5b_candidate_artifacts import run_manifest_to_artifact
from app.services.docling_extract import extract_structured


def main() -> None:
    out = Path("reports/agent_jobs/appendix5b_backend_gate_services_restore_v1_20260517")
    pdf = out / "prm_q_2025-12-31_source.pdf"
    structured_path = out / "prm_q_2025-12-31.docling.json"
    manifest_path = out / "prm_manifest.json"
    artifact_path = out / "prm_artifact.json"

    doc = extract_structured(str(pdf), backend="docling", strict_backend=True)
    structured_payload = {
        "extraction_method": doc.extraction_method,
        "page_count": doc.page_count,
        "source_pdf_page_count": doc.source_pdf_page_count,
        "docling_version": doc.docling_version,
        "tables": [
            {
                "page_number": table.page_number,
                "caption": table.caption,
                "rows": table.rows,
                "headers": table.headers,
            }
            for table in doc.tables
        ],
        "sections": doc.sections,
    }
    structured_path.write_text(
        json.dumps(structured_payload, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    manifest = {
        "artifact_type": "appendix5b_manifest_v1",
        "run_id": "appendix5b_backend_gate_services_restore_v1_20260517_prm",
        "canonical_write": False,
        "documents": [
            {
                "document_id": "prm_q_2025-12-31_appendix5b",
                "ticker": "PRM",
                "period_end": "2025-12-31",
                "period_type": "Q",
                "source_file": str(pdf),
                "structured_source_path": str(structured_path),
                "tables": structured_payload["tables"],
                "gold": {
                    "ticker": "PRM",
                    "period_end": "2025-12-31",
                    "period_type": "Q",
                    "metrics": {"operating_cf": -246000},
                    "expected_nulls": [],
                    "tolerances": {"operating_cf": 0.01},
                },
            }
        ],
        "summary": {
            "documents": 1,
            "tables": len(doc.tables),
            "sections": len(doc.sections),
        },
    }
    manifest_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    artifact = run_manifest_to_artifact(
        manifest_path=manifest_path,
        output_path=artifact_path,
        repo_root=Path("."),
    )
    print(
        json.dumps(
            {
                "status": "SUCCESS",
                "structured_path": str(structured_path),
                "manifest_path": str(manifest_path),
                "artifact_path": str(artifact_path),
                "docling_method": doc.extraction_method,
                "page_count": doc.page_count,
                "table_count": len(doc.tables),
                "artifact_summary": artifact.get("summary"),
            },
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
