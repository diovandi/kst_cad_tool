from __future__ import annotations

import numpy as np
from numpy.typing import NDArray

from .motion import ScrewMotion, calc_d


def input_wr_compose(mot: ScrewMotion, pts: NDArray[np.float64], max_d: float) -> tuple[NDArray[np.float64], float]:
    """Python port of `input_wr_compose.m`.

    Returns
    -------
    input_wr : (6,) ndarray
        Input wrench corresponding to the given motion.
    d : float
        Maximum moment arm used in the composition.
    """

    omu = mot.omu
    mu = mot.mu
    rho = mot.rho
    h = mot.h

    if np.isfinite(h):
        d = calc_d(omu, rho, pts, max_d)
    else:
        d = float("inf")

    # MATLAB: if abs(hw)>=d -> rotation; elseif h==inf -> pure translation; else -> force
    # Handle pure translation first (h=inf) so we don't set hw=inf and wrongly take rotation branch
    if not np.isfinite(h):
        # Pure translation: fi=mu, ti=0
        fi = np.asarray(mu, dtype=float)
        ti = np.zeros(3, dtype=float)
    else:
        hs = h
        hw = 1.0 / h if h != 0.0 else float("inf")
        if not np.isfinite(hw) or abs(hw) >= d:
            # Rotation-dominant (includes h=0: hw=inf, fi=hs*d*omu=0, ti=d*omu)
            fi = (float(hs) * d) * omu
            ti = d * omu
        else:
            # Translation-dominant motion, force input
            fi = omu
            ti = hw * omu

    input_wr = -np.concatenate([fi, ti])
    return input_wr.astype(float), float(d)

