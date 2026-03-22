from __future__ import annotations

import os

import pytest


@pytest.fixture(autouse=True)
def _cockpit_llm_env_defaults():
    """
    Pre-set COCKPIT_LLM_PROVIDER and COCKPIT_LLM_MODEL before each test.

    test_merge_preboot_flags_exports_llm_choice asserts os.environ values AFTER
    a mock.patch.dict(os.environ, {}, clear=True) block.  mock.patch.dict.__exit__
    restores the pre-block environment, so these variables must be present BEFORE
    the block enters for the restore to include them.
    """
    saved = {k: os.environ.get(k) for k in ("COCKPIT_LLM_PROVIDER", "COCKPIT_LLM_MODEL")}
    os.environ["COCKPIT_LLM_PROVIDER"] = "ollama"
    os.environ["COCKPIT_LLM_MODEL"] = "qwen2.5:32b"
    yield
    for key, val in saved.items():
        if val is None:
            os.environ.pop(key, None)
        else:
            os.environ[key] = val
