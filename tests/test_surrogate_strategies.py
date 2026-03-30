"""Tests for surrogate optimization strategies: adaptive RF, BO, and Pareto."""

from __future__ import annotations

import numpy as np
import pytest

from kst_rating_tool import ConstraintSet, PointConstraint
from kst_rating_tool.optimization import surrogate
from kst_rating_tool.rating import RatingResults

try:
    from kst_rating_tool.optimization import surrogate_bo
except ImportError:
    surrogate_bo = None  # type: ignore[assignment]

try:
    from kst_rating_tool.optimization import surrogate_pareto
except ImportError:
    surrogate_pareto = None  # type: ignore[assignment]


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


def _parameterization(x: np.ndarray) -> ConstraintSet:
    """Maps x[0] in [-1, 1] to a constraint set; score is a smooth function of x."""
    return _make_constraints(6 if float(x[0]) >= 0 else 5)


def _smooth_fake_analyze(constraints: ConstraintSet) -> RatingResults:
    """Fake analysis that produces a score based on geometry (smooth-ish)."""
    if not constraints.points:
        return _fake_rating(0.0)
    avg_x = float(np.mean([p.position[0] for p in constraints.points]))
    score = 10.0 - (avg_x - 2.5) ** 2
    return _fake_rating(max(0.0, score))


def _multi_metric_fake_analyze(constraints: ConstraintSet) -> RatingResults:
    """Fake analysis with conflicting metrics (for Pareto tests)."""
    if not constraints.points:
        return _fake_rating(0.0)
    n = constraints.total_cp
    avg_x = float(np.mean([p.position[0] for p in constraints.points]))
    wtr = max(0.0, 10.0 - avg_x ** 2)
    mrr = max(0.0, avg_x * 2.0)
    mtr = max(0.0, 5.0 + avg_x)
    tor = mtr / mrr if mrr > 0 else 0.0
    R = np.full((1, 1), np.inf, dtype=float)
    Ri = np.zeros((1, 1), dtype=float)
    return RatingResults(R=R, Ri=Ri, WTR=wtr, MRR=mrr, MTR=mtr, TOR=tor)


# --- Adaptive RF tests ---


class TestAdaptiveRF:
    def test_raises_importerror_without_sklearn(self, monkeypatch):
        monkeypatch.setattr(surrogate, "RandomForestRegressor", None)
        with pytest.raises(ImportError, match="scikit-learn"):
            surrogate.optimize_surrogate_adaptive(
                parameterization=_parameterization,
                bounds=[(-1.0, 1.0)],
                n_initial=4,
                n_iter=2,
                batch_size=2,
                seed=1,
            )

    def test_smoke_with_mocked_analyze(self, monkeypatch):
        if surrogate.RandomForestRegressor is None:
            pytest.skip("scikit-learn not installed")

        monkeypatch.setattr(surrogate, "analyze_constraints", _smooth_fake_analyze)

        result = surrogate.optimize_surrogate_adaptive(
            parameterization=_parameterization,
            bounds=[(-1.0, 1.0)],
            objective="TOR",
            n_initial=10,
            n_iter=3,
            batch_size=3,
            n_candidates=50,
            alpha=1.0,
            seed=42,
        )

        assert result.n_real_evals == 10 + 3 * 3
        assert result.best_constraints.total_cp in (5, 6)
        assert result.best_rating.TOR >= 0.0
        assert len(result.history) == result.n_real_evals
        assert 0.0 <= result.model_r2 <= 1.0

    def test_progress_callback_called(self, monkeypatch):
        if surrogate.RandomForestRegressor is None:
            pytest.skip("scikit-learn not installed")

        monkeypatch.setattr(surrogate, "analyze_constraints", _smooth_fake_analyze)

        calls: list[tuple[int, int, float]] = []

        def callback(n: int, total: int, best: float) -> None:
            calls.append((n, total, best))

        surrogate.optimize_surrogate_adaptive(
            parameterization=_parameterization,
            bounds=[(-1.0, 1.0)],
            n_initial=5,
            n_iter=2,
            batch_size=2,
            seed=1,
            progress_callback=callback,
        )

        expected_total = 5 + 2 * 2
        assert len(calls) == expected_total
        assert calls[0][0] == 1
        assert calls[-1][0] == expected_total
        assert all(c[1] == expected_total for c in calls)

    def test_multidimensional(self, monkeypatch):
        """Adaptive RF works with multi-D bounds."""
        if surrogate.RandomForestRegressor is None:
            pytest.skip("scikit-learn not installed")

        def param_2d(x: np.ndarray) -> ConstraintSet:
            n = max(3, int(6 - abs(x[0]) - abs(x[1])))
            return _make_constraints(n)

        monkeypatch.setattr(surrogate, "analyze_constraints", _smooth_fake_analyze)

        result = surrogate.optimize_surrogate_adaptive(
            parameterization=param_2d,
            bounds=[(-1.0, 1.0), (-1.0, 1.0)],
            n_initial=15,
            n_iter=3,
            batch_size=3,
            n_candidates=100,
            seed=7,
        )

        assert result.n_real_evals == 15 + 3 * 3
        assert result.best_rating.TOR >= 0.0


