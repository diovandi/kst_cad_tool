"""
Search space functions for constraint revision (move/orient/resize).
Ported from move_lin_srch.m, move_pln_srch.m, move_curvlin_srch.m,
orient1d_srch.m, orient2d_srch.m, line_orient1d_srch.m, resize_*.m.
All constraint indices are 1-based. Arrays cp, cpin, clin, cpln, cpln_prop are modified in place.
"""

from __future__ import annotations

import numpy as np
from numpy.typing import NDArray


def _norm3(v: NDArray[np.float64]) -> NDArray[np.float64]:
    n = np.linalg.norm(v)
    return v / n if n > 0 else v


def move_lin_srch(
    x_grp: float,
    cp_rev_in_group: NDArray[np.int_],
    lin_srch: NDArray[np.float64],
    cp: NDArray[np.float64],
    cpin: NDArray[np.float64],
    clin: NDArray[np.float64],
    cpln: NDArray[np.float64],
    no_cp: int,
    no_cpin: int,
    no_clin: int,
    no_cpln: int,
) -> None:
    """Move constraints along a line. lin_srch: [center(3), line_dir(3), scale]."""
    if cp_rev_in_group.size == 0:
        return
    idx0 = int(cp_rev_in_group.flat[0])
    line_dir = _norm3(lin_srch[3:6].astype(float))
    center = lin_srch[0:3]

    if idx0 <= no_cp:
        ctr_move = center - cp[idx0 - 1, 0:3]
    elif idx0 <= no_cp + no_cpin:
        ctr_move = center - cpin[idx0 - no_cp - 1, 0:3]
    elif idx0 <= no_cp + no_cpin + no_clin:
        ctr_move = center - clin[idx0 - no_cp - no_cpin - 1, 0:3]
    else:
        ctr_move = center - cpln[idx0 - no_cp - no_cpin - no_clin - 1, 0:3]

    scale = float(lin_srch[6]) if lin_srch.size >= 7 else 1.0
    delta = ctr_move + (x_grp * scale) * line_dir

    for idx in cp_rev_in_group.flat:
        if idx == 0:
            continue
        idx = int(idx)
        if idx <= no_cp:
            cp[idx - 1, 0:3] += delta
        elif idx <= no_cp + no_cpin:
            cpin[idx - no_cp - 1, 0:3] += delta
        elif idx <= no_cp + no_cpin + no_clin:
            clin[idx - no_cp - no_cpin - 1, 0:3] += delta
        else:
            cpln[idx - no_cp - no_cpin - no_clin - 1, 0:3] += delta


def move_pln_srch(
    x_grp: NDArray[np.float64],
    cp_rev_in_group: NDArray[np.int_],
    pln_srch: NDArray[np.float64],
    cp: NDArray[np.float64],
    cpin: NDArray[np.float64],
    clin: NDArray[np.float64],
    cpln: NDArray[np.float64],
    no_cp: int,
    no_cpin: int,
    no_clin: int,
    no_cpln: int,
) -> None:
    """Move constraints in a plane. pln_srch: [center(3), x_dir(3), x_width, y_dir(3), y_width] -> 11 elements."""
    if cp_rev_in_group.size == 0:
        return
    idx0 = int(cp_rev_in_group.flat[0])
    x_dir = _norm3(pln_srch[3:6].astype(float))
    y_dir = _norm3(pln_srch[7:10].astype(float))
    center = pln_srch[0:3]
    x_width = float(pln_srch[6]) if pln_srch.size >= 7 else 1.0
    y_width = float(pln_srch[10]) if pln_srch.size >= 11 else 1.0

    if idx0 <= no_cp:
        ctr_move = center - cp[idx0 - 1, 0:3]
    elif idx0 <= no_cp + no_cpin:
        ctr_move = center - cpin[idx0 - no_cp - 1, 0:3]
    elif idx0 <= no_cp + no_cpin + no_clin:
        ctr_move = center - clin[idx0 - no_cp - no_cpin - 1, 0:3]
    else:
        ctr_move = center - cpln[idx0 - no_cp - no_cpin - no_clin - 1, 0:3]

    delta = ctr_move + (x_grp[0] * x_width) * x_dir + (x_grp[1] * y_width) * y_dir

    for idx in cp_rev_in_group.flat:
        if idx == 0:
            continue
        idx = int(idx)
        if idx <= no_cp:
            cp[idx - 1, 0:3] = cp[idx - 1, 0:3] + delta
        elif idx <= no_cp + no_cpin:
            cpin[idx - no_cp - 1, 0:3] = cpin[idx - no_cp - 1, 0:3] + delta
        elif idx <= no_cp + no_cpin + no_clin:
            clin[idx - no_cp - no_cpin - 1, 0:3] = clin[idx - no_cp - no_cpin - 1, 0:3] + delta
        else:
            cpln[idx - no_cp - no_cpin - no_clin - 1, 0:3] = cpln[idx - no_cp - no_cpin - no_clin - 1, 0:3] + delta


