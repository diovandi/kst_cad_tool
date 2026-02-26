"""Parameterizations: map x in [-1, 1]^d to a ConstraintSet for modification optimization."""

from __future__ import annotations

from typing import Protocol

import numpy as np

from ..constraints import (
    ConstraintSet,
    LineConstraint,
    PinConstraint,
    PointConstraint,
)


class Parameterization(Protocol):
    """Callable that maps a parameter vector x to a ConstraintSet."""

    def __call__(self, x: np.ndarray) -> ConstraintSet:
        ...


def _as_1d(x: np.ndarray) -> np.ndarray:
    return np.asarray(x, dtype=float).ravel()


class PointOnLineParameterization:
    """Single point constraint moving along a line; x in [-1, 1]."""

    def __init__(
        self,
        base: ConstraintSet,
        point_index: int,
        line_start: np.ndarray,
        line_end: np.ndarray,
    ):
        """Parameterize the position of one point constraint along a line.

        Parameters
        ----------
        base
            Base constraint set; point at point_index will be moved.
        point_index
            Global 0-based index of the point constraint to move (must be a point).
        line_start, line_end
            (3,) positions; position = line_start + (x+1)/2 * (line_end - line_start).
        """
        self.base = base
        self.point_index = point_index
        self.line_start = np.asarray(line_start, dtype=float).reshape(3)
        self.line_end = np.asarray(line_end, dtype=float).reshape(3)
        n_pt = len(base.points)
        if point_index < 0 or point_index >= n_pt:
            raise ValueError("point_index must refer to a point constraint")

    def __call__(self, x: np.ndarray) -> ConstraintSet:
        t = (_as_1d(x)[0] + 1.0) / 2.0
        t = np.clip(t, 0.0, 1.0)
        position = self.line_start + t * (self.line_end - self.line_start)
        points = []
        for i, p in enumerate(self.base.points):
            if i == self.point_index:
                points.append(PointConstraint(position.copy(), p.normal.copy()))
            else:
                points.append(
                    PointConstraint(p.position.copy(), p.normal.copy())
                )
        return ConstraintSet(
            points=points,
            pins=list(self.base.pins),
            lines=list(self.base.lines),
            planes=list(self.base.planes),
        )


class Orientation1DParameterization:
    """Single pin or line constraint with 1D orientation search; x in [-1, 1]."""

    def __init__(
        self,
        base: ConstraintSet,
        constraint_index: int,
        axis: np.ndarray,
        angle_range: tuple[float, float] = (-np.pi, np.pi),
    ):
        """Parameterize the orientation of one pin (or line constraint dir) about an axis.

        Parameters
        ----------
        base
            Base constraint set.
        constraint_index
            Global 0-based index: must be a pin or a line (constraint_dir is rotated).
        axis
            (3,) rotation axis (will be normalized).
        angle_range
            (min_angle, max_angle) in radians; x=-1 -> min, x=1 -> max.
        """
        self.base = base
        self.constraint_index = constraint_index
        self.axis = np.asarray(axis, dtype=float).reshape(3)
        n = np.linalg.norm(self.axis)
        if n > 0:
            self.axis = self.axis / n
        self.angle_range = angle_range
        n_pt = len(base.points)
        n_pin = len(base.pins)
        n_lin = len(base.lines)
        # Valid range: pins [n_pt, n_pt+n_pin) and lines [n_pt+n_pin, n_pt+n_pin+n_lin); reject points and planes
        if not (n_pt <= constraint_index < n_pt + n_pin + n_lin):
            raise ValueError("constraint_index must be a pin or line")

    def _rodrigues(self, v: np.ndarray, axis: np.ndarray, angle: float) -> np.ndarray:
        """Rotate v about axis by angle (Rodrigues formula)."""
        return (
            v * np.cos(angle)
            + np.cross(axis, v) * np.sin(angle)
            + axis * (np.dot(axis, v) * (1 - np.cos(angle)))
        )

    def __call__(self, x: np.ndarray) -> ConstraintSet:
        s = _as_1d(x)[0]
        a0, a1 = self.angle_range
        angle = a0 + (s + 1.0) / 2.0 * (a1 - a0)
        n_pt = len(self.base.points)
        n_pin = len(self.base.pins)
        pins = []
        for i, p in enumerate(self.base.pins):
            idx = n_pt + i
            if idx == self.constraint_index:
                new_axis = self._rodrigues(p.axis.copy(), self.axis, angle)
                pins.append(PinConstraint(p.center.copy(), new_axis))
            else:
                pins.append(PinConstraint(p.center.copy(), p.axis.copy()))
        lines = []
        for i, ln in enumerate(self.base.lines):
            idx = n_pt + n_pin + i
            if idx == self.constraint_index:
                new_dir = self._rodrigues(ln.constraint_dir.copy(), self.axis, angle)
                lines.append(
                    LineConstraint(
                        ln.midpoint.copy(),
                        ln.line_dir.copy(),
                        new_dir,
                        ln.length,
                    )
                )
            else:
                lines.append(
                    LineConstraint(
                        ln.midpoint.copy(),
                        ln.line_dir.copy(),
                        ln.constraint_dir.copy(),
                        ln.length,
                    )
                )
        return ConstraintSet(
            points=list(self.base.points),
            pins=pins,
            lines=lines,
            planes=list(self.base.planes),
        )