# --- Bayesian Optimization tests ---


class TestBayesianOptimization:
    def test_module_importable(self):
        if surrogate_bo is None:
            pytest.skip("surrogate_bo could not be imported (sklearn missing?)")
        assert hasattr(surrogate_bo, "optimize_bo")
        assert hasattr(surrogate_bo, "BOResult")

    def test_raises_importerror_without_sklearn(self, monkeypatch):
        if surrogate_bo is None:
            pytest.skip("surrogate_bo could not be imported")
        monkeypatch.setattr(surrogate_bo, "GaussianProcessRegressor", None)
        with pytest.raises(ImportError, match="scikit-learn"):
            surrogate_bo.optimize_bo(
                parameterization=_parameterization,
                bounds=[(-1.0, 1.0)],
                n_initial=4,
                n_iter=2,
                seed=1,
            )

    def test_smoke_with_mocked_analyze(self, monkeypatch):
        if surrogate_bo is None:
            pytest.skip("surrogate_bo could not be imported")
        if surrogate_bo.GaussianProcessRegressor is None:
            pytest.skip("scikit-learn not installed")

        monkeypatch.setattr(surrogate_bo, "analyze_constraints", _smooth_fake_analyze)

        result = surrogate_bo.optimize_bo(
            parameterization=_parameterization,
            bounds=[(-1.0, 1.0)],
            objective="TOR",
            n_initial=8,
            n_iter=5,
            batch_size=1,
            seed=42,
        )

        assert result.n_real_evals == 8 + 5
        assert result.best_constraints.total_cp in (5, 6)
        assert result.best_rating.TOR >= 0.0
        assert len(result.history) == result.n_real_evals
        assert isinstance(result.model_r2, float)

    def test_progress_callback(self, monkeypatch):
        if surrogate_bo is None:
            pytest.skip("surrogate_bo could not be imported")
        if surrogate_bo.GaussianProcessRegressor is None:
            pytest.skip("scikit-learn not installed")

        monkeypatch.setattr(surrogate_bo, "analyze_constraints", _smooth_fake_analyze)

        calls: list[tuple[int, int, float]] = []

        def callback(n: int, total: int, best: float) -> None:
            calls.append((n, total, best))

        surrogate_bo.optimize_bo(
            parameterization=_parameterization,
            bounds=[(-1.0, 1.0)],
            n_initial=5,
            n_iter=3,
            seed=1,
            progress_callback=callback,
        )

        expected_total = 5 + 3
        assert len(calls) == expected_total
        assert calls[-1][0] == expected_total

    def test_batch_mode(self, monkeypatch):
        """BO with batch_size > 1 (kriging believer)."""
        if surrogate_bo is None:
            pytest.skip("surrogate_bo could not be imported")
        if surrogate_bo.GaussianProcessRegressor is None:
            pytest.skip("scikit-learn not installed")

        monkeypatch.setattr(surrogate_bo, "analyze_constraints", _smooth_fake_analyze)

        result = surrogate_bo.optimize_bo(
            parameterization=_parameterization,
            bounds=[(-1.0, 1.0)],
            n_initial=6,
            n_iter=2,
            batch_size=3,
            seed=42,
        )

        assert result.n_real_evals == 6 + 2 * 3
        assert result.best_rating.TOR >= 0.0

    def test_2d_optimization(self, monkeypatch):
        """BO works in 2D."""
        if surrogate_bo is None:
            pytest.skip("surrogate_bo could not be imported")
        if surrogate_bo.GaussianProcessRegressor is None:
            pytest.skip("scikit-learn not installed")

        def param_2d(x: np.ndarray) -> ConstraintSet:
            n = max(3, int(6 - abs(x[0]) - abs(x[1])))
            return _make_constraints(n)

        monkeypatch.setattr(surrogate_bo, "analyze_constraints", _smooth_fake_analyze)

        result = surrogate_bo.optimize_bo(
            parameterization=param_2d,
            bounds=[(-1.0, 1.0), (-1.0, 1.0)],
            n_initial=10,
            n_iter=5,
            seed=7,
        )

        assert result.n_real_evals == 15
        assert result.best_rating.TOR >= 0.0