def move_curvlin_srch(
    x_grp: float,
    cp_rev_in_group: NDArray[np.int_],
    circlin_srch: NDArray[np.float64],
    cp: NDArray[np.float64],
    cpin: NDArray[np.float64],
    clin: NDArray[np.float64],
    cpln: NDArray[np.float64],
    no_cp: int,
    no_cpin: int,
    no_clin: int,
    no_cpln: int,
) -> None:
    """Move constraints along a curved line (rotation about axis). circlin_srch: [center(3), axis_dir(3), angle_deg]."""
    angle_deg = x_grp * (float(circlin_srch[6]) if circlin_srch.size >= 7 else 90.0)
    angle_rad = np.deg2rad(angle_deg)
    local_orig = circlin_srch[0:3]

    c = np.cos(angle_rad)
    s = np.sin(angle_rad)
    rot_local = np.array([[c, -s, 0], [s, c, 0], [0, 0, 1]], dtype=float)

    for idx in cp_rev_in_group.flat:
        idx = int(idx)
        if idx <= no_cp:
            local_x = cp[idx - 1, 0:3] - local_orig
        elif idx <= no_cp + no_cpin:
            local_x = cpin[idx - no_cp - 1, 0:3] - local_orig
        elif idx <= no_cp + no_cpin + no_clin:
            local_x = clin[idx - no_cp - no_cpin - 1, 0:3] - local_orig
        else:
            local_x = cpln[idx - no_cp - no_cpin - no_clin - 1, 0:3] - local_orig

        dp = rot_local @ local_x
        new_pos = local_orig + dp

        if idx <= no_cp:
            cp[idx - 1, 0:3] = new_pos
        elif idx <= no_cp + no_cpin:
            cpin[idx - no_cp - 1, 0:3] = new_pos
        elif idx <= no_cp + no_cpin + no_clin:
            clin[idx - no_cp - no_cpin - 1, 0:3] = new_pos
        else:
            cpln[idx - no_cp - no_cpin - no_clin - 1, 0:3] = new_pos


