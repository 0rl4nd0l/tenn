#!/usr/bin/env python3
"""Embedding quality evaluation using Anthropic Claude as judge.

Queries Qdrant for test cases, retrieves chunks, and asks Claude to evaluate:
1. Relevance: Are the retrieved chunks actually relevant to the query?
2. Narrative enrichment: Do announcement_type/section_heading add useful context?
3. Coverage: Are important document types represented?

Usage:
    source .env && PYTHONPATH=backend python scripts/eval_embedding_quality.py
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

from dotenv import load_dotenv
load_dotenv(Path(__file__).resolve().parent.parent / ".env")

# Override Docker-internal URLs with localhost for direct script execution
os.environ.setdefault("QDRANT_URL", "http://127.0.0.1:6333")
if "qdrant:" in os.getenv("QDRANT_URL", ""):
    os.environ["QDRANT_URL"] = "http://127.0.0.1:6333"

import httpx
import anthropic
from qdrant_client import QdrantClient

QDRANT_URL = os.getenv("QDRANT_URL", "http://127.0.0.1:6333")
OLLAMA_URL = "http://127.0.0.1:11434"
EMBED_MODEL = "nomic-embed-text"
COLLECTION = "asx_docs"

# Test queries spanning different document types and tickers
TEST_QUERIES = [
    {"query": "What are BHP's key financial risks?", "ticker": "BHP", "expected_types": ["financial_performance"]},
    {"query": "BHP director appointments and board changes", "ticker": "BHP", "expected_types": ["management_and_governance"]},
    {"query": "BHP substantial holder changes", "ticker": "BHP", "expected_types": ["ownership_and_holders"]},
    {"query": "CBA capital structure and securities", "ticker": "CBA", "expected_types": ["capital_structure_securities"]},
    {"query": "RIO investor presentation strategy", "ticker": "RIO", "expected_types": ["investor_communications", "financial_performance"]},
    {"query": "BHP operational update production", "ticker": "BHP", "expected_types": ["operations_projects", "financial_performance"]},
]


def embed_query(query: str) -> list[float]:
    """Embed via Ollama directly (bypasses llama-server probe)."""
    resp = httpx.post(
        f"{OLLAMA_URL}/api/embeddings",
        json={"model": EMBED_MODEL, "prompt": query},
        timeout=30.0,
    )
    resp.raise_for_status()
    return resp.json()["embedding"]


def search_qdrant(qc: QdrantClient, query_vector: list[float], ticker: str, top_k: int = 5) -> list[dict]:
    from qdrant_client.models import Filter, FieldCondition, MatchValue
    results = qc.search(
        collection_name=COLLECTION,
        query_vector=query_vector,
        query_filter=Filter(must=[FieldCondition(key="ticker", match=MatchValue(value=ticker))]),
        limit=top_k,
        with_payload=True,
    )
    hits = []
    for r in results:
        p = r.payload or {}
        hits.append({
            "score": round(r.score, 4),
            "ticker": p.get("ticker"),
            "title": (p.get("title") or "")[:80],
            "announcement_type": p.get("announcement_type"),
            "section_heading": (p.get("section_heading") or "")[:60],
            "text": (p.get("text") or "")[:500],
            "doc_class": p.get("doc_class"),
            "doc_subtype": p.get("doc_subtype"),
        })
    return hits


def evaluate_with_claude(client: anthropic.Anthropic, query: str, expected_types: list[str], hits: list[dict]) -> dict:
    hits_json = json.dumps(hits, indent=2, ensure_ascii=False)
    prompt = f"""You are evaluating the quality of a vector search retrieval system for ASX financial documents.

Query: "{query}"
Expected document types: {expected_types}

Retrieved chunks (top 5):
{hits_json}

Evaluate on these dimensions (score 1-5 each):

1. **relevance**: Are the retrieved chunks actually relevant to the query? Do they contain information that helps answer it?
2. **type_accuracy**: Do the announcement_type labels match what you'd expect? Are financial docs labelled "financial_performance", governance docs labelled "management_and_governance", etc.?
3. **section_value**: Does the section_heading field provide useful context about where in the document this chunk came from? Or is it generic/unhelpful (e.g., just "For personal use only")?
4. **coverage**: Are the expected document types represented in the results? Or are irrelevant document types dominating?
5. **text_quality**: Is the chunk text clean and readable, or is it garbled/tabular noise?

Return ONLY valid JSON:
{{"relevance": 1-5, "type_accuracy": 1-5, "section_value": 1-5, "coverage": 1-5, "text_quality": 1-5, "overall": 1-5, "notes": "brief explanation of strengths and weaknesses"}}"""

    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=500,
        messages=[{"role": "user", "content": prompt}],
    )
    text = response.content[0].text.strip()
    if text.startswith("```"):
        text = "\n".join(l for l in text.splitlines() if not l.startswith("```")).strip()
    return json.loads(text)


def main():
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        print("ERROR: ANTHROPIC_API_KEY not set. Source .env first.")
        sys.exit(1)

    claude = anthropic.Anthropic(api_key=api_key)
    qc = QdrantClient(url=QDRANT_URL, timeout=30)

    print(f"{'='*70}")
    print(f"Embedding Quality Evaluation — {len(TEST_QUERIES)} test queries")
    print(f"Collection: {COLLECTION} @ {QDRANT_URL}")
    print(f"Judge: Claude Sonnet 4")
    print(f"{'='*70}\n")

    results = []
    for i, tc in enumerate(TEST_QUERIES):
        print(f"[{i+1}/{len(TEST_QUERIES)}] {tc['query'][:60]}...")

        # Embed and search
        vec = embed_query(tc["query"])
        hits = search_qdrant(qc, vec, tc["ticker"])

        enriched = sum(1 for h in hits if h.get("announcement_type"))
        print(f"  Retrieved {len(hits)} hits ({enriched} with announcement_type)")

        # Judge with Claude
        try:
            evaluation = evaluate_with_claude(claude, tc["query"], tc["expected_types"], hits)
            results.append({"query": tc["query"], "ticker": tc["ticker"], **evaluation})
            print(f"  Scores: rel={evaluation['relevance']} type={evaluation['type_accuracy']} "
                  f"section={evaluation['section_value']} cover={evaluation['coverage']} "
                  f"text={evaluation['text_quality']} overall={evaluation['overall']}")
            print(f"  Notes: {evaluation['notes'][:120]}")
        except Exception as e:
            print(f"  ERROR: {e}")
            results.append({"query": tc["query"], "ticker": tc["ticker"], "error": str(e)})
        print()

    # Summary
    scored = [r for r in results if "overall" in r]
    if scored:
        def avg(field: str) -> float:
            return sum(r[field] for r in scored) / len(scored)
        print(f"{'='*70}")
        print(f"SUMMARY ({len(scored)}/{len(TEST_QUERIES)} evaluated)")
        print(f"  Relevance:      {avg('relevance'):.1f}/5")
        print(f"  Type accuracy:  {avg('type_accuracy'):.1f}/5")
        print(f"  Section value:  {avg('section_value'):.1f}/5")
        print(f"  Coverage:       {avg('coverage'):.1f}/5")
        print(f"  Text quality:   {avg('text_quality'):.1f}/5")
        print(f"  Overall:        {avg('overall'):.1f}/5")
        print(f"{'='*70}")

    # Save detailed results
    out_path = Path("reports/embedding_quality_eval.json")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(results, indent=2, ensure_ascii=False))
    print(f"\nDetailed results: {out_path}")


if __name__ == "__main__":
    main()
