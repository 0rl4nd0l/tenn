"""prompt_registry.py — versioned prompt bundles for extraction evaluation.

A PromptBundle groups the three LLM prompts used by the multipass extraction
pipeline (pass1 classifier, pass3a metric extractor, pass3b narrative
extractor) under a single id. Bundles are content-addressable via the same
sha256[:16] formula that populates ``extraction_runs.prompt_hash``, preserving
historical hash → eval linkage.

The live extraction path uses the ``"default"`` bundle, which
``multipass_extraction`` registers at import time from its module-level prompt
constants. The evaluation matrix runner can register additional bundles to
compare prompt variants against the same gold fixtures.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass


@dataclass(frozen=True)
class PromptBundle:
    """Immutable group of the three multipass extraction prompt templates.

    Fields match the ``str.format`` placeholders expected by the call sites in
    ``multipass_extraction._run_pass1_classifier``,
    ``multipass_extraction._extract_metrics_from_table`` and
    ``multipass_extraction._run_pass3b_narrative_extractor``.
    """

    id: str
    pass1: str
    pass3a: str
    pass3b: str
    description: str = ""

    def compute_hash(self) -> str:
        """sha256[:16] fingerprint compatible with ``extraction_runs.prompt_hash``.

        Must remain byte-for-byte identical to the legacy formula in
        ``multipass_extraction`` so historical ``prompt_hash`` values in the
        database keep linking back to the correct prompt bundle.
        """
        return hashlib.sha256(
            (self.pass1 + self.pass3a + self.pass3b).encode()
        ).hexdigest()[:16]


PROMPT_BUNDLES: dict[str, PromptBundle] = {}


def register_bundle(bundle: PromptBundle) -> None:
    """Register a bundle under its id.

    Rebuilds are idempotent: the registry is repopulated from source on every
    process start, so overwriting an existing id is allowed (and intentional
    for hot-reload in tests).
    """
    PROMPT_BUNDLES[bundle.id] = bundle


def resolve(bundle_id: str | None) -> PromptBundle:
    """Return the bundle for ``bundle_id`` (or ``"default"`` if ``None``).

    Fails fast on unknown ids — per the root-cause-first bug-resolution
    principle, we do not silently substitute the default when a caller asked
    for a specific variant that was never registered.
    """
    resolved_id = bundle_id or "default"
    try:
        return PROMPT_BUNDLES[resolved_id]
    except KeyError as exc:
        known = sorted(PROMPT_BUNDLES.keys())
        raise KeyError(
            f"Unknown prompt bundle id: {resolved_id!r}. Known bundles: {known}"
        ) from exc
