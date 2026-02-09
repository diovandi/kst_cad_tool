from __future__ import annotations

from dataclasses import dataclass
from typing import List, Tuple

import numpy as np
from numpy.typing import NDArray

from .constraints import ConstraintSet
from .input_wr import input_wr_compose
from .motion import ScrewMotion
from .react_wr import react_wr_5_compose


@dataclass
class RatingResults:
    R: NDArray[np.float64]
    Ri: NDArray[np.float64]
    WTR: float
    MRR: float
    MTR: float
    TOR: float


def rate_cp(
    mot: NDArray[np.float64],
    react_wr_5: NDArray[np.float64],
    input_wr: NDArray[np.float64],
    cp_row: NDArray[np.float64],
) -> Tuple[float, float]:
    """Python port of `rate_cp.m` for a single point constraint.

    MATLAB uses react_wr = [react_wr_5; wr_pt_set]' so columns are wrenches,
    and solves react_wr \\ input_wr (static_sol = react_wr \\ input_wr).
    We build react_wr (6,6) with columns = wrenches and solve react_wr @ x = b.
    """
    rho = mot[6:9]
    cp_pos = cp_row[0:3] - rho
    wr_pt_set = np.concatenate([cp_row[3:6], np.cross(cp_pos, cp_row[3:6])])

    # MATLAB: react_wr = [react_wr_5; wr_pt_set]' -> columns = wrenches, solve react_wr \ input_wr
    react_wr = np.vstack([react_wr_5, wr_pt_set]).T.astype(np.float64, copy=False)  # (6, 6), cols = wrenches
    if not np.all(np.isfinite(react_wr)) or not np.all(np.isfinite(input_wr)):
        return float("inf"), float("inf")
    b = np.asarray(input_wr, dtype=np.float64).reshape(6)
    # MATLAB: rank(react_wr')==6 then react_wr\input_wr
    tol_rank = max(react_wr.shape) * np.finfo(float).eps * max(np.linalg.norm(react_wr, "fro"), 1.0)
    if np.linalg.matrix_rank(react_wr, tol=tol_rank) != 6:
        return float("inf"), float("inf")
    try:
        static_sol = np.linalg.solve(react_wr, b)
    except np.linalg.LinAlgError:
        static_sol = np.linalg.pinv(react_wr) @ b
    if not np.all(np.isfinite(static_sol)):
        return float("inf"), float("inf")
    val = float(static_sol[-1])
    if val >= 0:
        return float(val), float("inf")
    return float("inf"), float(-val)


def rate_cpin(
    mot: NDArray[np.float64],
    react_wr_5: NDArray[np.float64],
    input_wr: NDArray[np.float64],
    cpin_row: NDArray[np.float64],
) -> float:
    """Python port of rate_cpin.m. Returns single Rcpin (same for both directions)."""
    omu = mot[0:3]
    muu = mot[3:6]
    rho = mot[6:9]
    h = float(mot[9])
    cpin_ctr = cpin_row[0:3]
    cpin_normal = cpin_row[3:6]
    if np.isfinite(h):
        mom_arm = cpin_ctr - rho
        if np.linalg.norm(mom_arm) > 0:
            line_action = h * omu + np.cross(omu, mom_arm)
        else:
            line_action = np.zeros(3, dtype=float)
    else:
        line_action = muu.copy()
    const_dir = np.cross(cpin_normal, np.cross(line_action, cpin_normal))
    const_dir = np.round(const_dir * 1e5) * 1e-5
    if np.linalg.norm(const_dir) > 0:
        const_dir = const_dir / np.linalg.norm(const_dir)
        wr_const_dir = np.concatenate([const_dir, np.cross(cpin_ctr - rho, const_dir)])
        react_wr = np.vstack([react_wr_5, wr_const_dir]).T  # (6, n_cols), columns = wrenches, match MATLAB react_wr\input_wr
        if react_wr.shape[1] >= 6 and np.linalg.matrix_rank(react_wr) == 6:
            try:
                static_sol = np.linalg.lstsq(react_wr, np.asarray(input_wr, dtype=float).reshape(6), rcond=None)[0]
                if static_sol.size > 0 and np.isfinite(static_sol[-1]):
                    return float(abs(static_sol[-1]))
            except Exception:
                pass
    return float("inf")


