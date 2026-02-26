"""
Known-loading (specmot) optimization: rate_specmot, main_specmot_optim.
Ported from rate_specmot.m, main_specmot_optim.m.
"""
from __future__ import annotations

from typing import List, Optional, Tuple

import numpy as np
from numpy.typing import NDArray

from ..constraints import ConstraintSet
from ..pipeline import analyze_specified_motions
from ..rating import RatingResults
from .revision import RevisionConfig, _apply_search


def rate_specmot(
    x: NDArray[np.float64],
    x_map: NDArray[np.int_],
    config: RevisionConfig,
    constraints: ConstraintSet,
    specmot: NDArray[np.float64],
) -> Tuple[RatingResults, NDArray[np.float64], NDArray[np.float64]]:
    """Rate constraints for specified motion(s) after applying revision config (port of rate_specmot.m).

    Copies constraint arrays, applies search-space modifications per config, then runs
    analyze_specified_motions on the revised constraints. Returns (rating, Ri, mot_proc).
    """
    cp, cpin, clin, cpln, cpln_prop = constraints.to_matlab_style_arrays()
    no_cp = cp.shape[0]
    no_cpin = cpin.shape[0]
    no_clin = clin.shape[0]
    no_cpln = cpln.shape[0]
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
    result = analyze_specified_motions(revised, specmot)
    return result.rating, result.Ri, result.mot_proc


def main_specmot_optim(
    config: RevisionConfig,
    constraints: ConstraintSet,
    specmot: NDArray[np.float64],
    no_step: int = 10,
    progress_callback: Optional[callable] = None,
) -> Tuple[NDArray[np.float64], NDArray[np.float64], NDArray[np.float64], NDArray[np.float64], NDArray[np.int_]]:
    """Known-loading optimization over revision parameters (port of main_specmot_optim.m).

    Factorial search over x in [-1, 1]^no_dim with no_step; for each x calls rate_specmot.
    Returns WTR_optim, MRR_optim, MTR_optim, TOR_optim (1D or 2D per no_dim), and x_map.
    """
    grp_rev_type = config.grp_rev_type
    row = 1
    x_map = np.zeros((len(config.grp_members), 2), dtype=np.int_)
    for i in range(grp_rev_type.size):
        rt = int(grp_rev_type.flat[i])
        if rt in (4, 6, 9):
            x_map[i, :] = [row, row + 1]
            row += 2
        else:
            x_map[i, :] = [row, 0]
            row += 1
    no_dim = row - 1
    if no_dim == 0:
        r = analyze_specified_motions(constraints, specmot).rating
        return (
            np.array([r.WTR]),
            np.array([r.MRR]),
            np.array([r.MTR]),
            np.array([r.TOR]),
            x_map,
        )
    x_inc = np.linspace(-1.0, 1.0, no_step + 1)
    tot_it = (no_step + 1) ** no_dim
    tot_i = [0]

    if no_dim == 1:
        WTR_list: List[float] = []
        MRR_list: List[float] = []
        MTR_list: List[float] = []
        TOR_list: List[float] = []
        for ai, a in enumerate(x_inc):
            x = np.array([a], dtype=float)
            if progress_callback and tot_i[0] % max(1, tot_it // 10) == 0:
                progress_callback(tot_i[0], tot_it)
            rating, _, _ = rate_specmot(x, x_map, config, constraints, specmot)
            WTR_list.append(rating.WTR)
            MRR_list.append(rating.MRR)
            MTR_list.append(rating.MTR)
            TOR_list.append(rating.TOR)
            tot_i[0] += 1
        WTR_optim = np.array(WTR_list, dtype=float)
        MRR_optim = np.array(MRR_list, dtype=float)
        MTR_optim = np.array(MTR_list, dtype=float)
        TOR_optim = np.array(TOR_list, dtype=float)
        return WTR_optim, MRR_optim, MTR_optim, TOR_optim, x_map

    if no_dim == 2:
        WTR_optim = np.full((len(x_inc), len(x_inc)), np.nan, dtype=float)
        MRR_optim = np.full((len(x_inc), len(x_inc)), np.nan, dtype=float)
        MTR_optim = np.full((len(x_inc), len(x_inc)), np.nan, dtype=float)
        TOR_optim = np.full((len(x_inc), len(x_inc)), np.nan, dtype=float)
        for ai, a in enumerate(x_inc):
            for bi, b in enumerate(x_inc):
                x = np.array([a, b], dtype=float)
                if progress_callback and tot_i[0] % max(1, tot_it // 10) == 0:
                    progress_callback(tot_i[0], tot_it)
                rating, _, _ = rate_specmot(x, x_map, config, constraints, specmot)
                WTR_optim[ai, bi] = rating.WTR
                MRR_optim[ai, bi] = rating.MRR
                MTR_optim[ai, bi] = rating.MTR
                TOR_optim[ai, bi] = rating.TOR if rating.MRR != 0 else np.nan
                tot_i[0] += 1
        with np.errstate(divide="ignore", invalid="ignore"):
            TOR_optim = np.where(MRR_optim != 0, MTR_optim / MRR_optim, np.nan)
        return WTR_optim, MRR_optim, MTR_optim, TOR_optim, x_map

    WTR_list = []
    MRR_list = []
    MTR_list = []
    TOR_list = []
    for ai, a in enumerate(x_inc):
        x = np.array([a] + [0.0] * (no_dim - 1), dtype=float)
        if no_dim > 1:
            x[1] = x_inc[0]
        if progress_callback and tot_i[0] % max(1, tot_it // 10) == 0:
            progress_callback(tot_i[0], tot_it)
        rating, _, _ = rate_specmot(x, x_map, config, constraints, specmot)
        WTR_list.append(rating.WTR)
        MRR_list.append(rating.MRR)
        MTR_list.append(rating.MTR)
        TOR_list.append(rating.TOR if rating.MRR != 0 else np.nan)
        tot_i[0] += 1
    return (
        np.array(WTR_list),
        np.array(MRR_list),
        np.array(MTR_list),
        np.array(TOR_list),
        x_map,
    )
