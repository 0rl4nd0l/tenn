#!/usr/bin/env python3
"""Stage 4 framework extraction for methodology documents."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Iterable, Mapping

import yaml


REPO_ROOT = Path(__file__).resolve().parents[1]
WORKSPACE_ROOT = REPO_ROOT.parent
BACKEND_ROOT = REPO_ROOT / "backend"
DEFAULT_SEMANTIC_CHUNKS = WORKSPACE_ROOT / "reports" / "investment_preprocess" / "semantic_chunks.jsonl"
TOKEN_RE = re.compile(r"[A-Za-z0-9_]+")
DEFAULT_MAX_PROMPT_CHARS = 18000
DEFAULT_LLM_URL = "http://127.0.0.1:8080"
DEFAULT_LLM_MODEL = "local-model"


def _ensure_backend_path() -> None:
    if str(BACKEND_ROOT) not in sys.path:
        sys.path.insert(0, str(BACKEND_ROOT))


def _load_backend_extraction_runtime() -> dict[str, Any]:
    _ensure_backend_path()
    try:
        import httpx

        from app.services.extraction import EXTRACTOR_VERSION
        from app.services.llamacpp_runtime import generate_json_llamacpp
    except ImportError as exc:
        raise RuntimeError(
            "Extraction runtime dependencies are unavailable. "
            "Use the financial-engine_v2 environment with backend dependencies installed."
        ) from exc

    return {
        "httpx": httpx,
        "EXTRACTOR_VERSION": f"{EXTRACTOR_VERSION}+llamacpp_openai",
        "generate_json_llamacpp": generate_json_llamacpp,
    }


@dataclass(frozen=True)
class SourceChunk:
    chunk_id: str
    doc_id: str
    chunk_index: int
    text: str
    source_file: str
    source_path: str
    page_start: int | None
    page_end: int | None
    section: str


@dataclass(frozen=True)
class DocumentContext:
    doc_id: str
    source_file: str
    source_path: str
    chunks: tuple[SourceChunk, ...]


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for lineno, raw_line in enumerate(handle, start=1):
            text = raw_line.strip()
            if not text:
                continue
            payload = json.loads(text)
            if not isinstance(payload, dict):
                raise RuntimeError(f"JSONL row {lineno} is not a JSON object")
            rows.append(payload)
    return rows


def _resolve_semantic_chunks_path(path: Path) -> Path:
    requested = path.expanduser().resolve()
    candidates = [requested]

    if requested.name == "semantic_chunks.jsonl":
        candidates.extend(
            [
                WORKSPACE_ROOT / "reports" / "investment_preprocess" / "semantic_chunks.jsonl",
                REPO_ROOT / "reports" / "investment_preprocess" / "semantic_chunks.jsonl",
            ]
        )

    checked: list[Path] = []
    seen = set()
    for candidate in candidates:
        resolved = candidate.expanduser().resolve()
        key = str(resolved)
        if key in seen:
            continue
        seen.add(key)
        checked.append(resolved)
        if resolved.exists():
            return resolved

    checked_str = "\n".join(f"- {candidate}" for candidate in checked)
    raise FileNotFoundError(
        "semantic chunks file not found. Checked:\n"
        f"{checked_str}\n"
        "Run stage 1+2 first with `preprocess_investment_pdfs.py`, or pass the correct `--semantic-chunks` path."
    )


def _coerce_optional_int(value: Any) -> int | None:
    if value in (None, ""):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _normalize_text(value: Any) -> str:
    text = str(value or "").strip()
    return re.sub(r"\s+", " ", text)


def _normalize_family(value: Any) -> str:
    text = _normalize_text(value).lower()
    text = re.sub(r"[^a-z0-9]+", "_", text)
    return re.sub(r"_+", "_", text).strip("_")


def _normalize_string_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        items = [part.strip() for part in re.split(r"[;\n]+", value) if part.strip()]
    elif isinstance(value, list):
        items = [_normalize_text(item) for item in value if _normalize_text(item)]
    else:
        items = [_normalize_text(value)] if _normalize_text(value) else []

    deduped: list[str] = []
    seen = set()
    for item in items:
        key = item.casefold()
        if key in seen:
            continue
        seen.add(key)
        deduped.append(item)
    return deduped


def _load_taxonomy_families(path: Path) -> list[str]:
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    values: list[str] = []
    if isinstance(payload, dict):
        if isinstance(payload.get("families"), list):
            values = [str(item) for item in payload["families"]]
        elif isinstance(payload.get("families"), Mapping):
            values = [str(key) for key in payload["families"].keys()]
        elif isinstance(payload.get("framework_families"), list):
            values = [str(item) for item in payload["framework_families"]]
        elif isinstance(payload.get("framework_families"), Mapping):
            values = [str(key) for key in payload["framework_families"].keys()]
        else:
            values = [str(key) for key in payload.keys()]
    elif isinstance(payload, list):
        values = [str(item) for item in payload]

    families = [_normalize_family(item) for item in values if _normalize_family(item)]
    deduped: list[str] = []
    seen = set()
    for family in families:
        if family in seen:
            continue
        seen.add(family)
        deduped.append(family)
    if not deduped:
        raise RuntimeError(f"taxonomy file did not yield any framework families: {path}")
    return deduped


def _resolve_schema_ref(root_schema: Mapping[str, Any], ref: str) -> Mapping[str, Any]:
    if not ref.startswith("#/"):
        raise RuntimeError(f"unsupported schema ref: {ref}")
    node: Any = root_schema
    for raw_part in ref[2:].split("/"):
        part = raw_part.replace("~1", "/").replace("~0", "~")
        if not isinstance(node, Mapping) or part not in node:
            raise RuntimeError(f"invalid schema ref: {ref}")
        node = node[part]
    if not isinstance(node, Mapping):
        raise RuntimeError(f"schema ref did not resolve to an object: {ref}")
    return node


def _schema_matches_type(value: Any, type_name: str) -> bool:
    if type_name == "object":
        return isinstance(value, dict)
    if type_name == "array":
        return isinstance(value, list)
    if type_name == "string":
        return isinstance(value, str)
    if type_name == "integer":
        return isinstance(value, int) and not isinstance(value, bool)
    if type_name == "number":
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    if type_name == "boolean":
        return isinstance(value, bool)
    if type_name == "null":
        return value is None
    return True


def _schema_allows_type(schema: Mapping[str, Any], type_name: str) -> bool:
    expected = schema.get("type")
    if expected is None:
        return type_name in {"object", "array"} and (
            ("properties" in schema and type_name == "object") or ("items" in schema and type_name == "array")
        )
    if isinstance(expected, list):
        return type_name in expected
    return expected == type_name


def _schema_errors(
    value: Any,
    schema: Mapping[str, Any],
    root_schema: Mapping[str, Any],
    *,
    path: str = "$",
) -> list[str]:
    if "$ref" in schema:
        return _schema_errors(value, _resolve_schema_ref(root_schema, str(schema["$ref"])), root_schema, path=path)

    if "anyOf" in schema:
        branches = schema.get("anyOf")
        if isinstance(branches, list):
            if not any(not _schema_errors(value, branch, root_schema, path=path) for branch in branches if isinstance(branch, Mapping)):
                return [f"{path}: did not match anyOf"]

    if "oneOf" in schema:
        branches = schema.get("oneOf")
        matches = 0
        if isinstance(branches, list):
            for branch in branches:
                if isinstance(branch, Mapping) and not _schema_errors(value, branch, root_schema, path=path):
                    matches += 1
        if matches != 1:
            return [f"{path}: did not match exactly one oneOf branch"]

    errors: list[str] = []
    expected = schema.get("type")
    if expected is not None:
        expected_types = expected if isinstance(expected, list) else [expected]
        if not any(_schema_matches_type(value, str(type_name)) for type_name in expected_types):
            return [f"{path}: expected {expected_types}, got {type(value).__name__}"]

    if "enum" in schema:
        allowed = schema.get("enum")
        if isinstance(allowed, list) and value not in allowed:
            errors.append(f"{path}: value {value!r} is not in enum")

    if "const" in schema and value != schema.get("const"):
        errors.append(f"{path}: value {value!r} does not match const")

    if _schema_allows_type(schema, "object") and isinstance(value, dict):
        properties = schema.get("properties") if isinstance(schema.get("properties"), Mapping) else {}
        required = schema.get("required") if isinstance(schema.get("required"), list) else []
        for key in required:
            if key not in value:
                errors.append(f"{path}: missing required property {key!r}")
        for key, child in value.items():
            child_path = f"{path}.{key}"
            if key in properties and isinstance(properties[key], Mapping):
                errors.extend(_schema_errors(child, properties[key], root_schema, path=child_path))
            elif schema.get("additionalProperties") is False:
                errors.append(f"{path}: additional property {key!r} is not allowed")
            elif isinstance(schema.get("additionalProperties"), Mapping):
                errors.extend(_schema_errors(child, schema["additionalProperties"], root_schema, path=child_path))

    if _schema_allows_type(schema, "array") and isinstance(value, list):
        min_items = schema.get("minItems")
        if isinstance(min_items, int) and len(value) < min_items:
            errors.append(f"{path}: expected at least {min_items} items")
        if schema.get("uniqueItems") is True and len({json.dumps(item, sort_keys=True) for item in value}) != len(value):
            errors.append(f"{path}: array items must be unique")
        items = schema.get("items")
        if isinstance(items, Mapping):
            for index, item in enumerate(value):
                errors.extend(_schema_errors(item, items, root_schema, path=f"{path}[{index}]"))

    if _schema_allows_type(schema, "string") and isinstance(value, str):
        min_length = schema.get("minLength")
        if isinstance(min_length, int) and len(value) < min_length:
            errors.append(f"{path}: expected length >= {min_length}")
        pattern = schema.get("pattern")
        if isinstance(pattern, str) and not re.search(pattern, value):
            errors.append(f"{path}: value does not match pattern {pattern!r}")

    if isinstance(value, (int, float)) and not isinstance(value, bool):
        minimum = schema.get("minimum")
        maximum = schema.get("maximum")
        if isinstance(minimum, (int, float)) and value < minimum:
            errors.append(f"{path}: expected value >= {minimum}")
        if isinstance(maximum, (int, float)) and value > maximum:
            errors.append(f"{path}: expected value <= {maximum}")

    return errors


def _extract_record_schema(schema: Mapping[str, Any]) -> Mapping[str, Any]:
    if schema.get("type") == "array" and isinstance(schema.get("items"), Mapping):
        return schema["items"]
    properties = schema.get("properties")
    if isinstance(properties, Mapping):
        frameworks = properties.get("frameworks")
        if isinstance(frameworks, Mapping):
            if "$ref" in frameworks:
                frameworks = _resolve_schema_ref(schema, str(frameworks["$ref"]))
            if frameworks.get("type") == "array" and isinstance(frameworks.get("items"), Mapping):
                return frameworks["items"]
    return schema


def _output_schema_errors(records: list[dict[str, Any]], schema: Mapping[str, Any]) -> list[str]:
    if schema.get("type") == "array":
        return _schema_errors(records, schema, schema)
    properties = schema.get("properties")
    if isinstance(properties, Mapping) and "frameworks" in properties:
        return _schema_errors({"frameworks": records}, schema, schema)
    return [
        error
        for index, record in enumerate(records)
        for error in _schema_errors(record, schema, schema, path=f"$[{index}]")
    ]


def _load_chunks(semantic_chunks_path: Path) -> tuple[dict[str, list[SourceChunk]], dict[str, list[SourceChunk]]]:
    rows = _read_jsonl(semantic_chunks_path)
    by_doc_id: dict[str, list[SourceChunk]] = {}
    by_source_stem: dict[str, list[SourceChunk]] = {}
    for payload in rows:
        doc_id = _normalize_text(payload.get("doc_id"))
        if not doc_id:
            continue
        source_path = _normalize_text(payload.get("source_path"))
        source_file = _normalize_text(payload.get("source_file_name") or payload.get("source_file"))
        if not source_file and source_path:
            source_file = Path(source_path).name
        chunk = SourceChunk(
            chunk_id=_normalize_text(payload.get("chunk_id")),
            doc_id=doc_id,
            chunk_index=int(payload.get("chunk_index") or 0),
            text=_normalize_text(payload.get("text")),
            source_file=source_file,
            source_path=source_path,
            page_start=_coerce_optional_int(payload.get("page_start")),
            page_end=_coerce_optional_int(payload.get("page_end")),
            section=_normalize_text(payload.get("section")),
        )
        by_doc_id.setdefault(doc_id, []).append(chunk)
        stems = {
            Path(source_file).stem.lower() if source_file else "",
            Path(source_path).stem.lower() if source_path else "",
        }
        for stem in stems:
            if stem:
                by_source_stem.setdefault(stem, []).append(chunk)

    for value in by_doc_id.values():
        value.sort(key=lambda row: (row.chunk_index, row.chunk_id))
    for value in by_source_stem.values():
        value.sort(key=lambda row: (row.doc_id, row.chunk_index, row.chunk_id))
    return by_doc_id, by_source_stem


def _resolve_cleaned_text_dir(cleaned_text_dir: Path | None, semantic_chunks_path: Path) -> Path:
    if cleaned_text_dir is not None:
        resolved = cleaned_text_dir.expanduser().resolve()
        if not resolved.exists():
            raise FileNotFoundError(f"cleaned text directory not found: {resolved}")
        return resolved
    candidates = [
        semantic_chunks_path.parent / "cleaned_text",
        semantic_chunks_path.parent / "extracted_text",
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate.resolve()
    raise FileNotFoundError(
        f"could not locate cleaned text directory next to {semantic_chunks_path}; "
        "checked cleaned_text/ and extracted_text/"
    )


def _resolve_document_context(
    text_path: Path,
    by_doc_id: Mapping[str, list[SourceChunk]],
    by_source_stem: Mapping[str, list[SourceChunk]],
) -> DocumentContext | None:
    stem = text_path.stem
    if stem in by_doc_id:
        chunks = tuple(by_doc_id[stem])
    else:
        chunks = tuple(by_source_stem.get(stem.lower(), ()))
        doc_ids = {chunk.doc_id for chunk in chunks}
        if len(doc_ids) > 1:
            raise RuntimeError(f"ambiguous chunk mapping for {text_path.name}: {sorted(doc_ids)}")
    if not chunks:
        return None
    first = chunks[0]
    return DocumentContext(
        doc_id=first.doc_id,
        source_file=first.source_file,
        source_path=first.source_path,
        chunks=chunks,
    )


def _record_schema_property_names(schema: Mapping[str, Any]) -> set[str]:
    props = schema.get("properties")
    return set(props.keys()) if isinstance(props, Mapping) else set()


def _framework_id(context: DocumentContext, family: str, title: str) -> str:
    seed = "|".join(
        [
            context.doc_id,
            _normalize_family(family),
            _normalize_text(title).casefold(),
        ]
    )
    return hashlib.sha256(seed.encode("utf-8")).hexdigest()[:24]


def _framework_query_tokens(record: Mapping[str, Any]) -> set[str]:
    parts: list[str] = []
    for key in ("title", "summary", "principles", "signals_or_indicators", "decision_rules", "risk_notes"):
        value = record.get(key)
        if isinstance(value, list):
            parts.extend(str(item) for item in value)
        elif value:
            parts.append(str(value))
    return {
        token.lower()
        for token in TOKEN_RE.findall(" ".join(parts))
        if len(token) >= 3
    }


def _select_evidence(context: DocumentContext, record: Mapping[str, Any]) -> list[SourceChunk]:
    tokens = _framework_query_tokens(record)
    scored: list[tuple[int, int, SourceChunk]] = []
    for chunk in context.chunks:
        chunk_tokens = {token.lower() for token in TOKEN_RE.findall(chunk.text) if len(token) >= 3}
        overlap = len(tokens.intersection(chunk_tokens)) if tokens else 0
        scored.append((overlap, chunk.chunk_index, chunk))

    matched = [chunk for overlap, _, chunk in sorted(scored, key=lambda item: (-item[0], item[1])) if overlap > 0]
    return matched or list(context.chunks)


def _chunk_page_numbers(chunk: SourceChunk) -> list[int]:
    if isinstance(chunk.page_start, int) and isinstance(chunk.page_end, int) and chunk.page_end >= chunk.page_start:
        return list(range(chunk.page_start, chunk.page_end + 1))

    pages: list[int] = []
    seen_pages = set()
    for value in (chunk.page_start, chunk.page_end):
        if isinstance(value, int) and value not in seen_pages:
            seen_pages.add(value)
            pages.append(value)
    return pages


def _source_pages_use_objects(record_schema: Mapping[str, Any]) -> bool:
    properties = record_schema.get("properties")
    if not isinstance(properties, Mapping):
        return False
    source_pages = properties.get("source_pages")
    if not isinstance(source_pages, Mapping):
        return False
    items = source_pages.get("items")
    return isinstance(items, Mapping) and (
        items.get("type") == "object" or isinstance(items.get("properties"), Mapping)
    )


def _quote_excerpt(text: str, max_chars: int = 240) -> str:
    normalized = _normalize_text(text)
    if len(normalized) <= max_chars:
        return normalized
    truncated = normalized[: max_chars - 3].rstrip()
    return f"{truncated}..."


def _build_source_pages(selected_chunks: list[SourceChunk], record_schema: Mapping[str, Any]) -> list[Any]:
    use_objects = _source_pages_use_objects(record_schema)
    pages: list[Any] = []
    seen_pages = set()
    for chunk in selected_chunks:
        quote = _quote_excerpt(chunk.text)
        for page in _chunk_page_numbers(chunk):
            if page in seen_pages:
                continue
            seen_pages.add(page)
            if use_objects:
                page_record: dict[str, Any] = {"page": page}
                if quote:
                    page_record["quote"] = quote
                pages.append(page_record)
            else:
                pages.append(page)
    return pages


def _build_evidence_chunk_ids(selected_chunks: list[SourceChunk]) -> list[str]:
    evidence_chunk_ids: list[str] = []
    seen_chunk_ids = set()
    for chunk in selected_chunks:
        if not chunk.chunk_id or chunk.chunk_id in seen_chunk_ids:
            continue
        seen_chunk_ids.add(chunk.chunk_id)
        evidence_chunk_ids.append(chunk.chunk_id)
    return evidence_chunk_ids


def _coerce_optional_float(value: Any) -> float | None:
    if value in (None, ""):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _prompt_output_schema(record_schema: Mapping[str, Any], allowed_families: list[str]) -> str:
    properties = record_schema.get("properties") if isinstance(record_schema.get("properties"), Mapping) else {}
    field_order = ["framework_family", "title", "principles", "signals_or_indicators", "decision_rules", "risk_notes"]
    for optional_field in ("summary", "confidence"):
        if optional_field in properties:
            field_order.append(optional_field)
    schema_fields: dict[str, Any] = {}
    for field_name in field_order:
        if field_name == "framework_family":
            schema_fields[field_name] = {"type": "string", "enum": allowed_families}
        elif field_name == "confidence":
            if field_name in properties:
                schema_fields[field_name] = {"type": "number", "minimum": 0, "maximum": 1}
        elif field_name in {"principles", "signals_or_indicators", "decision_rules", "risk_notes"}:
            schema_fields[field_name] = {"type": "array", "items": {"type": "string"}}
        else:
            schema_fields[field_name] = {"type": "string"}
    return json.dumps({"frameworks": [schema_fields]}, indent=2, ensure_ascii=False)


def build_framework_prompt(
    text: str,
    allowed_families: list[str],
    record_schema: Mapping[str, Any],
    max_prompt_chars: int = DEFAULT_MAX_PROMPT_CHARS,
) -> str:
    clipped = str(text or "")[:max_prompt_chars]
    family_list = ", ".join(allowed_families)
    schema_text = _prompt_output_schema(record_schema, allowed_families)
    return f"""You are an investment methodology extraction engine.