def rate_clin(
    mot: NDArray[np.float64],
    react_wr_5: NDArray[np.float64],
    input_wr: NDArray[np.float64],
    clin_row: NDArray[np.float64],
) -> Tuple[float, float]:
    """Python port of rate_clin.m. Returns Rclin_pos, Rclin_neg.
    MATLAB uses react_wr = [react_wr_5; wr]' so columns = wrenches, solve react_wr \\ input_wr.
    react_wr_5 can have more than 5 rows (e.g. 2 pin + 1 line = 6 rows); last column coeff is used.
    """
    rho = mot[6:9]
    clin_ctr = clin_row[0:3]
    clin_dir = clin_row[3:6] / np.linalg.norm(clin_row[3:6])
    clin_normal = clin_row[6:9]
    clin_halflen = clin_row[9] / 2.0
    clin_end1 = clin_ctr + clin_halflen * clin_dir
    clin_end2 = clin_ctr - clin_halflen * clin_dir
    wr_clin_end1 = np.concatenate([clin_normal, np.cross(clin_end1 - rho, clin_normal)])
    wr_clin_end2 = np.concatenate([clin_normal, np.cross(clin_end2 - rho, clin_normal)])
    M = np.array([float("inf"), float("inf")], dtype=float)
    b = np.asarray(input_wr, dtype=np.float64).reshape(6)
    for idx, wr in enumerate([wr_clin_end1, wr_clin_end2]):
        # react_wr (6, n_cols): columns = wrenches, match MATLAB [react_wr_5; wr]'
        react_wr = np.vstack([react_wr_5, wr]).T
        if react_wr.shape[1] < 6 or np.linalg.matrix_rank(react_wr) != 6:
            continue
        try:
            static_sol = np.linalg.lstsq(react_wr, b, rcond=None)[0]
        except Exception:
            continue
        if static_sol.size > 0 and np.isfinite(static_sol[-1]):
            M[idx] = float(static_sol[-1])
    Mpos = np.full(2, float("inf"), dtype=float)
    Mneg = np.full(2, float("inf"), dtype=float)
    for b in range(2):
        if abs(M[b]) < 0.0001:
            M[b] = 0.0
        if M[b] > 0:
            Mpos[b] = M[b]
        if M[b] < 0:
            Mneg[b] = -M[b]
    with np.errstate(divide="ignore", invalid="ignore"):
        Rclin_pos = 1.0 / (1.0 / Mpos[0] + 1.0 / Mpos[1])
        Rclin_neg = 1.0 / (1.0 / Mneg[0] + 1.0 / Mneg[1])
    Rclin_pos = float(Rclin_pos) if np.isfinite(Rclin_pos) else float("inf")
    Rclin_neg = float(Rclin_neg) if np.isfinite(Rclin_neg) else float("inf")
    return Rclin_pos, Rclin_neg


def rate_cpln1(
    mot: NDArray[np.float64],
    react_wr_5: NDArray[np.float64],
    input_wr: NDArray[np.float64],
    cpln_row: NDArray[np.float64],
    cpln_prop_row: NDArray[np.float64],
) -> Tuple[float, float]:
    """Python port of rate_cpln1.m (rectangular plane). Returns Rcpln_pos, Rcpln_neg."""
    rho = mot[6:9]
    cpln_ctr = cpln_row[0:3]
    cpln_normal = cpln_row[3:6]
    cpln_widthdir = cpln_prop_row[0:3]
    cpln_heightdir = cpln_prop_row[4:7]
    cpln_halfwidth = cpln_prop_row[3] / 2.0
    cpln_halfheight = cpln_prop_row[7] / 2.0
    cpln_end1 = cpln_ctr + cpln_halfwidth * cpln_widthdir + cpln_halfheight * cpln_heightdir
    cpln_end2 = cpln_ctr + cpln_halfwidth * cpln_widthdir - cpln_halfheight * cpln_heightdir
    cpln_end3 = cpln_ctr - cpln_halfwidth * cpln_widthdir + cpln_halfheight * cpln_heightdir
    cpln_end4 = cpln_ctr - cpln_halfwidth * cpln_widthdir - cpln_halfheight * cpln_heightdir
    wr_cpln_end = np.array([
        np.concatenate([cpln_normal, np.cross(cpln_end1 - rho, cpln_normal)]),
        np.concatenate([cpln_normal, np.cross(cpln_end2 - rho, cpln_normal)]),
        np.concatenate([cpln_normal, np.cross(cpln_end3 - rho, cpln_normal)]),
        np.concatenate([cpln_normal, np.cross(cpln_end4 - rho, cpln_normal)]),
    ], dtype=float)
    b = np.asarray(input_wr, dtype=np.float64).reshape(6)
    M = np.full(4, float("inf"), dtype=float)
    for a in range(4):
        react_wr = np.vstack([react_wr_5, wr_cpln_end[a, :]]).T  # (6, n_cols)
        if react_wr.shape[1] >= 6 and np.linalg.matrix_rank(react_wr) == 6:
            try:
                static_sol = np.linalg.lstsq(react_wr, b, rcond=None)[0]
                if static_sol.size > 0 and np.isfinite(static_sol[-1]):
                    M[a] = float(static_sol[-1])
            except Exception:
                pass
    Mpos = np.full(4, float("inf"), dtype=float)
    Mneg = np.full(4, float("inf"), dtype=float)
    for b in range(4):
        if abs(M[b]) < 0.0001:
            M[b] = 0.0
        if M[b] > 0:
            Mpos[b] = M[b]
        if M[b] < 0:
            Mneg[b] = -M[b]
    with np.errstate(divide="ignore", invalid="ignore"):
        Rcpln_pos = 1.0 / (1.0 / Mpos[0] + 1.0 / Mpos[1] + 1.0 / Mpos[2] + 1.0 / Mpos[3])
        Rcpln_neg = 1.0 / (1.0 / Mneg[0] + 1.0 / Mneg[1] + 1.0 / Mneg[2] + 1.0 / Mneg[3])
    Rcpln_pos = float(Rcpln_pos) if np.isfinite(Rcpln_pos) else float("inf")
    Rcpln_neg = float(Rcpln_neg) if np.isfinite(Rcpln_neg) else float("inf")
    return Rcpln_pos, Rcpln_neg