# --- Expected Improvement unit test ---


class TestExpectedImprovement:
    def test_ei_positive_for_improvement(self):
        if surrogate_bo is None:
            pytest.skip("surrogate_bo could not be imported")
        if surrogate_bo.GaussianProcessRegressor is None:
            pytest.skip("scikit-learn not installed")

        from sklearn.gaussian_process import GaussianProcessRegressor
        from sklearn.gaussian_process.kernels import RBF

        X_train = np.array([[0.0], [1.0], [2.0]])
        y_train = np.array([1.0, 3.0, 2.0])
        gp = GaussianProcessRegressor(kernel=RBF(), alpha=1e-6)
        gp.fit(X_train, y_train)

        X_test = np.linspace(-1, 3, 50).reshape(-1, 1)
        ei = surrogate_bo._expected_improvement(X_test, gp, y_best=3.0, xi=0.01)

        assert ei.shape == (50,)
        assert np.all(ei >= 0.0)
        assert np.max(ei) > 0.0


# --- Latin Hypercube tests ---


class TestLHS:
    def test_lhs_range(self):
        X = surrogate._latin_hypercube(100, 3, seed=0)
        assert X.shape == (100, 3)
        assert np.all(X >= -1.0)
        assert np.all(X <= 1.0)

    def test_lhs_stratification(self):
        """Each column should have roughly one point per stratum."""
        n = 100
        X = surrogate._latin_hypercube(n, 2, seed=42)
        for j in range(2):
            bins = np.floor((X[:, j] + 1.0) / 2.0 * n).astype(int)
            bins = np.clip(bins, 0, n - 1)
            assert len(np.unique(bins)) == n

    def test_bo_lhs_range(self):
        if surrogate_bo is None:
            pytest.skip("surrogate_bo not available")
        X = surrogate_bo._latin_hypercube(50, 2, seed=0)
        assert X.shape == (50, 2)
        assert np.all(X >= -1.0)
        assert np.all(X <= 1.0)


# --- Non-dominated sorting tests ---


class TestNonDominatedSort:
    def test_simple_2d(self):
        if surrogate_pareto is None:
            pytest.skip("surrogate_pareto not available")
        Y = np.array([
            [1.0, 5.0],
            [3.0, 3.0],
            [5.0, 1.0],
            [2.0, 2.0],
        ])
        mask = surrogate_pareto._non_dominated_sort(Y)
        assert mask[0]   # (1, 5) is non-dominated
        assert mask[1]   # (3, 3) is non-dominated
        assert mask[2]   # (5, 1) is non-dominated
        assert not mask[3]  # (2, 2) is dominated by (3, 3)

    def test_single_point(self):
        if surrogate_pareto is None:
            pytest.skip("surrogate_pareto not available")
        Y = np.array([[1.0, 2.0]])
        mask = surrogate_pareto._non_dominated_sort(Y)
        assert mask[0]

    def test_all_identical(self):
        if surrogate_pareto is None:
            pytest.skip("surrogate_pareto not available")
        Y = np.array([[1.0, 1.0], [1.0, 1.0], [1.0, 1.0]])
        mask = surrogate_pareto._non_dominated_sort(Y)
        assert np.all(mask)


