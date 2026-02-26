"""
Constraint reduction optimization (optim_main_red).
Ported from optim_main_red.m.
Adds constraint_set_without, optimize_reduction (greedy/full).
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
from ..pipeline import DetailedAnalysisResult, analyze_constraints, analyze_constraints_detailed
from ..rating import RatingResults, aggregate_ratings


def constraint_set_without(
    constraints: ConstraintSet,
    indices_to_remove: Sequence[int],
) -> ConstraintSet:
    """Build a new ConstraintSet omitting the given constraint indices.

    Indices are global 0-based in order: points, then pins, then lines, then planes.
    This ordering matches ConstraintSet.total_cp and combo_preproc.

    Parameters
    ----------
    constraints
        Full constraint set.
    indices_to_remove
        0-based global indices of constraints to omit.

    Returns
    -------
    ConstraintSet
        New set with specified constraints removed.
    """
    remove_set = set(indices_to_remove)
    n_pt = len(constraints.points)
    n_pin = len(constraints.pins)
    n_lin = len(constraints.lines)
    n_pln = len(constraints.planes)

    points = [
        PointConstraint(
            constraints.points[i].position.copy(),
            constraints.points[i].normal.copy(),
        )
        for i in range(n_pt)
        if i not in remove_set
    ]
    pins = [
        PinConstraint(
            constraints.pins[i].center.copy(),
            constraints.pins[i].axis.copy(),
        )
        for i in range(n_pin)
        if (n_pt + i) not in remove_set
    ]
    lines = [
        LineConstraint(
            constraints.lines[i].midpoint.copy(),
            constraints.lines[i].line_dir.copy(),
            constraints.lines[i].constraint_dir.copy(),
            constraints.lines[i].length,
        )
        for i in range(n_lin)
        if (n_pt + n_pin + i) not in remove_set
    ]
    planes = [
        PlaneConstraint(
            constraints.planes[i].midpoint.copy(),
            constraints.planes[i].normal.copy(),
            constraints.planes[i].type,
            constraints.planes[i].prop.copy(),
        )
        for i in range(n_pln)
        if (n_pt + n_pin + n_lin + i) not in remove_set
    ]
    return ConstraintSet(points=points, pins=pins, lines=lines, planes=planes)


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
class ReductionResult:
    """Result of constraint reduction optimization."""

    best_constraints: ConstraintSet
    best_rating: RatingResults
    indices_removed: list[int]
    history: list[tuple[list[int], RatingResults]] = field(default_factory=list)


def optimize_reduction(
    constraints: ConstraintSet,
    n_remove: int,
    method: Literal["greedy", "full"] = "greedy",
    objective: str = "TOR",
) -> ReductionResult:
    """Find which constraints to remove to maximize the chosen rating metric.

    Parameters
    ----------
    constraints
        Full constraint set.
    n_remove
        Number of constraints to remove.
    method
        'greedy': remove one at a time, each step choosing the removal that
        gives the best metric (O(n_remove * total_cp) evaluations).
        'full': enumerate all combinations (only for small total_cp and n_remove).
    objective
        Metric to maximize: 'TOR', 'WTR', 'MRR', or 'MTR'.

    Returns
    -------
    ReductionResult
        Best reduced ConstraintSet, its ratings, indices removed, and history.
    """
    total_cp = constraints.total_cp
    if n_remove >= total_cp:
        raise ValueError("n_remove must be less than total number of constraints")
    if n_remove <= 0:
        return ReductionResult(
            best_constraints=constraints,
            best_rating=analyze_constraints(constraints),
            indices_removed=[],
            history=[],
        )

    if method == "full":
        return _optimize_reduction_full(constraints, n_remove, objective)
    return _optimize_reduction_greedy(constraints, n_remove, objective)


def _optimize_reduction_greedy(
    constraints: ConstraintSet,
    n_remove: int,
    objective: str,
) -> ReductionResult:
    current = constraints
    removed: list[int] = []
    history: list[tuple[list[int], RatingResults]] = []
    total_cp = constraints.total_cp
    remaining_indices = list(range(total_cp))

    for _ in range(n_remove):
        best_metric = float("-inf")
        best_idx: Optional[int] = None
        best_rating: Optional[RatingResults] = None
        for idx in remaining_indices:
            candidate_removed = removed + [idx]
            reduced = constraint_set_without(constraints, candidate_removed)
            rating = analyze_constraints(reduced)
            val = _objective_value(rating, objective)
            if val > best_metric:
                best_metric = val
                best_idx = idx
                best_rating = rating
        if best_idx is None or best_rating is None:
            break
        removed.append(best_idx)
        remaining_indices.remove(best_idx)
        history.append((list(removed), best_rating))

    best_constraints = constraint_set_without(constraints, removed)
    best_rating = analyze_constraints(best_constraints) if removed else analyze_constraints(constraints)
    return ReductionResult(
        best_constraints=best_constraints,
        best_rating=best_rating,
        indices_removed=removed,
        history=history,
    )


def _optimize_reduction_full(
    constraints: ConstraintSet,
    n_remove: int,
    objective: str,
) -> ReductionResult:
    total_cp = constraints.total_cp
    best_metric = float("-inf")
    best_removed: list[int] = []
    best_rating: Optional[RatingResults] = None
    history: list[tuple[list[int], RatingResults]] = []

    for combo in itertools.combinations(range(total_cp), n_remove):
        removed = list(combo)
        reduced = constraint_set_without(constraints, removed)
        rating = analyze_constraints(reduced)
        history.append((removed, rating))
        val = _objective_value(rating, objective)
        if val > best_metric:
            best_metric = val
            best_removed = removed
            best_rating = rating

    best_constraints = constraint_set_without(constraints, best_removed)
    return ReductionResult(
        best_constraints=best_constraints,
        best_rating=best_rating if best_rating is not None else analyze_constraints(best_constraints),
        indices_removed=best_removed,
        history=history,
    )


def optim_main_red(
    baseline: DetailedAnalysisResult,
    no_red: int,
    progress_callback: Optional[Callable[[int, int], None]] = None,
) -> tuple[NDArray[np.float64], NDArray[np.int_], NDArray[np.float64], NDArray[np.float64], NDArray[np.float64], NDArray[np.float64]]:
    """Try removing no_red constraints at a time; return WTR/MRR/MTR/TOR per removal combination and % change.

    Returns:
        WTR_optim_all: (n_combos,) WTR after removal
        cp_del_comb: (n_combos, no_red) constraint indices removed per combo
        WTR_optim_chg, MRR_optim_chg, MTR_optim_chg, TOR_optim_chg: percent change vs baseline
    """
    import itertools
    total_cp = baseline.constraints.total_cp
    if no_red > total_cp or no_red < 1:
        return (
            np.array([baseline.rating.WTR]),
            np.empty((0, no_red), dtype=np.int_),
            np.zeros(1),
            np.zeros(1),
            np.zeros(1),
            np.zeros(1),
        )

    combo = baseline.combo
    combo_proc = baseline.combo_proc
    combo_dup_idx = baseline.combo_dup_idx
    no_mot_half = baseline.no_mot_half
    mot_half = baseline.mot_half
    mot_all = baseline.mot_all
    Ri = baseline.Ri

    Rating_org = np.array([
        baseline.rating.WTR, baseline.rating.MRR, baseline.rating.MTR, baseline.rating.TOR
    ])

    cp_del_comb = np.array(list(itertools.combinations(range(1, total_cp + 1), no_red)), dtype=np.int_)
    n_combos = cp_del_comb.shape[0]

    WTR_list: List[float] = []
    MRR_list: List[float] = []
    MTR_list: List[float] = []

    for a in range(n_combos):
        if progress_callback:
            progress_callback(a + 1, n_combos)
        cp_del_idx = cp_del_comb[a, :]

        del_idx = set()
        for c in cp_del_idx.flat:
            del_idx.update(np.where(combo == c)[0].tolist())
        del_idx = np.array(sorted(del_idx), dtype=np.int_)
        combo_red_idx = np.setdiff1d(np.arange(combo.shape[0]), del_idx)
        dup_idx = np.unique(combo_dup_idx[combo_red_idx])
        if dup_idx.size and dup_idx.flat[0] == 0:
            dup_idx = dup_idx[1:]
        del_idx_all = set()
        for c in cp_del_idx.flat:
            rows = np.where(combo_proc[:, 1:6] == c)[0]
            del_idx_all.update(rows.tolist())
        del_idx_all = np.array(sorted(del_idx_all), dtype=np.int_)
        del_idx_nondup = np.setdiff1d(del_idx_all, dup_idx)
        remain_idx = np.setdiff1d(np.arange(no_mot_half), del_idx_nondup)
        remain_idx_full = np.concatenate([remain_idx, remain_idx + no_mot_half])

        combo_proc_red = combo_proc[remain_idx, 1:6]
        Ri_red = Ri[remain_idx_full, :]
        Ri_red = np.delete(Ri_red, np.array(cp_del_idx) - 1, axis=1)
        mot_all_red = mot_all[remain_idx_full]

        mot_all_red_uniq, uniq_idx = np.unique(mot_all_red, axis=0, return_index=True)
        Ri_red_uniq = Ri_red[uniq_idx, :]

        rating_res = aggregate_ratings(1.0 / np.maximum(Ri_red_uniq, 1e-12))
        WTR_list.append(rating_res.WTR)
        MRR_list.append(rating_res.MRR)
        MTR_list.append(rating_res.MTR)

    WTR_optim_all = np.array(WTR_list)
    MRR_optim_all = np.array(MRR_list)
    MTR_optim_all = np.array(MTR_list)
    TOR_optim_all = np.where(MRR_optim_all != 0, MTR_optim_all / MRR_optim_all, np.nan)

    WTR_optim_chg = np.where(Rating_org[0] != 0, (WTR_optim_all - Rating_org[0]) / Rating_org[0] * 100, 0)
    MRR_optim_chg = np.where(Rating_org[1] != 0, (MRR_optim_all - Rating_org[1]) / Rating_org[1] * 100, 0)
    MTR_optim_chg = np.where(Rating_org[2] != 0, (MTR_optim_all - Rating_org[2]) / Rating_org[2] * 100, 0)
    TOR_optim_chg = np.where(Rating_org[3] != 0, (TOR_optim_all - Rating_org[3]) / Rating_org[3] * 100, 0)

    return WTR_optim_all, cp_del_comb, WTR_optim_chg, MRR_optim_chg, MTR_optim_chg, TOR_optim_chg
