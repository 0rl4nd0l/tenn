"""
test_prompt_model_matrix.py — prompt-registry + model-override unit tests.

These are the regression guards for Phase 1 of the prompt×model matrix
evaluation work. They lock in three invariants:

  1. PROMPT_HASH as persisted in ``extraction_runs.prompt_hash`` stays
     byte-identical to the legacy sha256[:16] formula, so historical rows
     keep linking back to the canonical prompt bundle.
  2. ``resolve()`` fails fast on unknown ids — no silent fallback to the
     default bundle when a caller asked for a specific variant.
  3. ``run_multipass_extraction`` threads a ``model_override`` through to
     the LLM call's metadata payload as ``requested_model``, which is the
     key honoured by ``app.services.llm._resolve_runtime_from_metadata``.

All tests are pure unit tests — no network, no DB, no real LLM.
"""

from __future__ import annotations

import hashlib
import re

import pytest

from app.services.multipass_extraction import (
    _PASS1_PROMPT,
    _PASS3A_PROMPT,
    _PASS3B_PROMPT,
    PROMPT_HASH,
    _run_pass1_classifier,
    _run_pass3b_narrative_extractor,
)
from app.services.prompt_registry import (
    PROMPT_BUNDLES,
    PromptBundle,
    register_bundle,
    resolve,
)


# ---------------------------------------------------------------------------
# Invariant 1 — default bundle hash matches legacy PROMPT_HASH
# ---------------------------------------------------------------------------


class TestDefaultBundleHashInvariant:
    """If these tests break, extraction_runs.prompt_hash will silently drift
    on the next run and stale-cache detection loses its anchor."""

    @pytest.mark.unit
    def test_default_bundle_registered(self) -> None:
        assert "default" in PROMPT_BUNDLES
        bundle = resolve("default")
        assert bundle.id == "default"
        assert bundle.pass1 == _PASS1_PROMPT
        assert bundle.pass3a == _PASS3A_PROMPT
        assert bundle.pass3b == _PASS3B_PROMPT

    @pytest.mark.unit
    def test_default_bundle_hash_matches_legacy_formula(self) -> None:
        """Protects the sha256(pass1 + pass3a + pass3b)[:16] contract."""
        expected = hashlib.sha256(
            (_PASS1_PROMPT + _PASS3A_PROMPT + _PASS3B_PROMPT).encode()
        ).hexdigest()[:16]
        assert resolve("default").compute_hash() == expected
        assert PROMPT_HASH == expected

    @pytest.mark.unit
    def test_default_bundle_hash_shape(self) -> None:
        h = resolve("default").compute_hash()
        assert len(h) == 16
        assert re.fullmatch(r"[0-9a-f]+", h)

    @pytest.mark.unit
    def test_compute_hash_is_deterministic(self) -> None:
        bundle = PromptBundle(id="x", pass1="a", pass3a="b", pass3b="c")
        assert bundle.compute_hash() == bundle.compute_hash()


# ---------------------------------------------------------------------------
# Invariant 2 — resolve() fails fast on unknown ids, immutability holds
# ---------------------------------------------------------------------------


class TestResolve:
    @pytest.mark.unit
    def test_resolve_none_returns_default(self) -> None:
        assert resolve(None).id == "default"

    @pytest.mark.unit
    def test_resolve_unknown_raises_keyerror(self) -> None:
        with pytest.raises(KeyError) as excinfo:
            resolve("not-a-real-bundle-id")
        # Known bundles list must be surfaced to aid debugging.
        assert "default" in str(excinfo.value)
        assert "not-a-real-bundle-id" in str(excinfo.value)

    @pytest.mark.unit
    def test_prompt_bundle_is_frozen(self) -> None:
        bundle = resolve("default")
        with pytest.raises(Exception):  # FrozenInstanceError subclasses Exception
            bundle.pass1 = "mutated"  # type: ignore[misc]

    @pytest.mark.unit
    def test_register_bundle_allows_overwrite(self) -> None:
        register_bundle(
            PromptBundle(id="_overwrite_test", pass1="a", pass3a="b", pass3b="c")
        )
        register_bundle(
            PromptBundle(
                id="_overwrite_test",
                pass1="a2",
                pass3a="b2",
                pass3b="c2",
                description="replaced",
            )
        )
        try:
            assert resolve("_overwrite_test").pass1 == "a2"
            assert resolve("_overwrite_test").description == "replaced"
        finally:
            PROMPT_BUNDLES.pop("_overwrite_test", None)

    @pytest.mark.unit
    def test_different_bundles_have_different_hashes(self) -> None:
        a = PromptBundle(id="a", pass1="x", pass3a="y", pass3b="z")
        b = PromptBundle(id="b", pass1="x", pass3a="y", pass3b="DIFFERENT")
        assert a.compute_hash() != b.compute_hash()