# --- Pareto optimization tests ---


class TestParetoOptimization:
    def test_module_importable(self):
        if surrogate_pareto is None:
            pytest.skip("surrogate_pareto not available")
        assert hasattr(surrogate_pareto, "optimize_pareto")
        assert hasattr(surrogate_pareto, "ParetoResult")
        assert hasattr(surrogate_pareto, "ParetoPoint")

    def test_raises_importerror_without_sklearn(self, monkeypatch):
        if surrogate_pareto is None:
            pytest.skip("surrogate_pareto not available")
        monkeypatch.setattr(surrogate_pareto, "RandomForestRegressor", None)
        with pytest.raises(ImportError, match="scikit-learn"):
            surrogate_pareto.optimize_pareto(
                parameterization=_parameterization,
                bounds=[(-1.0, 1.0)],
                n_initial=4,
                n_iter=1,
                batch_size=2,
                n_validate=2,
                seed=1,
            )

    def test_smoke_with_mocked_analyze(self, monkeypatch):
        if surrogate_pareto is None:
            pytest.skip("surrogate_pareto not available")
        if surrogate_pareto.RandomForestRegressor is None:
            pytest.skip("scikit-learn not installed")

        monkeypatch.setattr(
            surrogate_pareto, "analyze_constraints", _multi_metric_fake_analyze
        )

        result = surrogate_pareto.optimize_pareto(
            parameterization=_parameterization,
            bounds=[(-1.0, 1.0)],
            n_initial=15,
            n_iter=2,
            batch_size=3,
            n_candidates=50,
            n_validate=5,
            seed=42,
        )

        assert result.n_real_evals >= 15 + 2 * 3
        assert len(result.pareto_front) >= 1
        for pp in result.pareto_front:
            assert pp.metrics.shape == (4,)
            assert pp.rating.WTR >= 0.0

    def test_subset_objectives(self, monkeypatch):
        """Pareto with only WTR and MRR."""
        if surrogate_pareto is None:
            pytest.skip("surrogate_pareto not available")
        if surrogate_pareto.RandomForestRegressor is None:
            pytest.skip("scikit-learn not installed")

        monkeypatch.setattr(
            surrogate_pareto, "analyze_constraints", _multi_metric_fake_analyze
        )

        result = surrogate_pareto.optimize_pareto(
            parameterization=_parameterization,
            bounds=[(-1.0, 1.0)],
            objectives=["WTR", "MRR"],
            n_initial=10,
            n_iter=1,
            batch_size=3,
            n_candidates=50,
            n_validate=5,
            seed=7,
        )

        assert len(result.pareto_front) >= 1

    def test_progress_callback(self, monkeypatch):
        if surrogate_pareto is None:
            pytest.skip("surrogate_pareto not available")
        if surrogate_pareto.RandomForestRegressor is None:
            pytest.skip("scikit-learn not installed")

        monkeypatch.setattr(
            surrogate_pareto, "analyze_constraints", _multi_metric_fake_analyze
        )

        calls: list[tuple[int, int]] = []

        def callback(n: int, total: int) -> None:
            calls.append((n, total))

        surrogate_pareto.optimize_pareto(
            parameterization=_parameterization,
            bounds=[(-1.0, 1.0)],
            n_initial=5,
            n_iter=1,
            batch_size=2,
            n_candidates=30,
            n_validate=3,
            seed=1,
            progress_callback=callback,
        )

        assert len(calls) >= 5 + 2
        assert calls[0][0] == 1
