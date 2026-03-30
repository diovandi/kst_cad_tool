"""Surrogate-based modification optimization: fit a model, optimize it, validate top-k.

Provides two strategies:
- One-shot (`optimize_modification_surrogate`): LHS + RF + DE on surrogate + validate top-k.
- Adaptive (`optimize_surrogate_adaptive`): iterative RF with tree-variance exploration.
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


class Parameterization(Protocol):
    """Callable that maps x in [-1, 1]^d to a ConstraintSet."""

    def __call__(self, x: np.ndarray) -> ConstraintSet:
        ...


ProgressCallback = Callable[[int, int, float], None]


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
    model_r2: float = 0.0
    history: list[tuple[NDArray[np.float64], float]] = field(default_factory=list)


def _latin_hypercube(n: int, d: int, seed: int | None = None) -> NDArray[np.float64]:
    """Sample n points in [-1, 1]^d using Latin hypercube (stratified)."""
    rng = np.random.default_rng(seed)
    out = np.zeros((n, d), dtype=np.float64)
    for j in range(d):
        perm = rng.permutation(n)
        out[:, j] = -1.0 + (perm + rng.uniform(0, 1, size=n)) * (2.0 / n)
    return out


def _rf_uncertainty(rf: "RandomForestRegressor", X: NDArray[np.float64]) -> NDArray[np.float64]:
    """Per-point uncertainty estimate from RF tree disagreement (std across trees)."""
    tree_preds = np.array([t.predict(X) for t in rf.estimators_])
    return np.std(tree_preds, axis=0)


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
    X = _latin_hypercube(n_samples, d, seed=seed)
    y = np.zeros(n_samples, dtype=np.float64)
    for i in range(n_samples):
        cs = parameterization(X[i])
        res = analyze_constraints(cs)
        y[i] = _objective_value(res, objective)
    rf = RandomForestRegressor(n_estimators=100, max_depth=10, random_state=seed, n_jobs=1)
    rf.fit(X, y)

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


def optimize_surrogate_adaptive(
    parameterization: Parameterization,
    bounds: list[tuple[float, float]],
    objective: str = "TOR",
    n_initial: int = 50,
    n_iter: int = 10,
    batch_size: int = 5,
    n_candidates: int = 5000,
    alpha: float = 1.0,
    seed: int | None = None,
    progress_callback: ProgressCallback | None = None,
) -> SurrogateResult:
    """Iterative RF surrogate with adaptive sampling guided by tree disagreement.

    Instead of a single one-shot fit, this strategy alternates between fitting
    the RF and selecting new evaluation points in regions where the model
    predicts high objective value **or** is highly uncertain.

    Acquisition score per candidate: ``predicted_mean + alpha * predicted_std``
    where std is the standard deviation across individual RF trees.

    Total real evaluations: ``n_initial + n_iter * batch_size``.

    Parameters
    ----------
    parameterization
        Maps x (in bounds) to a ConstraintSet.
    bounds
        Per-dimension (low, high) bounds.
    objective
        Metric to maximize: 'TOR', 'WTR', 'MRR', or 'MTR'.
    n_initial
        Number of initial LHS samples.
    n_iter
        Number of adaptive iterations.
    batch_size
        New points evaluated per iteration.
    n_candidates
        Random candidate pool size for acquisition scoring each iteration.
    alpha
        Exploration weight (higher = more exploration of uncertain regions).
    seed
        Random seed.
    progress_callback
        Called as callback(eval_number, total_evals, best_so_far).

    Returns
    -------
    SurrogateResult
    """
    if RandomForestRegressor is None:
        raise ImportError(
            "optimize_surrogate_adaptive requires scikit-learn; "
            "install with: pip install scikit-learn"
        )

    d = len(bounds)
    total_budget = n_initial + n_iter * batch_size
    rng = np.random.default_rng(seed)

    lo = np.array([b[0] for b in bounds], dtype=np.float64)
    hi = np.array([b[1] for b in bounds], dtype=np.float64)

    # --- Phase 1: initial DoE ---
    X = _latin_hypercube(n_initial, d, seed=seed)
    X_scaled = lo + (X + 1.0) / 2.0 * (hi - lo)
    y = np.zeros(n_initial, dtype=np.float64)
    history: list[tuple[NDArray[np.float64], float]] = []

    best_val = float("-inf")
    best_x = X_scaled[0].copy()
    best_rating: RatingResults | None = None

    for i in range(n_initial):
        cs = parameterization(X_scaled[i])
        res = analyze_constraints(cs)
        val = _objective_value(res, objective)
        y[i] = val
        history.append((X_scaled[i].copy(), val))
        if val > best_val:
            best_val = val
            best_x = X_scaled[i].copy()
            best_rating = res
        if progress_callback is not None:
            progress_callback(i + 1, total_budget, best_val)

    n_evals = n_initial
    n_surrogate_evals = 0

    # --- Phase 2: adaptive iterations ---
    for iteration in range(n_iter):
        rf = RandomForestRegressor(
            n_estimators=150,
            max_depth=None,
            min_samples_leaf=2,
            random_state=seed,
            n_jobs=1,
        )
        rf.fit(X_scaled, y)

        # Generate random candidate pool
        cand = lo + rng.random((n_candidates, d)) * (hi - lo)
        n_surrogate_evals += n_candidates

        # Score: mean + alpha * std (upper confidence bound style)
        mu = rf.predict(cand)
        sigma = _rf_uncertainty(rf, cand)
        acquisition = mu + alpha * sigma

        # Pick top batch_size candidates (with deduplication by distance)
        top_idx = np.argsort(-acquisition)
        selected: list[int] = []
        for idx in top_idx:
            if len(selected) >= batch_size:
                break
            x_cand = cand[idx]
            if selected:
                dists = np.linalg.norm(
                    cand[selected] - x_cand, axis=1
                )
                if np.min(dists) < 1e-6 * np.linalg.norm(hi - lo):
                    continue
            selected.append(int(idx))

        # Pad with random if deduplication left us short
        while len(selected) < batch_size:
            idx = int(rng.integers(n_candidates))
            if idx not in selected:
                selected.append(idx)

        # Evaluate selected candidates
        new_X = cand[selected]
        new_y = np.zeros(len(selected), dtype=np.float64)
        for j, sel in enumerate(selected):
            x_eval = cand[sel]
            cs = parameterization(x_eval)
            res = analyze_constraints(cs)
            val = _objective_value(res, objective)
            new_y[j] = val
            history.append((x_eval.copy(), val))
            if val > best_val:
                best_val = val
                best_x = x_eval.copy()
                best_rating = res
            n_evals += 1
            if progress_callback is not None:
                progress_callback(n_evals, total_budget, best_val)

        X_scaled = np.vstack([X_scaled, new_X])
        y = np.append(y, new_y)

    # --- Final model quality ---
    rf_final = RandomForestRegressor(
        n_estimators=150, max_depth=None, min_samples_leaf=2,
        random_state=seed, n_jobs=1,
    )
    rf_final.fit(X_scaled, y)
    y_pred = rf_final.predict(X_scaled)
    ss_res = float(np.sum((y - y_pred) ** 2))
    ss_tot = float(np.sum((y - np.mean(y)) ** 2))
    r2 = 1.0 - ss_res / ss_tot if ss_tot > 0 else 0.0

    if best_rating is None:
        best_constraints = parameterization(best_x)
        best_rating = analyze_constraints(best_constraints)
    else:
        best_constraints = parameterization(best_x)

    return SurrogateResult(
        best_x=best_x,
        best_constraints=best_constraints,
        best_rating=best_rating,
        n_real_evals=n_evals,
        n_surrogate_evals=n_surrogate_evals,
        model_r2=r2,
        history=history,
    )
