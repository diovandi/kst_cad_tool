"""
Constraint addition optimization (optim_main_add).
Clean Python implementation; the original MATLAB optim_main_add.m was marked
"preliminary and contains errors" (constraint indices were used as scalars instead
of row slices). This module fixes that and mirrors the pattern of reduction.py.
"""

from __future__ import annotations

import itertools
from dataclasses import dataclass, field
from typing import Callable, List, Literal, Optional, Sequence

import numpy as np
from numpy.typing import NDArray

from ..constraints import (
    ConstraintSet,
    LineConstraint,
    PinConstraint,
    PlaneConstraint,
    PointConstraint,
)
from ..pipeline import analyze_constraints
from ..rating import RatingResults


def constraint_set_with(
    baseline: ConstraintSet,
    pool: ConstraintSet,
    indices_to_add: Sequence[int],
) -> ConstraintSet:
    """Build a new ConstraintSet combining baseline with selected pool constraints.

    Indices into *pool* are global 0-based in order: points, then pins, then
    lines, then planes — the same ordering as ConstraintSet.total_cp.

    Parameters
    ----------
    baseline
        Existing constraint set (unchanged).
    pool
        Candidate constraints to draw from.
    indices_to_add
        0-based global indices into *pool* of constraints to add.

    Returns
    -------
    ConstraintSet
        New set = baseline + selected pool constraints (deep copies).
    """
    add_set = set(indices_to_add)
    n_pt = len(pool.points)
    n_pin = len(pool.pins)
    n_lin = len(pool.lines)

    extra_points = [
        PointConstraint(pool.points[i].position.copy(), pool.points[i].normal.copy())
        for i in range(n_pt)
        if i in add_set
    ]
    extra_pins = [
        PinConstraint(pool.pins[i].center.copy(), pool.pins[i].axis.copy())
        for i in range(n_pin)
        if (n_pt + i) in add_set
    ]
    extra_lines = [
        LineConstraint(
            pool.lines[i].midpoint.copy(),
            pool.lines[i].line_dir.copy(),
            pool.lines[i].constraint_dir.copy(),
            pool.lines[i].length,
        )
        for i in range(n_lin)
        if (n_pt + n_pin + i) in add_set
    ]
    extra_planes = [
        PlaneConstraint(
            pool.planes[i].midpoint.copy(),
            pool.planes[i].normal.copy(),
            pool.planes[i].type,
            pool.planes[i].prop.copy(),
        )
        for i in range(len(pool.planes))
        if (n_pt + n_pin + n_lin + i) in add_set
    ]

    return ConstraintSet(
        points=list(baseline.points) + extra_points,
        pins=list(baseline.pins) + extra_pins,
        lines=list(baseline.lines) + extra_lines,
        planes=list(baseline.planes) + extra_planes,
    )


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
class AdditionResult:
    """Result of constraint addition optimization."""

    best_constraints: ConstraintSet
    best_rating: RatingResults
    indices_added: list[int]  # 0-based indices into candidate_pool
    history: list[tuple[list[int], RatingResults]] = field(default_factory=list)


def optimize_addition(
    baseline: ConstraintSet,
    candidate_pool: ConstraintSet,
    n_add: int = 1,
    method: Literal["greedy", "full"] = "greedy",
    objective: str = "TOR",
) -> AdditionResult:
    """Find which constraints from *candidate_pool* to add to *baseline* to maximise the rating.

    Parameters
    ----------
    baseline
        Existing constraint set to augment.
    candidate_pool
        Candidate constraints that may be added.  All four types are supported;
        indices follow the standard global ordering (points -> pins -> lines -> planes).
    n_add
        Number of constraints to add.
    method
        ``'greedy'``: add one at a time, each step choosing the candidate that
        gives the best metric (O(n_add * pool_size) evaluations).
        ``'full'``: enumerate all C(pool_size, n_add) combinations.
    objective
        Metric to maximise: ``'TOR'``, ``'WTR'``, ``'MRR'``, or ``'MTR'``.

    Returns
    -------
    AdditionResult
        Best augmented ConstraintSet, its ratings, indices added, and history.
    """
    pool_size = candidate_pool.total_cp
    if pool_size == 0 or n_add <= 0:
        return AdditionResult(
            best_constraints=baseline,
            best_rating=analyze_constraints(baseline),
            indices_added=[],
            history=[],
        )
    n_add = min(n_add, pool_size)

    if method == "full":
        return _optimize_addition_full(baseline, candidate_pool, n_add, objective)
    return _optimize_addition_greedy(baseline, candidate_pool, n_add, objective)


def _optimize_addition_greedy(
    baseline: ConstraintSet,
    pool: ConstraintSet,
    n_add: int,
    objective: str,
) -> AdditionResult:
    current = baseline
    added: list[int] = []
    history: list[tuple[list[int], RatingResults]] = []
    remaining = list(range(pool.total_cp))

    for _ in range(n_add):
        best_metric = float("-inf")
        best_idx: Optional[int] = None
        best_rating: Optional[RatingResults] = None
        for idx in remaining:
            augmented = constraint_set_with(current, pool, [idx])
            rating = analyze_constraints(augmented)
            val = _objective_value(rating, objective)
            if val > best_metric:
                best_metric = val
                best_idx = idx
                best_rating = rating
        if best_idx is None or best_rating is None:
            break
        # Commit: build the new baseline including this best pick
        current = constraint_set_with(current, pool, [best_idx])
        added.append(best_idx)
        remaining.remove(best_idx)
        history.append((list(added), best_rating))

    best_constraints = constraint_set_with(baseline, pool, added)
    best_rating_final = analyze_constraints(best_constraints) if added else analyze_constraints(baseline)
    return AdditionResult(
        best_constraints=best_constraints,
        best_rating=best_rating_final,
        indices_added=added,
        history=history,
    )