def rate_cpln2(
    mot: NDArray[np.float64],
    react_wr_5: NDArray[np.float64],
    input_wr: NDArray[np.float64],
    cpln_row: NDArray[np.float64],
    cpln_prop_row: NDArray[np.float64],
) -> Tuple[float, float]:
    """Python port of rate_cpln2.m (circular plane). Returns Rcpln_pos, Rcpln_neg."""
    omu = mot[0:3]
    rho = mot[6:9]
    h = float(mot[9])
    cpln_ctr = cpln_row[0:3]
    cpln_normal = cpln_row[3:6]
    cpln_rad = float(cpln_prop_row[0])
    if np.isfinite(h):
        mom_arm = cpln_ctr - rho
        if np.linalg.norm(mom_arm) > 0:
            mom_arm_proj = np.cross(cpln_normal, np.cross(mom_arm, cpln_normal))
        else:
            mom_arm_proj = np.cross(omu, cpln_normal)
        if np.linalg.norm(mom_arm_proj) > 0:
            mom_arm_proj = mom_arm_proj / np.linalg.norm(mom_arm_proj)
        cpln_edge_pos1 = cpln_ctr + mom_arm_proj * cpln_rad
        cpln_edge_pos2 = cpln_ctr - mom_arm_proj * cpln_rad
    else:
        cpln_edge_pos1 = cpln_ctr.copy()
        cpln_edge_pos2 = cpln_ctr.copy()
    wr1 = np.concatenate([cpln_normal, np.cross(cpln_edge_pos1 - rho, cpln_normal)])
    wr2 = np.concatenate([cpln_normal, np.cross(cpln_edge_pos2 - rho, cpln_normal)])
    b = np.asarray(input_wr, dtype=np.float64).reshape(6)
    M1 = M2 = float("inf")
    for idx, react_wr in enumerate([np.vstack([react_wr_5, wr1]).T, np.vstack([react_wr_5, wr2]).T]):
        if react_wr.shape[1] >= 6 and np.linalg.matrix_rank(react_wr) == 6:
            try:
                static_sol = np.linalg.lstsq(react_wr, b, rcond=None)[0]
                if static_sol.size > 0 and np.isfinite(static_sol[-1]):
                    if idx == 0:
                        M1 = float(static_sol[-1])
                    else:
                        M2 = float(static_sol[-1])
            except Exception:
                pass
    M = np.array([M1, M2], dtype=float)
    Mpos = np.full(2, float("inf"), dtype=float)
    Mneg = np.full(2, float("inf"), dtype=float)
    for b in range(2):
        if abs(M[b]) < 0.0001:
            M[b] = 0.0
        if M[b] > 0:
            Mpos[b] = M[b]
        if M[b] < 0:
            Mneg[b] = -M[b]
    with np.errstate(divide="ignore", invalid="ignore"):
        Rcpln_pos = 1.0 / (2.0 * (1.0 / Mpos[0] + 1.0 / Mpos[1]))
        Rcpln_neg = 1.0 / (2.0 * (1.0 / Mneg[0] + 1.0 / Mneg[1]))
    Rcpln_pos = float(Rcpln_pos) if np.isfinite(Rcpln_pos) else float("inf")
    Rcpln_neg = float(Rcpln_neg) if np.isfinite(Rcpln_neg) else float("inf")
    return Rcpln_pos, Rcpln_neg


