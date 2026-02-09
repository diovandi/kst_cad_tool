"""Shared utilities matching MATLAB behaviour."""
from __future__ import annotations

import numpy as np
from numpy.typing import NDArray


def matlab_rank(A: NDArray[np.float64]) -> int:
    """Compute matrix rank matching MATLAB's ``rank()`` function.

    MATLAB uses ``max(size(A)) * eps(max(svd(A)))`` as tolerance.
    ``eps(x)`` in MATLAB == ``np.spacing(x)`` in NumPy.
    """
    S = np.linalg.svd(A, compute_uv=False)
    if S.size == 0:
        return 0
    tol = float(max(A.shape) * np.spacing(S[0]))
    return int(np.sum(S > tol))


def matlab_null(A: NDArray[np.float64]) -> NDArray[np.float64]:
    """Compute the null space of *A* matching MATLAB's ``null(A)`` output.

    For 1×3 row vectors (the only case used for pin/plane axes in this
    codebase) a deterministic Gram-Schmidt procedure is used that reproduces
    MATLAB's (MKL-based) sign convention exactly.

    For other shapes, falls back to SVD-based computation with a deterministic
    sign convention (largest-absolute-value element positive per column of V).

    Returns an n×k matrix whose columns form an orthonormal basis for null(A).
    """
    A = np.atleast_2d(np.asarray(A, dtype=float))
    m, n = A.shape

    if m == 1 and n == 3:
        # Analytical null space for a 1×3 row vector.
        # Normalise the axis direction.
        a = A[0].copy()
        a_norm = np.linalg.norm(a)
        if a_norm == 0:
            return np.eye(3, dtype=float)
        a = a / a_norm

        # Pick coordinate axes sorted by smallest |a_i| first (most
        # perpendicular to *a*).  This matches MATLAB/MKL's dgesdd output
        # for axis-aligned and general vectors.
        order = np.argsort(np.abs(a))  # ascending

        # Modified Gram-Schmidt starting from the most perpendicular axes
        v1 = np.zeros(3, dtype=float)
        v1[order[0]] = 1.0
        v1 = v1 - np.dot(v1, a) * a
        v1 = v1 / np.linalg.norm(v1)

        v2 = np.zeros(3, dtype=float)
        v2[order[1]] = 1.0
        v2 = v2 - np.dot(v2, a) * a
        v2 = v2 - np.dot(v2, v1) * v1
        v2 = v2 / np.linalg.norm(v2)

        return np.column_stack([v1, v2])

    # General case: SVD-based null space.
    U, S, Vh = np.linalg.svd(A, full_matrices=True)
    tol = max(m, n) * np.spacing(S[0]) if S.size > 0 else 0.0
    r = int(np.sum(S > tol))
    V = Vh.T
    # Apply MATLAB sign convention: largest absolute value in each column positive.
    for col in range(n):
        max_idx = int(np.argmax(np.abs(V[:, col])))
        if V[max_idx, col] < 0:
            V[:, col] = -V[:, col]
    return V[:, r:]
