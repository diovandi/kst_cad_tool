"""Parameterizations: map x in [-1, 1]^d to a ConstraintSet for modification optimization."""

from __future__ import annotations

from typing import TYPE_CHECKING, List, Protocol

import numpy as np
from numpy.typing import NDArray

from ..constraints import (
    ConstraintSet,
    LineConstraint,
    PinConstraint,
    PlaneConstraint,
    PointConstraint,
)

if TYPE_CHECKING:
    from .revision import RevisionConfig


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


def build_x_map(config: "RevisionConfig") -> tuple[NDArray[np.int_], int]:
    """Compute x_map and no_dim from a RevisionConfig.

    Returns (x_map, no_dim) where x_map[i] gives the 1-based column
    indices into x for group i.  Types 4, 6, 9 consume two columns;
    all others consume one.
    """
    row = 1
    x_map = np.zeros((len(config.grp_members), 2), dtype=np.int_)
    for i in range(len(config.grp_members)):
        if config.grp_rev_type.flat[i] in (4, 6, 9):
            x_map[i, 0] = row
            x_map[i, 1] = row + 1
            row += 2
        else:
            x_map[i, 0] = row
            x_map[i, 1] = 0
            row += 1
    return x_map, row - 1


class PerturbationParameterization:
    """Maps x in [-1, 1]^(3*n) to a perturbed ConstraintSet.

    Each constraint's position is shifted by ``x[3*i : 3*i+3] * max_delta``.
    This bridges sensitivity analysis (identifying *which* constraint is most
    sensitive) with continuous optimizers such as ``optimize_modification`` and
    ``optimize_bo`` (finding *how far* to move it for best improvement).

    Parameters
    ----------
    base
        Base constraint set (all four types supported).
    max_delta
        Maximum positional perturbation per axis in model units.
    constraint_indices
        Optional list of global 0-based constraint indices to perturb.
        If None (default), all constraints are perturbed (d = 3 * total_cp).

    Examples
    --------
    >>> param = PerturbationParameterization(cs, max_delta=0.5)
    >>> from kst_rating_tool.optimization import optimize_modification
    >>> result = optimize_modification(param, max_eval=200)
    """

    def __init__(
        self,
        base: ConstraintSet,
        max_delta: float = 0.5,
        constraint_indices: list[int] | None = None,
    ) -> None:
        self.base = base
        self.max_delta = float(max_delta)
        total = base.total_cp
        if constraint_indices is None:
            self._indices: list[int] = list(range(total))
        else:
            for idx in constraint_indices:
                if idx < 0 or idx >= total:
                    raise ValueError(
                        f"constraint_index {idx} out of range (total_cp={total})"
                    )
            self._indices = list(constraint_indices)

    @property
    def n_params(self) -> int:
        """Dimensionality of the parameter vector: 3 * len(constraint_indices)."""
        return 3 * len(self._indices)

    @property
    def bounds(self) -> list[tuple[float, float]]:
        """Bounds for each parameter dimension: [(-1, 1), ...] * n_params."""
        return [(-1.0, 1.0)] * self.n_params

    def __call__(self, x: np.ndarray) -> ConstraintSet:
        x_flat = np.asarray(x, dtype=float).ravel()
        if x_flat.size != self.n_params:
            raise ValueError(
                f"Expected x of length {self.n_params}, got {x_flat.size}"
            )

        n_pt = len(self.base.points)
        n_pin = len(self.base.pins)
        n_lin = len(self.base.lines)

        # Deep-copy all constraints; then apply perturbations to selected ones
        points = [PointConstraint(p.position.copy(), p.normal.copy()) for p in self.base.points]
        pins = [PinConstraint(p.center.copy(), p.axis.copy()) for p in self.base.pins]
        lines = [
            LineConstraint(ln.midpoint.copy(), ln.line_dir.copy(), ln.constraint_dir.copy(), ln.length)
            for ln in self.base.lines
        ]
        planes = [
            PlaneConstraint(pl.midpoint.copy(), pl.normal.copy(), pl.type, pl.prop.copy())
            for pl in self.base.planes
        ]

        for k, global_idx in enumerate(self._indices):
            delta = x_flat[3 * k : 3 * k + 3] * self.max_delta
            if global_idx < n_pt:
                points[global_idx].position += delta
            elif global_idx < n_pt + n_pin:
                pins[global_idx - n_pt].center += delta
            elif global_idx < n_pt + n_pin + n_lin:
                lines[global_idx - n_pt - n_pin].midpoint += delta
            else:
                planes[global_idx - n_pt - n_pin - n_lin].midpoint += delta

        return ConstraintSet(points=points, pins=pins, lines=lines, planes=planes)


class RevisionParameterization:
    """Wraps the MATLAB-style _apply_search to produce a ConstraintSet from x in [-1,1]^d.

    This bridges the factorial-grid revision code with the continuous
    surrogate optimizers that expect ``Parameterization(x) -> ConstraintSet``.
    """

    def __init__(
        self,
        base: ConstraintSet,
        config: "RevisionConfig",
        x_map: NDArray[np.int_] | None = None,
    ):
        from .revision import RevisionConfig as _RC  # noqa: F401

        self.base = base
        self.config = config
        if x_map is None:
            x_map, _ = build_x_map(config)
        self.x_map = x_map

    def __call__(self, x: np.ndarray) -> ConstraintSet:
        from .revision import _apply_search

        cp, cpin, clin, cpln, cpln_prop = self.base.to_matlab_style_arrays()
        cp = cp.copy()
        cpin = cpin.copy()
        clin = clin.copy()
        cpln = cpln.copy()
        cpln_prop = cpln_prop.copy() if cpln_prop.size else cpln_prop
        _apply_search(
            np.asarray(x, dtype=float),
            self.x_map,
            self.config,
            cp, cpin, clin, cpln, cpln_prop,
            cp.shape[0], cpin.shape[0], clin.shape[0], cpln.shape[0],
        )
        return ConstraintSet.from_matlab_style_arrays(cp, cpin, clin, cpln, cpln_prop)
