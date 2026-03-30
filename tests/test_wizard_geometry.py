"""Tests for wizard geometry size warnings."""

from __future__ import annotations

import numpy as np

from kst_rating_tool.constraints import ConstraintSet, LineConstraint, PlaneConstraint
from kst_rating_tool.wizard_geometry import MIN_RECOMMENDED_FEATURE_MM, geometry_size_warnings


def test_line_too_short_warns():
    cs = ConstraintSet()
    cs.lines.append(
        LineConstraint(
            np.zeros(3),
            np.array([1.0, 0.0, 0.0]),
            np.array([0.0, 0.0, 1.0]),
            3.0,
        )
    )
    msgs = geometry_size_warnings(cs)
    assert len(msgs) == 1
    assert "3" in msgs[0] and str(int(MIN_RECOMMENDED_FEATURE_MM)) in msgs[0]


def test_plane_rectangular_warns():
    cs = ConstraintSet()
    prop = np.array([1.0, 0.0, 0.0, 4.0, 0.0, 1.0, 0.0, 4.0], dtype=float)
    cs.planes.append(PlaneConstraint(np.zeros(3), np.array([0.0, 0.0, 1.0]), 1, prop))
    msgs = geometry_size_warnings(cs)
    assert len(msgs) == 1


def test_plane_ok():
    cs = ConstraintSet()
    prop = np.array([1.0, 0.0, 0.0, 10.0, 0.0, 1.0, 0.0, 10.0], dtype=float)
    cs.planes.append(PlaneConstraint(np.zeros(3), np.array([0.0, 0.0, 1.0]), 1, prop))
    assert geometry_size_warnings(cs) == []


def test_plane_circular_small_diameter_warns():
    cs = ConstraintSet()
    cs.planes.append(PlaneConstraint(np.zeros(3), np.array([0.0, 0.0, 1.0]), 2, np.array([2.0], dtype=float)))
    msgs = geometry_size_warnings(cs)
    assert len(msgs) == 1
