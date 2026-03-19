from __future__ import annotations

import pytest

from autodev.runtime.experiment_engine import run_experiments


def test_run_experiments_picks_highest_passing_candidate() -> None:
    patches = iter(
        [
            {"autodev/x.py": "x = 1\n"},
            {"autodev/x.py": "x = 2\n"},
            {"autodev/x.py": "x = 3\n"},
        ]
    )

    def patch_generator(task: str) -> dict[str, str]:
        assert task == "optimize"
        return next(patches)

    scores = {
        "variant_1": (-1.1, True),
        "variant_2": (-0.7, True),
        "variant_3": (-0.9, True),
    }

    selection = run_experiments("optimize", patch_generator, lambda patch, patch_id: scores[patch_id])
    assert selection.winner.patch_id == "variant_2"
    assert selection.winner_patch["autodev/x.py"] == "x = 2\n"
    assert [item.patch_id for item in selection.variants] == ["variant_2", "variant_3", "variant_1"]


def test_run_experiments_excludes_failed_candidates() -> None:
    patches = iter(
        [
            {"autodev/x.py": "x = 1\n"},
            {"autodev/x.py": "x = 2\n"},
            {"autodev/x.py": "x = 3\n"},
        ]
    )

    def patch_generator(task: str) -> dict[str, str]:
        _ = task
        return next(patches)

    scores = {
        "variant_1": (-0.2, False),
        "variant_2": (-0.6, True),
        "variant_3": (-0.8, True),
    }

    selection = run_experiments("task", patch_generator, lambda patch, patch_id: scores[patch_id])
    assert selection.winner.patch_id == "variant_2"
    assert selection.winner.passed_gates is True
    assert any(item.patch_id == "variant_1" and not item.passed_gates for item in selection.variants)


def test_run_experiments_raises_when_all_fail() -> None:
    patches = iter(
        [
            {"autodev/x.py": "x = 1\n"},
            {"autodev/x.py": "x = 2\n"},
            {"autodev/x.py": "x = 3\n"},
        ]
    )

    def patch_generator(task: str) -> dict[str, str]:
        _ = task
        return next(patches)

    with pytest.raises(RuntimeError, match="all_experiments_failed"):
        run_experiments("task", patch_generator, lambda patch, patch_id: (-1e9, False))
