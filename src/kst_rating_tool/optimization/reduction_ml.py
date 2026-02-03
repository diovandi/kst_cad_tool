"""ML-assisted constraint reduction: rank removal candidates with a model, evaluate top-k."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal, Sequence

import numpy as np
from numpy.typing import NDArray

from ..constraints import ConstraintSet
from ..pipeline import analyze_constraints
from ..rating import RatingResults

from .reduction import constraint_set_without, optimize_reduction

try:
    from sklearn.ensemble import RandomForestRegressor
except ImportError:
    RandomForestRegressor = None  # type: ignore[misc, assignment]


def _objective_value(results: RatingResults, objective: str) -> float:
    if objective == "TOR":
        return results.TOR if results.TOR != float("inf") else 0.0
    if objective == "WTR":
        return results.WTR
    if objective == "MRR":
        return results.MRR
    if objective == "MTR":
        return results.MTR
    raise ValueError(f"Unknown objective: {objective}")


def _constraint_features(constraints: ConstraintSet, global_index: int) -> NDArray[np.float64]:
    """Build a feature vector for one constraint (for 1-at-a-time removal prediction).

    Features: type one-hot (point=1,0,0,0; pin=0,1,0,0; line=0,0,1,0; plane=0,0,0,1),
    position/normal stats (mean, std of coords), index (normalized).
    """
    n_pt = len(constraints.points)
    n_pin = len(constraints.pins)
    n_lin = len(constraints.lines)
    n_pln = len(constraints.planes)
    total_cp = constraints.total_cp
    feat: list[float] = []
    # Type one-hot
    if global_index < n_pt:
        feat = [1.0, 0.0, 0.0, 0.0]
        p = constraints.points[global_index]
        pos = p.position
        nrm = p.normal
    elif global_index < n_pt + n_pin:
        feat = [0.0, 1.0, 0.0, 0.0]
        p = constraints.pins[global_index - n_pt]
        pos = p.center
        nrm = p.axis
    elif global_index < n_pt + n_pin + n_lin:
        feat = [0.0, 0.0, 1.0, 0.0]
        ln = constraints.lines[global_index - n_pt - n_pin]
        pos = ln.midpoint
        nrm = ln.constraint_dir
    else:
        feat = [0.0, 0.0, 0.0, 1.0]
        pl = constraints.planes[global_index - n_pt - n_pin - n_lin]
        pos = pl.midpoint
        nrm = pl.normal
    feat.extend([float(np.mean(pos)), float(np.std(pos) + 1e-12)])
    feat.extend([float(np.mean(nrm)), float(np.std(nrm) + 1e-12)])
    feat.append(float(global_index) / max(1, total_cp - 1))
    return np.array(feat, dtype=np.float64)


def _collect_training_data(
    constraints: ConstraintSet,
    objective: str = "TOR",
) -> tuple[NDArray[np.float64], NDArray[np.float64]]:
    """Run greedy 1-at-a-time removals and record (features, delta objective) per removal.

    Returns X (n_removals * total_cp, n_features), y (delta objective when that constraint removed).
    """
    total_cp = constraints.total_cp
    baseline = analyze_constraints(constraints)
    base_val = _objective_value(baseline, objective)
    X_list: list[NDArray[np.float64]] = []
    y_list: list[float] = []
    for idx in range(total_cp):
        reduced = constraint_set_without(constraints, [idx])
        res = analyze_constraints(reduced)
        val = _objective_value(res, objective)
        delta = val - base_val
        feat = _constraint_features(constraints, idx)
        X_list.append(feat)
        y_list.append(delta)
    X = np.vstack(X_list)
    y = np.array(y_list, dtype=np.float64)
    return X, y


@dataclass
class MLReductionResult:
    """Result of ML-assisted constraint reduction."""

    best_constraints: ConstraintSet
    best_rating: RatingResults
    indices_removed: list[int]
    n_real_evals: int
    history: list[tuple[list[int], RatingResults]] = field(default_factory=list)


def optimize_reduction_ml(
    constraints: ConstraintSet,
    n_remove: int,
    objective: str = "TOR",
    top_k: int = 50,
    seed: int | None = None,
) -> MLReductionResult:
    """Remove n_remove constraints using an ML ranker to reduce real evaluations.

    (1) Collect training data: for each constraint, remove it and record (features, delta TOR).
    (2) Train a Random Forest to predict delta TOR from features.
    (3) For n_remove > 1: generate candidate subsets (or use greedy with model ranking),
        score with the model, evaluate only top_k with the real pipeline; pick best.

    For n_remove == 1 we just use the model to rank and evaluate top_k removals.
    For n_remove > 1 we use greedy: at each step, score each remaining constraint with the
    model (predict delta if we remove it), try removing the top top_k candidates with
    real pipeline, pick best and remove it; repeat.

    Parameters
    ----------
    constraints
        Full constraint set.
    n_remove
        Number of constraints to remove.
    objective
        Metric to maximize: 'TOR', 'WTR', 'MRR', or 'MTR'.
    top_k
        Number of removal candidates to evaluate with the real pipeline per step.
    seed
        Random seed for RF.

    Returns
    -------
    MLReductionResult
        Best reduced ConstraintSet, ratings, indices removed, and eval count.
    """
    if RandomForestRegressor is None:
        raise ImportError("optimize_reduction_ml requires scikit-learn; install with pip install scikit-learn")

    total_cp = constraints.total_cp
    if n_remove >= total_cp or n_remove <= 0:
        return MLReductionResult(
            best_constraints=constraints,
            best_rating=analyze_constraints(constraints),
            indices_removed=[],
            n_real_evals=0,
            history=[],
        )

    # Collect training data (1-at-a-time removals)
    X, y = _collect_training_data(constraints, objective)
    rf = RandomForestRegressor(n_estimators=100, max_depth=10, random_state=seed, n_jobs=-1)
    rf.fit(X, y)
    n_real_evals = total_cp  # training

    removed: list[int] = []
    remaining = list(range(total_cp))
    history: list[tuple[list[int], RatingResults]] = []

    for _ in range(n_remove):
        if not remaining:
            break
        # Score each remaining constraint with the model (predict delta)
        feats = np.vstack([_constraint_features(constraints, idx) for idx in remaining])
        preds = rf.predict(feats)
        # Top top_k by predicted delta
        k = min(top_k, len(remaining))
        top_indices_in_remaining = np.argsort(-preds)[:k]
        best_metric = float("-inf")
        best_idx_in_remaining: int | None = None
        best_rating: RatingResults | None = None
        for pos in top_indices_in_remaining:
            idx = remaining[pos]
            candidate_removed = removed + [idx]
            reduced = constraint_set_without(constraints, candidate_removed)
            res = analyze_constraints(reduced)
            n_real_evals += 1
            history.append((list(candidate_removed), res))
            val = _objective_value(res, objective)
            if val > best_metric:
                best_metric = val
                best_idx_in_remaining = pos
                best_rating = res
        if best_idx_in_remaining is None or best_rating is None:
            break
        chosen = remaining[best_idx_in_remaining]
        removed.append(chosen)
        remaining.remove(chosen)

    best_constraints = constraint_set_without(constraints, removed)
    best_rating = analyze_constraints(best_constraints) if removed else analyze_constraints(constraints)
    return MLReductionResult(
        best_constraints=best_constraints,
        best_rating=best_rating,
        indices_removed=removed,
        n_real_evals=n_real_evals,
        history=history,
    )
