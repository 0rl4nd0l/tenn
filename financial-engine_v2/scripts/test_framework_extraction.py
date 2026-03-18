from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import yaml

import embed_methodology_chunks
import extract_investment_frameworks


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row) + "\n")


class EmbedMethodologyChunksTests(unittest.TestCase):
    def test_resolve_semantic_chunks_path_prefers_workspace_reports_output(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            workspace_root = tmp_path / "workspace"
            repo_root = workspace_root / "financial-engine_v2"
            semantic_chunks = workspace_root / "reports" / "investment_preprocess" / "semantic_chunks.jsonl"
            _write_jsonl(
                semantic_chunks,
                [
                    {
                        "chunk_id": "chunk-a",
                        "doc_id": "doc-1",
                        "chunk_index": 0,
                        "text": "Valuation uses discounted cash flow.",
                    }
                ],
            )

            requested = repo_root / "reports" / "investment_preprocess" / "semantic_chunks.jsonl"
            with mock.patch.object(embed_methodology_chunks, "WORKSPACE_ROOT", workspace_root), mock.patch.object(
                embed_methodology_chunks, "REPO_ROOT", repo_root
            ):
                resolved = embed_methodology_chunks._resolve_semantic_chunks_path(requested)

            self.assertEqual(resolved, semantic_chunks.resolve())

    def test_run_batches_embeddings_and_preserves_qdrant_payload(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            semantic_chunks = tmp_path / "semantic_chunks.jsonl"
            out_dir = tmp_path / "embeddings"
            _write_jsonl(
                semantic_chunks,
                [
                    {
                        "chunk_id": "chunk-a",
                        "doc_id": "doc-1",
                        "chunk_index": 0,
                        "text": "Valuation uses discounted cash flow.",
                        "source_file_name": "valuation_notes.pdf",
                        "page_start": 1,
                        "page_end": 1,
                        "framework_family": "valuation",
                        "section": "overview",
                    },
                    {
                        "chunk_id": "chunk-b",
                        "doc_id": "doc-1",
                        "chunk_index": 1,
                        "text": "Technical analysis uses support and resistance.",
                        "source_file_name": "valuation_notes.pdf",
                        "page_start": 2,
                        "page_end": 2,
                        "framework_family": "technical_analysis",
                        "section": "signals",
                    },
                    {
                        "chunk_id": "chunk-c",
                        "doc_id": "doc-2",
                        "chunk_index": 0,
                        "text": "Sector rotation tracks macro cycles.",
                        "source_file_name": "sector_rotation.pdf",
                        "page_start": 1,
                        "page_end": 3,
                        "framework_family": "sector_rotation",
                        "section": "summary",
                    },
                ],
            )

            batch_calls: list[list[str]] = []
            ensured: list[tuple[str, int]] = []
            upserted: list[dict] = []

            def fake_embed_batch(texts, **kwargs):
                batch_calls.append(list(texts))
                return [[float(index), float(index + 1)] for index, _ in enumerate(texts, start=1)]

            def fake_ensure_collection(client, collection, dim):
                ensured.append((collection, dim))

            def fake_upsert_points(client, collection, points):
                upserted.extend(points)

            summary = embed_methodology_chunks.run(
                semantic_chunks_path=semantic_chunks,
                out_dir=out_dir,
                batch_size=2,
                qdrant_url="http://localhost:6333",
                ollama_url="http://localhost:11434",
                embed_model="nomic-embed-text",
                embed_batch_fn=fake_embed_batch,
                qdrant_factory=lambda url: {"url": url},
                ensure_collection_fn=fake_ensure_collection,
                upsert_points_fn=fake_upsert_points,
            )

            self.assertEqual(summary["status"], "success")
            self.assertEqual(summary["chunks_embedded"], 3)
            self.assertEqual(batch_calls, [[
                "Valuation uses discounted cash flow.",
                "Technical analysis uses support and resistance.",
            ], [
                "Sector rotation tracks macro cycles.",
            ]])
            self.assertTrue(ensured)
            self.assertEqual(ensured[0], ("methodology_chunks", 2))
            self.assertEqual(len(upserted), 3)
            self.assertEqual(
                upserted[0]["payload"],
                {
                    "logical_point_id": "doc-1:0",
                    "chunk_id": "chunk-a",
                    "source_file": "valuation_notes.pdf",
                    "page_start": 1,
                    "page_end": 1,
                    "framework_family": "valuation",
                    "section": "overview",
                },
            )
            self.assertEqual(
                upserted[0]["id"],
                embed_methodology_chunks._qdrant_point_id("doc-1:0"),
            )
            manifest_rows = [
                json.loads(line)
                for line in (out_dir / "embedding_manifest.jsonl").read_text(encoding="utf-8").splitlines()
                if line.strip()
            ]
            self.assertEqual(len(manifest_rows), 3)
            self.assertEqual(manifest_rows[0]["point_id"], "doc-1:0")
            self.assertEqual(
                manifest_rows[0]["qdrant_point_id"],
                embed_methodology_chunks._qdrant_point_id("doc-1:0"),
            )


class ExtractInvestmentFrameworksTests(unittest.TestCase):
    def test_resolve_semantic_chunks_path_prefers_workspace_reports_output(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            workspace_root = tmp_path / "workspace"
            repo_root = workspace_root / "financial-engine_v2"
            semantic_chunks = workspace_root / "reports" / "investment_preprocess" / "semantic_chunks.jsonl"
            _write_jsonl(
                semantic_chunks,
                [
                    {
                        "chunk_id": "chunk-a",
                        "doc_id": "doc-1",
                        "chunk_index": 0,
                        "text": "Discounted cash flow values cash generation.",
                    }
                ],
            )

            requested = repo_root / "reports" / "investment_preprocess" / "semantic_chunks.jsonl"
            with mock.patch.object(
                extract_investment_frameworks, "WORKSPACE_ROOT", workspace_root
            ), mock.patch.object(extract_investment_frameworks, "REPO_ROOT", repo_root):
                resolved = extract_investment_frameworks._resolve_semantic_chunks_path(requested)

            self.assertEqual(resolved, semantic_chunks.resolve())

    def test_run_validates_schema_before_writing_outputs(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            cleaned_text_dir = tmp_path / "cleaned_text"
            cleaned_text_dir.mkdir(parents=True)
            (cleaned_text_dir / "doc-1.txt").write_text(
                "Discounted cash flow values cash generation. Margin of safety matters. "
                "Watch free cash flow, return on capital, and downside risk.",
                encoding="utf-8",
            )

            semantic_chunks = tmp_path / "semantic_chunks.jsonl"
            _write_jsonl(
                semantic_chunks,
                [
                    {
                        "chunk_id": "chunk-a",
                        "doc_id": "doc-1",
                        "chunk_index": 0,
                        "text": "Discounted cash flow values cash generation and return on capital.",
                        "source_file_name": "valuation_notes.pdf",
                        "source_path": "/tmp/valuation_notes.pdf",
                        "page_start": 1,
                        "page_end": 1,
                        "section": "overview",
                    },
                    {
                        "chunk_id": "chunk-b",
                        "doc_id": "doc-1",
                        "chunk_index": 1,
                        "text": "Margin of safety and downside risk shape decision rules.",
                        "source_file_name": "valuation_notes.pdf",
                        "source_path": "/tmp/valuation_notes.pdf",
                        "page_start": 2,
                        "page_end": 2,
                        "section": "risk",
                    },
                ],
            )

            framework_schema = tmp_path / "framework_schema.json"
            framework_schema.write_text(
                json.dumps(
                    {
                        "type": "object",
                        "required": [
                            "framework_id",
                            "framework_family",
                            "title",
                            "principles",
                            "signals_or_indicators",
                            "decision_rules",
                            "risk_notes",
                            "source_pages",
                            "evidence_chunk_ids",
                        ],
                        "properties": {
                            "framework_id": {"type": "string", "minLength": 1},
                            "framework_family": {
                                "type": "string",
                                "enum": ["valuation", "technical_analysis"],
                            },
                            "title": {"type": "string", "minLength": 1},
                            "principles": {"type": "array", "items": {"type": "string"}, "minItems": 1},
                            "signals_or_indicators": {"type": "array", "items": {"type": "string"}},
                            "decision_rules": {"type": "array", "items": {"type": "string"}},
                            "risk_notes": {"type": "array", "items": {"type": "string"}, "minItems": 1},
                            "source_pages": {"type": "array", "items": {"type": "integer"}},
                            "evidence_chunk_ids": {
                                "type": "array",
                                "items": {"type": "string"},
                                "minItems": 1,
                            },
                        },
                        "additionalProperties": False,
                    }
                ),
                encoding="utf-8",
            )

            framework_taxonomy = tmp_path / "framework_taxonomy.yaml"
            framework_taxonomy.write_text(
                yaml.safe_dump({"families": ["valuation", "technical_analysis"]}),
                encoding="utf-8",
            )

            def fake_generate_json(prompt, **kwargs):
                self.assertIn("valuation", prompt)
                return {
                    "frameworks": [
                        {
                            "framework_family": "valuation",
                            "title": "Discounted Cash Flow",
                            "principles": ["Value future cash generation conservatively"],
                            "signals_or_indicators": ["Free cash flow", "Return on capital"],
                            "decision_rules": ["Require margin of safety before entry"],
                            "risk_notes": ["Downside risk rises when assumptions are aggressive"],
                        },
                        {
                            "framework_family": "valuation",
                            "title": "Broken Framework",
                            "principles": ["Uses cash generation"],
                            "signals_or_indicators": ["Free cash flow"],
                            "decision_rules": ["Compare value to price"],
                            "risk_notes": [],
                        },
                    ]
                }

            summary = extract_investment_frameworks.run(
                semantic_chunks_path=semantic_chunks,
                framework_schema_path=framework_schema,
                framework_taxonomy_path=framework_taxonomy,
                cleaned_text_dir=cleaned_text_dir,
                out_dir=tmp_path / "framework_records",
                generate_json_fn=fake_generate_json,
            )

            self.assertEqual(summary["status"], "success")
            self.assertEqual(summary["frameworks_written"], 1)
            self.assertEqual(summary["frameworks_rejected"], 1)

            jsonl_rows = [
                json.loads(line)
                for line in (tmp_path / "framework_records" / "frameworks.jsonl").read_text(encoding="utf-8").splitlines()
                if line.strip()
            ]
            self.assertEqual(len(jsonl_rows), 1)
            self.assertEqual(jsonl_rows[0]["framework_family"], "valuation")
            self.assertTrue(jsonl_rows[0]["evidence_chunk_ids"])
            self.assertEqual(jsonl_rows[0]["source_pages"], [1, 2])

            yaml_rows = yaml.safe_load((tmp_path / "framework_records" / "frameworks.yaml").read_text(encoding="utf-8"))
            self.assertEqual(len(yaml_rows), 1)
            self.assertEqual(yaml_rows[0]["title"], "Discounted Cash Flow")


if __name__ == "__main__":
    unittest.main()
