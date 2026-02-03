from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Sequence

import numpy as np


@dataclass
class PointConstraint:
    """Point contact (CP).

    MATLAB syntax: cp = [x, y, z, nx, ny, nz]
    """

    position: np.ndarray  # shape (3,)
    normal: np.ndarray  # shape (3,)


@dataclass
class PinConstraint:
    """Pin contact (CPIN).

    MATLAB syntax: cpin = [x, y, z, ax, ay, az]
    """

    center: np.ndarray  # shape (3,)
    axis: np.ndarray  # shape (3,)


@dataclass
class LineConstraint:
    """Line contact (CLIN).

    MATLAB syntax:
        clin = [mx, my, mz, lx, ly, lz, nx, ny, nz, length]

    where:
        m  = midpoint
        l  = line direction
        n  = constraint normal
    """

    midpoint: np.ndarray  # shape (3,)
    line_dir: np.ndarray  # shape (3,)
    constraint_dir: np.ndarray  # shape (3,)
    length: float


@dataclass
class PlaneConstraint:
    """Plane contact (CPLN).

    MATLAB syntax:
        cpln = [px, py, pz, nx, ny, nz, type]
    where:
        type = 1 rectangular, 2 circular

    Plane properties (CPLN_PROP):
        - rectangular: [xdir(3), xlen, ydir(3), ylen]
        - circular: [radius]
    """

    midpoint: np.ndarray  # shape (3,)
    normal: np.ndarray  # shape (3,)
    type: int
    prop: np.ndarray  # property row from cpln_prop


@dataclass
class ConstraintSet:
    """Container grouping all constraint types."""

    points: List[PointConstraint] = field(default_factory=list)
    pins: List[PinConstraint] = field(default_factory=list)
    lines: List[LineConstraint] = field(default_factory=list)
    planes: List[PlaneConstraint] = field(default_factory=list)

    @property
    def total_cp(self) -> int:
        """Total number of constraints (all types)."""

        return len(self.points) + len(self.pins) + len(self.lines) + len(self.planes)

    def to_matlab_style_arrays(self) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
        """Export to MATLAB-style arrays (cp, cpin, clin, cpln, cpln_prop).

        This mirrors the input format of `cp_to_wrench.m` for easier
        comparison with the reference implementation.
        """

        if self.points:
            cp = np.array([np.concatenate((p.position, p.normal)) for p in self.points], dtype=float)
        else:
            cp = np.empty((0, 6), dtype=float)

        if self.pins:
            cpin = np.array([np.concatenate((p.center, p.axis)) for p in self.pins], dtype=float)
        else:
            cpin = np.empty((0, 6), dtype=float)

        if self.lines:
            clin = np.array(
                [
                    np.concatenate((ln.midpoint, ln.line_dir, ln.constraint_dir, np.array([ln.length], dtype=float)))
                    for ln in self.lines
                ],
                dtype=float,
            )
        else:
            clin = np.empty((0, 10), dtype=float)

        if self.planes:
            cpln = np.array(
                [
                    np.concatenate((pl.midpoint, pl.normal, np.array([pl.type], dtype=float)))
                    for pl in self.planes
                ],
                dtype=float,
            )
            cpln_prop = np.vstack([pl.prop for pl in self.planes]).astype(float)
        else:
            cpln = np.empty((0, 7), dtype=float)
            cpln_prop = np.empty((0, 0), dtype=float)

        return cp, cpin, clin, cpln, cpln_prop

    @classmethod
    def from_matlab_style_arrays(
        cls,
        cp: np.ndarray,
        cpin: np.ndarray,
        clin: np.ndarray,
        cpln: np.ndarray,
        cpln_prop: np.ndarray,
    ) -> ConstraintSet:
        """Build ConstraintSet from MATLAB-style arrays (e.g. after search-space modification)."""
        points = [PointConstraint(row[0:3].copy(), row[3:6].copy()) for row in cp]
        pins = [PinConstraint(row[0:3].copy(), row[3:6].copy()) for row in cpin]
        lines = [
            LineConstraint(
                row[0:3].copy(),
                row[3:6].copy(),
                row[6:9].copy(),
                float(row[9]),
            )
            for row in clin
        ]
        planes = []
        for i in range(cpln.shape[0]):
            row = cpln[i]
            prop = cpln_prop[i].copy() if cpln_prop.size > 0 and i < cpln_prop.shape[0] else np.array([], dtype=float)
            planes.append(
                PlaneConstraint(
                    row[0:3].copy(),
                    row[3:6].copy(),
                    int(row[6]),
                    prop,
                )
            )
        return cls(points=points, pins=pins, lines=lines, planes=planes)


def _as_array(vec: Sequence[float]) -> np.ndarray:
    arr = np.asarray(vec, dtype=float).reshape(-1)
    return arr


def normalize(v: np.ndarray) -> np.ndarray:
    """Return a normalized copy of v, leaving zeros unchanged."""

    n = np.linalg.norm(v)
    if n == 0:
        return v.copy()
    return v / n