# ---------------------------------------------------------------------------
# Invariant 3 — prompt_bundle threads through pass functions, and
# model_override reaches _llm_json_call as metadata["requested_model"].
# ---------------------------------------------------------------------------


class _RecordedCall:
    """Captures the args passed to a single _llm_json_call invocation."""

    def __init__(self) -> None:
        self.prompt: str | None = None
        self.max_tokens: int | None = None
        self.model_override: str | None = None

    def __call__(
        self, prompt: str, llm_client, max_tokens: int = 512, *, model_override=None
    ) -> dict:
        self.prompt = prompt
        self.max_tokens = max_tokens
        self.model_override = model_override
        # Return the shape each pass expects so the outer function doesn't raise.
        return {
            "report_type": "A",
            "period_end": "2024-06-30",
            "currency": "AUD",
            "scale": "millions",
            "classifier_confidence": 0.9,
            "risk_summary": None,
            "risk_bullets": None,
            "guidance_summary": None,
            "material_changes": None,
            "confidence_narrative": 0.0,
        }


@pytest.mark.unit
def test_pass1_uses_custom_bundle_and_model_override(monkeypatch) -> None:
    recorded = _RecordedCall()
    monkeypatch.setattr(
        "app.services.multipass_extraction._llm_json_call", recorded
    )
    variant = PromptBundle(
        id="_variant_test_pass1",
        pass1="VARIANT-CLASSIFIER title={title} first_page={first_page_text}",
        pass3a=_PASS3A_PROMPT,
        pass3b=_PASS3B_PROMPT,
    )
    register_bundle(variant)
    try:
        _run_pass1_classifier(
            title="ACME Half-Year",
            first_page_text="Period ended 30 June 2024",
            llm_client=None,
            prompt_bundle=resolve("_variant_test_pass1"),
            model_override="qwen2.5-14b-instruct",
        )
        assert recorded.prompt is not None
        assert recorded.prompt.startswith("VARIANT-CLASSIFIER title=ACME Half-Year")
        assert recorded.model_override == "qwen2.5-14b-instruct"
    finally:
        PROMPT_BUNDLES.pop("_variant_test_pass1", None)


@pytest.mark.unit
def test_pass3b_uses_custom_bundle_and_model_override(monkeypatch) -> None:
    recorded = _RecordedCall()
    monkeypatch.setattr(
        "app.services.multipass_extraction._llm_json_call", recorded
    )
    variant = PromptBundle(
        id="_variant_test_pass3b",
        pass1=_PASS1_PROMPT,
        pass3a=_PASS3A_PROMPT,
        pass3b="VARIANT-NARRATIVE prose_text={prose_text}",
    )
    register_bundle(variant)
    try:
        _run_pass3b_narrative_extractor(
            sections=[{"text": "Risks include commodity price exposure."}],
            llm_client=None,
            prompt_bundle=resolve("_variant_test_pass3b"),
            model_override="qwen3-30b-a3b-instruct",
        )
        assert recorded.prompt is not None
        assert recorded.prompt.startswith("VARIANT-NARRATIVE prose_text=")
        assert recorded.model_override == "qwen3-30b-a3b-instruct"
    finally:
        PROMPT_BUNDLES.pop("_variant_test_pass3b", None)


@pytest.mark.unit
def test_model_override_becomes_requested_model_metadata(monkeypatch) -> None:
    """_llm_json_call must put model_override into metadata['requested_model']
    so that app.services.llm._resolve_runtime_from_metadata picks it up."""
    from app.services import multipass_extraction as mpx

    captured: dict[str, object] = {}

    def fake_generate_json(prompt, metadata=None, client=None):
        captured["metadata"] = dict(metadata or {})
        return {"ok": True}

    monkeypatch.setattr(
        "app.services.llm.generate_json", fake_generate_json
    )

    mpx._llm_json_call(
        "dummy prompt",
        llm_client=None,
        max_tokens=64,
        model_override="qwen2.5-14b-instruct",
    )

    meta = captured["metadata"]
    assert isinstance(meta, dict)
    assert meta.get("component") == "multipass_extraction"
    assert meta.get("task_type") == "reasoning"
    assert meta.get("requested_model") == "qwen2.5-14b-instruct"


@pytest.mark.unit
def test_no_model_override_omits_requested_model(monkeypatch) -> None:
    from app.services import multipass_extraction as mpx

    captured: dict[str, object] = {}

    def fake_generate_json(prompt, metadata=None, client=None):
        captured["metadata"] = dict(metadata or {})
        return {"ok": True}

    monkeypatch.setattr(
        "app.services.llm.generate_json", fake_generate_json
    )

    mpx._llm_json_call("dummy", llm_client=None, max_tokens=64)

    meta = captured["metadata"]
    assert isinstance(meta, dict)
    assert "requested_model" not in meta
