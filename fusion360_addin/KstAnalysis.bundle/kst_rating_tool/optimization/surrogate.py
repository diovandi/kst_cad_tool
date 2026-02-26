"""Surrogate-based modification optimization: fit a model, optimize it, validate top-k."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol

import numpy as np
from numpy.typing import NDArray
from scipy.optimize import differential_evolution

from ..constraints import ConstraintSet
from ..pipeline import analyze_constraints
from ..rating import RatingResults

try:
    from sklearn.ensemble import RandomForestRegressor
except ImportError:
    RandomForestRegressor = None  # type: ignore[misc, assignment]


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
class SurrogateResult:
    """Result of surrogate-based modification optimization."""

    best_x: NDArray[np.float64]
    best_constraints: ConstraintSet
    best_rating: RatingResults
    n_real_evals: int
    n_surrogate_evals: int = 0


def _latin_hypercube(n: int, d: int, seed: int | None = None) -> NDArray[np.float64]:
    """Sample n points in [-1, 1]^d using Latin hypercube (stratified)."""
    rng = np.random.default_rng(seed)
    out = np.zeros((n, d), dtype=np.float64)
    for j in range(d):
        perm = rng.permutation(n)
        out[:, j] = -1.0 + (perm + rng.uniform(0, 1, size=n)) * (2.0 / n)
    return out


def optimize_modification_surrogate(
    parameterization: Parameterization,
    bounds: list[tuple[float, float]],
    objective: str = "TOR",
    n_samples: int = 300,
    n_validate: int = 20,
    n_surrogate_evals: int = 2000,
    seed: int | None = None,
) -> SurrogateResult:
    """Optimize modification via a surrogate model to reduce real evaluations.

    Samples n_samples points, fits a Random Forest to predict the objective,
    optimizes the surrogate (cheap), then re-evaluates the top n_validate
    designs with the real pipeline and returns the best.

    Parameters
    ----------
    parameterization
        Callable mapping x (in bounds) to a ConstraintSet.
    bounds
        Per-dimension (low, high) bounds; typically (-1, 1) for each.
    objective
        Metric to maximize: 'TOR', 'WTR', 'MRR', or 'MTR'.
    n_samples
        Number of real evaluations to train the surrogate.
    n_validate
        Number of top predicted designs to re-evaluate with the real pipeline.
    n_surrogate_evals
        Max evaluations when optimizing the surrogate.
    seed
        Random seed for sampling and RF.

    Returns
    -------
    SurrogateResult
        Best x, ConstraintSet, ratings, and eval counts.
    """
    if RandomForestRegressor is None:
        raise ImportError("optimize_modification_surrogate requires scikit-learn; install with pip install scikit-learn")

    d = len(bounds)
    rng = np.random.default_rng(seed)
    # Sample training data
    X = _latin_hypercube(n_samples, d, seed=seed)
    y = np.zeros(n_samples, dtype=np.float64)
    for i in range(n_samples):
        cs = parameterization(X[i])
        res = analyze_constraints(cs)
        y[i] = _objective_value(res, objective)
    # Fit surrogate
    rf = RandomForestRegressor(n_estimators=100, max_depth=10, random_state=seed, n_jobs=-1)
    rf.fit(X, y)
    # Optimize surrogate (maximize = minimize -pred)
    def neg_pred(x: NDArray[np.float64]) -> float:
        return -float(rf.predict(x.reshape(1, -1))[0])

    result = differential_evolution(
        neg_pred,
        bounds,
        maxiter=max(1, n_surrogate_evals // (d * 10)),
        popsize=min(20, max(5, 5 * d)),
        seed=rng,
        polish=True,
        atol=1e-6,
        tol=1e-6,
        updating="deferred",
        workers=1,
        disp=False,
    )
    # Collect top n_validate by surrogate prediction (from search + training)
    all_x = np.vstack([X, result.x.reshape(1, -1)])
    preds = rf.predict(all_x)
    top_idx = np.argsort(-preds)[:n_validate]
    best_metric = float("-inf")
    best_x: NDArray[np.float64] = all_x[top_idx[0]]
    best_rating: RatingResults | None = None
    for idx in top_idx:
        x = all_x[idx]
        cs = parameterization(x)
        res = analyze_constraints(cs)
        val = _objective_value(res, objective)
        if val > best_metric:
            best_metric = val
            best_x = x
            best_rating = res
    if best_rating is None:
        best_constraints = parameterization(best_x)
        best_rating = analyze_constraints(best_constraints)
    else:
        best_constraints = parameterization(best_x)
    return SurrogateResult(
        best_x=best_x,
        best_constraints=best_constraints,
        best_rating=best_rating,
        n_real_evals=n_samples + n_validate,
        n_surrogate_evals=n_surrogate_evals,
    )
