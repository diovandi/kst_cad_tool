from __future__ import annotations

from dataclasses import dataclass
from typing import List, Tuple

import numpy as np
from numpy.typing import NDArray

from .constraints import ConstraintSet
from .utils import matlab_null


WrenchArray = NDArray[np.float64]  # shape (k, 6)


@dataclass
class WrenchSystem:
    """Simple wrapper around a k×6 wrench matrix."""

    wrenches: WrenchArray  # rows are [om, mu]

    def as_array(self) -> WrenchArray:
        return self.wrenches


def cp_to_wrench(constraints: ConstraintSet) -> Tuple[List[WrenchSystem], NDArray[np.float64], float]:
    """Port of `cp_to_wrench.m`.

    Parameters
    ----------
    constraints:
        Container of point, pin, line, and plane constraints.

    Returns
    -------
    wr_all : list[WrenchSystem]
        Each entry is a 1×6, 2×6, or 3×6 wrench system.
    pts : (N, 3) ndarray
        Discretized constraint locations for moment arm calculation.
    max_d : float
        Maximum pairwise distance between points in `pts`.
    """

    cp, cpin, clin, cpln, cpln_prop = constraints.to_matlab_style_arrays()

    wr_all: List[WrenchSystem] = []

    # Point constraints
    for i in range(cp.shape[0]):
        n = cp[i, 3:6]
        p = cp[i, 0:3]
        mu = np.cross(p, n)
        wr = np.concatenate((n, mu))[None, :]
        wr_all.append(WrenchSystem(wr.astype(float)))

    # Pin constraints
    for i in range(cpin.shape[0]):
        center = cpin[i, 0:3]
        axis = cpin[i, 3:6]
        axes = matlab_null(axis.reshape(1, 3))  # 3×2
        om_axis1 = axes[:, 0]
        om_axis2 = axes[:, 1]
        mu_axis1 = np.cross(center, om_axis1)
        mu_axis2 = np.cross(center, om_axis2)
        wr = np.vstack(
            [
                np.concatenate((om_axis1, mu_axis1)),
                np.concatenate((om_axis2, mu_axis2)),
            ]
        )
        wr_all.append(WrenchSystem(wr.astype(float)))

    # Line constraints
    for i in range(clin.shape[0]):
        midpoint = clin[i, 0:3]
        line_dir = clin[i, 3:6]
        constraint_dir = clin[i, 6:9]

        om_axis1 = constraint_dir  # zero pitch
        om_axis2 = np.zeros(3)  # infinite pitch
        mu_axis1 = np.cross(midpoint, om_axis1)
        mu_axis2 = np.cross(line_dir, constraint_dir)

        wr = np.vstack(
            [
                np.concatenate((om_axis1, mu_axis1)),
                np.concatenate((om_axis2, mu_axis2)),
            ]
        )
        wr_all.append(WrenchSystem(wr.astype(float)))

    # Plane constraints
    for i in range(cpln.shape[0]):
        midpoint = cpln[i, 0:3]
        normal = cpln[i, 3:6]

        axes = matlab_null(normal.reshape(1, 3))  # 3×2
        om_axis1 = normal  # zero pitch
        om_axis2 = np.zeros(3)  # infinite pitch
        om_axis3 = np.zeros(3)  # infinite pitch
        mu_axis1 = np.cross(midpoint, om_axis1)
        mu_axis2 = axes[:, 0]
        mu_axis3 = axes[:, 1]

        wr = np.vstack(
            [
                np.concatenate((om_axis1, mu_axis1)),
                np.concatenate((om_axis2, mu_axis2)),
                np.concatenate((om_axis3, mu_axis3)),
            ]
        )
        wr_all.append(WrenchSystem(wr.astype(float)))

    # Discretized points (pts) and max_d, mirroring MATLAB logic
    pts_list: List[NDArray[np.float64]] = []

    if cp.size:
        pts_list.append(cp[:, 0:3])

    if cpin.size:
        pts_list.append(cpin[:, 0:3])

    if clin.size:
        line_pts = []
        for i in range(clin.shape[0]):
            midpoint = clin[i, 0:3]
            line_dir = clin[i, 3:6]
            length = clin[i, 9]
            line_pts.append(midpoint + (length / 2.0) * line_dir)
            line_pts.append(midpoint - (length / 2.0) * line_dir)
        pts_list.append(np.vstack(line_pts))

    if cpln.size:
        plane_pts = []
        for i in range(cpln.shape[0]):
            midpoint = cpln[i, 0:3]
            normal = cpln[i, 3:6]
            ptype = int(cpln[i, 6])
            prop = cpln_prop[i]
            if ptype == 1 and prop.size >= 8:
                xdir = prop[0:3]
                xlen = prop[3]
                ydir = prop[4:7]
                ylen = prop[7]
                plane_pts.append(midpoint + xlen / 2.0 * xdir + ylen / 2.0 * ydir)
                plane_pts.append(midpoint + xlen / 2.0 * xdir - ylen / 2.0 * ydir)
                plane_pts.append(midpoint - xlen / 2.0 * xdir + ylen / 2.0 * ydir)
                plane_pts.append(midpoint - xlen / 2.0 * xdir - ylen / 2.0 * ydir)
            elif ptype == 2 and prop.size >= 1:
                radius = prop[0]
                axes = matlab_null(normal.reshape(1, 3))
                e1 = axes[:, 0]
                e2 = axes[:, 1]
                c45 = np.cos(np.deg2rad(45.0))
                plane_pts.append(midpoint + radius * e1)
                plane_pts.append(midpoint - radius * e1)
                plane_pts.append(midpoint + radius * e2)
                plane_pts.append(midpoint - radius * e2)
                plane_pts.append(midpoint + c45 * radius * e1 + c45 * radius * e2)
                plane_pts.append(midpoint + c45 * radius * e1 - c45 * radius * e2)
                plane_pts.append(midpoint - c45 * radius * e1 + c45 * radius * e2)
                plane_pts.append(midpoint - c45 * radius * e1 - c45 * radius * e2)
        if plane_pts:
            pts_list.append(np.vstack(plane_pts))

    if pts_list:
        pts = np.vstack(pts_list).astype(float)
    else:
        pts = np.empty((0, 3), dtype=float)

    if pts.shape[0] >= 2:
        # pairwise distances (brute force, small N expected)
        idx = np.triu_indices(pts.shape[0], k=1)
        diffs = pts[idx[0]] - pts[idx[1]]
        dists = np.linalg.norm(diffs, axis=1)
        max_d = float(dists.max())
    else:
        max_d = 0.0

    return wr_all, pts, max_d

