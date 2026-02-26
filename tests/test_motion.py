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
from kst_rating_tool.motion import specmot_row_to_screw, ScrewMotion

def test_specmot_row_to_screw_finite_pitch():
    # Input: [omega_x, omega_y, omega_z, rho_x, rho_y, rho_z, h]
    # h = 2.0
    # omu = [1, 2, 2] -> norm = 3 -> normalized = [1/3, 2/3, 2/3]
    # rho = [1, 0, 0]
    # mu = h * omu + cross(rho, omu)
    # cross([1, 0, 0], [1/3, 2/3, 2/3]) = [0, -2/3, 2/3]
    # mu = 2 * [1/3, 2/3, 2/3] + [0, -2/3, 2/3]
    #    = [2/3, 4/3, 4/3] + [0, -2/3, 2/3]
    #    = [2/3, 2/3, 6/3] = [2/3, 2/3, 2.0]

    row = np.array([1.0, 2.0, 2.0, 1.0, 0.0, 0.0, 2.0], dtype=float)
    screw = specmot_row_to_screw(row)

    expected_omu = np.array([1.0/3.0, 2.0/3.0, 2.0/3.0])
    expected_mu = np.array([2.0/3.0, 2.0/3.0, 2.0])

    np.testing.assert_allclose(screw.omu, expected_omu, atol=1e-12)
    np.testing.assert_allclose(screw.mu, expected_mu, atol=1e-12)
    np.testing.assert_allclose(screw.rho, row[3:6], atol=1e-12)
    assert screw.h == 2.0

def test_specmot_row_to_screw_infinite_pitch():
    # h = inf
    # Input omu serves as translation direction: [3, 4, 0] -> norm=5 -> normalized=[0.6, 0.8, 0]
    # rho is ignored for mu calculation in infinite pitch case in this implementation

    row = np.array([3.0, 4.0, 0.0, 1.0, 1.0, 1.0, np.inf], dtype=float)
    screw = specmot_row_to_screw(row)

    expected_mu = np.array([0.6, 0.8, 0.0])
    expected_omu = np.zeros(3)

    np.testing.assert_allclose(screw.omu, expected_omu, atol=1e-12)
    np.testing.assert_allclose(screw.mu, expected_mu, atol=1e-12)
    assert np.isinf(screw.h)

def test_specmot_row_to_screw_zero_vector_finite_h():
    # omu = [0, 0, 0], h = 1.0
    # Should result in zero omu and zero mu

    row = np.array([0.0, 0.0, 0.0, 1.0, 1.0, 1.0, 1.0], dtype=float)
    screw = specmot_row_to_screw(row)

    np.testing.assert_allclose(screw.omu, np.zeros(3), atol=1e-12)
    np.testing.assert_allclose(screw.mu, np.zeros(3), atol=1e-12)
    assert screw.h == 1.0

def test_specmot_row_to_screw_zero_vector_infinite_h():
    # direction = [0, 0, 0], h = inf
    # Should result in zero omu and zero mu

    row = np.array([0.0, 0.0, 0.0, 1.0, 1.0, 1.0, np.inf], dtype=float)
    screw = specmot_row_to_screw(row)

    np.testing.assert_allclose(screw.omu, np.zeros(3), atol=1e-12)
    np.testing.assert_allclose(screw.mu, np.zeros(3), atol=1e-12)
    assert np.isinf(screw.h)

def test_specmot_row_to_screw_zero_pitch():
    # h = 0
    # omu = [0, 0, 1] (already normalized)
    # rho = [1, 0, 0]
    # mu = 0 * omu + cross(rho, omu) = cross([1, 0, 0], [0, 0, 1]) = [0, -1, 0]

    row = np.array([0.0, 0.0, 1.0, 1.0, 0.0, 0.0, 0.0], dtype=float)
    screw = specmot_row_to_screw(row)

    expected_omu = np.array([0.0, 0.0, 1.0])
    expected_mu = np.array([0.0, -1.0, 0.0])

    np.testing.assert_allclose(screw.omu, expected_omu, atol=1e-12)
    np.testing.assert_allclose(screw.mu, expected_mu, atol=1e-12)
    assert screw.h == 0.0
