"""Experiment orchestration for candidate patch benchmarking."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable


MAX_EXPERIMENTS = 3
BENCHMARK_TIMEOUT = 60
FAILED_BENCHMARK_SCORE = -1e9


class FatalExperimentError(RuntimeError):
    """Raised when experiment execution must stop immediately."""


@dataclass(frozen=True)
class ExperimentResult:
    patch_id: str
    benchmark_score: float
    passed_gates: bool


@dataclass(frozen=True)
class ExperimentSelection:
    winner: ExperimentResult
    winner_patch: dict[str, str]
    variants: list[ExperimentResult]


def run_experiments(
    task: str,
    patch_generator: Callable[[str], dict[str, str]],
    benchmark_fn: Callable[[dict[str, str], str], tuple[float, bool]],
) -> ExperimentSelection:
    """Generate, benchmark, and select the highest-scoring passing candidate."""
    _ = task
    variants: list[ExperimentResult] = []
    winner: ExperimentResult | None = None
    winner_patch: dict[str, str] | None = None

    for index in range(MAX_EXPERIMENTS):
        patch_id = f"variant_{index + 1}"
        score = FAILED_BENCHMARK_SCORE
        passed = False
        patch: dict[str, str] = {}

        try:
            patch = patch_generator(task)
            score, passed = benchmark_fn(patch, patch_id)
        except FatalExperimentError:
            raise
        except Exception:
            score = FAILED_BENCHMARK_SCORE
            passed = False

        result = ExperimentResult(
            patch_id=patch_id,
            benchmark_score=float(score),
            passed_gates=bool(passed),
        )
        variants.append(result)
        if result.passed_gates and (winner is None or result.benchmark_score > winner.benchmark_score):
            winner = result
            winner_patch = dict(patch)

    ranked = sorted(variants, key=lambda item: item.benchmark_score, reverse=True)
    if winner is None or winner_patch is None:
        raise RuntimeError("all_experiments_failed")
    return ExperimentSelection(winner=winner, winner_patch=winner_patch, variants=ranked)
