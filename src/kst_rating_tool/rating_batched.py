"""Batched constraint rating (vectorized NumPy / optional PyTorch).

Mirrors ``rating._rate_motion_all_constraints`` outputs for one motion.
"""

from __future__ import annotations

import numpy as np
from numpy.typing import NDArray

from .numeric_backend import BackendState
from .utils import matlab_rank_batched


def _rate_cp_batch_numpy(
    mot: NDArray[np.float64],
    react_wr_5: NDArray[np.float64],
    input_wr: NDArray[np.float64],
    cp_rows: NDArray[np.float64],
) -> tuple[NDArray[np.float64], NDArray[np.float64]]:
    from .rating import rate_cp

    N = cp_rows.shape[0]
    if N == 0:
        return np.zeros(0, dtype=np.float64), np.zeros(0, dtype=np.float64)
    k = int(react_wr_5.shape[0])
    if k != 5:
        Rpos = np.full(N, np.inf, dtype=np.float64)
        Rneg = np.full(N, np.inf, dtype=np.float64)
        for j in range(N):
            Rpos[j], Rneg[j] = rate_cp(mot, react_wr_5, input_wr, cp_rows[j, :])
        return Rpos, Rneg
    rho = mot[6:9]
    cp_pos = cp_rows[:, 0:3] - rho
    n = cp_rows[:, 3:6]
    wr_pt = np.concatenate([n, np.cross(cp_pos, n, axis=1)], axis=1)
    rw = react_wr_5[None, :, :]
    stacked = np.concatenate([np.broadcast_to(rw, (N, 5, 6)), wr_pt[:, None, :]], axis=1)
    ranks = matlab_rank_batched(stacked)
    rank_ok = ranks == 6
    react_wr = np.transpose(stacked, (0, 2, 1))
    b = np.asarray(input_wr, dtype=np.float64).reshape(6)
    finite_ok = np.isfinite(react_wr).all(axis=(1, 2)) & np.all(np.isfinite(b))
    good = rank_ok & finite_ok
    x = np.full((N, 6), np.nan, dtype=np.float64)
    if np.any(good):
        for i in np.flatnonzero(good):
            try:
                x[i] = np.linalg.solve(react_wr[i], b)
            except np.linalg.LinAlgError:
                pass
    val = x[:, -1]
    Rpos = np.where(~good, np.inf, np.where(val >= 0, val, np.inf))
    Rneg = np.where(~good, np.inf, np.where(val < 0, -val, np.inf))
    return Rpos, Rneg


def _rate_cpin_numpy(
    mot: NDArray[np.float64],
    react_wr_5: NDArray[np.float64],
    input_wr: NDArray[np.float64],
    cpin_row: NDArray[np.float64],
) -> float:
    from .rating import rate_cpin

    return rate_cpin(mot, react_wr_5, input_wr, cpin_row)


def _rate_cpin_batch_numpy(
    mot: NDArray[np.float64],
    react_wr_5: NDArray[np.float64],
    input_wr: NDArray[np.float64],
    cpin_rows: NDArray[np.float64],
) -> NDArray[np.float64]:
    """One value per pin (same as rate_cpin)."""
    n = cpin_rows.shape[0]
    if n == 0:
        return np.zeros(0, dtype=np.float64)
    out = np.full(n, np.inf, dtype=np.float64)
    for j in range(n):
        out[j] = _rate_cpin_numpy(mot, react_wr_5, input_wr, cpin_rows[j, :])
    return out


def _rate_clin_numpy(
    mot: NDArray[np.float64],
    react_wr_5: NDArray[np.float64],
    input_wr: NDArray[np.float64],
    clin_row: NDArray[np.float64],
) -> tuple[float, float]:
    from .rating import rate_clin

    return rate_clin(mot, react_wr_5, input_wr, clin_row)


def _rate_cpln_numpy(
    mot: NDArray[np.float64],
    react_wr_5: NDArray[np.float64],
    input_wr: NDArray[np.float64],
    cpln_row: NDArray[np.float64],
    cpln_prop_row: NDArray[np.float64],
    ptype: int,
) -> tuple[float, float]:
    from .rating import rate_cpln1, rate_cpln2

    if ptype == 2:
        return rate_cpln2(mot, react_wr_5, input_wr, cpln_row, cpln_prop_row)
    return rate_cpln1(mot, react_wr_5, input_wr, cpln_row, cpln_prop_row)


def rate_motion_all_constraints_batched_numpy(
    mot_arr: NDArray[np.float64],
    react_wr_5: NDArray[np.float64],
    input_wr: NDArray[np.float64],
    cp: NDArray[np.float64],
    cpin: NDArray[np.float64],
    clin: NDArray[np.float64],
    cpln: NDArray[np.float64],
    cpln_prop: NDArray[np.float64],
) -> tuple[
    NDArray[np.float64],
    NDArray[np.float64],
    NDArray[np.float64],
    NDArray[np.float64],
    NDArray[np.float64],
    NDArray[np.float64],
    NDArray[np.float64],
]:
    """Same return signature as ``pipeline._rate_motion_all_constraints``."""
    no_cp, no_cpin, no_clin, no_cpln = cp.shape[0], cpin.shape[0], clin.shape[0], cpln.shape[0]
    Rcp_pos, Rcp_neg = _rate_cp_batch_numpy(mot_arr, react_wr_5, input_wr, cp) if no_cp else (
        np.zeros(0),
        np.zeros(0),
    )
    Rcpin_row = _rate_cpin_batch_numpy(mot_arr, react_wr_5, input_wr, cpin) if no_cpin else np.zeros(0)
    Rclin_pos = np.full(no_clin, np.inf, dtype=float)
    Rclin_neg = np.full(no_clin, np.inf, dtype=float)
    for j in range(no_clin):
        Rclin_pos[j], Rclin_neg[j] = _rate_clin_numpy(mot_arr, react_wr_5, input_wr, clin[j, :])
    Rcpln_pos = np.full(no_cpln, np.inf, dtype=float)
    Rcpln_neg = np.full(no_cpln, np.inf, dtype=float)
    for j in range(no_cpln):
        ptype = int(cpln[j, 6]) if cpln.shape[1] >= 7 else 1
        Rcpln_pos[j], Rcpln_neg[j] = _rate_cpln_numpy(
            mot_arr, react_wr_5, input_wr, cpln[j, :], cpln_prop[j, :], ptype
        )
    return Rcp_pos, Rcp_neg, Rcpin_row, Rclin_pos, Rclin_neg, Rcpln_pos, Rcpln_neg


