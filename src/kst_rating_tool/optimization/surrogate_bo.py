"""Bayesian Optimization surrogate using Gaussian Processes.

Sequential model-based optimization: fit a GP, maximize an acquisition function
(Expected Improvement) to select the next evaluation point, update, repeat.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Literal, Protocol

import numpy as np
from numpy.typing import NDArray
from scipy.optimize import differential_evolution
from scipy.stats import norm

from ..constraints import ConstraintSet
from ..pipeline import analyze_constraints
from ..rating import RatingResults

try:
    from sklearn.gaussian_process import GaussianProcessRegressor
    from sklearn.gaussian_process.kernels import Matern, WhiteKernel, ConstantKernel
except ImportError:
    GaussianProcessRegressor = None  # type: ignore[misc, assignment]
    Matern = None  # type: ignore[misc, assignment]
    WhiteKernel = None  # type: ignore[misc, assignment]
    ConstantKernel = None  # type: ignore[misc, assignment]


class Parameterization(Protocol):
    """Callable that maps x in bounds to a ConstraintSet."""

    def __call__(self, x: np.ndarray) -> ConstraintSet: ...


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
class BOResult:
    """Result of Bayesian Optimization."""

    best_x: NDArray[np.float64]
    best_constraints: ConstraintSet
    best_rating: RatingResults
    n_real_evals: int
    model_r2: float = 0.0
    history: list[tuple[NDArray[np.float64], float]] = field(default_factory=list)


def _latin_hypercube(n: int, d: int, seed: int | None = None) -> NDArray[np.float64]:
    """Sample n points in [0, 1]^d using Latin hypercube, then scale to [-1, 1]."""
    rng = np.random.default_rng(seed)
    out = np.zeros((n, d), dtype=np.float64)
    for j in range(d):
        perm = rng.permutation(n)
        out[:, j] = (perm + rng.uniform(0, 1, size=n)) / n
    return out * 2.0 - 1.0


def _scale_to_bounds(
    X: NDArray[np.float64], bounds: list[tuple[float, float]]
) -> NDArray[np.float64]:
    """Scale X from [-1, 1]^d to actual bounds."""
    lo = np.array([b[0] for b in bounds], dtype=np.float64)
    hi = np.array([b[1] for b in bounds], dtype=np.float64)
    return lo + (X + 1.0) / 2.0 * (hi - lo)


def _scale_from_bounds(
    X: NDArray[np.float64], bounds: list[tuple[float, float]]
) -> NDArray[np.float64]:
    """Scale X from actual bounds to [-1, 1]^d (for GP in unit space)."""
    lo = np.array([b[0] for b in bounds], dtype=np.float64)
    hi = np.array([b[1] for b in bounds], dtype=np.float64)
    return 2.0 * (X - lo) / (hi - lo) - 1.0


def _expected_improvement(
    X: NDArray[np.float64],
    gp: "GaussianProcessRegressor",
    y_best: float,
    xi: float = 0.01,
) -> NDArray[np.float64]:
    """Expected Improvement acquisition function (to maximize).

    Parameters
    ----------
    X : (n, d) candidate points (in GP's input space).
    gp : fitted GaussianProcessRegressor.
    y_best : best observed objective value so far.
    xi : exploration-exploitation trade-off (higher = more exploration).
    """
    mu, sigma = gp.predict(X, return_std=True)
    sigma = np.maximum(sigma, 1e-12)
    improvement = mu - y_best - xi
    Z = improvement / sigma
    ei = improvement * norm.cdf(Z) + sigma * norm.pdf(Z)
    return ei


def optimize_bo(
    parameterization: Parameterization,
    bounds: list[tuple[float, float]],
    objective: str = "TOR",
    n_initial: int = 30,
    n_iter: int = 70,
    batch_size: int = 1,
    xi: float = 0.01,
    seed: int | None = None,
    progress_callback: ProgressCallback | None = None,
) -> BOResult:
    """Bayesian Optimization with Gaussian Process surrogate.

    Sequential model-based optimization loop:
    1. Evaluate `n_initial` LHS points with the real pipeline.
    2. Fit a GP (Matern-5/2 kernel + noise).
    3. For `n_iter` iterations: maximize Expected Improvement to pick the next
       point, evaluate it, update the GP.
    4. Return the best observed design.

    Total real evaluations: `n_initial + n_iter * batch_size`.

    Parameters
    ----------
    parameterization
        Maps x (in bounds) to a ConstraintSet.
    bounds
        Per-dimension (low, high) bounds.
    objective
        Metric to maximize: 'TOR', 'WTR', 'MRR', or 'MTR'.
    n_initial
        Number of initial LHS samples for the DoE.
    n_iter
        Number of BO iterations (each adds `batch_size` real evaluations).
    batch_size
        Evaluations per BO iteration.  >1 uses a simple kriging-believer
        heuristic (predict the batch point as "observed" to diversify).
    xi
        Expected Improvement exploration parameter.
    seed
        Random seed.
    progress_callback
        Called as callback(eval_number, total_evals, best_so_far) after each
        real evaluation.

    Returns
    -------
    BOResult
    """
    if GaussianProcessRegressor is None:
        raise ImportError(
            "optimize_bo requires scikit-learn; "
            "install with: pip install scikit-learn"
        )

    d = len(bounds)
    total_budget = n_initial + n_iter * batch_size
    rng = np.random.default_rng(seed)

    # --- Phase 1: initial DoE ---
    X_init_unit = _latin_hypercube(n_initial, d, seed=seed)
    X_init = _scale_to_bounds(X_init_unit, bounds)

    X_all = np.empty((0, d), dtype=np.float64)
    y_all = np.empty(0, dtype=np.float64)
    history: list[tuple[NDArray[np.float64], float]] = []

    best_val = float("-inf")
    best_x = X_init[0].copy()
    best_rating: RatingResults | None = None

    for i in range(n_initial):
        x = X_init[i]
        cs = parameterization(x)
        res = analyze_constraints(cs)
        val = _objective_value(res, objective)

        X_all = np.vstack([X_all, x.reshape(1, -1)]) if X_all.size else x.reshape(1, -1)
        y_all = np.append(y_all, val)
        history.append((x.copy(), val))

        if val > best_val:
            best_val = val
            best_x = x.copy()
            best_rating = res

        if progress_callback is not None:
            progress_callback(i + 1, total_budget, best_val)

    # --- Phase 2: GP-based sequential optimization ---
    kernel = ConstantKernel(1.0, (1e-3, 1e3)) * Matern(
        length_scale=np.ones(d), length_scale_bounds=(1e-2, 1e2), nu=2.5
    ) + WhiteKernel(noise_level=1e-4, noise_level_bounds=(1e-10, 1e1))

    gp = GaussianProcessRegressor(
        kernel=kernel,
        n_restarts_optimizer=5,
        random_state=seed,
        normalize_y=True,
        alpha=1e-8,
    )

    X_unit = _scale_from_bounds(X_all, bounds)
    gp.fit(X_unit, y_all)
    unit_bounds = [(-1.0, 1.0)] * d

    n_evals = n_initial
    for iteration in range(n_iter):
        candidates_for_batch: list[NDArray[np.float64]] = []
        gp_copy_y = y_all.copy()
        gp_copy_X = X_unit.copy()

        for _ in range(batch_size):
            y_best_so_far = float(np.max(gp_copy_y))

            def neg_ei(x_unit: NDArray[np.float64]) -> float:
                ei = _expected_improvement(
                    x_unit.reshape(1, -1), gp, y_best_so_far, xi=xi
                )
                return -float(ei[0])

            de_result = differential_evolution(
                neg_ei,
                unit_bounds,
                maxiter=max(20, 100 // d),
                popsize=max(5, min(15, 3 * d)),
                seed=rng,
                tol=1e-7,
                atol=1e-7,
                updating="deferred",
                workers=1,
                disp=False,
            )

            next_x_unit = de_result.x.reshape(1, -1)
            candidates_for_batch.append(next_x_unit[0])

            if batch_size > 1:
                pred_val = gp.predict(next_x_unit)[0]
                gp_copy_X = np.vstack([gp_copy_X, next_x_unit])
                gp_copy_y = np.append(gp_copy_y, pred_val)
                gp.fit(gp_copy_X, gp_copy_y)

        for x_unit in candidates_for_batch:
            x_real = _scale_to_bounds(x_unit.reshape(1, -1), bounds)[0]
            cs = parameterization(x_real)
            res = analyze_constraints(cs)
            val = _objective_value(res, objective)

            X_all = np.vstack([X_all, x_real.reshape(1, -1)])
            y_all = np.append(y_all, val)
            X_unit = np.vstack([X_unit, x_unit.reshape(1, -1)])
            history.append((x_real.copy(), val))

            if val > best_val:
                best_val = val
                best_x = x_real.copy()
                best_rating = res

            n_evals += 1
            if progress_callback is not None:
                progress_callback(n_evals, total_budget, best_val)

        gp.fit(X_unit, y_all)

    # --- Compute model quality metric ---
    y_pred = gp.predict(X_unit)
    ss_res = float(np.sum((y_all - y_pred) ** 2))
    ss_tot = float(np.sum((y_all - np.mean(y_all)) ** 2))
    r2 = 1.0 - ss_res / ss_tot if ss_tot > 0 else 0.0

    if best_rating is None:
        best_constraints = parameterization(best_x)
        best_rating = analyze_constraints(best_constraints)
    else:
        best_constraints = parameterization(best_x)

    return BOResult(
        best_x=best_x,
        best_constraints=best_constraints,
        best_rating=best_rating,
        n_real_evals=n_evals,
        model_r2=r2,
        history=history,
    )
