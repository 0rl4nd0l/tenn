import json
import re
from typing import Any

import httpx


def _normalize_url(base: str) -> str:
    return base.rstrip("/")


def _extract_first_json_object(raw: str) -> str:
    text = str(raw or "")
    start = text.find("{")
    if start < 0:
        return text
    depth = 0
    in_str = False
    escape = False
    for idx in range(start, len(text)):
        ch = text[idx]
        if in_str:
            if escape:
                escape = False
            elif ch == "\\":
                escape = True
            elif ch == '"':
                in_str = False
            continue
        if ch == '"':
            in_str = True
        elif ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return text[start : idx + 1]
    return text[start:]


def _sanitize_jsonish(raw: str) -> str:
    text = str(raw or "").strip()
    text = re.sub(r"^\s*```(?:json)?\s*", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\s*```\s*$", "", text)
    text = (
        text.replace("“", '"')
        .replace("”", '"')
        .replace("’", "'")
        .replace("‘", "'")
    )
    text = _extract_first_json_object(text)
    text = re.sub(
        r'([{,]\s*)([A-Za-z_][A-Za-z0-9_ \-./]*)(\s*:)',
        lambda m: f'{m.group(1)}"{m.group(2).strip()}"{m.group(3)}',
        text,
    )

    def _single_to_double(match: re.Match) -> str:
        body = match.group(1)
        body = body.replace("\\'", "'").replace('"', '\\"')
        return f'"{body}"'

    text = re.sub(r"'([^'\\]*(?:\\.[^'\\]*)*)'", _single_to_double, text)
    text = re.sub(r",(\s*[}\]])", r"\1", text)
    return text


def _parse_json_response(text: str) -> dict:
    raw = (text or "").strip()
    if not raw:
        raise ValueError("Empty response from Ollama")
    candidates = [raw, _extract_first_json_object(raw), _sanitize_jsonish(raw)]
    seen = set()
    for candidate in candidates:
        c = str(candidate or "").strip()
        if not c or c in seen:
            continue
        seen.add(c)
        try:
            parsed = json.loads(c)
        except json.JSONDecodeError:
            continue
        if isinstance(parsed, dict):
            return parsed
        if isinstance(parsed, list) and parsed and isinstance(parsed[0], dict):
            return parsed[0]
    raise ValueError(f"No valid JSON object found in model response: {raw[:400]}")


def ollama_embed(ollama_url: str, model: str, texts: list[str], timeout: float = 180.0) -> list[list[float]]:
    if not texts:
        return []

    base_url = _normalize_url(ollama_url)
    with httpx.Client(timeout=timeout) as c:
        # Prefer modern endpoint first (Ollama >= 0.1.40+), then fallback.
        r = c.post(f"{base_url}/api/embed", json={"model": model, "input": texts})
        if r.status_code == 404:
            vecs = []
            for t in texts:
                legacy = c.post(f"{base_url}/api/embeddings", json={"model": model, "prompt": t})
                legacy.raise_for_status()
                data = legacy.json()
                vec = data.get("embedding")
                if not isinstance(vec, list):
                    raise RuntimeError(f"Bad embeddings response: {data}")
                vecs.append(vec)
            return vecs

        r.raise_for_status()
        data = r.json()
        embeddings = data.get("embeddings")
        if not isinstance(embeddings, list):
            raise RuntimeError(f"Bad embed response: {data}")
        if embeddings and not isinstance(embeddings[0], list):
            raise RuntimeError(f"Bad embed vector shape: {data}")
        return embeddings


def ollama_generate_json(
    ollama_url: str,
    model: str,
    prompt: str,
    timeout: float = 900.0,
    json_schema: dict[str, Any] | None = None,
) -> dict:
    with httpx.Client(timeout=timeout) as c:
        payload = {
            "model": model,
            "prompt": prompt,
            "stream": False,
            "options": {"temperature": 0},
        }
        # Ask Ollama to enforce valid JSON output where supported.
        payload["format"] = json_schema if json_schema is not None else "json"
        r = c.post(f"{_normalize_url(ollama_url)}/api/generate", json=payload)
        if r.status_code >= 400:
            # Fallback for older/limited runtimes that reject structured output args.
            fallback = {"model": model, "prompt": prompt, "stream": False}
            r = c.post(f"{_normalize_url(ollama_url)}/api/generate", json=fallback)
        r.raise_for_status()
        txt = r.json().get("response", "")
        try:
            return _parse_json_response(txt)
        except Exception:
            # Last-resort repair pass: ask model to emit strict JSON only.
            schema_block = ""
            if json_schema is not None:
                schema_block = f"\nRequired JSON schema:\n{json.dumps(json_schema, ensure_ascii=False)}\n"
            repair_prompt = (
                "Return ONLY a valid JSON object. No markdown, no commentary.\n"
                f"{schema_block}"
                f"RAW_RESPONSE:\n{txt[:20000]}"
            )
            repair_payload = {
                "model": model,
                "prompt": repair_prompt,
                "stream": False,
                "options": {"temperature": 0},
            }
            repair_payload["format"] = json_schema if json_schema is not None else "json"
            rr = c.post(f"{_normalize_url(ollama_url)}/api/generate", json=repair_payload)
            if rr.status_code >= 400:
                rr = c.post(
                    f"{_normalize_url(ollama_url)}/api/generate",
                    json={"model": model, "prompt": repair_prompt, "stream": False},
                )
            rr.raise_for_status()
            repaired_txt = rr.json().get("response", "")
            return _parse_json_response(repaired_txt)
