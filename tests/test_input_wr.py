from unittest.mock import patch

import numpy as np
import pytest

from kst_rating_tool.input_wr import input_wr_compose
from kst_rating_tool.motion import ScrewMotion

# Common setup for tests
@pytest.fixture
def mock_screw_motion():
    return ScrewMotion(
        omu=np.array([0.0, 0.0, 1.0]),
        mu=np.array([0.0, 0.0, 0.0]),
        rho=np.array([0.0, 0.0, 0.0]),
        h=0.0
    )

@pytest.fixture
def dummy_pts():
    return np.array([[1.0, 0.0, 0.0]])

def test_input_wr_compose_pure_translation(mock_screw_motion, dummy_pts):
    """Scenario 1: Pure Translation (h = inf)."""
    mock_screw_motion.h = float("inf")
    # For pure translation, mu is the direction
    mock_screw_motion.mu = np.array([1.0, 0.0, 0.0])

    # max_d doesn't matter for pure translation as calc_d is skipped
    input_wr, d = input_wr_compose(mock_screw_motion, dummy_pts, max_d=10.0)

    assert d == float("inf")

    # Expected: fi = mu, ti = 0
    expected_fi = np.array([1.0, 0.0, 0.0])
    expected_ti = np.array([0.0, 0.0, 0.0])
    expected_wr = -np.concatenate([expected_fi, expected_ti])

    np.testing.assert_array_almost_equal(input_wr, expected_wr)

@patch("kst_rating_tool.input_wr.calc_d")
def test_input_wr_compose_rotation_dominant_zero_pitch(mock_calc_d, mock_screw_motion, dummy_pts):
    """Scenario 2: Rotation Dominant (h=0)."""
    mock_screw_motion.h = 0.0
    mock_screw_motion.omu = np.array([0.0, 0.0, 1.0])

    # Mock calc_d to return a specific distance
    mock_calc_d.return_value = 5.0

    input_wr, d = input_wr_compose(mock_screw_motion, dummy_pts, max_d=10.0)

    assert d == 5.0
    mock_calc_d.assert_called_once()

    # h=0 -> hw=inf. abs(hw) >= d is true.
    # fi = (hs * d) * omu = 0 * 5 * [0,0,1] = [0,0,0]
    # ti = d * omu = 5 * [0,0,1] = [0,0,5]
    expected_fi = np.array([0.0, 0.0, 0.0])
    expected_ti = np.array([0.0, 0.0, 5.0])
    expected_wr = -np.concatenate([expected_fi, expected_ti])

    np.testing.assert_array_almost_equal(input_wr, expected_wr)

@patch("kst_rating_tool.input_wr.calc_d")
def test_input_wr_compose_rotation_dominant_small_pitch(mock_calc_d, mock_screw_motion, dummy_pts):
    """Scenario 3: Rotation Dominant (finite h, small). abs(1/h) >= d."""
    mock_screw_motion.h = 0.1
    mock_screw_motion.omu = np.array([0.0, 0.0, 1.0])

    # d=5. hw = 1/0.1 = 10. abs(10) >= 5 is true.
    mock_calc_d.return_value = 5.0

    input_wr, d = input_wr_compose(mock_screw_motion, dummy_pts, max_d=10.0)

    assert d == 5.0

    # fi = (hs * d) * omu = 0.1 * 5 * [0,0,1] = [0, 0, 0.5]
    # ti = d * omu = 5 * [0,0,1] = [0, 0, 5]
    expected_fi = np.array([0.0, 0.0, 0.5])
    expected_ti = np.array([0.0, 0.0, 5.0])
    expected_wr = -np.concatenate([expected_fi, expected_ti])

    np.testing.assert_array_almost_equal(input_wr, expected_wr)

@patch("kst_rating_tool.input_wr.calc_d")
def test_input_wr_compose_translation_dominant_large_pitch(mock_calc_d, mock_screw_motion, dummy_pts):
    """Scenario 4: Translation Dominant (finite h, large). abs(1/h) < d."""
    mock_screw_motion.h = 10.0
    mock_screw_motion.omu = np.array([0.0, 0.0, 1.0])

    # d=5. hw = 1/10 = 0.1. abs(0.1) < 5 is true (wait, abs(hw) < d branch).
    # Logic: if ... or abs(hw) >= d: rotation dominant
    # else: translation dominant.
    # Here 0.1 < 5, so it goes to else.
    mock_calc_d.return_value = 5.0

    input_wr, d = input_wr_compose(mock_screw_motion, dummy_pts, max_d=10.0)

    assert d == 5.0

    # Translation dominant:
    # fi = omu = [0,0,1]
    # ti = hw * omu = 0.1 * [0,0,1] = [0, 0, 0.1]
    expected_fi = np.array([0.0, 0.0, 1.0])
    expected_ti = np.array([0.0, 0.0, 0.1])
    expected_wr = -np.concatenate([expected_fi, expected_ti])

    np.testing.assert_array_almost_equal(input_wr, expected_wr)

@patch("kst_rating_tool.input_wr.calc_d")
def test_input_wr_compose_calc_d_called_correctly(mock_calc_d, mock_screw_motion, dummy_pts):
    """Scenario 5: verify calc_d arguments are passed through."""
    mock_screw_motion.h = 1.0
    max_d = 123.45

    mock_calc_d.return_value = 1.0

    input_wr_compose(mock_screw_motion, dummy_pts, max_d)

    mock_calc_d.assert_called_once_with(mock_screw_motion.omu, mock_screw_motion.rho, dummy_pts, max_d)
