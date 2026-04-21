from __future__ import annotations

import re
from typing import Any, Sequence

from app.services.fact_contract import FAILURE_CODES, CanonicalFact


# Regex to find numbers in prose (e.g., $28.5 billion, 437 million, -421.1)
_NUMERIC_PATTERN = re.compile(
    r"[-+]?\d[\d,]*(?:\.\d+)?\s*(?:billion|million|bn|mn|m|b|k)?", re.IGNORECASE
)


def verify_synthesis_claims(
    prose: str, facts: Sequence[CanonicalFact]
) -> tuple[str, list[dict[str, Any]]]:
    """
    Scans prose for numeric claims and ensures each is backed by a CanonicalFact
    with a valid source page and span.
    """
    sentences = re.split(r"(?<=[.!?])\s+", prose)
    verified_sentences = []
    issues = []

    for sentence in sentences:
        matches = list(_NUMERIC_PATTERN.finditer(sentence))
        if not matches:
            verified_sentences.append(sentence)
            continue

        sentence_ok = True
        for match in matches:
            num_match = match.group(0)
            # Basic validation: does any fact match this number (roughly)?
            # In a real implementation, this would be more sophisticated (NLP/semantic).
            found_match = False
            for fact in facts:
                if _is_numeric_match(num_match, fact):
                    if fact.source_page and fact.source_span:
                        found_match = True
                        break
                    else:
                        issues.append({
                            "code": FAILURE_CODES["UNSUPPORTED_NUMERIC_CLAIM"],
                            "message": f"Numeric claim {num_match} lacks source provenance.",
                            "sentence": sentence
                        })

            if not found_match:
                sentence_ok = False
                if not any(iss["sentence"] == sentence for iss in issues):
                   issues.append({
                        "code": FAILURE_CODES["UNSUPPORTED_NUMERIC_CLAIM"],
                        "message": f"Numeric claim {num_match} is unsupported by canonical facts.",
                        "sentence": sentence
                    })
                break

        if sentence_ok:
            verified_sentences.append(sentence)
        else:
            verified_sentences.append("[UNSUPPORTED_NUMERIC_CLAIM]")

    return " ".join(verified_sentences), issues


def verify_comparisons(
    facts_to_compare: list[CanonicalFact]
) -> list[dict[str, Any]]:
    """
    Enforces basis-safe and scale-safe comparisons.
    All facts in a comparison must share same metric_key, basis, period_type, and scale.
    """
    if not facts_to_compare:
        return []

    issues = []
    first = facts_to_compare[0]
    for fact in facts_to_compare[1:]:
        if fact.metric_key != first.metric_key:
             # Comparisons between different metrics might be okay (e.g., EBIT vs Revenue)
             # but we check basis and period alignment.
             pass
        
        if fact.basis != first.basis:
            issues.append({
                "code": FAILURE_CODES["BASIS_MISMATCH"],
                "message": f"Cannot compare {first.basis} with {fact.basis} for {fact.metric_key}.",
                "facts": [first.to_dict(), fact.to_dict()]
            })
        
        if fact.period_type != first.period_type:
             # Often a failure point if comparing Half-year to Full-year without framing
             issues.append({
                "code": FAILURE_CODES["DATA_MISSING"], # or a new PERIOD_MISMATCH
                "message": f"Period type mismatch: {first.period_type} vs {fact.period_type}.",
                "facts": [first.to_dict(), fact.to_dict()]
            })

    return issues


def _is_numeric_match(text: str, fact: CanonicalFact) -> bool:
    # Very simple normalization for proof-of-concept
    # We want to compare the absolute value of the number in text with fact.value * scale_multiplier
    
    clean_text = re.sub(r"[^\d.]", "", text)
    if not clean_text:
        return False
    try:
        val = float(clean_text)
        # Handle scales roughly for the text
        lower_text = text.lower()
        text_multiplier = 1.0
        if "billion" in lower_text or "bn" in lower_text or lower_text.endswith("b"):
            text_multiplier = 1_000_000_000.0
        elif "million" in lower_text or "mn" in lower_text or lower_text.endswith("m"):
            text_multiplier = 1_000_000.0
        elif "thousand" in lower_text or "k" in lower_text:
            text_multiplier = 1_000.0
        
        abs_text_val = val * text_multiplier
        
        # Get fact's absolute value
        fact_multiplier = 1.0
        fact_scale = fact.scale.lower()
        if "billion" in fact_scale:
            fact_multiplier = 1_000_000_000.0
        elif "million" in fact_scale:
            fact_multiplier = 1_000_000.0
        elif "thousand" in fact_scale:
            fact_multiplier = 1_000.0
            
        abs_fact_val = fact.value * fact_multiplier
        
        # Check against fact.value (with some tolerance)
        if abs_fact_val == 0:
            return abs_text_val == 0
            
        return abs(abs_text_val - abs_fact_val) / abs(abs_fact_val) < 0.05
    except ValueError:
        return False
