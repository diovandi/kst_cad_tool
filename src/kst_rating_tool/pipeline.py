from __future__ import annotations

from dataclasses import dataclass, field
from multiprocessing import Pool
from typing import Dict, List, Set, Tuple

import numpy as np
from numpy.typing import NDArray
from scipy.linalg import null_space

from .combination import combo_preproc
from .constraints import ConstraintSet
from .input_wr import input_wr_compose
from .motion import ScrewMotion, rec_mot, specmot_row_to_screw
from .rating import (
    RatingResults,
    aggregate_ratings,
    rate_cp,
    rate_cpin,
    rate_clin,
    rate_cpln1,
    rate_cpln2,
)
from .react_wr import form_combo_wrench, react_wr_5_compose
from .utils import matlab_rank
from .wrench import WrenchSystem, cp_to_wrench


def _process_combo_chunk(
    args: Tuple[
        List[int],
        NDArray[np.int_],
        List[NDArray[np.float64]],
        NDArray[np.float64],
        float,
        ConstraintSet,
    ],
) -> List[Tuple[int, NDArray[np.float64], NDArray[np.float64]]]:  # R_two_rows (2, total_cp)
    """Process a chunk of combo rows; return (combo_i, mot_row, R_row) for rank-5 combos.
    Used by parallel analysis; no duplicate detection (done in main process).
    """
    combo_indices, combo_chunk, wr_all_list, pts, max_d, constraints = args
    cp, cpin, clin, cpln, cpln_prop = constraints.to_matlab_style_arrays()
    total_cp = constraints.total_cp
    out: List[Tuple[int, NDArray[np.float64], NDArray[np.float64]]] = []
    for idx, combo_row in zip(combo_indices, combo_chunk):
        W = form_combo_wrench(wr_all_list, combo_row)
        if W.size == 0:
            continue
        if matlab_rank(W) != 5:
            continue
        mot = rec_mot(W)
        mot_arr = mot.as_array().ravel()
        mot_arr = np.round(mot_arr * 1e4) / 1e4
        input_wr, _ = input_wr_compose(mot, pts, max_d)
        react_wr_5 = react_wr_5_compose(constraints, combo_row, mot.rho)
        rcp_pos, rcp_neg, rcpin, rclin_pos, rclin_neg, rcpln_pos, rcpln_neg = _rate_motion_all_constraints(
            mot_arr, react_wr_5, input_wr, cp, cpin, clin, cpln, cpln_prop
        )
        row_forward = np.hstack([rcp_pos, rcpin, rclin_pos, rcpln_pos])
        row_reverse = np.hstack([rcp_neg, rcpin, rclin_neg, rcpln_neg])
        R_two_rows = np.vstack([row_forward, row_reverse])
        out.append((idx, mot_arr, R_two_rows))
    return out


@dataclass
class DetailedAnalysisResult:
    """Result of full main_loop-style analysis for use by optimizers.

    Mirrors MATLAB globals: R, Ri, mot_half, mot_all, combo_proc, combo_dup_idx,
    no_mot_half, Rating_all.
    """
    R: NDArray[np.float64]
    Ri: NDArray[np.float64]
    mot_half: NDArray[np.float64]
    mot_all: NDArray[np.float64]
    combo_proc: NDArray[np.int_]
    combo_dup_idx: NDArray[np.int_]
    no_mot_half: int
    rating: RatingResults
    wr_all: List[NDArray[np.float64]]
    pts: NDArray[np.float64]
    max_d: float
    constraints: ConstraintSet
    combo: NDArray[np.int_]