Return valid JSON only.
Return exactly one JSON object with exactly one top-level key: "frameworks".
Each framework object must follow this schema for extractable fields:
{schema_text}

Rules:
- Extract only frameworks explicitly supported by the source text.
- Use only framework_family values from this taxonomy: {family_list}
- If no supported frameworks exist, return {{"frameworks": []}}
- Provide a non-empty title and at least one principle for every framework.
- Keep arrays concise, specific, and deduplicated.
- confidence must be a number between 0 and 1 when present.
- Do not invent source_file_name, source_path, source_pages, source_doc_id, evidence_chunk_ids, or metadata fields. The pipeline will add source attribution after extraction.

Document text:
{clipped}"""


def _default_generate_json(
    prompt: str,
    *,
    llm_url: str,
    model: str,
    backend_runtime: Mapping[str, Any],
    client: Any = None,
) -> Any:
    return backend_runtime["generate_json_llamacpp"](llm_url, model, prompt, client=client)


def _normalize_framework_candidates(payload: Any) -> list[Mapping[str, Any]]:
    if isinstance(payload, dict):
        frameworks = payload.get("frameworks")
        if isinstance(frameworks, list):
            return [row for row in frameworks if isinstance(row, Mapping)]
        framework_like_keys = {
            "framework_family",
            "title",
            "summary",
            "principles",
            "signals_or_indicators",
            "decision_rules",
            "risk_notes",
            "confidence",
        }
        if framework_like_keys.intersection(payload.keys()):
            return [payload]
    if isinstance(payload, list):
        return [row for row in payload if isinstance(row, Mapping)]
    return []


def _add_optional_source_fields(
    record: dict[str, Any],
    record_schema: Mapping[str, Any],
    context: DocumentContext,
) -> None:
    properties = _record_schema_property_names(record_schema)
    optional_values = {
        "source_file": context.source_file,
        "source_file_name": context.source_file,
        "source_path": context.source_path,
        "doc_id": context.doc_id,
        "source_doc_id": context.doc_id,
    }
    for key, value in optional_values.items():
        if key in properties and value:
            record[key] = value


def _write_jsonl(path: Path, rows: Iterable[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")


def _build_record_metadata(prompt: str, llm_model: str, extractor_version: str) -> dict[str, Any]:
    return {
        "extractor_model": llm_model,
        "extractor_version": extractor_version,
        "prompt_hash": hashlib.sha256(prompt.encode("utf-8")).hexdigest(),
        "review_status": "pending",
    }


def run(
    *,
    semantic_chunks_path: Path,
    framework_schema_path: Path,
    framework_taxonomy_path: Path,
    cleaned_text_dir: Path | None = None,
    out_dir: Path | None = None,
    llm_model: str = DEFAULT_LLM_MODEL,
    llm_url: str = DEFAULT_LLM_URL,
    max_prompt_chars: int = DEFAULT_MAX_PROMPT_CHARS,
    generate_json_fn: Callable[..., Any] | None = None,
) -> dict[str, Any]:
    semantic_chunks_path = _resolve_semantic_chunks_path(semantic_chunks_path)

    framework_schema_path = framework_schema_path.expanduser().resolve()
    if not framework_schema_path.exists():
        raise FileNotFoundError(f"framework schema not found: {framework_schema_path}")

    framework_taxonomy_path = framework_taxonomy_path.expanduser().resolve()
    if not framework_taxonomy_path.exists():
        raise FileNotFoundError(f"framework taxonomy not found: {framework_taxonomy_path}")

    cleaned_dir = _resolve_cleaned_text_dir(cleaned_text_dir, semantic_chunks_path)
    out_dir = (out_dir or (semantic_chunks_path.parent / "framework_records")).expanduser().resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    schema = json.loads(framework_schema_path.read_text(encoding="utf-8"))
    if not isinstance(schema, Mapping):
        raise RuntimeError("framework schema must be a JSON object")
    record_schema = _extract_record_schema(schema)
    taxonomy_families = _load_taxonomy_families(framework_taxonomy_path)
    chunks_by_doc_id, chunks_by_source_stem = _load_chunks(semantic_chunks_path)

    backend_runtime: Mapping[str, Any] | None = None
    resolved_llm_url = str(llm_url or DEFAULT_LLM_URL).strip()
    resolved_llm_model = str(llm_model or DEFAULT_LLM_MODEL).strip()
    http_client = None
    if generate_json_fn is None:
        backend_runtime = _load_backend_extraction_runtime()
        if not resolved_llm_url:
            raise RuntimeError("llm_url is required")
        if not resolved_llm_model:
            raise RuntimeError("llm_model is required")
        generate_json_fn = _default_generate_json
        http_client = backend_runtime["httpx"].Client(timeout=480.0)

    valid_records: list[dict[str, Any]] = []
    rejected_records: list[dict[str, Any]] = []
    extractor_version = (
        str(backend_runtime["EXTRACTOR_VERSION"])
        if backend_runtime is not None
        else "llamacpp_openai"
    )

    try:
        for text_path in sorted(cleaned_dir.glob("*.txt")):
            raw_text = text_path.read_text(encoding="utf-8")
            context = _resolve_document_context(text_path, chunks_by_doc_id, chunks_by_source_stem)
            if context is None:
                rejected_records.append(
                    {
                        "source_text": str(text_path),
                        "errors": ["missing_source_attribution_context"],
                    }
                )
                continue

            prompt = build_framework_prompt(
                raw_text,
                taxonomy_families,
                record_schema,
                max_prompt_chars=max_prompt_chars,
            )
            try:
                payload = generate_json_fn(
                    prompt,
                    llm_url=resolved_llm_url,
                    model=resolved_llm_model,
                    backend_runtime=backend_runtime or {},
                    client=http_client,
                )
            except Exception as exc:
                rejected_records.append(
                    {
                        "source_text": str(text_path),
                        "doc_id": context.doc_id,
                        "errors": [f"llm_generation_failed:{exc}"],
                    }
                )
                continue

            candidates = _normalize_framework_candidates(payload)
            if not candidates:
                explicit_empty = (
                    payload == []
                    or payload == {"frameworks": []}
                    or (isinstance(payload, Mapping) and isinstance(payload.get("frameworks"), list) and not payload["frameworks"])
                )
                if not explicit_empty:
                    rejected_records.append(
                        {
                            "source_text": str(text_path),
                            "doc_id": context.doc_id,
                            "errors": ["invalid_framework_payload_shape"],
                        }
                    )
                continue

            for candidate in candidates:
                family = _normalize_family(candidate.get("framework_family"))
                title = _normalize_text(candidate.get("title"))
                summary = _normalize_text(candidate.get("summary"))
                principles = _normalize_string_list(candidate.get("principles"))
                signals = _normalize_string_list(candidate.get("signals_or_indicators"))
                decision_rules = _normalize_string_list(candidate.get("decision_rules"))
                risk_notes = _normalize_string_list(candidate.get("risk_notes"))
                confidence = _coerce_optional_float(candidate.get("confidence"))
                selected_chunks = _select_evidence(
                    context,
                    {
                        "title": title,
                        "summary": summary,
                        "principles": principles,
                        "signals_or_indicators": signals,
                        "decision_rules": decision_rules,
                        "risk_notes": risk_notes,
                    },
                )
                evidence_chunk_ids = _build_evidence_chunk_ids(selected_chunks)
                source_pages = _build_source_pages(selected_chunks, record_schema)
                record = {
                    "framework_id": _framework_id(context, family, title),
                    "framework_family": family,
                    "title": title,
                    "principles": principles,
                    "signals_or_indicators": signals,
                    "decision_rules": decision_rules,
                    "risk_notes": risk_notes,
                    "source_pages": source_pages,
                    "evidence_chunk_ids": evidence_chunk_ids,
                }
                if summary:
                    record["summary"] = summary
                if confidence is not None:
                    record["confidence"] = confidence
                _add_optional_source_fields(record, record_schema, context)
                if "metadata" in _record_schema_property_names(record_schema):
                    record["metadata"] = _build_record_metadata(prompt, resolved_llm_model, extractor_version)

                errors: list[str] = []
                properties = _record_schema_property_names(record_schema)
                known_chunk_ids = {chunk.chunk_id for chunk in context.chunks if chunk.chunk_id}
                if "summary" not in properties:
                    record.pop("summary", None)
                if "confidence" not in properties:
                    record.pop("confidence", None)
                if family not in taxonomy_families:
                    errors.append(f"framework_family_not_in_taxonomy:{family or 'missing'}")
                if not title:
                    errors.append("missing_title")
                if not principles:
                    errors.append("missing_principles")
                if not context.source_file and not context.source_path:
                    errors.append("missing_source_attribution_context")
                if "source_file_name" in properties and not record.get("source_file_name"):
                    errors.append("missing_source_file_name")
                if "evidence_chunk_ids" in properties and not record["evidence_chunk_ids"]:
                    errors.append("missing_evidence_chunk_ids")
                invalid_chunk_ids = sorted(chunk_id for chunk_id in record["evidence_chunk_ids"] if chunk_id not in known_chunk_ids)
                if invalid_chunk_ids:
                    errors.append("invalid_evidence_chunk_ids:" + ",".join(invalid_chunk_ids))
                if not record["source_pages"]:
                    errors.append("missing_source_attribution")
                errors.extend(_schema_errors(record, record_schema, schema))
                if errors:
                    rejected_records.append(
                        {
                            "source_text": str(text_path),
                            "doc_id": context.doc_id,
                            "candidate": record,
                            "errors": errors,
                        }
                    )
                    continue
                valid_records.append(record)

        output_errors = _output_schema_errors(valid_records, schema)
        if output_errors:
            raise RuntimeError("framework output schema validation failed: " + "; ".join(output_errors))
    finally:
        if http_client is not None:
            http_client.close()

    jsonl_path = out_dir / "frameworks.jsonl"
    yaml_path = out_dir / "frameworks.yaml"
    _write_jsonl(jsonl_path, valid_records)
    yaml_path.write_text(yaml.safe_dump(valid_records, sort_keys=False), encoding="utf-8")

    summary = {
        "status": "success",
        "semantic_chunks": str(semantic_chunks_path),
        "cleaned_text_dir": str(cleaned_dir),
        "framework_schema": str(framework_schema_path),
        "framework_taxonomy": str(framework_taxonomy_path),
        "frameworks_written": len(valid_records),
        "frameworks_rejected": len(rejected_records),
        "outputs": {
            "frameworks_jsonl": str(jsonl_path),
            "frameworks_yaml": str(yaml_path),
        },
        "llm_model": resolved_llm_model,
        "llm_url": resolved_llm_url,
    }
    if backend_runtime is not None:
        summary["extractor_version"] = backend_runtime["EXTRACTOR_VERSION"]
    if rejected_records:
        summary["rejected_examples"] = rejected_records[:5]
    return summary


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Extract structured investment frameworks from methodology text.")
    parser.add_argument(
        "--semantic-chunks",
        default=str(DEFAULT_SEMANTIC_CHUNKS),
        help="Path to semantic_chunks.jsonl from stage 2 preprocessing.",
    )
    parser.add_argument(
        "--cleaned-text-dir",
        default="",
        help="Directory containing cleaned text files. Defaults to cleaned_text/ or extracted_text/ next to semantic_chunks.jsonl.",
    )
    parser.add_argument("--framework-schema", required=True, help="Path to framework_schema.json.")
    parser.add_argument("--framework-taxonomy", required=True, help="Path to framework_taxonomy.yaml.")
    parser.add_argument(
        "--out-dir",
        default="",
        help="Output directory for framework records. Defaults to <semantic-chunks-parent>/framework_records.",
    )
    parser.add_argument("--llm-model", default=DEFAULT_LLM_MODEL, help="llama.cpp model name.")
    parser.add_argument("--llm-url", default=DEFAULT_LLM_URL, help="llama.cpp OpenAI-compatible base URL.")
    parser.add_argument(
        "--max-prompt-chars",
        type=int,
        default=DEFAULT_MAX_PROMPT_CHARS,
        help="Maximum cleaned-text characters included in each extraction prompt.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    summary = run(
        semantic_chunks_path=Path(args.semantic_chunks),
        framework_schema_path=Path(args.framework_schema),
        framework_taxonomy_path=Path(args.framework_taxonomy),
        cleaned_text_dir=Path(args.cleaned_text_dir) if args.cleaned_text_dir else None,
        out_dir=Path(args.out_dir) if args.out_dir else None,
        llm_model=str(args.llm_model),
        llm_url=str(args.llm_url),
        max_prompt_chars=max(1, int(args.max_prompt_chars)),
    )
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
