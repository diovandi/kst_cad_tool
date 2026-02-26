"""Tests for shared utility functions."""

import numpy as np
import pytest

from kst_rating_tool.utils import matlab_rank


@pytest.mark.parametrize(
    "A, expected_rank",
    [
        (np.eye(3), 3),
        (np.zeros((3, 3)), 0),
        (np.ones((3, 3)), 1),
        ([[1, 0, 0], [0, 1, 0], [0, 0, 0]], 2),
        ([[1, 2, 3], [2, 4, 6], [3, 6, 9]], 1),
    ],
)
def test_matlab_rank_basic(A, expected_rank):
    """Test basic rank scenarios."""
    assert matlab_rank(np.array(A, dtype=float)) == expected_rank


@pytest.mark.parametrize(
    "shape",
    [
        (0, 0),
        (0, 5),
        (5, 0),
    ],
)
def test_matlab_rank_empty(shape):
    """Test empty matrices."""
    A = np.zeros(shape)
    assert matlab_rank(A) == 0


@pytest.mark.parametrize(
    "val, expected_rank",
    [
        (0.0, 0),
        (1.0, 1),
        (1e-15, 1),  # Small but significant
        (1e-323, 1),  # Denormal but non-zero
    ],
)
def test_matlab_rank_1x1(val, expected_rank):
    """Test 1x1 matrices."""
    A = np.array([[val]])
    assert matlab_rank(A) == expected_rank


def test_matlab_rank_small_singular_values():
    """Test matrices with small singular values relative to tolerance."""
    # Tolerance is max(size(A)) * eps(max(svd(A)))

    # Case 1: All values are very small and identical
    # max_sv = eps ≈ 2.22e-16. tol = 2 * eps(eps), on the order of 1e-31.
    # Both singular values are eps ≈ 2.22e-16, which are >> tol. Rank 2.
    eps = np.spacing(1.0)
    A = np.diag([eps, eps])
    assert matlab_rank(A) == 2

    # Case 2: One value is significant, one is noise below tolerance
    # max_sv = 1.0. tol = 2 * eps(1.0) = 2 * 2.22e-16 = 4.44e-16.
    # 2nd sv = 1e-16. < tol. Rank 1.
    A = np.diag([1.0, 1e-16])
    assert matlab_rank(A) == 1

    # Case 3: One value is significant, one is slightly above tolerance
    # max_sv = 1.0. tol = 4.44e-16.
    # 2nd sv = 5e-16. > tol. Rank 2.
    A = np.diag([1.0, 5e-16])
    assert matlab_rank(A) == 2


def test_matlab_rank_ill_conditioned():
    """Test ill-conditioned matrices (Hilbert matrix)."""
    # Hilbert matrix is notoriously ill-conditioned.
    # H_5x5 has rank 5 theoretically, but numerically might be tricky.
    # However, svd-based rank usually gets it right if condition number is not too huge.
    from scipy.linalg import hilbert

    H = hilbert(5)
    assert matlab_rank(H) == 5

    H = hilbert(10)
    # The condition number of H(10) is ~1e13.
    # max sv ~ 1.5. min sv ~ 1e-13.
    # tol ~ 10 * eps(1.5) ~ 10 * 3.33e-16 ~ 3.33e-15.
    # min sv > tol (1e-13 > 3e-15).
    # So it should be full rank (10).
    assert matlab_rank(H) == 10

    # H(15) condition number ~ 1e17.
    # max sv ~ 1.5. tol ~ 15 * eps(1.5) ~ 5e-15.
    # min sv might be smaller than tol.
    # Let's verify behavior.
    H15 = hilbert(15)
    # In double precision, MATLAB's `rank(hilb(15))` returns 13 due to the
    # default tolerance max(m, n) * eps(max(singular_value)).
    # However, depending on the exact numpy/scipy build (OpenBLAS vs MKL etc),
    # and the version, the singular values might differ slightly.
    # We verified in this environment rank is 12.
    # We assert it is close to 12 or 13.
    r = matlab_rank(H15)
    assert r in (12, 13)


def test_matlab_rank_tall_wide():
    """Test tall and wide matrices."""
    # Tall matrix (5x2), rank 2
    A = np.zeros((5, 2))
    A[0, 0] = 1
    A[1, 1] = 1
    assert matlab_rank(A) == 2

    # Wide matrix (2x5), rank 2
    A = np.zeros((2, 5))
    A[0, 0] = 1
    A[1, 1] = 1
    assert matlab_rank(A) == 2

    # Rank deficient tall
    A = np.zeros((5, 2))
    A[:, 0] = 1
    A[:, 1] = 1  # Col 1 is same as Col 0
    assert matlab_rank(A) == 1
