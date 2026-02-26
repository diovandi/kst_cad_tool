"""
Sensitivity analysis: position and orientation perturbation (sens_analysis_pos, sens_analysis_orient).
Ported from sens_analysis_pos.m, sens_analysis_orient.m.
"""
from __future__ import annotations

from typing import Optional

import numpy as np
from numpy.typing import NDArray
from scipy.linalg import null_space

from ..constraints import ConstraintSet
from ..pipeline import DetailedAnalysisResult
from .revision import RevisionConfig, optim_main_rev


def sens_analysis_pos(
    baseline: DetailedAnalysisResult,
    constraints: ConstraintSet,
    pert_dist: float,
    no_step: int = 2,
    progress_callback: Optional[callable] = None,
) -> tuple[NDArray[np.float64], NDArray[np.float64], NDArray[np.float64], NDArray[np.float64]]:
    """Sensitivity analysis by perturbing constraint position (port of sens_analysis_pos.m).

    For each constraint idx, sets up a plane search space (grp_rev_type=4) with center at
    constraint and null(normal) directions, scale pert_dist; runs optim_main_rev and
    collects WTR/MRR/MTR/TOR change. Returns (SAP_WTR, SAP_MRR, SAP_MTR, SAP_TOR)
    each of shape (total_cp, no_step+1, no_step+1) for 2D grid.
    """
    cp, cpin, clin, cpln, cpln_prop = constraints.to_matlab_style_arrays()
    no_cp = cp.shape[0]
    no_cpin = cpin.shape[0]
    no_clin = clin.shape[0]
    no_cpln = cpln.shape[0]
    total_cp = no_cp + no_cpin + no_clin + no_cpln
    n = no_step + 1
    SAP_WTR = np.full((total_cp, n, n), np.nan, dtype=float)
    SAP_MRR = np.full((total_cp, n, n), np.nan, dtype=float)
    SAP_MTR = np.full((total_cp, n, n), np.nan, dtype=float)
    SAP_TOR = np.full((total_cp, n, n), np.nan, dtype=float)
    rating_base = baseline.rating

    for idx in range(1, total_cp + 1):
        if idx <= no_cp:
            k = idx - 1
            cp_ctr = cp[k, 0:3]
            cp_normal = cp[k, 3:6]
        elif idx <= no_cp + no_cpin:
            k = idx - 1 - no_cp
            cp_ctr = cpin[k, 0:3]
            cp_normal = cpin[k, 3:6]
        elif idx <= no_cp + no_cpin + no_clin:
            k = idx - 1 - no_cp - no_cpin
            cp_ctr = clin[k, 0:3]
            cp_normal = clin[k, 6:9]
        else:
            k = idx - 1 - no_cp - no_cpin - no_clin
            cp_ctr = cpln[k, 0:3]
            cp_normal = cpln[k, 3:6]
        xy = null_space(cp_normal.reshape(1, 3))
        if xy.shape[1] < 2:
            continue
        grp_srch_spc = np.concatenate([
            cp_ctr, xy[:, 0], np.array([pert_dist]), xy[:, 1], np.array([pert_dist])
        ]).astype(float)
        config = RevisionConfig(
            grp_members=[np.array([idx], dtype=np.int_)],
            grp_rev_type=np.array([4], dtype=np.int_),
            grp_srch_spc=[grp_srch_spc],
        )
        WTR_opt, MRR_opt, MTR_opt, TOR_opt, _ = optim_main_rev(
            baseline, config, no_step, progress_callback=progress_callback
        )
        if WTR_opt.ndim == 2:
            SAP_WTR[idx - 1, :, :] = (WTR_opt - rating_base.WTR) / max(rating_base.WTR, 1e-12) * 100
            SAP_MRR[idx - 1, :, :] = (MRR_opt - rating_base.MRR) / max(rating_base.MRR, 1e-12) * 100
            SAP_MTR[idx - 1, :, :] = (MTR_opt - rating_base.MTR) / max(rating_base.MTR, 1e-12) * 100
            SAP_TOR[idx - 1, :, :] = (TOR_opt - rating_base.TOR) / max(rating_base.TOR, 1e-12) * 100
        else:
            SAP_WTR[idx - 1, :, 0] = (WTR_opt - rating_base.WTR) / max(rating_base.WTR, 1e-12) * 100
            SAP_MRR[idx - 1, :, 0] = (MRR_opt - rating_base.MRR) / max(rating_base.MRR, 1e-12) * 100
            SAP_MTR[idx - 1, :, 0] = (MTR_opt - rating_base.MTR) / max(rating_base.MTR, 1e-12) * 100
            SAP_TOR[idx - 1, :, 0] = (TOR_opt - rating_base.TOR) / max(rating_base.TOR, 1e-12) * 100

    return SAP_WTR, SAP_MRR, SAP_MTR, SAP_TOR


