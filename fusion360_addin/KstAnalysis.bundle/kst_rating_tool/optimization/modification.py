"""Constraint modification optimization: continuous search over parameterized constraint sets."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal, Protocol

import numpy as np
from numpy.typing import NDArray
from scipy.optimize import differential_evolution

from ..constraints import ConstraintSet
from ..pipeline import analyze_constraints
from ..rating import RatingResults


class Parameterization(Protocol):
    """Callable that maps x in [-1, 1]^d to a ConstraintSet."""

    def __call__(self, x: np.ndarray) -> ConstraintSet:
        ...


def _objective_value(results: RatingResults, objective: str) -> float:
    """Extract scalar to maximize from RatingResults."""
    if objective == "TOR":
        return results.TOR if results.TOR != float("inf") else 0.0
    if objective == "WTR":
        return results.WTR
    if objective == "MRR":
        return results.MRR
    if objective == "MTR":
        return results.MTR
    raise ValueError(f"Unknown objective: {objective}")


@dataclass
class ModificationResult:
    """Result of constraint modification optimization."""

    best_x: NDArray[np.float64]
    best_constraints: ConstraintSet
    best_rating: RatingResults
    history: list[tuple[NDArray[np.float64], RatingResults]] = field(default_factory=list)


def optimize_modification(
    parameterization: Parameterization,
    bounds: list[tuple[float, float]] | None = None,
    objective: str = "TOR",
    method: Literal["diffevo"] = "diffevo",
    max_eval: int = 500,
    seed: int | None = None,
) -> ModificationResult:
    """Maximize a rating metric over a parameterized constraint set.

    Parameters
    ----------
    parameterization
        Callable mapping x (in [-1, 1]^d) to a ConstraintSet.
    bounds
        Per-dimension bounds; default is (-1, 1) for each dimension.
        Inferred from a single evaluation if None (d = len(x) from first call).
    objective
        Metric to maximize: 'TOR', 'WTR', 'MRR', or 'MTR'.
    method
        Currently only 'diffevo' (differential evolution).
    max_eval
        Maximum number of objective evaluations.
    seed
        Random seed for reproducibility.

    Returns
    -------
    ModificationResult
        Best x, resulting ConstraintSet, ratings, and optional history.
    """
    if bounds is None:
        # Default: 1D [-1, 1]; can be overridden by caller for multi-D
        bounds = [(-1.0, 1.0)]
    dim = len(bounds)
    history: list[tuple[NDArray[np.float64], RatingResults]] = []

    def obj(x: NDArray[np.float64]) -> float:
        constraints = parameterization(x)
        results = analyze_constraints(constraints)
        history.append((x.copy(), results))
        # Minimize negative metric
        return -_objective_value(results, objective)

    rng = np.random.default_rng(seed)
    result = differential_evolution(
        obj,
        bounds,
        maxiter=max(1, max_eval // (dim * 10)),
        popsize=min(15, max(5, 5 * dim)),
        seed=rng,
        polish=True,
        atol=1e-6,
        tol=1e-6,
        updating="deferred",
        workers=1,
        disp=False,
    )
    best_x = result.x.astype(np.float64)
    best_constraints = parameterization(best_x)
    best_rating = analyze_constraints(best_constraints)
    return ModificationResult(
        best_x=best_x,
        best_constraints=best_constraints,
        best_rating=best_rating,
        history=history,
    )
