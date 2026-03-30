"""Multi-output surrogate with Pareto front discovery.

Trains independent RF models for each metric (WTR, MRR, MTR, TOR), then uses
non-dominated sorting to find the Pareto front of trade-offs across metrics.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Protocol

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

METRICS = ("WTR", "MRR", "MTR", "TOR")


class Parameterization(Protocol):
    """Callable that maps x in bounds to a ConstraintSet."""

    def __call__(self, x: np.ndarray) -> ConstraintSet: ...


ProgressCallback = Callable[[int, int], None]


def _metric_vector(results: RatingResults) -> NDArray[np.float64]:
    """Extract [WTR, MRR, MTR, TOR] from RatingResults (TOR clamped for inf)."""
    tor = results.TOR if results.TOR != float("inf") else 0.0
    return np.array([results.WTR, results.MRR, results.MTR, tor], dtype=np.float64)


@dataclass
class ParetoPoint:
    """One non-dominated design on the Pareto front."""

    x: NDArray[np.float64]
    constraints: ConstraintSet
    rating: RatingResults
    metrics: NDArray[np.float64]  # [WTR, MRR, MTR, TOR]


@dataclass
class ParetoResult:
    """Result of multi-output Pareto optimization."""

    pareto_front: list[ParetoPoint]
    n_real_evals: int
    n_surrogate_evals: int = 0
    all_metrics: NDArray[np.float64] = field(default_factory=lambda: np.empty((0, 4)))


def _latin_hypercube(n: int, d: int, seed: int | None = None) -> NDArray[np.float64]:
    """Sample n points in [-1, 1]^d using Latin hypercube (stratified)."""
    rng = np.random.default_rng(seed)
    out = np.zeros((n, d), dtype=np.float64)
    for j in range(d):
        perm = rng.permutation(n)
        out[:, j] = -1.0 + (perm + rng.uniform(0, 1, size=n)) * (2.0 / n)
    return out


def _non_dominated_sort(Y: NDArray[np.float64]) -> NDArray[np.bool_]:
    """Return boolean mask of non-dominated rows (all objectives maximized).

    Point i dominates point j if Y[i, k] >= Y[j, k] for all k and strictly >
    for at least one k.
    """
    n = Y.shape[0]
    is_pareto = np.ones(n, dtype=bool)
    for i in range(n):
        if not is_pareto[i]:
            continue
        for j in range(n):
            if i == j or not is_pareto[j]:
                continue
            if np.all(Y[j] >= Y[i]) and np.any(Y[j] > Y[i]):
                is_pareto[i] = False
                break
    return is_pareto


def _rf_uncertainty(rf: "RandomForestRegressor", X: NDArray[np.float64]) -> NDArray[np.float64]:
    """Per-point uncertainty from RF tree disagreement."""
    tree_preds = np.array([t.predict(X) for t in rf.estimators_])
    return np.std(tree_preds, axis=0)


def optimize_pareto(
    parameterization: Parameterization,
    bounds: list[tuple[float, float]],
    objectives: list[str] | None = None,
    n_initial: int = 80,
    n_iter: int = 5,
    batch_size: int = 10,
    n_candidates: int = 5000,
    n_validate: int = 20,
    alpha: float = 1.0,
    seed: int | None = None,
    progress_callback: ProgressCallback | None = None,
) -> ParetoResult:
    """Multi-output surrogate optimization with Pareto front discovery.

    1. Evaluate `n_initial` LHS points with the real pipeline, recording all
       four metrics per point.
    2. For `n_iter` iterations:
       a. Fit one RF per objective.
       b. Score candidates by a combined UCB across all objectives.
       c. Evaluate top `batch_size` candidates.
    3. Identify Pareto front from surrogate predictions over a large candidate
       pool; validate top `n_validate` with real evaluations.
    4. Return the non-dominated set.

    Parameters
    ----------
    parameterization
        Maps x (in bounds) to a ConstraintSet.
    bounds
        Per-dimension (low, high).
    objectives
        Subset of ('WTR', 'MRR', 'MTR', 'TOR') to include in Pareto analysis.
        Default: all four.
    n_initial
        Initial DoE size.
    n_iter
        Adaptive iterations.
    batch_size
        New evaluations per iteration.
    n_candidates
        Random candidate pool size per iteration.
    n_validate
        Pareto candidates to validate with real pipeline at the end.
    alpha
        Exploration weight for UCB acquisition.
    seed
        Random seed.
    progress_callback
        Called as callback(eval_number, total_evals).

    Returns
    -------
    ParetoResult
    """
    if RandomForestRegressor is None:
        raise ImportError(
            "optimize_pareto requires scikit-learn; "
            "install with: pip install scikit-learn"
        )

    if objectives is None:
        objectives = list(METRICS)
    obj_indices = [METRICS.index(o) for o in objectives]

    d = len(bounds)
    total_budget = n_initial + n_iter * batch_size + n_validate
    rng = np.random.default_rng(seed)

    lo = np.array([b[0] for b in bounds], dtype=np.float64)
    hi = np.array([b[1] for b in bounds], dtype=np.float64)

    # --- Phase 1: initial DoE ---
    X_unit = _latin_hypercube(n_initial, d, seed=seed)
    X_scaled = lo + (X_unit + 1.0) / 2.0 * (hi - lo)
    Y = np.zeros((n_initial, 4), dtype=np.float64)

    ratings_cache: dict[int, RatingResults] = {}

    for i in range(n_initial):
        cs = parameterization(X_scaled[i])
        res = analyze_constraints(cs)
        Y[i] = _metric_vector(res)
        ratings_cache[i] = res
        if progress_callback is not None:
            progress_callback(i + 1, total_budget)

    n_evals = n_initial
    n_surrogate_evals = 0

    # --- Phase 2: adaptive multi-output iterations ---
    for iteration in range(n_iter):
        rfs = {}
        for obj_idx in obj_indices:
            rf = RandomForestRegressor(
                n_estimators=150, max_depth=None, min_samples_leaf=2,
                random_state=seed, n_jobs=1,
            )
            rf.fit(X_scaled, Y[:, obj_idx])
            rfs[obj_idx] = rf

        cand = lo + rng.random((n_candidates, d)) * (hi - lo)
        n_surrogate_evals += n_candidates * len(obj_indices)

        # Combined UCB score: sum of (mean + alpha*std) across objectives
        combined_score = np.zeros(n_candidates, dtype=np.float64)
        for obj_idx in obj_indices:
            rf = rfs[obj_idx]
            mu = rf.predict(cand)
            sigma = _rf_uncertainty(rf, cand)
            y_range = float(np.ptp(Y[:, obj_idx])) or 1.0
            combined_score += (mu + alpha * sigma) / y_range

        top_idx = np.argsort(-combined_score)
        selected: list[int] = []
        for idx in top_idx:
            if len(selected) >= batch_size:
                break
            x_cand = cand[idx]
            if selected:
                dists = np.linalg.norm(cand[selected] - x_cand, axis=1)
                if np.min(dists) < 1e-6 * np.linalg.norm(hi - lo):
                    continue
            selected.append(int(idx))

        while len(selected) < batch_size:
            idx = int(rng.integers(n_candidates))
            if idx not in selected:
                selected.append(idx)

        new_X = cand[selected]
        new_Y = np.zeros((len(selected), 4), dtype=np.float64)
        for j, sel in enumerate(selected):
            cs = parameterization(cand[sel])
            res = analyze_constraints(cs)
            new_Y[j] = _metric_vector(res)
            ratings_cache[X_scaled.shape[0] + j] = res
            n_evals += 1
            if progress_callback is not None:
                progress_callback(n_evals, total_budget)

        X_scaled = np.vstack([X_scaled, new_X])
        Y = np.vstack([Y, new_Y])

    # --- Phase 3: Pareto front from surrogate + validation ---
    rfs_final = {}
    for obj_idx in obj_indices:
        rf = RandomForestRegressor(
            n_estimators=150, max_depth=None, min_samples_leaf=2,
            random_state=seed, n_jobs=1,
        )
        rf.fit(X_scaled, Y[:, obj_idx])
        rfs_final[obj_idx] = rf

    cand_final = lo + rng.random((n_candidates * 2, d)) * (hi - lo)
    all_pool = np.vstack([X_scaled, cand_final])
    n_pool = all_pool.shape[0]

    pred_Y = np.zeros((n_pool, len(obj_indices)), dtype=np.float64)
    for k, obj_idx in enumerate(obj_indices):
        pred_Y[:, k] = rfs_final[obj_idx].predict(all_pool)

    pareto_mask = _non_dominated_sort(pred_Y)
    pareto_indices = np.where(pareto_mask)[0]

    # Pick up to n_validate from the Pareto front (prioritize diversity)
    if len(pareto_indices) > n_validate:
        chosen = rng.choice(pareto_indices, size=n_validate, replace=False)
    else:
        chosen = pareto_indices

    pareto_points: list[ParetoPoint] = []
    validated_Y = np.zeros((len(chosen), 4), dtype=np.float64)

    for j, idx in enumerate(chosen):
        x = all_pool[idx]
        if idx < X_scaled.shape[0] and idx in ratings_cache:
            res = ratings_cache[idx]
        else:
            cs = parameterization(x)
            res = analyze_constraints(cs)
            n_evals += 1
            if progress_callback is not None:
                progress_callback(n_evals, total_budget)

        mv = _metric_vector(res)
        validated_Y[j] = mv
        pareto_points.append(ParetoPoint(
            x=x.copy(),
            constraints=parameterization(x),
            rating=res,
            metrics=mv,
        ))

    # Re-filter to actual Pareto front after validation
    validated_obj = validated_Y[:, obj_indices]
    final_mask = _non_dominated_sort(validated_obj)
    pareto_front = [p for p, m in zip(pareto_points, final_mask) if m]

    if not pareto_front and pareto_points:
        pareto_front = [pareto_points[0]]

    return ParetoResult(
        pareto_front=pareto_front,
        n_real_evals=n_evals,
        n_surrogate_evals=n_surrogate_evals,
        all_metrics=Y,
    )