def _optimize_addition_full(
    baseline: ConstraintSet,
    pool: ConstraintSet,
    n_add: int,
    objective: str,
) -> AdditionResult:
    pool_size = pool.total_cp
    best_metric = float("-inf")
    best_added: list[int] = []
    best_rating: Optional[RatingResults] = None
    history: list[tuple[list[int], RatingResults]] = []

    for combo in itertools.combinations(range(pool_size), n_add):
        indices = list(combo)
        augmented = constraint_set_with(baseline, pool, indices)
        rating = analyze_constraints(augmented)
        history.append((indices, rating))
        val = _objective_value(rating, objective)
        if val > best_metric:
            best_metric = val
            best_added = indices
            best_rating = rating

    best_constraints = constraint_set_with(baseline, pool, best_added)
    return AdditionResult(
        best_constraints=best_constraints,
        best_rating=best_rating if best_rating is not None else analyze_constraints(best_constraints),
        indices_added=best_added,
        history=history,
    )


def optim_main_add(
    baseline_cs: ConstraintSet,
    candidate_pool: ConstraintSet,
    no_add: int = 1,
    progress_callback: Optional[Callable[[int, int], None]] = None,
) -> tuple[
    NDArray[np.float64],
    NDArray[np.int_],
    NDArray[np.float64],
    NDArray[np.float64],
    NDArray[np.float64],
    NDArray[np.float64],
]:
    """Try adding no_add constraints at a time; return WTR/MRR/MTR/TOR per addition
    combination and % change vs baseline (MATLAB-compatible interface).

    Enumerates all C(pool_size, no_add) combinations and evaluates each.  For
    large pools, prefer ``optimize_addition(..., method='greedy')`` instead.

    Parameters
    ----------
    baseline_cs
        Existing constraint set to augment.
    candidate_pool
        Pool of candidate constraints to add from.
    no_add
        Number of constraints to add per combination.
    progress_callback
        Optional callback(current_iter, total_iters).

    Returns
    -------
    WTR_optim_all : (n_combos,)
    cp_add_comb   : (n_combos, no_add)  0-based pool indices added per combo
    WTR_optim_chg : (n_combos,)  % change vs baseline
    MRR_optim_chg : (n_combos,)
    MTR_optim_chg : (n_combos,)
    TOR_optim_chg : (n_combos,)
    """
    pool_size = candidate_pool.total_cp
    baseline_rating = analyze_constraints(baseline_cs)
    Rating_org = np.array([
        baseline_rating.WTR, baseline_rating.MRR,
        baseline_rating.MTR, baseline_rating.TOR,
    ])

    if no_add < 1 or pool_size == 0:
        return (
            np.array([baseline_rating.WTR]),
            np.empty((0, max(no_add, 1)), dtype=np.int_),
            np.zeros(1),
            np.zeros(1),
            np.zeros(1),
            np.zeros(1),
        )

    no_add = min(no_add, pool_size)
    combos = list(itertools.combinations(range(pool_size), no_add))
    cp_add_comb = np.array(combos, dtype=np.int_)
    n_combos = len(combos)

    WTR_list: List[float] = []
    MRR_list: List[float] = []
    MTR_list: List[float] = []
    TOR_list: List[float] = []

    for a, indices in enumerate(combos):
        if progress_callback:
            progress_callback(a + 1, n_combos)
        augmented = constraint_set_with(baseline_cs, candidate_pool, list(indices))
        rating = analyze_constraints(augmented)
        WTR_list.append(rating.WTR)
        MRR_list.append(rating.MRR)
        MTR_list.append(rating.MTR)
        TOR_list.append(rating.TOR if rating.MRR != 0 else float("nan"))

    WTR_optim_all = np.array(WTR_list)
    MRR_optim_all = np.array(MRR_list)
    MTR_optim_all = np.array(MTR_list)
    TOR_optim_all = np.array(TOR_list)

    def _pct_chg(arr: NDArray, base: float) -> NDArray:
        with np.errstate(divide="ignore", invalid="ignore"):
            return np.where(base != 0, (arr - base) / base * 100, 0.0)

    WTR_optim_chg = _pct_chg(WTR_optim_all, Rating_org[0])
    MRR_optim_chg = _pct_chg(MRR_optim_all, Rating_org[1])
    MTR_optim_chg = _pct_chg(MTR_optim_all, Rating_org[2])
    TOR_optim_chg = _pct_chg(TOR_optim_all, Rating_org[3])

    return WTR_optim_all, cp_add_comb, WTR_optim_chg, MRR_optim_chg, MTR_optim_chg, TOR_optim_chg
