from __future__ import annotations

import itertools
from typing import List, Sequence, Tuple

import numpy as np

from .constraints import ConstraintSet


def combo_preproc(constraints: ConstraintSet) -> np.ndarray:
    """Python equivalent of `combo_preproc.m`.

    Parameters
    ----------
    constraints:
        Constraint set describing the assembly.

    Returns
    -------
    combo : (N, 5) ndarray of int
        Each row contains a combination of constraint indices (1-based),
        padded with zeros where fewer than 5 constraints are used.
    """

    total_cp = constraints.total_cp

    has_plane = len(constraints.planes) > 0
    has_pin_or_line = len(constraints.pins) > 0 or len(constraints.lines) > 0

    indices = list(range(1, total_cp + 1))

    def _nchoosek(n: int) -> np.ndarray:
        if n > total_cp:
            return np.empty((0, n), dtype=int)
        combos = list(itertools.combinations(indices, n))
        if not combos:
            return np.empty((0, n), dtype=int)
        return np.asarray(combos, dtype=int)

    combo2 = np.empty((0, 5), dtype=int)
    combo3 = np.empty((0, 5), dtype=int)
    combo4 = np.empty((0, 5), dtype=int)

    if has_plane:
        c2 = _nchoosek(2)
        c3 = _nchoosek(3)
        c4 = _nchoosek(4)
        c5 = _nchoosek(5)
        if c2.size:
            combo2 = np.hstack([c2, np.zeros((c2.shape[0], 3), dtype=int)])
        if c3.size:
            combo3 = np.hstack([c3, np.zeros((c3.shape[0], 2), dtype=int)])
        if c4.size:
            combo4 = np.hstack([c4, np.zeros((c4.shape[0], 1), dtype=int)])
    elif has_pin_or_line:
        c3 = _nchoosek(3)
        c4 = _nchoosek(4)
        c5 = _nchoosek(5)
        if c3.size:
            combo3 = np.hstack([c3, np.zeros((c3.shape[0], 2), dtype=int)])
        if c4.size:
            combo4 = np.hstack([c4, np.zeros((c4.shape[0], 1), dtype=int)])
    else:
        c5 = _nchoosek(5)

    if 'c5' not in locals():
        c5 = np.empty((0, 5), dtype=int)

    combo = np.vstack([combo2, combo3, combo4, c5]) if any(
        x.size for x in (combo2, combo3, combo4, c5)
    ) else np.empty((0, 5), dtype=int)

    # Match MATLAB nchoosek row order (lexicographic by columns 0..4)
    if combo.size > 0:
        order = np.lexsort((combo[:, 4], combo[:, 3], combo[:, 2], combo[:, 1], combo[:, 0]))
        combo = combo[order]

    return combo

