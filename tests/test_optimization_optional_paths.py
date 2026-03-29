from __future__ import annotations

import numpy as np

from kst_rating_tool import ConstraintSet, PointConstraint
from kst_rating_tool.optimization import reduction_ml, surrogate
from kst_rating_tool.rating import RatingResults


def _make_constraints(n_points: int = 6) -> ConstraintSet:
    pts = [
        PointConstraint(
            position=np.array([float(i), 0.0, 0.0], dtype=float),
            normal=np.array([0.0, 0.0, 1.0], dtype=float),
        )
        for i in range(n_points)
    ]
    return ConstraintSet(points=pts)


def _fake_rating(score: float) -> RatingResults:
    R = np.full((1, 1), np.inf, dtype=float)
    Ri = np.zeros((1, 1), dtype=float)
    return RatingResults(R=R, Ri=Ri, WTR=score, MRR=score, MTR=score, TOR=score)


def test_surrogate_raises_importerror_without_sklearn(monkeypatch):
    monkeypatch.setattr(surrogate, "RandomForestRegressor", None)

    def parameterization(x: np.ndarray) -> ConstraintSet:
        return _make_constraints(6 if float(x[0]) >= 0 else 5)

    try:
        surrogate.optimize_modification_surrogate(
            parameterization=parameterization,
            bounds=[(-1.0, 1.0)],
            n_samples=4,
            n_validate=2,
            n_surrogate_evals=20,
            seed=1,
        )
    except ImportError:
        return
    raise AssertionError("Expected ImportError when scikit-learn is unavailable")


def test_reduction_ml_raises_importerror_without_sklearn(monkeypatch):
    monkeypatch.setattr(reduction_ml, "RandomForestRegressor", None)
    constraints = _make_constraints()

    try:
        reduction_ml.optimize_reduction_ml(constraints=constraints, n_remove=1, top_k=2, seed=1)
    except ImportError:
        return
    raise AssertionError("Expected ImportError when scikit-learn is unavailable")


def test_surrogate_and_ml_reduction_smoke_with_small_inputs(monkeypatch):
    if surrogate.RandomForestRegressor is None or reduction_ml.RandomForestRegressor is None:
        return

    def fake_analyze_constraints(constraints: ConstraintSet) -> RatingResults:
        # Lower total_cp should produce lower objective; this keeps optimization deterministic.
        return _fake_rating(float(constraints.total_cp))

    monkeypatch.setattr(surrogate, "analyze_constraints", fake_analyze_constraints)
    monkeypatch.setattr(reduction_ml, "analyze_constraints", fake_analyze_constraints)

    def parameterization(x: np.ndarray) -> ConstraintSet:
        return _make_constraints(6 if float(x[0]) >= 0 else 5)

    sur_res = surrogate.optimize_modification_surrogate(
        parameterization=parameterization,
        bounds=[(-1.0, 1.0)],
        objective="TOR",
        n_samples=4,
        n_validate=2,
        n_surrogate_evals=20,
        seed=1,
    )
    assert sur_res.n_real_evals >= 6
    assert sur_res.best_constraints.total_cp in (5, 6)

    red_res = reduction_ml.optimize_reduction_ml(
        constraints=_make_constraints(6),
        n_remove=1,
        objective="TOR",
        top_k=2,
        seed=1,
    )
    assert len(red_res.indices_removed) == 1
    assert red_res.best_constraints.total_cp == 5