def _rate_motion_all_constraints(
    mot_arr: NDArray[np.float64],
    react_wr_5: NDArray[np.float64],
    input_wr: NDArray[np.float64],
    cp: NDArray[np.float64],
    cpin: NDArray[np.float64],
    clin: NDArray[np.float64],
    cpln: NDArray[np.float64],
    cpln_prop: NDArray[np.float64],
) -> tuple[NDArray[np.float64], NDArray[np.float64], NDArray[np.float64], NDArray[np.float64], NDArray[np.float64], NDArray[np.float64]]:
    """Build one motion's Rcp_pos, Rcp_neg, Rcpin, Rclin_pos, Rclin_neg, Rcpln_pos, Rcpln_neg (match main_loop.m)."""
    no_cp, no_cpin, no_clin, no_cpln = cp.shape[0], cpin.shape[0], clin.shape[0], cpln.shape[0]
    Rcp_pos = np.full(no_cp, np.inf, dtype=float)
    Rcp_neg = np.full(no_cp, np.inf, dtype=float)
    for j in range(no_cp):
        Rcp_pos[j], Rcp_neg[j] = rate_cp(mot_arr, react_wr_5, input_wr, cp[j, :])
    Rcpin_row = np.full(no_cpin, np.inf, dtype=float)
    for j in range(no_cpin):
        Rcpin_row[j] = rate_cpin(mot_arr, react_wr_5, input_wr, cpin[j, :])
    Rclin_pos = np.full(no_clin, np.inf, dtype=float)
    Rclin_neg = np.full(no_clin, np.inf, dtype=float)
    for j in range(no_clin):
        Rclin_pos[j], Rclin_neg[j] = rate_clin(mot_arr, react_wr_5, input_wr, clin[j, :])
    Rcpln_pos = np.full(no_cpln, np.inf, dtype=float)
    Rcpln_neg = np.full(no_cpln, np.inf, dtype=float)
    for j in range(no_cpln):
        if cpln[j, 6] == 1:
            Rcpln_pos[j], Rcpln_neg[j] = rate_cpln1(mot_arr, react_wr_5, input_wr, cpln[j, :], cpln_prop[j, :])
        else:
            Rcpln_pos[j], Rcpln_neg[j] = rate_cpln2(mot_arr, react_wr_5, input_wr, cpln[j, :], cpln_prop[j, :])
    return Rcp_pos, Rcp_neg, Rcpin_row, Rclin_pos, Rclin_neg, Rcpln_pos, Rcpln_neg