def orient1d_srch(
    x_grp: float,
    cp_rev_in_group: NDArray[np.int_],
    dir1d_srch: NDArray[np.float64],
    cp: NDArray[np.float64],
    cpin: NDArray[np.float64],
    clin: NDArray[np.float64],
    cpln: NDArray[np.float64],
    no_cp: int,
    no_cpin: int,
    no_clin: int,
    no_cpln: int,
) -> None:
    """Reorient normal about one axis. dir1d_srch: [local_rot_axis(3), angle_deg]."""
    angle_deg = x_grp * (float(dir1d_srch[3]) if dir1d_srch.size >= 4 else 90.0)
    dn = np.array([0, -np.sin(np.deg2rad(angle_deg)), np.cos(np.deg2rad(angle_deg))], dtype=float)
    dn = _norm3(dn)
    local_x = dir1d_srch[0:3]

    for idx in cp_rev_in_group.flat:
        idx = int(idx)
        if idx <= no_cp:
            local_z = cp[idx - 1, 3:6]
        elif idx <= no_cp + no_cpin:
            local_z = cpin[idx - no_cp - 1, 3:6]
        elif idx <= no_cp + no_cpin + no_clin:
            local_z = clin[idx - no_cp - no_cpin - 1, 6:9]
        else:
            local_z = cpln[idx - no_cp - no_cpin - no_clin - 1, 3:6]

        local_y = np.cross(local_z, local_x)
        rot = np.column_stack([local_x, local_y, local_z])
        new_normal = rot @ dn
        new_normal = _norm3(new_normal)

        if idx <= no_cp:
            cp[idx - 1, 3:6] = new_normal
        elif idx <= no_cp + no_cpin:
            cpin[idx - no_cp - 1, 3:6] = new_normal
        elif idx <= no_cp + no_cpin + no_clin:
            clin[idx - no_cp - no_cpin - 1, 6:9] = new_normal
        else:
            cpln[idx - no_cp - no_cpin - no_clin - 1, 3:6] = new_normal


def orient2d_srch(
    x_grp: NDArray[np.float64],
    cp_rev_in_group: NDArray[np.int_],
    dir2d_srch: NDArray[np.float64],
    cp: NDArray[np.float64],
    cpin: NDArray[np.float64],
    clin: NDArray[np.float64],
    cpln: NDArray[np.float64],
    no_cp: int,
    no_cpin: int,
    no_clin: int,
    no_cpln: int,
) -> None:
    """Reorient normal about two axes. dir2d_srch: [local_x(3), local_y(3), angle_x, angle_y]."""
    alpha = x_grp[0] * (float(dir2d_srch[6]) if dir2d_srch.size >= 7 else 90.0)
    beta = x_grp[1] * (float(dir2d_srch[7]) if dir2d_srch.size >= 8 else 90.0)
    dn = np.array(
        [
            np.sin(np.deg2rad(beta)),
            -np.sin(np.deg2rad(alpha)),
            np.cos(np.deg2rad(alpha)) * np.cos(np.deg2rad(beta)),
        ],
        dtype=float,
    )
    dn = _norm3(dn)
    local_x = dir2d_srch[0:3]
    local_y = dir2d_srch[3:6]

    for idx in cp_rev_in_group.flat:
        idx = int(idx)
        if idx <= no_cp:
            local_z = cp[idx - 1, 3:6]
        elif idx <= no_cp + no_cpin:
            local_z = cpin[idx - no_cp - 1, 3:6]
        elif idx <= no_cp + no_cpin + no_clin:
            local_z = clin[idx - no_cp - no_cpin - 1, 6:9]
        else:
            local_z = cpln[idx - no_cp - no_cpin - no_clin - 1, 3:6]

        rot = np.column_stack([local_x, local_y, local_z])
        new_normal = rot @ dn
        new_normal = _norm3(new_normal)

        if idx <= no_cp:
            cp[idx - 1, 3:6] = new_normal
        elif idx <= no_cp + no_cpin:
            cpin[idx - no_cp - 1, 3:6] = new_normal
        elif idx <= no_cp + no_cpin + no_clin:
            clin[idx - no_cp - no_cpin - 1, 6:9] = new_normal
        else:
            cpln[idx - no_cp - no_cpin - no_clin - 1, 3:6] = new_normal


