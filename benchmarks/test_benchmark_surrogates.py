"""Benchmarks comparing MATLAB-ported DE optimization vs surrogate strategies.

Measures:
- Solution quality (best objective value found)
- Number of real pipeline evaluations
- Wall-clock time
- Accuracy relative to exhaustive/high-budget DE reference

Run with: pytest benchmarks/test_benchmark_surrogates.py -v -s
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

import numpy as np
import pytest
from numpy.typing import NDArray

from kst_rating_tool import (
    ConstraintSet,
    LineConstraint,
    PinConstraint,
    PlaneConstraint,
    PointConstraint,
    analyze_constraints,
)
from kst_rating_tool.optimization.modification import optimize_modification
from kst_rating_tool.optimization.parameterizations import (
    Orientation1DParameterization,
    PointOnLineParameterization,
)
from kst_rating_tool.rating import RatingResults

try:
    from kst_rating_tool.optimization.surrogate import (
        optimize_modification_surrogate,
        optimize_surrogate_adaptive,
    )

    HAS_SURROGATE = True
except ImportError:
    HAS_SURROGATE = False

try:
    from kst_rating_tool.optimization.surrogate_bo import optimize_bo

    HAS_BO = True
except ImportError:
    HAS_BO = False

try:
    from kst_rating_tool.optimization.surrogate_pareto import optimize_pareto

    HAS_PARETO = True
except ImportError:
    HAS_PARETO = False


# ---------------------------------------------------------------------------
# Benchmark infrastructure
# ---------------------------------------------------------------------------

@dataclass
class BenchmarkResult:
    method: str
    objective: str
    best_value: float
    n_real_evals: int
    wall_time_s: float
    best_x: NDArray[np.float64] | None = None
    all_metrics: dict[str, float] = field(default_factory=dict)


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


def _all_metrics(results: RatingResults) -> dict[str, float]:
    return {
        "WTR": results.WTR,
        "MRR": results.MRR,
        "MTR": results.MTR,
        "TOR": results.TOR if results.TOR != float("inf") else 0.0,
    }


# ---------------------------------------------------------------------------
# Benchmark constraint sets (realistic geometry, not trivial)
# ---------------------------------------------------------------------------

def _chair_constraints() -> ConstraintSet:
    """Thompson chair (7 point contacts) -- thesis case1a."""
    pts = [
        ([3.57, -0.75, -0.50], [0.43, 0.75, 0.50]),
        ([4.87, 0.00, -0.50], [-0.87, 0.00, 0.50]),
        ([3.57, 0.75, -0.50], [0.43, -0.75, 0.50]),
        ([-1.57, 4.21, -0.50], [-0.43, -0.75, 0.50]),
        ([-2.43, 2.71, -0.50], [0.43, 0.75, 0.50]),
        ([-2.00, -3.46, -1.00], [0.00, 0.00, 1.00]),
        ([0.00, 0.00, 4.00], [0.00, 0.00, -1.00]),
    ]
    return ConstraintSet(
        points=[
            PointConstraint(
                position=np.array(p, dtype=float),
                normal=np.array(n, dtype=float),
            )
            for p, n in pts
        ]
    )


def _octahedron_constraints() -> ConstraintSet:
    """6 points on octahedron vertices with outward-facing normals."""
    pts_normals = [
        ((-1.0, 0.0, 0.0), (-1.0, 0.0, 0.0)),
        ((1.0, 0.0, 0.0), (1.0, 0.0, 0.0)),
        ((0.0, -1.0, 0.0), (0.0, -1.0, 0.0)),
        ((0.0, 1.0, 0.0), (0.0, 1.0, 0.0)),
        ((0.0, 0.0, -1.0), (0.0, 0.0, -1.0)),
        ((0.0, 0.0, 1.0), (0.0, 0.0, 1.0)),
    ]
    return ConstraintSet(
        points=[
            PointConstraint(
                position=np.array(p, dtype=float),
                normal=np.array(n, dtype=float),
            )
            for p, n in pts_normals
        ]
    )


def _mixed_constraints() -> ConstraintSet:
    """Mixed constraint set: 3 points + 1 pin + 1 line (5 total)."""
    return ConstraintSet(
        points=[
            PointConstraint(np.array([0, 0, 0], dtype=float), np.array([0, 0, 1], dtype=float)),
            PointConstraint(np.array([20, 0, 0], dtype=float), np.array([0, 0, 1], dtype=float)),
            PointConstraint(np.array([0, 20, 0], dtype=float), np.array([0, 0, 1], dtype=float)),
        ],
        pins=[
            PinConstraint(np.array([10, 10, 0], dtype=float), np.array([0, 1, 0], dtype=float)),
        ],
        lines=[
            LineConstraint(
                np.array([5, 5, 0], dtype=float),
                np.array([1, 0, 0], dtype=float),
                np.array([0, 0, 1], dtype=float),
                10.0,
            ),
        ],
    )


# ---------------------------------------------------------------------------
# Parameterization factories for benchmarking
# ---------------------------------------------------------------------------

def _chair_point_on_line_param() -> tuple[ConstraintSet, PointOnLineParameterization, list[tuple[float, float]]]:
    """Chair: move cp7 (index 6) along z-axis between z=0 and z=8."""
    base = _chair_constraints()
    param = PointOnLineParameterization(
        base=base,
        point_index=6,
        line_start=np.array([0.0, 0.0, 0.0]),
        line_end=np.array([0.0, 0.0, 8.0]),
    )
    bounds = [(-1.0, 1.0)]
    return base, param, bounds


def _octahedron_move_param() -> tuple[ConstraintSet, PointOnLineParameterization, list[tuple[float, float]]]:
    """Octahedron: move point 5 (top, z=1) between z=-2 and z=2."""
    base = _octahedron_constraints()
    param = PointOnLineParameterization(
        base=base,
        point_index=5,
        line_start=np.array([0.0, 0.0, -2.0]),
        line_end=np.array([0.0, 0.0, 2.0]),
    )
    bounds = [(-1.0, 1.0)]
    return base, param, bounds


def _mixed_orient_param() -> tuple[ConstraintSet, Orientation1DParameterization, list[tuple[float, float]]]:
    """Mixed: rotate the pin (global index 3) about z-axis, +/- 90 degrees."""
    base = _mixed_constraints()
    param = Orientation1DParameterization(
        base=base,
        constraint_index=3,
        axis=np.array([0.0, 0.0, 1.0]),
        angle_range=(-np.pi / 2, np.pi / 2),
    )
    bounds = [(-1.0, 1.0)]
    return base, param, bounds


# ---------------------------------------------------------------------------
# Helper: run one method and collect BenchmarkResult
# ---------------------------------------------------------------------------

def _run_de(
    param: Callable,
    bounds: list[tuple[float, float]],
    objective: str,
    max_eval: int,
    seed: int,
    polish: bool = True,
) -> BenchmarkResult:
    t0 = time.perf_counter()
    result = optimize_modification(
        parameterization=param,
        bounds=bounds,
        objective=objective,
        max_eval=max_eval,
        seed=seed,
        polish=polish,
    )
    elapsed = time.perf_counter() - t0
    return BenchmarkResult(
        method="DE (MATLAB-ported)",
        objective=objective,
        best_value=_objective_value(result.best_rating, objective),
        n_real_evals=len(result.history) + 1,
        wall_time_s=elapsed,
        best_x=result.best_x,
        all_metrics=_all_metrics(result.best_rating),
    )


def _run_one_shot_rf(
    param: Callable,
    bounds: list[tuple[float, float]],
    objective: str,
    n_samples: int,
    n_validate: int,
    seed: int,
) -> BenchmarkResult:
    t0 = time.perf_counter()
    result = optimize_modification_surrogate(
        parameterization=param,
        bounds=bounds,
        objective=objective,
        n_samples=n_samples,
        n_validate=n_validate,
        seed=seed,
    )
    elapsed = time.perf_counter() - t0
    return BenchmarkResult(
        method="One-shot RF",
        objective=objective,
        best_value=_objective_value(result.best_rating, objective),
        n_real_evals=result.n_real_evals,
        wall_time_s=elapsed,
        best_x=result.best_x,
        all_metrics=_all_metrics(result.best_rating),
    )


def _run_adaptive_rf(
    param: Callable,
    bounds: list[tuple[float, float]],
    objective: str,
    n_initial: int,
    n_iter: int,
    batch_size: int,
    seed: int,
) -> BenchmarkResult:
    t0 = time.perf_counter()
    result = optimize_surrogate_adaptive(
        parameterization=param,
        bounds=bounds,
        objective=objective,
        n_initial=n_initial,
        n_iter=n_iter,
        batch_size=batch_size,
        n_candidates=500,
        alpha=1.0,
        seed=seed,
    )
    elapsed = time.perf_counter() - t0
    return BenchmarkResult(
        method="Adaptive RF",
        objective=objective,
        best_value=_objective_value(result.best_rating, objective),
        n_real_evals=result.n_real_evals,
        wall_time_s=elapsed,
        best_x=result.best_x,
        all_metrics=_all_metrics(result.best_rating),
    )


def _run_bo(
    param: Callable,
    bounds: list[tuple[float, float]],
    objective: str,
    n_initial: int,
    n_iter: int,
    seed: int,
) -> BenchmarkResult:
    t0 = time.perf_counter()
    result = optimize_bo(
        parameterization=param,
        bounds=bounds,
        objective=objective,
        n_initial=n_initial,
        n_iter=n_iter,
        batch_size=1,
        seed=seed,
    )
    elapsed = time.perf_counter() - t0
    return BenchmarkResult(
        method="Bayesian Opt (GP)",
        objective=objective,
        best_value=_objective_value(result.best_rating, objective),
        n_real_evals=result.n_real_evals,
        wall_time_s=elapsed,
        best_x=result.best_x,
        all_metrics=_all_metrics(result.best_rating),
    )


def _print_results(
    problem_name: str,
    results: list[BenchmarkResult],
    reference_value: float | None = None,
) -> None:
    """Pretty-print benchmark comparison table."""
    print(f"\n{'='*80}")
    print(f"  BENCHMARK: {problem_name}")
    print(f"{'='*80}")
    print(f"  {'Method':<22} {'Objective':>9} {'Best':>10} {'Evals':>7} {'Time(s)':>9} {'WTR':>8} {'MRR':>8} {'MTR':>8} {'TOR':>8}")
    print(f"  {'-'*22} {'-'*9} {'-'*10} {'-'*7} {'-'*9} {'-'*8} {'-'*8} {'-'*8} {'-'*8}")
    for r in results:
        print(
            f"  {r.method:<22} {r.objective:>9} {r.best_value:>10.4f} "
            f"{r.n_real_evals:>7d} {r.wall_time_s:>9.3f} "
            f"{r.all_metrics.get('WTR', 0):>8.4f} {r.all_metrics.get('MRR', 0):>8.4f} "
            f"{r.all_metrics.get('MTR', 0):>8.4f} {r.all_metrics.get('TOR', 0):>8.4f}"
        )
    if reference_value is not None:
        print(f"\n  Reference (exhaustive DE): {reference_value:.4f}")
        for r in results:
            gap = abs(r.best_value - reference_value)
            pct = gap / reference_value * 100 if reference_value != 0 else 0
            print(f"    {r.method:<22}: gap = {gap:.4f} ({pct:.1f}%)")
    print()


# ---------------------------------------------------------------------------
# Exhaustive reference: high-budget DE for ground truth
# ---------------------------------------------------------------------------

def _compute_reference(
    param: Callable,
    bounds: list[tuple[float, float]],
    objective: str,
    seed: int = 0,
) -> BenchmarkResult:
    """Run DE with a large budget to establish the 'ground truth' best value."""
    return _run_de(param, bounds, objective, max_eval=500, seed=seed)


# ---------------------------------------------------------------------------
# BENCHMARK TESTS
# ---------------------------------------------------------------------------

BUDGET_SMALL = 50
BUDGET_MEDIUM = 100


class TestBenchmarkChairPointMove:
    """Benchmark: chair case, move cp7 along z-axis (1D)."""

    @pytest.fixture(scope="class")
    def setup(self):
        _, param, bounds = _chair_point_on_line_param()
        return param, bounds

    @pytest.fixture(scope="class")
    def reference(self, setup):
        param, bounds = setup
        return _compute_reference(param, bounds, "TOR", seed=0)

    def test_de_baseline(self, setup, reference):
        param, bounds = setup
        result = _run_de(param, bounds, "TOR", max_eval=BUDGET_MEDIUM, seed=42)
        assert result.best_value > 0.0
        assert result.n_real_evals <= BUDGET_MEDIUM + 50  # DE may exceed max_eval slightly

    @pytest.mark.skipif(not HAS_SURROGATE, reason="scikit-learn not installed")
    def test_one_shot_rf(self, setup, reference):
        param, bounds = setup
        result = _run_one_shot_rf(param, bounds, "TOR", n_samples=40, n_validate=10, seed=42)
        assert result.best_value > 0.0
        assert result.n_real_evals == 50

    @pytest.mark.skipif(not HAS_SURROGATE, reason="scikit-learn not installed")
    def test_adaptive_rf(self, setup, reference):
        param, bounds = setup
        result = _run_adaptive_rf(param, bounds, "TOR", n_initial=30, n_iter=4, batch_size=5, seed=42)
        assert result.best_value > 0.0
        assert result.n_real_evals == 50

    @pytest.mark.skipif(not HAS_BO, reason="scikit-learn not installed")
    def test_bayesian_opt(self, setup, reference):
        param, bounds = setup
        result = _run_bo(param, bounds, "TOR", n_initial=20, n_iter=30, seed=42)
        assert result.best_value > 0.0
        assert result.n_real_evals == 50

    @pytest.mark.skipif(
        not (HAS_SURROGATE and HAS_BO),
        reason="scikit-learn not installed",
    )
    def test_comparison_report(self, setup, reference):
        param, bounds = setup
        results = [reference]
        results.append(_run_de(param, bounds, "TOR", max_eval=BUDGET_SMALL, seed=42))
        results.append(_run_one_shot_rf(param, bounds, "TOR", n_samples=40, n_validate=10, seed=42))
        results.append(_run_adaptive_rf(param, bounds, "TOR", n_initial=30, n_iter=4, batch_size=5, seed=42))
        results.append(_run_bo(param, bounds, "TOR", n_initial=20, n_iter=30, seed=42))
        _print_results("Chair cp7 z-axis move (1D, TOR)", results, reference.best_value)


class TestBenchmarkOctahedronMove:
    """Benchmark: octahedron, move top point along z (1D)."""

    @pytest.fixture(scope="class")
    def setup(self):
        _, param, bounds = _octahedron_move_param()
        return param, bounds

    @pytest.fixture(scope="class")
    def reference(self, setup):
        param, bounds = setup
        return _compute_reference(param, bounds, "WTR", seed=0)

    def test_de_baseline(self, setup, reference):
        param, bounds = setup
        result = _run_de(param, bounds, "WTR", max_eval=BUDGET_MEDIUM, seed=42)
        assert result.best_value >= 0.0

    @pytest.mark.skipif(not HAS_SURROGATE, reason="scikit-learn not installed")
    def test_one_shot_rf(self, setup, reference):
        param, bounds = setup
        result = _run_one_shot_rf(param, bounds, "WTR", n_samples=40, n_validate=10, seed=42)
        assert result.best_value >= 0.0

    @pytest.mark.skipif(not HAS_SURROGATE, reason="scikit-learn not installed")
    def test_adaptive_rf(self, setup, reference):
        param, bounds = setup
        result = _run_adaptive_rf(param, bounds, "WTR", n_initial=30, n_iter=4, batch_size=5, seed=42)
        assert result.best_value >= 0.0

    @pytest.mark.skipif(not HAS_BO, reason="scikit-learn not installed")
    def test_bayesian_opt(self, setup, reference):
        param, bounds = setup
        result = _run_bo(param, bounds, "WTR", n_initial=20, n_iter=30, seed=42)
        assert result.best_value >= 0.0

    @pytest.mark.skipif(
        not (HAS_SURROGATE and HAS_BO),
        reason="scikit-learn not installed",
    )
    def test_comparison_report(self, setup, reference):
        param, bounds = setup
        results = [reference]
        results.append(_run_de(param, bounds, "WTR", max_eval=BUDGET_SMALL, seed=42))
        results.append(_run_one_shot_rf(param, bounds, "WTR", n_samples=40, n_validate=10, seed=42))
        results.append(_run_adaptive_rf(param, bounds, "WTR", n_initial=30, n_iter=4, batch_size=5, seed=42))
        results.append(_run_bo(param, bounds, "WTR", n_initial=20, n_iter=30, seed=42))
        _print_results("Octahedron top-point z-move (1D, WTR)", results, reference.best_value)


class TestBenchmarkMixedOrient:
    """Benchmark: mixed constraints, pin orientation (1D)."""

    @pytest.fixture(scope="class")
    def setup(self):
        _, param, bounds = _mixed_orient_param()
        return param, bounds

    @pytest.fixture(scope="class")
    def reference(self, setup):
        param, bounds = setup
        return _compute_reference(param, bounds, "TOR", seed=0)

    def test_de_baseline(self, setup, reference):
        param, bounds = setup
        result = _run_de(param, bounds, "TOR", max_eval=BUDGET_MEDIUM, seed=42)
        assert result.best_value >= 0.0

    @pytest.mark.skipif(not HAS_SURROGATE, reason="scikit-learn not installed")
    def test_adaptive_rf(self, setup, reference):
        param, bounds = setup
        result = _run_adaptive_rf(param, bounds, "TOR", n_initial=30, n_iter=4, batch_size=5, seed=42)
        assert result.best_value >= 0.0

    @pytest.mark.skipif(not HAS_BO, reason="scikit-learn not installed")
    def test_bayesian_opt(self, setup, reference):
        param, bounds = setup
        result = _run_bo(param, bounds, "TOR", n_initial=20, n_iter=30, seed=42)
        assert result.best_value >= 0.0

    @pytest.mark.skipif(
        not (HAS_SURROGATE and HAS_BO),
        reason="scikit-learn not installed",
    )
    def test_comparison_report(self, setup, reference):
        param, bounds = setup
        results = [reference]
        results.append(_run_de(param, bounds, "TOR", max_eval=BUDGET_SMALL, seed=42))
        results.append(_run_one_shot_rf(param, bounds, "TOR", n_samples=40, n_validate=10, seed=42))
        results.append(_run_adaptive_rf(param, bounds, "TOR", n_initial=30, n_iter=4, batch_size=5, seed=42))
        results.append(_run_bo(param, bounds, "TOR", n_initial=20, n_iter=30, seed=42))
        _print_results("Mixed pin orient (1D, TOR)", results, reference.best_value)


# ---------------------------------------------------------------------------
# Accuracy tests: surrogates must reach within tolerance of DE reference
# ---------------------------------------------------------------------------


class TestAccuracyChair:
    """Verify surrogates find solutions close to high-budget DE on chair case."""

    TOLERANCE_PCT = 15.0  # Allow 15% gap from reference

    @pytest.fixture(scope="class")
    def reference(self):
        _, param, bounds = _chair_point_on_line_param()
        return _compute_reference(param, bounds, "TOR", seed=0)

    @pytest.fixture(scope="class")
    def param_bounds(self):
        _, param, bounds = _chair_point_on_line_param()
        return param, bounds

    @pytest.mark.skipif(not HAS_SURROGATE, reason="scikit-learn not installed")
    def test_one_shot_rf_accuracy(self, param_bounds, reference):
        param, bounds = param_bounds
        result = _run_one_shot_rf(param, bounds, "TOR", n_samples=60, n_validate=15, seed=42)
        ref_val = reference.best_value
        if ref_val > 0:
            gap_pct = abs(result.best_value - ref_val) / ref_val * 100
            assert gap_pct < self.TOLERANCE_PCT, (
                f"One-shot RF accuracy: {result.best_value:.4f} vs ref {ref_val:.4f} "
                f"(gap {gap_pct:.1f}% > {self.TOLERANCE_PCT}%)"
            )

    @pytest.mark.skipif(not HAS_SURROGATE, reason="scikit-learn not installed")
    def test_adaptive_rf_accuracy(self, param_bounds, reference):
        param, bounds = param_bounds
        result = _run_adaptive_rf(param, bounds, "TOR", n_initial=40, n_iter=5, batch_size=5, seed=42)
        ref_val = reference.best_value
        if ref_val > 0:
            gap_pct = abs(result.best_value - ref_val) / ref_val * 100
            assert gap_pct < self.TOLERANCE_PCT, (
                f"Adaptive RF accuracy: {result.best_value:.4f} vs ref {ref_val:.4f} "
                f"(gap {gap_pct:.1f}% > {self.TOLERANCE_PCT}%)"
            )

    @pytest.mark.skipif(not HAS_BO, reason="scikit-learn not installed")
    def test_bo_accuracy(self, param_bounds, reference):
        param, bounds = param_bounds
        result = _run_bo(param, bounds, "TOR", n_initial=25, n_iter=40, seed=42)
        ref_val = reference.best_value
        if ref_val > 0:
            gap_pct = abs(result.best_value - ref_val) / ref_val * 100
            assert gap_pct < self.TOLERANCE_PCT, (
                f"BO accuracy: {result.best_value:.4f} vs ref {ref_val:.4f} "
                f"(gap {gap_pct:.1f}% > {self.TOLERANCE_PCT}%)"
            )


class TestAccuracyOctahedron:
    """Verify surrogates find solutions close to high-budget DE on octahedron."""

    TOLERANCE_PCT = 15.0

    @pytest.fixture(scope="class")
    def reference(self):
        _, param, bounds = _octahedron_move_param()
        return _compute_reference(param, bounds, "WTR", seed=0)

    @pytest.fixture(scope="class")
    def param_bounds(self):
        _, param, bounds = _octahedron_move_param()
        return param, bounds

    @pytest.mark.skipif(not HAS_SURROGATE, reason="scikit-learn not installed")
    def test_one_shot_rf_accuracy(self, param_bounds, reference):
        param, bounds = param_bounds
        result = _run_one_shot_rf(param, bounds, "WTR", n_samples=60, n_validate=15, seed=42)
        ref_val = reference.best_value
        if ref_val > 0:
            gap_pct = abs(result.best_value - ref_val) / ref_val * 100
            assert gap_pct < self.TOLERANCE_PCT

    @pytest.mark.skipif(not HAS_SURROGATE, reason="scikit-learn not installed")
    def test_adaptive_rf_accuracy(self, param_bounds, reference):
        param, bounds = param_bounds
        result = _run_adaptive_rf(param, bounds, "WTR", n_initial=40, n_iter=5, batch_size=5, seed=42)
        ref_val = reference.best_value
        if ref_val > 0:
            gap_pct = abs(result.best_value - ref_val) / ref_val * 100
            assert gap_pct < self.TOLERANCE_PCT

    @pytest.mark.skipif(not HAS_BO, reason="scikit-learn not installed")
    def test_bo_accuracy(self, param_bounds, reference):
        param, bounds = param_bounds
        result = _run_bo(param, bounds, "WTR", n_initial=25, n_iter=40, seed=42)
        ref_val = reference.best_value
        if ref_val > 0:
            gap_pct = abs(result.best_value - ref_val) / ref_val * 100
            assert gap_pct < self.TOLERANCE_PCT


class TestAccuracyMixed:
    """Verify surrogates find solutions close to high-budget DE on mixed case."""

    TOLERANCE_PCT = 20.0  # Slightly more lenient for mixed constraints

    @pytest.fixture(scope="class")
    def reference(self):
        _, param, bounds = _mixed_orient_param()
        return _compute_reference(param, bounds, "TOR", seed=0)

    @pytest.fixture(scope="class")
    def param_bounds(self):
        _, param, bounds = _mixed_orient_param()
        return param, bounds

    @pytest.mark.skipif(not HAS_SURROGATE, reason="scikit-learn not installed")
    def test_one_shot_rf_accuracy(self, param_bounds, reference):
        param, bounds = param_bounds
        result = _run_one_shot_rf(param, bounds, "TOR", n_samples=60, n_validate=15, seed=42)
        ref_val = reference.best_value
        if ref_val > 0:
            gap_pct = abs(result.best_value - ref_val) / ref_val * 100
            assert gap_pct < self.TOLERANCE_PCT

    @pytest.mark.skipif(not HAS_SURROGATE, reason="scikit-learn not installed")
    def test_adaptive_rf_accuracy(self, param_bounds, reference):
        param, bounds = param_bounds
        result = _run_adaptive_rf(param, bounds, "TOR", n_initial=40, n_iter=5, batch_size=5, seed=42)
        ref_val = reference.best_value
        if ref_val > 0:
            gap_pct = abs(result.best_value - ref_val) / ref_val * 100
            assert gap_pct < self.TOLERANCE_PCT

    @pytest.mark.skipif(not HAS_BO, reason="scikit-learn not installed")
    def test_bo_accuracy(self, param_bounds, reference):
        param, bounds = param_bounds
        result = _run_bo(param, bounds, "TOR", n_initial=25, n_iter=40, seed=42)
        ref_val = reference.best_value
        if ref_val > 0:
            gap_pct = abs(result.best_value - ref_val) / ref_val * 100
            assert gap_pct < self.TOLERANCE_PCT


# ---------------------------------------------------------------------------
# Pareto benchmark (multi-objective)
# ---------------------------------------------------------------------------

class TestBenchmarkPareto:
    """Benchmark Pareto front discovery on chair case."""

    @pytest.mark.skipif(not HAS_PARETO, reason="scikit-learn not installed")
    def test_pareto_discovers_front(self):
        _, param, bounds = _chair_point_on_line_param()
        t0 = time.perf_counter()
        result = optimize_pareto(
            parameterization=param,
            bounds=bounds,
            objectives=["WTR", "TOR"],
            n_initial=30,
            n_iter=2,
            batch_size=5,
            n_candidates=200,
            n_validate=10,
            seed=42,
        )
        elapsed = time.perf_counter() - t0
        print(f"\n  Pareto front discovery: {len(result.pareto_front)} points, "
              f"{result.n_real_evals} evals, {elapsed:.2f}s")
        for pp in result.pareto_front:
            print(f"    WTR={pp.metrics[0]:.4f}  MRR={pp.metrics[1]:.4f}  "
                  f"MTR={pp.metrics[2]:.4f}  TOR={pp.metrics[3]:.4f}")
        assert len(result.pareto_front) >= 1
        for pp in result.pareto_front:
            assert pp.rating.WTR >= 0.0


# ---------------------------------------------------------------------------
# Efficiency test: surrogates should use fewer evals than DE for similar quality
# ---------------------------------------------------------------------------

class TestEfficiency:
    """Verify surrogates match DE quality at equal evaluation budget.

    On simple 1D problems, DE may converge in very few evaluations.
    The value of surrogates is greatest on higher-dimensional or more
    expensive problems.  Here we verify that at a fixed budget, surrogates
    reach at least the same quality as DE.
    """

    BUDGET = 50

    @pytest.mark.skipif(
        not (HAS_SURROGATE and HAS_BO),
        reason="scikit-learn not installed",
    )
    def test_surrogates_match_de_quality_at_equal_budget(self):
        _, param, bounds = _chair_point_on_line_param()

        de_result = _run_de(param, bounds, "TOR", max_eval=self.BUDGET, seed=42)
        bo_result = _run_bo(param, bounds, "TOR", n_initial=20, n_iter=30, seed=42)
        arf_result = _run_adaptive_rf(
            param, bounds, "TOR", n_initial=30, n_iter=4, batch_size=5, seed=42
        )
        rf_result = _run_one_shot_rf(
            param, bounds, "TOR", n_samples=40, n_validate=10, seed=42
        )

        print(f"\n  Equal-budget efficiency comparison (budget={self.BUDGET}):")
        print(f"    DE:          {de_result.n_real_evals:3d} evals -> {de_result.best_value:.4f}")
        print(f"    One-shot RF: {rf_result.n_real_evals:3d} evals -> {rf_result.best_value:.4f}")
        print(f"    Adaptive RF: {arf_result.n_real_evals:3d} evals -> {arf_result.best_value:.4f}")
        print(f"    BO:          {bo_result.n_real_evals:3d} evals -> {bo_result.best_value:.4f}")

        tolerance = 0.15  # 15% gap allowed
        de_val = de_result.best_value
        if de_val > 0:
            for name, res in [("BO", bo_result), ("Adaptive RF", arf_result), ("One-shot RF", rf_result)]:
                gap_pct = (de_val - res.best_value) / de_val * 100
                assert gap_pct < tolerance * 100, (
                    f"{name} found {res.best_value:.4f} vs DE {de_val:.4f} "
                    f"(gap {gap_pct:.1f}%)"
                )


# ---------------------------------------------------------------------------
# Printer cover 5D benchmark (dissertation case5g)
# ---------------------------------------------------------------------------

def _printer_5d_case_path() -> Path:
    """Resolve the case5g .m file from the repo root."""
    here = Path(__file__).resolve().parent
    candidates = [
        here.parent / "matlab_script" / "Input_files" / "case5g_printer_5d.m",
        here.parents[1] / "matlab_script" / "Input_files" / "case5g_printer_5d.m",
    ]
    for p in candidates:
        if p.is_file():
            return p
    pytest.skip("case5g_printer_5d.m not found")


def _printer_5d_setup():
    """Load case5g and build RevisionConfig + RevisionParameterization."""
    from kst_rating_tool.io_legacy import load_case_m_file
    from kst_rating_tool.optimization.parameterizations import (
        RevisionParameterization,
        build_x_map,
    )
    from kst_rating_tool.optimization.revision import RevisionConfig

    case_path = _printer_5d_case_path()
    base = load_case_m_file(case_path)

    config = RevisionConfig(
        grp_members=[
            np.array([6, 7, 14, 8, 9, 15]),
            np.array([10, 11, 16, 12, 13, 17]),
            np.array([1, 5, 0, 0, 0, 0]),
            np.array([3, 4, 0, 0, 0, 0]),
            np.array([1, 5, 0, 0, 0, 0]),
        ],
        grp_rev_type=np.array([5, 5, 5, 5, 2]),
        grp_srch_spc=[
            np.array([0, 1, 0, 90, 0, 0, 0], dtype=float),
            np.array([0, 1, 0, 90, 0, 0, 0], dtype=float),
            np.array([0, 1, 0, 60, 0, 0, 0], dtype=float),
            np.array([0, 1, 0, 60, 0, 0, 0], dtype=float),
            np.array([7.125, 18, 3.2, -3.093, 0, 3.441, 4.5], dtype=float),
        ],
    )

    x_map, no_dim = build_x_map(config)
    assert no_dim == 5

    param = RevisionParameterization(base, config, x_map)
    bounds = [(-1.0, 1.0)] * no_dim
    return base, config, x_map, param, bounds


def _run_factorial(
    base,
    config,
    no_step: int,
) -> BenchmarkResult:
    """Run the MATLAB-ported factorial grid and return best TOR."""
    from kst_rating_tool import analyze_constraints_detailed
    from kst_rating_tool.optimization.revision import optim_main_rev

    t0 = time.perf_counter()
    baseline = analyze_constraints_detailed(base)
    WTR_all, MRR_all, MTR_all, TOR_all, x_map = optim_main_rev(
        baseline, config, no_step,
    )
    elapsed = time.perf_counter() - t0

    valid = np.isfinite(TOR_all)
    if valid.any():
        best_tor = float(np.nanmax(TOR_all))
    else:
        best_tor = 0.0

    n_inc = no_step + 1
    n_dim = len(config.grp_members)
    tot_evals = n_inc ** n_dim

    best_idx = np.unravel_index(np.nanargmax(TOR_all), TOR_all.shape)
    a_vals = np.linspace(-1, 1, n_inc)
    best_x = np.array([a_vals[i] for i in best_idx])

    return BenchmarkResult(
        method=f"Factorial (step={no_step})",
        objective="TOR",
        best_value=best_tor,
        n_real_evals=tot_evals,
        wall_time_s=elapsed,
        best_x=best_x,
        all_metrics={
            "WTR": float(WTR_all[best_idx]),
            "MRR": float(MRR_all[best_idx]),
            "MTR": float(MTR_all[best_idx]),
            "TOR": best_tor,
        },
    )


class TestBenchmarkPrinter5D:
    """Printer cover 5D benchmark -- dissertation case5g.

    Each ``analyze_constraints`` call takes ~2s for this 23-constraint case
    (13 CP + 4 CPIN + 6 CLIN), so budgets target ~60 evals per method
    (~2 min each, ~10 min for the full comparison report).

    NOTE: The MATLAB factorial grid (``optim_rev``) is ~30s/eval in Python
    because 16 of 23 constraints are revised.  DE with full
    ``analyze_constraints`` (~2s/eval) is used as the baseline instead.
    """

    @pytest.fixture(scope="class")
    def setup(self):
        return _printer_5d_setup()

    @pytest.fixture(scope="class")
    def de_reference(self, setup):
        _, _, _, param, bounds = setup
        return _run_de(param, bounds, "TOR", max_eval=60, seed=0, polish=False)

    def test_de_baseline(self, setup, de_reference):
        _, _, _, param, bounds = setup
        result = _run_de(param, bounds, "TOR", max_eval=50, seed=42,
                         polish=False)
        print(f"\n  DE: TOR={result.best_value:.4f}, evals={result.n_real_evals}, "
              f"time={result.wall_time_s:.1f}s")
        assert result.best_value > 0.0

    @pytest.mark.skipif(not HAS_SURROGATE, reason="scikit-learn not installed")
    def test_one_shot_rf(self, setup):
        _, _, _, param, bounds = setup
        result = _run_one_shot_rf(param, bounds, "TOR",
                                  n_samples=40, n_validate=15, seed=42)
        print(f"\n  One-shot RF: TOR={result.best_value:.4f}, evals={result.n_real_evals}, "
              f"time={result.wall_time_s:.1f}s")
        assert result.best_value > 0.0

    @pytest.mark.skipif(not HAS_SURROGATE, reason="scikit-learn not installed")
    def test_adaptive_rf(self, setup):
        _, _, _, param, bounds = setup
        result = _run_adaptive_rf(param, bounds, "TOR",
                                  n_initial=30, n_iter=3, batch_size=8, seed=42)
        print(f"\n  Adaptive RF: TOR={result.best_value:.4f}, evals={result.n_real_evals}, "
              f"time={result.wall_time_s:.1f}s")
        assert result.best_value > 0.0

    @pytest.mark.skipif(not HAS_BO, reason="scikit-learn not installed")
    def test_bayesian_opt(self, setup):
        _, _, _, param, bounds = setup
        result = _run_bo(param, bounds, "TOR",
                         n_initial=20, n_iter=35, seed=42)
        print(f"\n  BO: TOR={result.best_value:.4f}, evals={result.n_real_evals}, "
              f"time={result.wall_time_s:.1f}s")
        assert result.best_value > 0.0

    @pytest.mark.skipif(
        not (HAS_SURROGATE and HAS_BO),
        reason="scikit-learn not installed",
    )
    def test_comparison_report(self, setup, de_reference):
        _, _, _, param, bounds = setup
        results = [de_reference]
        results.append(_run_de(param, bounds, "TOR", max_eval=50, seed=42,
                               polish=False))
        results.append(_run_one_shot_rf(param, bounds, "TOR",
                                        n_samples=40, n_validate=15, seed=42))
        results.append(_run_adaptive_rf(param, bounds, "TOR",
                                        n_initial=30, n_iter=3, batch_size=8, seed=42))
        results.append(_run_bo(param, bounds, "TOR",
                               n_initial=20, n_iter=35, seed=42))
        _print_results("Printer cover 5D (TOR)", results, de_reference.best_value)


@pytest.mark.slow
class TestBenchmarkPrinter5DSlow:
    """Extended printer cover 5D benchmark with higher budgets (~25 min total).

    Uses DE with a large budget as the reference, then compares surrogates.
    """

    @pytest.fixture(scope="class")
    def setup(self):
        return _printer_5d_setup()

    @pytest.fixture(scope="class")
    def de_reference(self, setup):
        _, _, _, param, bounds = setup
        return _run_de(param, bounds, "TOR", max_eval=200, seed=0, polish=False)

    @pytest.mark.skipif(
        not (HAS_SURROGATE and HAS_BO),
        reason="scikit-learn not installed",
    )
    def test_full_comparison(self, setup, de_reference):
        _, _, _, param, bounds = setup
        results = [de_reference]
        results.append(_run_de(param, bounds, "TOR", max_eval=100, seed=42, polish=False))
        results.append(_run_one_shot_rf(param, bounds, "TOR",
                                        n_samples=100, n_validate=30, seed=42))
        results.append(_run_adaptive_rf(param, bounds, "TOR",
                                        n_initial=60, n_iter=5, batch_size=12, seed=42))
        results.append(_run_bo(param, bounds, "TOR",
                               n_initial=40, n_iter=90, seed=42))
        _print_results(
            "Printer cover 5D FULL (TOR)",
            results, de_reference.best_value,
        )

        ref_val = de_reference.best_value
        if ref_val > 0:
            for r in results[1:]:
                gap_pct = (ref_val - r.best_value) / ref_val * 100
                assert gap_pct < 30.0, (
                    f"{r.method} found {r.best_value:.4f} vs DE ref {ref_val:.4f} "
                    f"(gap {gap_pct:.1f}% > 30%)"
                )
