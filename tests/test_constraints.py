import numpy as np
import pytest
from kst_rating_tool.constraints import normalize


def test_normalize_zero_vector():
    """Test that a zero vector returns a zero vector (and a copy)."""
    v = np.zeros(3)
    n = normalize(v)
    assert np.array_equal(n, v)
    assert n is not v  # Ensure it returns a copy


def test_normalize_nonzero_vector():
    """Test that a non-zero vector is normalized correctly."""
    v = np.array([1.0, 1.0, 0.0])
    n = normalize(v)
    expected = np.array([1.0 / np.sqrt(2), 1.0 / np.sqrt(2), 0.0])
    assert np.allclose(n, expected)
    assert np.isclose(np.linalg.norm(n), 1.0)


def test_normalize_input_preservation():
    """Test that the original input vector is not modified."""
    v = np.array([3.0, 0.0, 4.0])
    original_v = v.copy()
    _ = normalize(v)
    assert np.array_equal(v, original_v)