def rate_motion_all_constraints_batched_torch(
    mot_arr: NDArray[np.float64],
    react_wr_5: NDArray[np.float64],
    input_wr: NDArray[np.float64],
    cp: NDArray[np.float64],
    cpin: NDArray[np.float64],
    clin: NDArray[np.float64],
    cpln: NDArray[np.float64],
    cpln_prop: NDArray[np.float64],
    state: BackendState,
) -> tuple[
    NDArray[np.float64],
    NDArray[np.float64],
    NDArray[np.float64],
    NDArray[np.float64],
    NDArray[np.float64],
    NDArray[np.float64],
    NDArray[np.float64],
]:
    """Torch path: batched CP on device; other types delegate to NumPy rating (CPU)."""
    assert state.kind == "torch" and state.torch_module is not None
    import torch

    from . import linalg_torch

    t = state.torch_module
    dev = state.device
    no_cp, no_cpin, no_clin, no_cpln = cp.shape[0], cpin.shape[0], clin.shape[0], cpln.shape[0]

    if no_cp > 0:
        k_rw = int(react_wr_5.shape[0])
        if k_rw != 5:
            return rate_motion_all_constraints_batched_numpy(
                mot_arr, react_wr_5, input_wr, cp, cpin, clin, cpln, cpln_prop
            )
        try:
            rho = t.as_tensor(mot_arr[6:9], dtype=t.float64, device=dev)
            cp_rows = t.as_tensor(cp, dtype=t.float64, device=dev)
            cp_pos = cp_rows[:, 0:3] - rho
            n = cp_rows[:, 3:6]
            wr_pt = torch.cat([n, torch.cross(cp_pos, n, dim=1)], dim=1)
            rw = t.as_tensor(react_wr_5, dtype=t.float64, device=dev).unsqueeze(0).expand(no_cp, -1, -1)
            stacked = torch.cat([rw, wr_pt.unsqueeze(1)], dim=1)
            ranks = linalg_torch.matlab_rank_batched_torch(stacked)
            rank_ok = ranks == 6
            react_wr = stacked.transpose(1, 2)
            b = t.as_tensor(input_wr, dtype=t.float64, device=dev).reshape(6)
            finite_ok = torch.isfinite(react_wr).all(dim=(1, 2)) & torch.isfinite(b).all()
            good = rank_ok & finite_ok
            N = no_cp
            x = torch.full((N, 6), float("nan"), dtype=t.float64, device=dev)
            if bool(good.any()):
                idx = torch.nonzero(good, as_tuple=False).squeeze(-1)
                br = react_wr[idx]
                bb = b.unsqueeze(0).expand(br.shape[0], -1)
                x[idx] = torch.linalg.solve(br, bb)
            val = x[:, -1]
            inf64 = torch.tensor(float("inf"), dtype=torch.float64, device=dev)
            Rcp_pos = torch.where(~good, inf64, torch.where(val >= 0, val, inf64))
            Rcp_neg = torch.where(~good, inf64, torch.where(val < 0, -val, inf64))
            Rcp_pos = Rcp_pos.detach().cpu().numpy()
            Rcp_neg = Rcp_neg.detach().cpu().numpy()
        except RuntimeError:
            return rate_motion_all_constraints_batched_numpy(
                mot_arr, react_wr_5, input_wr, cp, cpin, clin, cpln, cpln_prop
            )
    else:
        Rcp_pos = np.zeros(0, dtype=np.float64)
        Rcp_neg = np.zeros(0, dtype=np.float64)

    if no_cpin:
        Rcpin_row = _rate_cpin_batch_numpy(mot_arr, react_wr_5, input_wr, cpin)
    else:
        Rcpin_row = np.zeros(0, dtype=np.float64)

    Rclin_pos = np.full(no_clin, np.inf, dtype=float)
    Rclin_neg = np.full(no_clin, np.inf, dtype=float)
    for j in range(no_clin):
        Rclin_pos[j], Rclin_neg[j] = _rate_clin_numpy(mot_arr, react_wr_5, input_wr, clin[j, :])

    Rcpln_pos = np.full(no_cpln, np.inf, dtype=float)
    Rcpln_neg = np.full(no_cpln, np.inf, dtype=float)
    for j in range(no_cpln):
        ptype = int(cpln[j, 6]) if cpln.shape[1] >= 7 else 1
        Rcpln_pos[j], Rcpln_neg[j] = _rate_cpln_numpy(
            mot_arr, react_wr_5, input_wr, cpln[j, :], cpln_prop[j, :], ptype
        )

    return Rcp_pos, Rcp_neg, Rcpin_row, Rclin_pos, Rclin_neg, Rcpln_pos, Rcpln_neg
