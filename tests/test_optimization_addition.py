"""Tests for constraint addition optimization (addition.py)."""
from __future__ import annotations

import numpy as np
import pytest

from kst_rating_tool import ConstraintSet, PointConstraint, PinConstraint, analyze_constraints
from kst_rating_tool.optimization import (
    AdditionResult,
    constraint_set_with,
    optim_main_add,
    optimize_addition,
)


def _six_point_baseline() -> ConstraintSet:
    """Six-point isotropic baseline used throughout optimization tests."""
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


def _two_candidate_pool() -> ConstraintSet:
    """Two point-contact candidates to try adding."""
    return ConstraintSet(
        points=[
            PointConstraint(
                position=np.array([0.5, 0.5, 0.0], dtype=float),
                normal=np.array([0.0, 0.0, 1.0], dtype=float),
            ),
            PointConstraint(
                position=np.array([-0.5, -0.5, 0.0], dtype=float),
                normal=np.array([0.0, 0.0, 1.0], dtype=float),
            ),
        ]
    )


# ── constraint_set_with helper ──────────────────────────────────────────────

def test_constraint_set_with_adds_correct_constraint():
    baseline = _six_point_baseline()
    pool = _two_candidate_pool()

    augmented = constraint_set_with(baseline, pool, [0])
    assert len(augmented.points) == len(baseline.points) + 1
    np.testing.assert_array_equal(augmented.points[-1].position, pool.points[0].position)


def test_constraint_set_with_adds_multiple():
    baseline = _six_point_baseline()
    pool = _two_candidate_pool()

    augmented = constraint_set_with(baseline, pool, [0, 1])
    assert len(augmented.points) == len(baseline.points) + 2


def test_constraint_set_with_empty_indices_unchanged():
    baseline = _six_point_baseline()
    pool = _two_candidate_pool()
    augmented = constraint_set_with(baseline, pool, [])
    assert augmented.total_cp == baseline.total_cp


def test_constraint_set_with_pin_candidate():
    baseline = _six_point_baseline()
    pool = ConstraintSet(
        pins=[PinConstraint(np.array([1.0, 0.0, 0.0]), np.array([0.0, 0.0, 1.0]))]
    )
    augmented = constraint_set_with(baseline, pool, [0])
    assert len(augmented.pins) == 1
    assert len(augmented.points) == len(baseline.points)


# ── optimize_addition — greedy ───────────────────────────────────────────────

def test_optimize_addition_greedy_smoke():
    baseline = _six_point_baseline()
    pool = _two_candidate_pool()

    result = optimize_addition(baseline, pool, n_add=1, method="greedy")

    assert isinstance(result, AdditionResult)
    assert len(result.indices_added) == 1
    assert result.best_constraints.total_cp == baseline.total_cp + 1
    assert np.isfinite(result.best_rating.WTR)
    assert len(result.history) == 1


def test_optimize_addition_greedy_two_steps():
    baseline = _six_point_baseline()
    pool = _two_candidate_pool()

    result = optimize_addition(baseline, pool, n_add=2, method="greedy")

    assert len(result.indices_added) == 2
    assert result.best_constraints.total_cp == baseline.total_cp + 2


def test_optimize_addition_greedy_empty_pool():
    baseline = _six_point_baseline()
    pool = ConstraintSet()

    result = optimize_addition(baseline, pool, n_add=1, method="greedy")
    assert result.indices_added == []
    assert result.best_constraints.total_cp == baseline.total_cp


def test_optimize_addition_greedy_n_add_zero():
    baseline = _six_point_baseline()
    pool = _two_candidate_pool()

    result = optimize_addition(baseline, pool, n_add=0, method="greedy")
    assert result.indices_added == []


# ── optimize_addition — full enumeration ─────────────────────────────────────

def test_optimize_addition_full_smoke():
    baseline = _six_point_baseline()
    pool = _two_candidate_pool()

    result = optimize_addition(baseline, pool, n_add=1, method="full")

    assert isinstance(result, AdditionResult)
    assert len(result.indices_added) == 1
    # History should have 2 entries (one per candidate in pool)
    assert len(result.history) == 2


def test_optimize_addition_full_two_candidates_one_add():
    baseline = _six_point_baseline()
    pool = _two_candidate_pool()

    result = optimize_addition(baseline, pool, n_add=1, method="full")
    # Both candidates evaluated, best one selected
    assert result.best_constraints.total_cp == baseline.total_cp + 1


def test_optimize_addition_full_two_candidates_two_add():
    baseline = _six_point_baseline()
    pool = _two_candidate_pool()

    result = optimize_addition(baseline, pool, n_add=2, method="full")
    # Only one combo: C(2,2) = 1
    assert len(result.history) == 1
    assert result.best_constraints.total_cp == baseline.total_cp + 2


# ── optim_main_add (MATLAB-compatible) ───────────────────────────────────────

def test_optim_main_add_returns_correct_shapes():
    baseline = _six_point_baseline()
    pool = _two_candidate_pool()

    wtr_all, cp_add_comb, wtr_chg, mrr_chg, mtr_chg, tor_chg = optim_main_add(
        baseline, pool, no_add=1
    )

    # Two candidates => two combos for no_add=1
    assert wtr_all.shape == (2,)
    assert cp_add_comb.shape == (2, 1)
    assert wtr_chg.shape == (2,)
    assert mrr_chg.shape == (2,)
    assert mtr_chg.shape == (2,)
    assert tor_chg.shape == (2,)
    assert np.all(np.isfinite(wtr_all))


def test_optim_main_add_empty_pool():
    baseline = _six_point_baseline()
    pool = ConstraintSet()

    wtr_all, cp_add_comb, *_ = optim_main_add(baseline, pool, no_add=1)
    assert wtr_all.shape == (1,)
    assert cp_add_comb.shape[0] == 0


def test_optim_main_add_progress_callback():
    baseline = _six_point_baseline()
    pool = _two_candidate_pool()
    calls = []

    def cb(current, total):
        calls.append((current, total))

    optim_main_add(baseline, pool, no_add=1, progress_callback=cb)
    assert len(calls) == 2
    assert calls[-1] == (2, 2)


def test_optim_main_add_pct_change_sign():
    """Adding a constraint generally changes ratings; % change should be finite."""
    baseline = _six_point_baseline()
    pool = _two_candidate_pool()

    _, _, wtr_chg, mrr_chg, mtr_chg, _ = optim_main_add(baseline, pool, no_add=1)
    assert np.all(np.isfinite(wtr_chg))
    assert np.all(np.isfinite(mrr_chg))
    assert np.all(np.isfinite(mtr_chg))


# ── mixed-type candidate pool ────────────────────────────────────────────────

def test_optimize_addition_mixed_type_pool():
    """Pool with both point and pin candidates; global index ordering is points then pins."""
    baseline = _six_point_baseline()
    pool = ConstraintSet(
        points=[
            PointConstraint(np.array([0.5, 0.0, 0.0]), np.array([0.0, 0.0, 1.0]))
        ],
        pins=[
            PinConstraint(np.array([0.0, 0.5, 0.0]), np.array([0.0, 0.0, 1.0]))
        ],
    )

    result = optimize_addition(baseline, pool, n_add=1, method="full")
    # Two total candidates (1 point + 1 pin), n_add=1 => 2 combos
    assert len(result.history) == 2
    assert result.best_constraints.total_cp == baseline.total_cp + 1
