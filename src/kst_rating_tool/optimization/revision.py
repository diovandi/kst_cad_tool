"""
Constraint revision optimization (optim_main_rev, optim_rev).
Ported from optim_main_rev.m and optim_rev.m.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, List, Optional

import numpy as np
from numpy.typing import NDArray

from ..constraints import ConstraintSet
from ..pipeline import DetailedAnalysisResult, run_main_loop, analyze_constraints_detailed
from ..rating import aggregate_ratings, rate_motset
from ..wrench import cp_to_wrench
from .search_space import (
    move_lin_srch,
    move_pln_srch,
    move_curvlin_srch,
    orient1d_srch,
    orient2d_srch,
    line_orient1d_srch,
    resize_lin_srch,
    resize_rectpln_srch,
    resize_circpln_srch,
)


@dataclass
class RevisionConfig:
    """Configuration for constraint revision (grp_members, grp_rev_type, grp_srch_spc)."""

    grp_members: List[NDArray[np.int_]]
    grp_rev_type: NDArray[np.int_]
    grp_srch_spc: List[NDArray[np.float64]]


def _apply_search(
    x: NDArray[np.float64],
    x_map: NDArray[np.int_],
    config: RevisionConfig,
    cp: NDArray[np.float64],
    cpin: NDArray[np.float64],
    clin: NDArray[np.float64],
    cpln: NDArray[np.float64],
    cpln_prop: NDArray[np.float64],
    no_cp: int,
    no_cpin: int,
    no_clin: int,
    no_cpln: int,
) -> None:
    """Apply search space modifications in place to cp, cpin, clin, cpln, cpln_prop."""
    for i in range(len(config.grp_members)):
        rev_type = int(config.grp_rev_type.flat[i])
        cp_rev_in_group = np.asarray(config.grp_members[i]).ravel()
        cp_rev_in_group = cp_rev_in_group[cp_rev_in_group != 0]
        if cp_rev_in_group.size == 0:
            continue
        srch = config.grp_srch_spc[i] if i < len(config.grp_srch_spc) else np.array([])
        if rev_type == 1:
            continue
        if rev_type == 2:
            x_grp = float(x[x_map[i, 0] - 1])
            move_lin_srch(x_grp, cp_rev_in_group, srch, cp, cpin, clin, cpln, no_cp, no_cpin, no_clin, no_cpln)
        elif rev_type == 3:
            x_grp = float(x[x_map[i, 0] - 1])
            move_curvlin_srch(x_grp, cp_rev_in_group, srch, cp, cpin, clin, cpln, no_cp, no_cpin, no_clin, no_cpln)
        elif rev_type == 4:
            x_grp = x[x_map[i, 0] - 1 : x_map[i, 1]]
            move_pln_srch(x_grp, cp_rev_in_group, srch, cp, cpin, clin, cpln, no_cp, no_cpin, no_clin, no_cpln)
        elif rev_type == 5:
            x_grp = float(x[x_map[i, 0] - 1])
            orient1d_srch(x_grp, cp_rev_in_group, srch, cp, cpin, clin, cpln, no_cp, no_cpin, no_clin, no_cpln)
        elif rev_type == 6:
            x_grp = x[x_map[i, 0] - 1 : x_map[i, 1]]
            orient2d_srch(x_grp, cp_rev_in_group, srch, cp, cpin, clin, cpln, no_cp, no_cpin, no_clin, no_cpln)
        elif rev_type == 7:
            x_grp = float(x[x_map[i, 0] - 1])
            line_orient1d_srch(x_grp, cp_rev_in_group, srch, clin, no_cp, no_cpin, no_clin, no_cpln)
        elif rev_type == 8:
            x_grp = float(x[x_map[i, 0] - 1])
            resize_lin_srch(x_grp, cp_rev_in_group, srch, clin, no_cp, no_cpin, no_clin, no_cpln)
        elif rev_type == 9:
            x_grp = x[x_map[i, 0] - 1 : x_map[i, 1]]
            resize_rectpln_srch(x_grp, cp_rev_in_group, srch, cpln_prop, no_cp, no_cpin, no_clin, no_cpln)
        elif rev_type == 10:
            x_grp = float(x[x_map[i, 0] - 1])
            resize_circpln_srch(x_grp, cp_rev_in_group, srch, cpln_prop, no_cp, no_cpin, no_clin, no_cpln)


def optim_rev(
    x: NDArray[np.float64],
    x_map: NDArray[np.int_],
    baseline: DetailedAnalysisResult,
    config: RevisionConfig,
    cp_rev_all: NDArray[np.int_],
    combo_proc_optimbase: NDArray[np.int_],
    combo_new: NDArray[np.int_],
    Ri_optimbase: NDArray[np.float64],
    mot_all_optimbase: NDArray[np.float64],
    mot_half_optimbase: NDArray[np.float64],
) -> tuple[NDArray[np.float64], NDArray[np.float64], NDArray[np.float64]]:
    """Single revision evaluation: apply x, re-rate revised columns, run main_loop on combo_new, merge and rate.
    Returns (Rating_all_rev, Ri_new_uniq, mot_all_new_uniq).
    """
    cp, cpin, clin, cpln, cpln_prop = baseline.constraints.to_matlab_style_arrays()
    no_cp, no_cpin, no_clin, no_cpln = cp.shape[0], cpin.shape[0], clin.shape[0], cpln.shape[0]
    cp = cp.copy()
    cpin = cpin.copy()
    clin = clin.copy()
    cpln = cpln.copy()
    cpln_prop = cpln_prop.copy() if cpln_prop.size else cpln_prop

    _apply_search(
        x, x_map, config,
        cp, cpin, clin, cpln, cpln_prop,
        no_cp, no_cpin, no_clin, no_cpln,
    )
    revised = ConstraintSet.from_matlab_style_arrays(cp, cpin, clin, cpln, cpln_prop)
    wr_all_new, pts_rev, max_d_rev = cp_to_wrench(revised)
    wr_all_new_list = [w.as_array() for w in wr_all_new]

    R_recalc = rate_motset(
        combo_proc_optimbase,
        mot_half_optimbase,
        cp_rev_all,
        revised,
        pts_rev,
        max_d_rev,
    )
    Ri_recalc = np.where(np.isfinite(R_recalc) & (R_recalc > 0), 1.0 / R_recalc, 0.0)
    Ri_optimbase_recalc = Ri_optimbase.copy()
    for j, col in enumerate(cp_rev_all.flat):
        col = int(col)
        if col < Ri_optimbase_recalc.shape[1]:
            Ri_optimbase_recalc[:, col - 1] = Ri_recalc[:, j]

    mot_half_add, R_add = run_main_loop(
        combo_new, wr_all_new_list, revised, pts_rev, max_d_rev
    )
    if mot_half_add.size == 0:
        Ri_new = Ri_optimbase_recalc
        mot_all_new = mot_all_optimbase
    else:
        Ri_add = np.where(np.isfinite(R_add) & (R_add > 0), 1.0 / R_add, 0.0)
        mot_all_add_rev = np.hstack([-mot_half_add[:, :6], mot_half_add[:, 6:]])
        mot_all_add = np.vstack([mot_half_add, mot_all_add_rev])
        Ri_new = np.vstack([Ri_optimbase_recalc, Ri_add])
        mot_all_new = np.vstack([mot_all_optimbase, mot_all_add])
    _, uniq_idx = np.unique(mot_all_new, axis=0, return_index=True)
    Ri_new_uniq = Ri_new[uniq_idx, :]
    mot_all_new_uniq = mot_all_new[uniq_idx, :]
    rating_res = aggregate_ratings(1.0 / np.maximum(Ri_new_uniq, 1e-12))
    Rating_all_rev = np.array([
        rating_res.WTR, rating_res.MRR, rating_res.MTR, rating_res.TOR
    ], dtype=float)
    return Rating_all_rev, Ri_new_uniq, mot_all_new_uniq


def optim_main_rev(
    baseline: DetailedAnalysisResult,
    config: RevisionConfig,
    no_step: int,
    progress_callback: Optional[Callable[[int, int], None]] = None,
) -> tuple[NDArray[np.float64], NDArray[np.float64], NDArray[np.float64], NDArray[np.float64], NDArray[np.int_]]:
    """Factorial search over normalized x in [-1,1]^no_dim. Returns WTR_optim_all, MRR_optim_all, MTR_optim_all, TOR_optim_all, and x_map (for postproc)."""
    cp_rev_all = np.unique(np.concatenate([g.ravel() for g in config.grp_members]))
    cp_rev_all = cp_rev_all[cp_rev_all != 0]
    if cp_rev_all.size == 0:
        return (
            np.array([baseline.rating.WTR]),
            np.array([baseline.rating.MRR]),
            np.array([baseline.rating.MTR]),
            np.array([baseline.rating.TOR]),
            np.zeros((0, 2), dtype=np.int_),
        )

    combo = baseline.combo
    combo_proc = baseline.combo_proc
    combo_dup_idx = baseline.combo_dup_idx
    no_mot_half = baseline.no_mot_half
    mot_half = baseline.mot_half
    mot_all = baseline.mot_all
    Ri = baseline.Ri

    del_idx = set()
    for c in cp_rev_all.flat:
        del_idx.update(np.where(combo == c)[0].tolist())
    del_idx = np.array(sorted(del_idx), dtype=np.int_)
    combo_red_idx = np.setdiff1d(np.arange(combo.shape[0]), del_idx)
    dup_idx = np.unique(combo_dup_idx[combo_red_idx])
    if dup_idx.size and dup_idx.flat[0] == 0:
        dup_idx = dup_idx[1:]
    del_idx_all = set()
    for c in cp_rev_all.flat:
        rows = np.where(combo_proc[:, 1:6] == c)[0]
        del_idx_all.update(rows.tolist())
    del_idx_all = np.array(sorted(del_idx_all), dtype=np.int_)
    del_idx_nondup = np.setdiff1d(del_idx_all, dup_idx)
    remain_idx = np.setdiff1d(np.arange(no_mot_half), del_idx_nondup)
    remain_idx_full = np.concatenate([remain_idx, remain_idx + no_mot_half])
    combo_proc_optimbase = combo_proc[remain_idx, 1:6]
    mot_half_optimbase = mot_half[remain_idx]
    mot_all_optimbase = mot_all[remain_idx_full]
    Ri_optimbase = Ri[remain_idx_full, :]
    combo_new = combo[del_idx, :]

    row = 1
    x_map = np.zeros((len(config.grp_members), 2), dtype=np.int_)
    for i in range(len(config.grp_members)):
        if config.grp_rev_type.flat[i] in (4, 6, 9):
            x_map[i, 0] = row
            x_map[i, 1] = row + 1
            row += 2
        else:
            x_map[i, 0] = row
            x_map[i, 1] = 0
            row += 1
    no_dim = row - 1

    n_inc = no_step + 1
    a_vals = np.linspace(-1, 1, n_inc)
    tot_it = n_inc ** no_dim

    Rating_org = np.array([
        baseline.rating.WTR, baseline.rating.MRR, baseline.rating.MTR, baseline.rating.TOR
    ])

    if no_dim == 1:
        WTR_list: List[float] = []
        MRR_list: List[float] = []
        MTR_list: List[float] = []
        for ai in range(n_inc):
            if progress_callback:
                progress_callback(ai + 1, tot_it)
            x = np.array([a_vals[ai]], dtype=float)
            Rating_all_rev, _, _ = optim_rev(
                x, x_map, baseline, config, cp_rev_all,
                combo_proc_optimbase, combo_new,
                Ri_optimbase, mot_all_optimbase, mot_half_optimbase,
            )
            WTR_list.append(Rating_all_rev[0])
            MRR_list.append(Rating_all_rev[1])
            MTR_list.append(Rating_all_rev[2])
        WTR_optim_all = np.array(WTR_list)
        MRR_optim_all = np.array(MRR_list)
        MTR_optim_all = np.array(MTR_list)
    elif no_dim == 2:
        WTR_optim_all = np.zeros((n_inc, n_inc), dtype=float)
        MRR_optim_all = np.zeros((n_inc, n_inc), dtype=float)
        MTR_optim_all = np.zeros((n_inc, n_inc), dtype=float)
        count = 0
        for ai in range(n_inc):
            for bi in range(n_inc):
                if progress_callback:
                    progress_callback(count + 1, tot_it)
                count += 1
                x = np.array([a_vals[ai], a_vals[bi]], dtype=float)
                Rating_all_rev, _, _ = optim_rev(
                    x, x_map, baseline, config, cp_rev_all,
                    combo_proc_optimbase, combo_new,
                    Ri_optimbase, mot_all_optimbase, mot_half_optimbase,
                )
                WTR_optim_all[ai, bi] = Rating_all_rev[0]
                MRR_optim_all[ai, bi] = Rating_all_rev[1]
                MTR_optim_all[ai, bi] = Rating_all_rev[2]
    elif no_dim == 3:
        WTR_optim_all = np.zeros((n_inc, n_inc, n_inc), dtype=float)
        MRR_optim_all = np.zeros((n_inc, n_inc, n_inc), dtype=float)
        MTR_optim_all = np.zeros((n_inc, n_inc, n_inc), dtype=float)
        count = 0
        for ai in range(n_inc):
            for bi in range(n_inc):
                for ci in range(n_inc):
                    if progress_callback:
                        progress_callback(count + 1, tot_it)
                    count += 1
                    x = np.array([a_vals[ai], a_vals[bi], a_vals[ci]], dtype=float)
                    Rating_all_rev, _, _ = optim_rev(
                        x, x_map, baseline, config, cp_rev_all,
                        combo_proc_optimbase, combo_new,
                        Ri_optimbase, mot_all_optimbase, mot_half_optimbase,
                    )
                    WTR_optim_all[ai, bi, ci] = Rating_all_rev[0]
                    MRR_optim_all[ai, bi, ci] = Rating_all_rev[1]
                    MTR_optim_all[ai, bi, ci] = Rating_all_rev[2]
    else:
        WTR_optim_all = np.full((n_inc,) * no_dim, np.nan, dtype=float)
        MRR_optim_all = np.full((n_inc,) * no_dim, np.nan, dtype=float)
        MTR_optim_all = np.full((n_inc,) * no_dim, np.nan, dtype=float)
        for ai in range(n_inc):
            for bi in range(n_inc):
                x = np.array([a_vals[ai], a_vals[bi]] + [a_vals[0]] * max(0, no_dim - 2), dtype=float)
                Rating_all_rev, _, _ = optim_rev(
                    x, x_map, baseline, config, cp_rev_all,
                    combo_proc_optimbase, combo_new,
                    Ri_optimbase, mot_all_optimbase, mot_half_optimbase,
                )
                idx = (ai, bi) + (0,) * (no_dim - 2)
                WTR_optim_all[idx] = Rating_all_rev[0]
                MRR_optim_all[idx] = Rating_all_rev[1]
                MTR_optim_all[idx] = Rating_all_rev[2]

    TOR_optim_all = np.where(MRR_optim_all != 0, MTR_optim_all / MRR_optim_all, np.nan)
    return WTR_optim_all, MRR_optim_all, MTR_optim_all, TOR_optim_all, x_map
