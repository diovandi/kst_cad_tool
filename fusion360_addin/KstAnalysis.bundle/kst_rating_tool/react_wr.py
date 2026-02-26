from __future__ import annotations

from typing import List

import numpy as np
from numpy.typing import NDArray

from .constraints import ConstraintSet
from .utils import matlab_null


def form_combo_wrench(wr_all: List[NDArray[np.float64]], comb: NDArray[np.int_]) -> NDArray[np.float64]:
    """Form pivot wrench matrix from a combination row.

    This is a lightweight helper mirroring MATLAB's `form_combo_wrench.m`
    behaviour: stack the corresponding wrench systems and ensure a 5×6
    matrix (rank 5 expected).
    """

    rows: List[NDArray[np.float64]] = []
    for idx in comb:
        if idx == 0:
            continue
        # MATLAB is 1-based; Python is 0-based
        w = np.asarray(wr_all[idx - 1], dtype=float)
        rows.append(w)

    if not rows:
        return np.empty((0, 6), dtype=float)

    W = np.vstack(rows)
    return W


def react_wr_5_compose(constraints: ConstraintSet, comb: NDArray[np.int_], rho: NDArray[np.float64]) -> NDArray[np.float64]:
    """Python port of `react_wr_5_compose.m` for the original (baseline) set.

    This function re-computes the five-system constraining wrench matrix
    referenced to the screw axis position `rho`.
    """

    cp, cpin, clin, cpln, _ = constraints.to_matlab_style_arrays()

    no_cp = cp.shape[0]
    no_cpin = cpin.shape[0]
    no_clin = clin.shape[0]
    no_cpln = cpln.shape[0]

    rows: List[NDArray[np.float64]] = []

    for raw_idx in comb:
        if raw_idx == 0:
            continue
        idx = int(raw_idx)
        if idx <= no_cp:
            b = idx - 1
            cp_pos = cp[b, 0:3] - rho
            n = cp[b, 3:6]
            mu = np.cross(cp_pos, n)
            rows.append(np.concatenate([n, mu]))
        elif idx <= no_cp + no_cpin:
            b = idx - no_cp - 1
            cpin_pos = cpin[b, 0:3] - rho
            axis = cpin[b, 3:6]
            axes = matlab_null(axis.reshape(1, 3))
            om1 = axes[:, 0]
            om2 = axes[:, 1]
            mu1 = np.cross(cpin_pos, om1)
            mu2 = np.cross(cpin_pos, om2)
            rows.append(np.concatenate([om1, mu1]))
            rows.append(np.concatenate([om2, mu2]))
        elif idx <= no_cp + no_cpin + no_clin:
            b = idx - (no_cp + no_cpin) - 1
            clin_pos = clin[b, 0:3] - rho
            line_dir = clin[b, 3:6]
            constraint_dir = clin[b, 6:9]
            om1 = constraint_dir
            om2 = np.zeros(3, dtype=float)
            mu1 = np.cross(clin_pos, om1)
            mu2 = np.cross(line_dir, constraint_dir)
            rows.append(np.concatenate([om1, mu1]))
            rows.append(np.concatenate([om2, mu2]))
        elif idx <= no_cp + no_cpin + no_clin + no_cpln:
            b = idx - (no_cp + no_cpin + no_clin) - 1
            cpln_pos = cpln[b, 0:3] - rho
            normal = cpln[b, 3:6]
            axes = matlab_null(normal.reshape(1, 3))
            om1 = normal
            om2 = np.zeros(3, dtype=float)
            om3 = np.zeros(3, dtype=float)
            mu1 = np.cross(cpln_pos, om1)
            mu2 = axes[:, 0]
            mu3 = axes[:, 1]
            rows.append(np.concatenate([om1, mu1]))
            rows.append(np.concatenate([om2, mu2]))
            rows.append(np.concatenate([om3, mu3]))

    if not rows:
        return np.empty((0, 6), dtype=float)

    return np.vstack(rows).astype(float)