def aggregate_ratings(R: NDArray[np.float64]) -> RatingResults:
    """Compute WTR, MRR, MTR, TOR from resistance matrix R.
    Matches rating.m: round Ri to 4 decimals; if min(rowsum)==0 (free motion) set WTR=MRR=MTR=0.
    """

    if R.size == 0:
        return RatingResults(R=R, Ri=np.empty_like(R), WTR=0.0, MRR=0.0, MTR=0.0, TOR=0.0)

    Ri = 1.0 / R
    Ri[np.isinf(Ri)] = 0.0
    Ri[np.isnan(Ri)] = 0.0
    Ri = np.round(Ri * 1e4) * 1e-4

    rowsum = Ri.sum(axis=1)
    max_of_row = np.maximum(Ri.max(axis=1), 1e-12)

    with np.errstate(divide="ignore", invalid="ignore"):
        min_rowsum = float(rowsum.min()) if rowsum.size else 0.0
        if min_rowsum == 0:
            WTR = 0.0
            MRR = 0.0
            MTR = 0.0
            TOR = 0.0
        else:
            WTR = min_rowsum
            MRR = float(np.mean(rowsum / max_of_row)) if rowsum.size else 0.0
            MTR = float(np.mean(rowsum)) if rowsum.size else 0.0
            TOR = float(MTR / MRR) if MRR != 0.0 else float("inf")

    return RatingResults(R=R, Ri=Ri, WTR=WTR, MRR=MRR, MTR=MTR, TOR=TOR)


def _rows_per_constraint(idx: int, no_cp: int, no_cpin: int, no_clin: int, no_cpln: int) -> int:
    if idx <= no_cp:
        return 1
    if idx <= no_cp + no_cpin:
        return 2
    if idx <= no_cp + no_cpin + no_clin:
        return 2
    return 3


def _row_range_for_constraint_in_combo(
    combo_row: NDArray[np.int_],
    cp_eval: int,
    no_cp: int,
    no_cpin: int,
    no_clin: int,
    no_cpln: int,
) -> Tuple[int, int]:
    start = 0
    for c in combo_row.flat:
        if c == 0:
            continue
        n = _rows_per_constraint(int(c), no_cp, no_cpin, no_clin, no_cpln)
        if c == cp_eval:
            return start, start + n
        start += n
    return -1, -1


def rate_motset(
    combo_set: NDArray[np.int_],
    mot_half: NDArray[np.float64],
    cp_set: NDArray[np.int_],
    constraints: ConstraintSet,
    pts: NDArray[np.float64],
    max_d: float,
) -> NDArray[np.float64]:
    """Rate a set of constraints over a set of motions (for revision optimizer).
    combo_set: (n_mot, 5) constraint indices per motion; mot_half: (n_mot, 10); cp_set: 1-based indices.
    Returns R shape (2*n_mot, len(cp_set)) with Rpos then Rneg.
    """
    cp, cpin, clin, cpln, _ = constraints.to_matlab_style_arrays()
    no_cp, no_cpin, no_clin, no_cpln = cp.shape[0], cpin.shape[0], clin.shape[0], cpln.shape[0]
    n_mot = mot_half.shape[0]
    n_cp_set = cp_set.size
    Rpos = np.full((n_mot, n_cp_set), np.inf, dtype=float)
    Rneg = np.full((n_mot, n_cp_set), np.inf, dtype=float)

    for i in range(n_mot):
        mot = mot_half[i, :]
        rho = mot[6:9]
        combo_row = combo_set[i, :] if combo_set.ndim >= 2 else combo_set
        screw = ScrewMotion(mot[0:3], mot[3:6], mot[6:9], float(mot[9]))
        input_wr, _ = input_wr_compose(screw, pts, max_d)
        react_wr_5 = react_wr_5_compose(constraints, combo_row, rho)
        for j, cp_eval in enumerate(cp_set.flat):
            cp_eval = int(cp_eval)
            r0, r1 = _row_range_for_constraint_in_combo(
                combo_row, cp_eval, no_cp, no_cpin, no_clin, no_cpln
            )
            if r0 < 0:
                continue
            pivot_wr = np.delete(react_wr_5, np.arange(r0, r1), axis=0)
            while pivot_wr.shape[0] > 5:
                pivot_wr = np.delete(pivot_wr, -1, axis=0)
            if np.linalg.matrix_rank(pivot_wr) != 5:
                continue
            if cp_eval <= no_cp:
                cp_row = cp[cp_eval - 1, :]
                rp, rn = rate_cp(mot, pivot_wr, input_wr, cp_row)
                Rpos[i, j] = rp
                Rneg[i, j] = rn
    return np.vstack([Rpos, Rneg])

