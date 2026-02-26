import numpy as np
import pytest
from kst_rating_tool.motion import calc_d

def test_calc_d_empty_points():
    omu = np.array([1.0, 0.0, 0.0])
    rho = np.array([0.0, 0.0, 0.0])
    pts = np.empty((0, 3), dtype=float)
    max_d = 10.0
    assert calc_d(omu, rho, pts, max_d) == 0.0

def test_calc_d_points_on_line():
    omu = np.array([0.0, 0.0, 1.0])
    rho = np.array([0.0, 0.0, 0.0])
    # Points on Z-axis: (0,0,1), (0,0,-5)
    pts = np.array([[0.0, 0.0, 1.0], [0.0, 0.0, -5.0]])
    max_d = 10.0
    # Should be close to 0
    assert calc_d(omu, rho, pts, max_d) == pytest.approx(0.0)

def test_calc_d_known_distance():
    omu = np.array([0.0, 0.0, 1.0])
    rho = np.array([0.0, 0.0, 0.0])
    # Point at (2,0,0) -> distance from Z-axis is 2.0
    pts = np.array([[2.0, 0.0, 0.0]])
    max_d = 10.0
    assert calc_d(omu, rho, pts, max_d) == pytest.approx(2.0)

def test_calc_d_clamping():
    omu = np.array([0.0, 0.0, 1.0])
    rho = np.array([0.0, 0.0, 0.0])
    # Point at (20,0,0) -> distance from Z-axis is 20.0
    pts = np.array([[20.0, 0.0, 0.0]])
    max_d = 10.0
    # Should be clamped to 10.0
    assert calc_d(omu, rho, pts, max_d) == pytest.approx(10.0)

def test_calc_d_multiple_points():
    omu = np.array([0.0, 0.0, 1.0])
    rho = np.array([0.0, 0.0, 0.0])
    # Points at distance 2.0 and 5.0
    pts = np.array([[2.0, 0.0, 0.0], [5.0, 0.0, 0.0]])
    max_d = 10.0
    # Should return max distance = 5.0
    assert calc_d(omu, rho, pts, max_d) == pytest.approx(5.0)

def test_calc_d_multiple_points_clamped():
    omu = np.array([0.0, 0.0, 1.0])
    rho = np.array([0.0, 0.0, 0.0])
    # Points at distance 2.0 and 20.0
    pts = np.array([[2.0, 0.0, 0.0], [20.0, 0.0, 0.0]])
    max_d = 10.0
    # Max distance is 20.0, clamped to 10.0
    assert calc_d(omu, rho, pts, max_d) == pytest.approx(10.0)

def test_calc_d_exact_boundary():
    omu = np.array([0.0, 0.0, 1.0])
    rho = np.array([0.0, 0.0, 0.0])
    # Point at distance 10.0
    pts = np.array([[10.0, 0.0, 0.0]])
    max_d = 10.0
    assert calc_d(omu, rho, pts, max_d) == pytest.approx(10.0)