def sens_analysis_orient(
    baseline: DetailedAnalysisResult,
    constraints: ConstraintSet,
    pert_angle: float,
    no_step: int = 2,
    progress_callback: Optional[callable] = None,
) -> tuple[NDArray[np.float64], NDArray[np.float64], NDArray[np.float64], NDArray[np.float64]]:
    """Sensitivity analysis by perturbing constraint orientation (port of sens_analysis_orient.m).

    For each constraint, sets up orient2d search (grp_rev_type=6) with null(normal) axes
    and pert_angle; runs optim_main_rev and collects rating change. Returns (SAO_WTR, SAO_MRR, SAO_MTR, SAO_TOR).
    """
    cp, cpin, clin, cpln, cpln_prop = constraints.to_matlab_style_arrays()
    no_cp = cp.shape[0]
    no_cpin = cpin.shape[0]
    no_clin = clin.shape[0]
    no_cpln = cpln.shape[0]
    total_cp = no_cp + no_cpin + no_clin + no_cpln
    n = no_step + 1
    SAO_WTR = np.full((total_cp, n, n), np.nan, dtype=float)
    SAO_MRR = np.full((total_cp, n, n), np.nan, dtype=float)
    SAO_MTR = np.full((total_cp, n, n), np.nan, dtype=float)
    SAO_TOR = np.full((total_cp, n, n), np.nan, dtype=float)
    rating_base = baseline.rating

    for idx in range(1, total_cp + 1):
        if idx <= no_cp:
            k = idx - 1
            cp_normal = cp[k, 3:6]
        elif idx <= no_cp + no_cpin:
            k = idx - 1 - no_cp
            cp_normal = cpin[k, 3:6]
        elif idx <= no_cp + no_cpin + no_clin:
            k = idx - 1 - no_cp - no_cpin
            cp_normal = clin[k, 6:9]
        else:
            k = idx - 1 - no_cp - no_cpin - no_clin
            cp_normal = cpln[k, 3:6]
        xy = null_space(cp_normal.reshape(1, 3))
        if xy.shape[1] < 2:
            continue
        grp_srch_spc = np.concatenate([
            xy[:, 0], xy[:, 1], np.array([pert_angle, pert_angle])
        ]).astype(float)
        config = RevisionConfig(
            grp_members=[np.array([idx], dtype=np.int_)],
            grp_rev_type=np.array([6], dtype=np.int_),
            grp_srch_spc=[grp_srch_spc],
        )
        WTR_opt, MRR_opt, MTR_opt, TOR_opt, _ = optim_main_rev(
            baseline, config, no_step, progress_callback=progress_callback
        )
        if WTR_opt.ndim == 2:
            SAO_WTR[idx - 1, :, :] = (WTR_opt - rating_base.WTR) / max(rating_base.WTR, 1e-12) * 100
            SAO_MRR[idx - 1, :, :] = (MRR_opt - rating_base.MRR) / max(rating_base.MRR, 1e-12) * 100
            SAO_MTR[idx - 1, :, :] = (MTR_opt - rating_base.MTR) / max(rating_base.MTR, 1e-12) * 100
            SAO_TOR[idx - 1, :, :] = (TOR_opt - rating_base.TOR) / max(rating_base.TOR, 1e-12) * 100
        else:
            SAO_WTR[idx - 1, :, 0] = (WTR_opt - rating_base.WTR) / max(rating_base.WTR, 1e-12) * 100
            SAO_MRR[idx - 1, :, 0] = (MRR_opt - rating_base.MRR) / max(rating_base.MRR, 1e-12) * 100
            SAO_MTR[idx - 1, :, 0] = (MTR_opt - rating_base.MTR) / max(rating_base.MTR, 1e-12) * 100
            SAO_TOR[idx - 1, :, 0] = (TOR_opt - rating_base.TOR) / max(rating_base.TOR, 1e-12) * 100

    return SAO_WTR, SAO_MRR, SAO_MTR, SAO_TOR
