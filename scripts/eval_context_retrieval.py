#!/usr/bin/env python3
import argparse
import importlib.util
import json
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


def load_context_module(script_path: Path):
    spec = importlib.util.spec_from_file_location("build_qualitative_context_db", str(script_path))
    if spec is None or spec.loader is None:
        raise RuntimeError(f"failed to load module: {script_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_cases(path: Path) -> List[Dict[str, Any]]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(data, dict):
        cases = data.get("cases")
    else:
        cases = data
    if not isinstance(cases, list):
        raise RuntimeError("Eval file must be a list or an object with a 'cases' list")
    out: List[Dict[str, Any]] = []
    for idx, row in enumerate(cases, start=1):
        if not isinstance(row, dict):
            continue
        if not str(row.get("query", "")).strip():
            continue
        row.setdefault("id", f"case_{idx:03d}")
        out.append(row)
    return out


def row_matches(row: Dict[str, Any], matcher: Dict[str, Any]) -> bool:
    for key in ("company", "corpus", "doc_type", "section", "source"):
        if key in matcher and str(row.get(key, "")) != str(matcher.get(key, "")):
            return False

    wanted_ticker = str(matcher.get("ticker", "")).strip().upper()
    if wanted_ticker:
        row_ticker = str(row.get("ticker", ""))
        if "|" in row_ticker:
            parts = [p.strip().upper() for p in row_ticker.split("|") if p.strip()]
        else:
            parts = [p.strip().upper() for p in re.split(r"[,\s;/]+", row_ticker) if p.strip()]
        if wanted_ticker not in set(parts):
            return False

    file_contains = str(matcher.get("file_contains", "")).strip()
    if file_contains and file_contains.lower() not in str(row.get("file", "")).lower():
        return False

    text_contains = str(matcher.get("text_contains", "")).strip()
    if text_contains and text_contains.lower() not in str(row.get("text", "")).lower():
        return False

    return True


def first_expected_rank(
    rows: List[Tuple[float, Dict[str, Any]]],
    expect_any: List[Dict[str, Any]],
) -> Optional[int]:
    for rank, (_score, row) in enumerate(rows, start=1):
        for matcher in expect_any:
            if row_matches(row, matcher):
                return rank
    return None


def evaluate_case(mod, case: Dict[str, Any], args) -> Dict[str, Any]:
    filters = dict(case.get("filters") or {})
    top_k = int(case.get("top_k") or args.top_k)
    db_path = Path(str(case.get("db_path") or args.db_path)).expanduser()
    if not db_path.exists():
        raise RuntimeError(f"DB not found: {db_path}")

    rows = mod.query_sqlite(
        db_path=db_path,
        query=str(case["query"]),
        backend=args.embed_backend,
        model_name=args.embed_model,
        ollama_endpoint=args.ollama_endpoint,
        hash_dim=args.hash_dim,
        st_device=args.st_device,
        st_batch_size=args.st_batch_size,
        company=str(filters.get("company", "")),
        corpus_filter=str(filters.get("corpus", "")),
        doc_type_filter=str(filters.get("doc_type", "")),
        date_from=str(filters.get("date_from", "")),
        date_to=str(filters.get("date_to", "")),
        top_k=top_k,
        ticker_filter=str(filters.get("ticker", "")),
        source_filter=str(filters.get("source", "")),
        exclude_corpus_filter=str(filters.get("exclude_corpus", "")),
    )

    expect_any = case.get("expect_any") or []
    rank = None
    has_expect = bool(expect_any)
    hit = bool(rows)

    if has_expect:
        typed_expect = [m for m in expect_any if isinstance(m, dict)]
        rank = first_expected_rank(rows, typed_expect) if typed_expect else None
        hit = rank is not None

    preview = {}
    if rows:
        score, row = rows[0]
        preview = {
            "score": round(float(score), 4),
            "company": str(row.get("company", "")),
            "corpus": str(row.get("corpus", "")),
            "doc_type": str(row.get("doc_type", "")),
            "source": str(row.get("source", "")),
            "ticker": str(row.get("ticker", "")),
            "file": str(row.get("file", "")),
            "section": str(row.get("section", "")),
        }

    return {
        "id": str(case.get("id", "")),
        "query": str(case["query"]),
        "db_path": str(db_path),
        "top_k": top_k,
        "filters": filters,
        "has_expectations": has_expect,
        "hit": hit,
        "first_match_rank": rank,
        "result_count": len(rows),
        "top_result": preview,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="Evaluate qualitative context retrieval against expected matches")
    ap.add_argument("--eval-file", required=True, help="JSON file containing eval cases")
    ap.add_argument("--db-path", default="", help="Default sqlite DB path if a case omits db_path")
    ap.add_argument("--embed-backend", choices=["sentence-transformers", "ollama", "hash"], default="hash")
    ap.add_argument("--embed-model", default="bge-large-en-v1.5")
    ap.add_argument("--ollama-endpoint", default="http://127.0.0.1:11434")
    ap.add_argument("--hash-dim", type=int, default=384)
    ap.add_argument("--st-device", choices=["auto", "cpu", "cuda"], default="auto")
    ap.add_argument("--st-batch-size", type=int, default=16)
    ap.add_argument("--top-k", type=int, default=8)
    ap.add_argument("--out-json", default="", help="Optional output report path")
    args = ap.parse_args()

    eval_path = Path(args.eval_file).expanduser().resolve()
    if not eval_path.exists():
        print(f"Eval file not found: {eval_path}", file=sys.stderr)
        return 2

    script_path = Path(__file__).resolve().parent / "build_qualitative_context_db.py"
    mod = load_context_module(script_path)
    cases = load_cases(eval_path)
    if not cases:
        print("No valid cases found in eval file.", file=sys.stderr)
        return 2

    results: List[Dict[str, Any]] = []
    failures = 0
    for case in cases:
        try:
            outcome = evaluate_case(mod, case, args)
            results.append(outcome)
        except Exception as exc:
            failures += 1
            results.append(
                {
                    "id": str(case.get("id", "")),
                    "query": str(case.get("query", "")),
                    "error": str(exc),
                    "has_expectations": bool(case.get("expect_any")),
                    "hit": False,
                    "first_match_rank": None,
                }
            )

    scored = [r for r in results if r.get("has_expectations")]
    hit_count = sum(1 for r in scored if r.get("hit"))
    mrr = 0.0
    if scored:
        mrr = sum((1.0 / float(r["first_match_rank"])) if r.get("first_match_rank") else 0.0 for r in scored) / len(scored)

    print(f"cases={len(results)} scored={len(scored)} failures={failures}")
    if scored:
        print(f"hit@k={hit_count}/{len(scored)} ({(100.0 * hit_count / len(scored)):.1f}%) mrr={mrr:.4f}")
    for r in results:
        if r.get("error"):
            print(f"[ERROR] {r.get('id')}: {r.get('error')}")
            continue
        status = "PASS" if r.get("hit") else "FAIL"
        rank = r.get("first_match_rank")
        rank_txt = f" rank={rank}" if rank else ""
        top = r.get("top_result") or {}
        top_txt = ""
        if top:
            top_txt = f" top={Path(str(top.get('file', ''))).name} ({top.get('company','')}/{top.get('doc_type','')})"
        print(f"[{status}] {r.get('id')} hit@{r.get('top_k')}{rank_txt}{top_txt}")

    report = {
        "summary": {
            "cases": len(results),
            "scored": len(scored),
            "failures": failures,
            "hits": hit_count,
            "hit_rate": (float(hit_count) / len(scored)) if scored else None,
            "hit_at_k": (float(hit_count) / len(scored)) if scored else None,
            "mrr": mrr if scored else None,
        },
        "results": results,
    }

    if args.out_json:
        out_path = Path(args.out_json).expanduser()
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
        print(f"report_json={out_path}")

    return 0 if failures == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
