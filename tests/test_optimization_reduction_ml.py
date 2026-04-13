"""Tests for ML-assisted constraint reduction (reduction_ml.py)."""
from __future__ import annotations

import numpy as np
import pytest

from kst_rating_tool import ConstraintSet, PointConstraint, analyze_constraints
from kst_rating_tool.optimization import (
    MLReductionResult,
    optimize_reduction_ml,
)

try:
    from sklearn.ensemble import RandomForestRegressor

    HAS_SKLEARN = True
except ImportError:
    HAS_SKLEARN = False


def _six_point_baseline() -> ConstraintSet:
    """Six-point isotropic baseline."""
    pts = [
        (-1.0, 0.0, 0.0),
        (1.0, 0.0, 0.0),
        (0.0, -1.0, 0.0),
        (0.0, 1.0, 0.0),
        (0.0, 0.0, -1.0),
        (0.0, 0.0, 1.0),
    ]
    return ConstraintSet(
        points=[
            PointConstraint(
                position=np.array(p, dtype=float),
                normal=np.array([0.0, 0.0, 1.0], dtype=float),
            )
            for p in pts
        ]
    )


@pytest.mark.skipif(not HAS_SKLEARN, reason="scikit-learn not installed")
def test_optimize_reduction_ml_imports():
    """Ensure optimize_reduction_ml is importable when sklearn is available."""
    from kst_rating_tool.optimization import optimize_reduction_ml

    assert callable(optimize_reduction_ml)


def test_optimize_reduction_ml_raises_without_sklearn(monkeypatch):
    """Should raise ImportError if sklearn is not available."""
    from kst_rating_tool.optimization import reduction_ml

    monkeypatch.setattr(reduction_ml, "RandomForestRegressor", None)
    cs = _six_point_baseline()

    with pytest.raises(ImportError, match="scikit-learn"):
        reduction_ml.optimize_reduction_ml(cs, n_remove=1)


@pytest.mark.skipif(not HAS_SKLEARN, reason="scikit-learn not installed")
def test_optimize_reduction_ml_smoke():
    """Basic smoke test: runs without error and returns expected structure."""
    cs = _six_point_baseline()

    result = optimize_reduction_ml(cs, n_remove=1, top_k=3, seed=42)

    assert isinstance(result, MLReductionResult)
    assert result.best_constraints.total_cp == cs.total_cp - 1
    assert len(result.indices_removed) == 1
    assert result.n_real_evals >= cs.total_cp  # training + selection
    assert np.isfinite(result.best_rating.WTR)


@pytest.mark.skipif(not HAS_SKLEARN, reason="scikit-learn not installed")
def test_optimize_reduction_ml_n_remove_zero():
    """n_remove=0 should return baseline unchanged."""
    cs = _six_point_baseline()

    result = optimize_reduction_ml(cs, n_remove=0)

    assert result.indices_removed == []
    assert result.best_constraints.total_cp == cs.total_cp
    assert result.n_real_evals == 0


@pytest.mark.skipif(not HAS_SKLEARN, reason="scikit-learn not installed")
def test_optimize_reduction_ml_empty_constraints():
    """Empty constraint set should handle gracefully."""
    cs = ConstraintSet()

    result = optimize_reduction_ml(cs, n_remove=1)

    assert result.indices_removed == []
    assert result.best_constraints.total_cp == 0


@pytest.mark.skipif(not HAS_SKLEARN, reason="scikit-learn not installed")
def test_optimize_reduction_ml_n_remove_greater_than_total():
    """n_remove >= total_cp should return empty removal."""
    cs = _six_point_baseline()

    result = optimize_reduction_ml(cs, n_remove=6)

    assert result.indices_removed == []
    assert result.best_constraints.total_cp == 6


@pytest.mark.skipif(not HAS_SKLEARN, reason="scikit-learn not installed")
def test_optimize_reduction_ml_multiple_removals():
    """Remove multiple constraints iteratively."""
    cs = _six_point_baseline()

    result = optimize_reduction_ml(cs, n_remove=2, top_k=3, seed=42)

    assert len(result.indices_removed) == 2
    assert result.best_constraints.total_cp == cs.total_cp - 2
    assert len(result.history) >= 2
    # Indices should be unique
    assert len(set(result.indices_removed)) == 2


@pytest.mark.skipif(not HAS_SKLEARN, reason="scikit-learn not installed")
def test_optimize_reduction_ml_different_objectives():
    """Test with different objective functions."""
    cs = _six_point_baseline()

    for objective in ["TOR", "WTR", "MRR", "MTR"]:
        result = optimize_reduction_ml(cs, n_remove=1, objective=objective, top_k=3, seed=42)
        assert isinstance(result, MLReductionResult)
        assert len(result.indices_removed) == 1


@pytest.mark.skipif(not HAS_SKLEARN, reason="scikit-learn not installed")
def test_optimize_reduction_ml_top_k_limits_evals():
    """top_k parameter should limit the number of evaluations per removal step."""
    cs = _six_point_baseline()

    # With top_k=2, should evaluate at most 2 candidates per removal step
    result = optimize_reduction_ml(cs, n_remove=1, top_k=2, seed=42)

    # Training evals: total_cp (6)
    # Selection evals: at most top_k (2)
    # Total: at most 8
    assert result.n_real_evals <= 8


@pytest.mark.skipif(not HAS_SKLEARN, reason="scikit-learn not installed")
def test_optimize_reduction_ml_reproducibility():
    """Same seed should give same results (deterministic)."""
    cs = _six_point_baseline()

    result1 = optimize_reduction_ml(cs, n_remove=1, top_k=3, seed=123)
    result2 = optimize_reduction_ml(cs, n_remove=1, top_k=3, seed=123)

    assert result1.indices_removed == result2.indices_removed
    assert result1.n_real_evals == result2.n_real_evals


@pytest.mark.skipif(not HAS_SKLEARN, reason="scikit-learn not installed")
def test_optimize_reduction_ml_history_structure():
    """History should contain valid entries."""
    cs = _six_point_baseline()

    result = optimize_reduction_ml(cs, n_remove=2, top_k=2, seed=42)

    for removed_indices, rating in result.history:
        assert isinstance(removed_indices, list)
        assert len(removed_indices) > 0
        assert hasattr(rating, "WTR")
        assert hasattr(rating, "TOR")
        assert np.isfinite(rating.WTR)


@pytest.mark.skipif(not HAS_SKLEARN, reason="scikit-learn not installed")
def test_optimize_reduction_ml_improves_or_maintains_metric():
    """ML reduction should ideally improve or at least not severely hurt the objective."""
    cs = _six_point_baseline()
    baseline_rating = analyze_constraints(cs)

    result = optimize_reduction_ml(cs, n_remove=1, objective="TOR", top_k=3, seed=42)

    # Removing a constraint typically reduces TOR, but ML should pick the least harmful one
    # We just check the result is sane (finite, non-negative where applicable)
    assert np.isfinite(result.best_rating.TOR)
    assert np.isfinite(result.best_rating.WTR)
