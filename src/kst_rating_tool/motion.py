from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from numpy.typing import NDArray
from scipy.linalg import null_space


@dataclass
class ScrewMotion:
    """Screw motion representation.

    Fields follow `rec_mot.m`:
        mot = [omu(3), mu(3), rho(3), h]
    """

    omu: NDArray[np.float64]
    mu: NDArray[np.float64]
    rho: NDArray[np.float64]
    h: float

    def as_array(self) -> NDArray[np.float64]:
        return np.concatenate([self.omu, self.mu, self.rho, np.array([self.h], dtype=float)])


def specmot_row_to_screw(specmot_row: NDArray[np.float64]) -> ScrewMotion:
    """Build a ScrewMotion from one row of specmot (MATLAB main_specmot_orig format).

    specmot_row: [omega_x, omega_y, omega_z, rho_x, rho_y, rho_z, h]
    Normalizes omega; computes mu = h*omega + cross(rho, omega), or mu = omega for h=inf.
    """
    omu = np.asarray(specmot_row[0:3], dtype=float)
    rho = np.asarray(specmot_row[3:6], dtype=float)
    h = float(specmot_row[6])
    onorm = np.linalg.norm(omu)
    if onorm > 0:
        omu = omu / onorm
    else:
        omu = np.zeros(3, dtype=float)
    if np.isfinite(h):
        mu = h * omu + np.cross(rho, omu)
    else:
        # Pure translation: mu = direction, omu = 0 (MATLAB main_specmot_orig)
        mu = np.asarray(specmot_row[0:3], dtype=float)
        mnorm = np.linalg.norm(mu)
        if mnorm > 0:
            mu = mu / mnorm
        omu = np.zeros(3, dtype=float)
    return ScrewMotion(omu=omu, mu=mu, rho=rho, h=h)


def rec_mot(wrench: NDArray[np.float64]) -> ScrewMotion:
    """Python port of `rec_mot.m`.

    Parameters
    ----------
    wrench : (m, 6) ndarray
        Pivot wrench matrix whose null space defines the reciprocal motion.
    """

    # Null space returns a basis; MATLAB uses `null(wrench)` and then assumes
    # a unique 1D null space. We mimic by taking the first basis vector.
    ns = null_space(wrench)
    if ns.shape[1] == 0:
        raise ValueError("Wrench matrix has no non-trivial null space; cannot compute reciprocal motion.")

    x = ns[:, 0]
    x = np.round(x * 1e4) / 1e4

    mu = x[0:3]
    om = x[3:6]

    if np.linalg.norm(om) == 0.0:
        h = float("inf")
        rho = np.zeros(3, dtype=float)
        muu = mu / np.linalg.norm(mu)
        mot_arr = np.concatenate([om, muu, rho, np.array([h], dtype=float)])
    else:
        h = float(np.dot(mu, om) / np.dot(om, om))
        rho = np.cross(om, mu) / np.dot(om, om)
        omu = om / np.linalg.norm(om)
        mot_arr = np.concatenate([omu, mu, rho, np.array([h], dtype=float)])

    mot_arr = np.round(mot_arr * 1e4) / 1e4
    return ScrewMotion(
        omu=mot_arr[0:3],
        mu=mot_arr[3:6],
        rho=mot_arr[6:9],
        h=float(mot_arr[9]),
    )


def calc_d(omu: NDArray[np.float64], rho: NDArray[np.float64], pts: NDArray[np.float64], max_d: float) -> float:
    """Python port of `calc_d.m`."""

    if pts.size == 0:
        return 0.0

    mom_arm = pts - rho.reshape(1, 3)
    dist = np.linalg.norm(np.cross(omu.reshape(1, 3), mom_arm), axis=1)
    d = float(dist.max())
    if d > max_d:
        d = float(max_d)
    return d