def analyze_constraints(
    constraints: ConstraintSet,
    n_workers: int = 1,
) -> RatingResults:
    """High-level analysis pipeline for a fixed configuration.

    Mirrors main_loop.m and main.m: rates all constraint types (cp, cpin, clin, cpln),
    builds R = [Rcp Rcpin Rclin Rcpln], merges forward/reverse, unique motions, aggregate.

    Parameters
    ----------
    constraints
        Constraint set describing the assembly.
    n_workers
        Number of parallel workers for the combo loop (1 = sequential). Uses process-based
        parallelism; results are merged in combo order so output matches sequential run.
    """

    wr_all_sys, pts, max_d = cp_to_wrench(constraints)
    wr_all: List[NDArray[np.float64]] = [w.as_array() for w in wr_all_sys]

    combo = combo_preproc(constraints)
    cp, cpin, clin, cpln, cpln_prop = constraints.to_matlab_style_arrays()
    no_cp, no_cpin, no_clin, no_cpln = cp.shape[0], cpin.shape[0], clin.shape[0], cpln.shape[0]
    total_cp = no_cp + no_cpin + no_clin + no_cpln

    mot_hold: List[NDArray[np.float64]] = []
    mot_set: Set[Tuple[float, ...]] = set()
    Rcp_pos_rows: List[NDArray[np.float64]] = []
    Rcp_neg_rows: List[NDArray[np.float64]] = []
    Rcpin_rows: List[NDArray[np.float64]] = []
    Rclin_pos_rows: List[NDArray[np.float64]] = []
    Rclin_neg_rows: List[NDArray[np.float64]] = []
    Rcpln_pos_rows: List[NDArray[np.float64]] = []
    Rcpln_neg_rows: List[NDArray[np.float64]] = []

    if n_workers is not None and n_workers > 1:
        n_combo = combo.shape[0]
        chunk_size = max(1, (n_combo + n_workers - 1) // n_workers)
        chunks: List[Tuple[List[int], NDArray[np.int_]]] = []
        for s in range(0, n_combo, chunk_size):
            e = min(s + chunk_size, n_combo)
            chunks.append((list(range(s, e)), combo[s:e]))
        pool_args = [
            (indices, combo_chunk, wr_all, pts, max_d, constraints)
            for indices, combo_chunk in chunks
        ]
        with Pool(processes=n_workers) as pool:
            chunk_results = pool.map(_process_combo_chunk, pool_args)
        all_results: List[Tuple[int, NDArray[np.float64], NDArray[np.float64]]] = []
        for lst in chunk_results:
            all_results.extend(lst)
        all_results.sort(key=lambda x: x[0])
        for combo_i, mot_arr, R_two_rows in all_results:
            mot_row = mot_arr.reshape(1, -1)
            mot_tuple = tuple(mot_row.ravel())

            if mot_tuple in mot_set:
                continue

            mot_set.add(mot_tuple)
            mot_hold.append(mot_row.ravel().copy())
            Rcp_pos_rows.append(R_two_rows[0, :no_cp])
            Rcp_neg_rows.append(R_two_rows[1, :no_cp])
            Rcpin_rows.append(R_two_rows[0, no_cp : no_cp + no_cpin])
            Rclin_pos_rows.append(R_two_rows[0, no_cp + no_cpin : no_cp + no_cpin + no_clin])
            Rclin_neg_rows.append(R_two_rows[1, no_cp + no_cpin : no_cp + no_cpin + no_clin])
            Rcpln_pos_rows.append(R_two_rows[0, no_cp + no_cpin + no_clin : total_cp])
            Rcpln_neg_rows.append(R_two_rows[1, no_cp + no_cpin + no_clin : total_cp])
    else:
        for combo_row in combo:
            W = form_combo_wrench(wr_all, combo_row)
            if W.size == 0:
                continue
            if matlab_rank(W) != 5:
                continue

            mot = rec_mot(W)
            mot_arr = mot.as_array().ravel()
            mot_arr = np.round(mot_arr * 1e4) / 1e4
            mot_row = mot_arr.reshape(1, -1)
            mot_tuple = tuple(mot_row.ravel())

            if mot_tuple in mot_set:
                continue

            mot_set.add(mot_tuple)
            mot_hold.append(mot_row.ravel().copy())

            input_wr, _ = input_wr_compose(mot, pts, max_d)
            react_wr_5 = react_wr_5_compose(constraints, combo_row, mot.rho)
            rcp_pos, rcp_neg, rcpin, rclin_pos, rclin_neg, rcpln_pos, rcpln_neg = _rate_motion_all_constraints(
                mot_arr, react_wr_5, input_wr, cp, cpin, clin, cpln, cpln_prop
            )
            Rcp_pos_rows.append(rcp_pos)
            Rcp_neg_rows.append(rcp_neg)
            Rcpin_rows.append(rcpin)
            Rclin_pos_rows.append(rclin_pos)
            Rclin_neg_rows.append(rclin_neg)
            Rcpln_pos_rows.append(rcpln_pos)
            Rcpln_neg_rows.append(rcpln_neg)

    if not mot_hold:
        R = np.full((1, max(1, total_cp)), np.inf, dtype=float)
        return aggregate_ratings(R)

    Rcp_pos = np.vstack(Rcp_pos_rows)
    Rcp_neg = np.vstack(Rcp_neg_rows)
    Rcpin_half = np.vstack(Rcpin_rows)
    Rclin_pos = np.vstack(Rclin_pos_rows)
    Rclin_neg = np.vstack(Rclin_neg_rows)
    Rcpln_pos = np.vstack(Rcpln_pos_rows)
    Rcpln_neg = np.vstack(Rcpln_neg_rows)
    Rcp = np.vstack([Rcp_pos, Rcp_neg])
    Rcpin = np.vstack([Rcpin_half, Rcpin_half])
    Rclin = np.vstack([Rclin_pos, Rclin_neg])
    Rcpln = np.vstack([Rcpln_pos, Rcpln_neg])
    R = np.hstack([Rcp, Rcpin, Rclin, Rcpln])

    mot_half = np.vstack(mot_hold)
    mot_half_rev = np.hstack([-mot_half[:, :6], mot_half[:, 6:]])
    mot_all = np.vstack([mot_half, mot_half_rev])
    mot_all = np.round(mot_all * 1e4) / 1e4

    # Match MATLAB unique(mot_all_org, 'rows'): keep first occurrence of each unique motion
    _, uniq_idx = np.unique(mot_all, axis=0, return_index=True)
    R_uniq = R[uniq_idx, :]
    return aggregate_ratings(R_uniq)


def analyze_constraints_detailed(
    constraints: ConstraintSet,
    n_workers: int = 1,
) -> DetailedAnalysisResult:
    """Full analysis returning R, mot_half, combo_proc, combo_dup_idx for optimizers.

    Same as analyze_constraints but also returns intermediate structures; rates all constraint types.

    Parameters
    ----------
    constraints
        Constraint set describing the assembly.
    n_workers
        Number of parallel workers for the combo loop (1 = sequential). Uses process-based
        parallelism; results are merged in combo order so output matches sequential run.
    """
    wr_all_sys, pts, max_d = cp_to_wrench(constraints)
    wr_all_list: List[NDArray[np.float64]] = [w.as_array() for w in wr_all_sys]

    combo = combo_preproc(constraints)
    cp, cpin, clin, cpln, cpln_prop = constraints.to_matlab_style_arrays()
    no_cp, no_cpin, no_clin, no_cpln = cp.shape[0], cpin.shape[0], clin.shape[0], cpln.shape[0]
    total_cp = no_cp + no_cpin + no_clin + no_cpln

    mot_hold: List[NDArray[np.float64]] = []
    mot_map: Dict[Tuple[float, ...], int] = {}
    Rcp_pos_rows: List[NDArray[np.float64]] = []
    Rcp_neg_rows: List[NDArray[np.float64]] = []
    Rcpin_rows: List[NDArray[np.float64]] = []
    Rclin_pos_rows: List[NDArray[np.float64]] = []
    Rclin_neg_rows: List[NDArray[np.float64]] = []
    Rcpln_pos_rows: List[NDArray[np.float64]] = []
    Rcpln_neg_rows: List[NDArray[np.float64]] = []
    combo_proc_indices: List[int] = []
    combo_proc_rows_list: List[NDArray[np.int_]] = []
    combo_dup_idx = np.zeros(combo.shape[0], dtype=np.int_)

    if n_workers is not None and n_workers > 1:
        n_combo = combo.shape[0]
        chunk_size = max(1, (n_combo + n_workers - 1) // n_workers)
        chunks_d: List[Tuple[List[int], NDArray[np.int_]]] = []
        for s in range(0, n_combo, chunk_size):
            e = min(s + chunk_size, n_combo)
            chunks_d.append((list(range(s, e)), combo[s:e]))
        pool_args_d = [
            (indices, combo_chunk, wr_all_list, pts, max_d, constraints)
            for indices, combo_chunk in chunks_d
        ]
        with Pool(processes=n_workers) as pool:
            chunk_results_d = pool.map(_process_combo_chunk, pool_args_d)
        all_results_d: List[Tuple[int, NDArray[np.float64], NDArray[np.float64]]] = []
        for lst in chunk_results_d:
            all_results_d.extend(lst)
        all_results_d.sort(key=lambda x: x[0])
        mot_to_idx = {}
        for combo_i, mot_arr, R_two_rows in all_results_d:
            mot_row = mot_arr.reshape(1, -1)
            mot_tuple = tuple(mot_row.ravel())

            if mot_tuple in mot_map:
                idx_existing = mot_map[mot_tuple]
                combo_dup_idx[combo_i] = idx_existing + 1
                continue

            mot_map[mot_tuple] = len(mot_hold)
            combo_dup_idx[combo_i] = 0
            mot_hold.append(mot_row.ravel().copy())
            combo_proc_indices.append(combo_i + 1)
            combo_proc_rows_list.append(combo[combo_i])
            mot_seen_dict[mot_tuple] = len(mot_hold)
            mot_hold.append(mot_flat.copy())
            combo_proc_rows.append(np.array([combo_i + 1, *combo[combo_i]], dtype=np.int_))
            Rcp_pos_rows.append(R_two_rows[0, :no_cp])
            Rcp_neg_rows.append(R_two_rows[1, :no_cp])
            Rcpin_rows.append(R_two_rows[0, no_cp : no_cp + no_cpin])
            Rclin_pos_rows.append(R_two_rows[0, no_cp + no_cpin : no_cp + no_cpin + no_clin])
            Rclin_neg_rows.append(R_two_rows[1, no_cp + no_cpin : no_cp + no_cpin + no_clin])
            Rcpln_pos_rows.append(R_two_rows[0, no_cp + no_cpin + no_clin : total_cp])
            Rcpln_neg_rows.append(R_two_rows[1, no_cp + no_cpin + no_clin : total_cp])
    else:
        for combo_i, combo_row in enumerate(combo):
            W = form_combo_wrench(wr_all_list, combo_row)
            if W.size == 0:
                continue
            if matlab_rank(W) != 5:
                continue

            mot = rec_mot(W)
            mot_arr = mot.as_array().ravel()
            mot_arr = np.round(mot_arr * 1e4) / 1e4
            mot_row = mot_arr.reshape(1, -1)
            mot_tuple = tuple(mot_row.ravel())

            if mot_tuple in mot_map:
                idx_existing = mot_map[mot_tuple]
                combo_dup_idx[combo_i] = idx_existing + 1
                continue

            mot_map[mot_tuple] = len(mot_hold)
            combo_dup_idx[combo_i] = 0

            input_wr, _ = input_wr_compose(mot, pts, max_d)
            react_wr_5 = react_wr_5_compose(constraints, combo_row, mot.rho)
            rcp_pos, rcp_neg, rcpin, rclin_pos, rclin_neg, rcpln_pos, rcpln_neg = _rate_motion_all_constraints(
                mot_arr, react_wr_5, input_wr, cp, cpin, clin, cpln, cpln_prop
            )
            Rcp_pos_rows.append(rcp_pos)
            Rcp_neg_rows.append(rcp_neg)
            Rcpin_rows.append(rcpin)
            Rclin_pos_rows.append(rclin_pos)
            Rclin_neg_rows.append(rclin_neg)
            Rcpln_pos_rows.append(rcpln_pos)
            Rcpln_neg_rows.append(rcpln_neg)
            mot_hold.append(mot_row.ravel().copy())
            combo_proc_indices.append(combo_i + 1)
            combo_proc_rows_list.append(combo_row)
            mot_seen_dict[mot_tuple] = len(mot_hold)
            mot_hold.append(mot_flat.copy())
            combo_proc_rows.append(np.array([combo_i + 1, *combo_row], dtype=np.int_))

    if not mot_hold:
        R = np.full((1, max(1, total_cp)), np.inf, dtype=float)
        mot_half = np.empty((0, 10), dtype=float)
        combo_proc = np.empty((0, 6), dtype=np.int_)
        rating_res = aggregate_ratings(R)
        return DetailedAnalysisResult(
            R=R,
            Ri=rating_res.Ri,
            mot_half=mot_half,
            mot_all=np.empty((0, 10), dtype=float),
            combo_proc=combo_proc,
            combo_dup_idx=combo_dup_idx,
            no_mot_half=0,
            rating=rating_res,
            wr_all=wr_all_list,
            pts=pts,
            max_d=max_d,
            constraints=constraints,
            combo=combo,
        )

    Rcp_pos = np.vstack(Rcp_pos_rows)
    Rcp_neg = np.vstack(Rcp_neg_rows)
    Rcpin_half = np.vstack(Rcpin_rows)
    Rclin_pos = np.vstack(Rclin_pos_rows)
    Rclin_neg = np.vstack(Rclin_neg_rows)
    Rcpln_pos = np.vstack(Rcpln_pos_rows)
    Rcpln_neg = np.vstack(Rcpln_neg_rows)
    Rcp = np.vstack([Rcp_pos, Rcp_neg])
    Rcpin = np.vstack([Rcpin_half, Rcpin_half])
    Rclin = np.vstack([Rclin_pos, Rclin_neg])
    Rcpln = np.vstack([Rcpln_pos, Rcpln_neg])
    R = np.hstack([Rcp, Rcpin, Rclin, Rcpln])

    mot_half = np.vstack(mot_hold)
    mot_half_rev = np.hstack([-mot_half[:, :6], mot_half[:, 6:]])
    mot_all = np.vstack([mot_half, mot_half_rev])
    mot_all = np.round(mot_all * 1e4) / 1e4
    if not combo_proc_indices:
        combo_proc = np.empty((0, combo.shape[1] + 1), dtype=np.int_)
    else:
        indices_arr = np.array(combo_proc_indices, dtype=np.int_).reshape(-1, 1)
        combos_arr = np.vstack(combo_proc_rows_list)
        combo_proc = np.hstack([indices_arr, combos_arr])

    # Match MATLAB unique(mot_all_org, 'rows'): first occurrence per unique motion
    _, uniq_idx = np.unique(mot_all, axis=0, return_index=True)
    R_uniq = R[uniq_idx, :]
    rating_res = aggregate_ratings(R_uniq)
    Ri_full = np.where(np.isfinite(R) & (R > 0), 1.0 / R, 0.0)
    Ri_full = np.round(Ri_full * 1e4) * 1e-4

    return DetailedAnalysisResult(
        R=R,
        Ri=Ri_full,
        mot_half=mot_half,
        mot_all=mot_all,
        combo_proc=combo_proc,
        combo_dup_idx=combo_dup_idx,
        no_mot_half=mot_half.shape[0],
        rating=rating_res,
        wr_all=wr_all_list,
        pts=pts,
        max_d=max_d,
        constraints=constraints,
        combo=combo,
    )


def run_main_loop(
    combo: NDArray[np.int_],
    wr_all: List[NDArray[np.float64]],
    constraints: ConstraintSet,
    pts: NDArray[np.float64],
    max_d: float,
) -> tuple[NDArray[np.float64], NDArray[np.float64]]:
    """Run main_loop on given combo and wr_all; return mot_half and R (forward+reverse, all constraint types)."""
    cp, cpin, clin, cpln, cpln_prop = constraints.to_matlab_style_arrays()
    total_cp = constraints.total_cp
    mot_hold: List[NDArray[np.float64]] = []
    Rcp_pos_rows: List[NDArray[np.float64]] = []
    Rcp_neg_rows: List[NDArray[np.float64]] = []
    Rcpin_rows: List[NDArray[np.float64]] = []
    Rclin_pos_rows: List[NDArray[np.float64]] = []
    Rclin_neg_rows: List[NDArray[np.float64]] = []
    Rcpln_pos_rows: List[NDArray[np.float64]] = []
    Rcpln_neg_rows: List[NDArray[np.float64]] = []

    for combo_row in combo:
        W = form_combo_wrench(wr_all, combo_row)
        if W.size == 0 or matlab_rank(W) != 5:
            continue
        mot = rec_mot(W)
        mot_arr = mot.as_array().ravel()
        input_wr, _ = input_wr_compose(mot, pts, max_d)
        react_wr_5 = react_wr_5_compose(constraints, combo_row, mot.rho)
        rcp_pos, rcp_neg, rcpin, rclin_pos, rclin_neg, rcpln_pos, rcpln_neg = _rate_motion_all_constraints(
            mot_arr, react_wr_5, input_wr, cp, cpin, clin, cpln, cpln_prop
        )
        mot_hold.append(mot_arr)
        Rcp_pos_rows.append(rcp_pos)
        Rcp_neg_rows.append(rcp_neg)
        Rcpin_rows.append(rcpin)
        Rclin_pos_rows.append(rclin_pos)
        Rclin_neg_rows.append(rclin_neg)
        Rcpln_pos_rows.append(rcpln_pos)
        Rcpln_neg_rows.append(rcpln_neg)

    if not mot_hold:
        return np.empty((0, 10), dtype=float), np.empty((0, max(1, total_cp)), dtype=float)
    mot_half = np.vstack(mot_hold)
    Rcp_pos = np.vstack(Rcp_pos_rows)
    Rcp_neg = np.vstack(Rcp_neg_rows)
    Rcpin_half = np.vstack(Rcpin_rows)
    Rclin_pos = np.vstack(Rclin_pos_rows)
    Rclin_neg = np.vstack(Rclin_neg_rows)
    Rcpln_pos = np.vstack(Rcpln_pos_rows)
    Rcpln_neg = np.vstack(Rcpln_neg_rows)
    Rcp = np.vstack([Rcp_pos, Rcp_neg])
    Rcpin = np.vstack([Rcpin_half, Rcpin_half])
    Rclin = np.vstack([Rclin_pos, Rclin_neg])
    Rcpln = np.vstack([Rcpln_pos, Rcpln_neg])
    R = np.hstack([Rcp, Rcpin, Rclin, Rcpln])
    return mot_half, R


@dataclass
class SpecmotResult:
    """Result of known-loading (specified motion) analysis. Mirrors MATLAB main_specmot_orig."""

    rating: RatingResults
    Ri: NDArray[np.float64]
    mot_proc: NDArray[np.float64]


def analyze_specified_motions(
    constraints: ConstraintSet,
    specmot: NDArray[np.float64],
) -> SpecmotResult:
    """Rate constraints for a set of specified screw motions (known loading).

    Mirrors MATLAB main_specmot_orig.m (option 6). Rates all constraint types (cp, cpin, clin, cpln).
    specmot: (n, 7) array, each row [omega_x, omega_y, omega_z, rho_x, rho_y, rho_z, h].
    """
    specmot = np.atleast_2d(specmot)
    if specmot.shape[1] != 7:
        raise ValueError("specmot must have 7 columns per row: omega(3), rho(3), h(1)")

    _, pts, max_d = cp_to_wrench(constraints)
    cp, cpin, clin, cpln, cpln_prop = constraints.to_matlab_style_arrays()

    Rcp_pos_rows: List[NDArray[np.float64]] = []
    Rcp_neg_rows: List[NDArray[np.float64]] = []
    Rcpin_rows: List[NDArray[np.float64]] = []
    Rclin_pos_rows: List[NDArray[np.float64]] = []
    Rclin_neg_rows: List[NDArray[np.float64]] = []
    Rcpln_pos_rows: List[NDArray[np.float64]] = []
    Rcpln_neg_rows: List[NDArray[np.float64]] = []

    for m in range(specmot.shape[0]):
        screw = specmot_row_to_screw(specmot[m, :])
        mot_arr = screw.as_array().ravel()
        rec_mot_mat = np.concatenate([screw.mu, screw.omu]).reshape(1, 6)
        ns = null_space(rec_mot_mat)
        pivot_wr = ns.T if ns.size else np.empty((0, 6), dtype=float)
        input_wr, _ = input_wr_compose(screw, pts, max_d)
        rcp_pos, rcp_neg, rcpin, rclin_pos, rclin_neg, rcpln_pos, rcpln_neg = _rate_motion_all_constraints(
            mot_arr, pivot_wr, input_wr, cp, cpin, clin, cpln, cpln_prop
        )
        Rcp_pos_rows.append(rcp_pos)
        Rcp_neg_rows.append(rcp_neg)
        Rcpin_rows.append(rcpin)
        Rclin_pos_rows.append(rclin_pos)
        Rclin_neg_rows.append(rclin_neg)
        Rcpln_pos_rows.append(rcpln_pos)
        Rcpln_neg_rows.append(rcpln_neg)

    Rcp_pos = np.vstack(Rcp_pos_rows)
    Rcp_neg = np.vstack(Rcp_neg_rows)
    Rcpin_half = np.vstack(Rcpin_rows)
    Rclin_pos = np.vstack(Rclin_pos_rows)
    Rclin_neg = np.vstack(Rclin_neg_rows)
    Rcpln_pos = np.vstack(Rcpln_pos_rows)
    Rcpln_neg = np.vstack(Rcpln_neg_rows)
    Rcp = np.vstack([Rcp_pos, Rcp_neg])
    Rcpin = np.vstack([Rcpin_half, Rcpin_half])
    Rclin = np.vstack([Rclin_pos, Rclin_neg])
    Rcpln = np.vstack([Rcpln_pos, Rcpln_neg])
    R = np.hstack([Rcp, Rcpin, Rclin, Rcpln])

    specmot_rev = np.hstack([-specmot[:, 0:3], specmot[:, 3:7]])
    mot_proc = np.vstack([specmot, specmot_rev])
    mot_proc_10 = np.zeros((mot_proc.shape[0], 10), dtype=float)
    for m in range(mot_proc.shape[0]):
        s = specmot_row_to_screw(mot_proc[m, :])
        mot_proc_10[m, :] = s.as_array().ravel()

    Ri = 1.0 / R
    Ri[np.isinf(Ri)] = 0.0
    Ri[np.isnan(Ri)] = 0.0
    Ri = np.round(Ri * 1e4) * 1e-4
    rating_res = aggregate_ratings(R)
    return SpecmotResult(rating=rating_res, Ri=Ri, mot_proc=mot_proc_10)