def line_orient1d_srch(
    x_grp: float,
    cp_rev_in_group: NDArray[np.int_],
    lin_dir_srch: NDArray[np.float64],
    clin: NDArray[np.float64],
    no_cp: int,
    no_cpin: int,
    no_clin: int,
    no_cpln: int,
) -> None:
    """Reorient line direction and constraint normal (line constraints only). lin_dir_srch: [local_rot_axis(3), angle_deg]."""
    angle_deg = x_grp * (float(lin_dir_srch[3]) if lin_dir_srch.size >= 4 else 90.0)
    dn = np.array([0, -np.sin(np.deg2rad(angle_deg)), np.cos(np.deg2rad(angle_deg))], dtype=float)
    dn = _norm3(dn)
    local_x = lin_dir_srch[0:3]

    for idx in cp_rev_in_group.flat:
        idx = int(idx)
        if idx <= no_cp + no_cpin or idx > no_cp + no_cpin + no_clin:
            continue
        k = idx - no_cp - no_cpin - 1
        local_z = clin[k, 3:6]
        local_y = np.cross(local_z, local_x)
        rot = np.column_stack([local_x, local_y, local_z])
        new_linedir = rot @ dn
        clin[k, 3:6] = _norm3(new_linedir)
        local_z = clin[k, 6:9]
        local_y = np.cross(local_z, local_x)
        rot = np.column_stack([local_x, local_y, local_z])
        new_line_normal = rot @ dn
        clin[k, 6:9] = _norm3(new_line_normal)


def resize_lin_srch(
    x_grp: float,
    cp_rev_in_group: NDArray[np.int_],
    lin_size_srch: NDArray[np.float64],
    clin: NDArray[np.float64],
    no_cp: int,
    no_cpin: int,
    no_clin: int,
    no_cpln: int,
) -> None:
    """Resize line length. lin_size_srch: [min_length, max_length]. x_grp in [-1,1]."""
    lo = float(lin_size_srch[0])
    hi = float(lin_size_srch[1])
    line_length = lo + ((x_grp + 1) / 2) * (hi - lo)

    for idx in cp_rev_in_group.flat:
        idx = int(idx)
        if no_cp + no_cpin < idx <= no_cp + no_cpin + no_clin:
            clin[idx - no_cp - no_cpin - 1, 9] = line_length


def resize_rectpln_srch(
    x_grp: NDArray[np.float64],
    cp_rev_in_group: NDArray[np.int_],
    pln_size_srch: NDArray[np.float64],
    cpln_prop: NDArray[np.float64],
    no_cp: int,
    no_cpin: int,
    no_clin: int,
    no_cpln: int,
) -> None:
    """Resize rectangular plane. pln_size_srch: [min_len, max_len, min_width, max_width]. x_grp in [-1,1]^2."""
    pln_length = pln_size_srch[0] + (x_grp[0] + 1) / 2 * (pln_size_srch[1] - pln_size_srch[0])
    pln_width = pln_size_srch[2] + (x_grp[1] + 1) / 2 * (pln_size_srch[3] - pln_size_srch[2])

    for idx in cp_rev_in_group.flat:
        idx = int(idx)
        if no_cp + no_cpin + no_clin < idx <= no_cp + no_cpin + no_clin + no_cpln:
            k = idx - no_cp - no_cpin - no_clin - 1
            if cpln_prop.shape[1] >= 4:
                cpln_prop[k, 3] = pln_length
            if cpln_prop.shape[1] >= 8:
                cpln_prop[k, 7] = pln_width


def resize_circpln_srch(
    x_grp: float,
    cp_rev_in_group: NDArray[np.int_],
    pln_size_srch: NDArray[np.float64],
    cpln_prop: NDArray[np.float64],
    no_cp: int,
    no_cpin: int,
    no_clin: int,
    no_cpln: int,
) -> None:
    """Resize circular plane radius. pln_size_srch: [..., min_rad, max_rad] indices 5,6. x_grp in [-1,1]."""
    if pln_size_srch.size < 6:
        return
    lo = float(pln_size_srch[4])
    hi = float(pln_size_srch[5])
    pln_rad = lo + (x_grp + 1) / 2 * (hi - lo)

    for idx in cp_rev_in_group.flat:
        idx = int(idx)
        if no_cp + no_cpin + no_clin < idx <= no_cp + no_cpin + no_clin + no_cpln:
            k = idx - no_cp - no_cpin - no_clin - 1
            if cpln_prop.shape[1] >= 1:
                cpln_prop[k, 0] = pln_rad
