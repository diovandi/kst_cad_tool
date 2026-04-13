"""Tests for optim_main_rev, optim_postproc, rate_specmot, main_specmot_optim, and search_space."""
from __future__ import annotations

import numpy as np
import pytest

from kst_rating_tool import ConstraintSet, PointConstraint, analyze_constraints_detailed
from kst_rating_tool.optimization import (
    RevisionConfig,
    optim_main_rev,
    optim_postproc,
    optim_postproc_plot,
    rate_specmot,
    main_specmot_optim,
    move_lin_srch,
    orient1d_srch,
)


# ── shared fixtures ───────────────────────────────────────────────────────────

def _six_point_set() -> ConstraintSet:
    pts = [
        (-1.0, 0.0, 0.0),
        (1.0, 0.0, 0.0),
        (0.0, -1.0, 0.0),
        (0.0, 1.0, 0.0),
        (0.0, 0.0, -1.0),
        (0.0, 0.0, 1.0),
    ]
    return ConstraintSet(
        points=[
            PointConstraint(
                position=np.array(p, dtype=float),
                normal=np.array([0.0, 0.0, 1.0], dtype=float),
            )
            for p in pts
        ]
    )


def _simple_specmot() -> np.ndarray:
    """A single pure rotation about Z: [0,0,1, 0,0,0, 0]."""
    return np.array([[0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 0.0]], dtype=float)


def _line_revision_config_cp1(cs: ConstraintSet) -> RevisionConfig:
    """Move CP1 along X axis."""
    # lin_srch = [center(3), direction(3), scale]
    srch_spc = np.array([-1.0, 0.0, 0.0,  1.0, 0.0, 0.0,  0.5], dtype=float)
    return RevisionConfig(
        grp_members=[np.array([1], dtype=np.int_)],
        grp_rev_type=np.array([2], dtype=np.int_),
        grp_srch_spc=[srch_spc],
    )


# ── optim_main_rev ────────────────────────────────────────────────────────────

def test_optim_main_rev_1d_smoke():
    cs = _six_point_set()
    baseline = analyze_constraints_detailed(cs)
    config = _line_revision_config_cp1(cs)

    WTR_all, MRR_all, MTR_all, TOR_all, x_map = optim_main_rev(baseline, config, no_step=3)

    assert WTR_all.shape == (4,), f"Expected shape (4,), got {WTR_all.shape}"
    assert MRR_all.shape == (4,)
    assert MTR_all.shape == (4,)
    assert np.all(np.isfinite(WTR_all))
    assert np.all(np.isfinite(MRR_all))
    assert np.all(np.isfinite(MTR_all))
    assert x_map.shape == (1, 2)


def test_optim_main_rev_returns_finite_values():
    """All rating values returned by the search must be finite (not NaN/Inf)."""
    cs = _six_point_set()
    baseline = analyze_constraints_detailed(cs)
    config = _line_revision_config_cp1(cs)

    WTR_all, MRR_all, MTR_all, _, _ = optim_main_rev(baseline, config, no_step=5)

    assert np.all(np.isfinite(WTR_all)), "WTR values must be finite"
    assert np.all(np.isfinite(MRR_all)), "MRR values must be finite"
    assert np.all(np.isfinite(MTR_all)), "MTR values must be finite"


def test_optim_main_rev_progress_callback():
    cs = _six_point_set()
    baseline = analyze_constraints_detailed(cs)
    config = _line_revision_config_cp1(cs)
    calls = []

    def cb(current, total):
        calls.append((current, total))

    optim_main_rev(baseline, config, no_step=2, progress_callback=cb)
    assert len(calls) == 3  # no_step+1 = 3 increments for 1D
    assert calls[-1][0] == calls[-1][1]  # last call: current == total


def test_optim_main_rev_no_rev_type_constant_results():
    """Rev type 1 (none) applies no modification, so all grid points should yield the same rating."""
    cs = _six_point_set()
    baseline = analyze_constraints_detailed(cs)
    config = RevisionConfig(
        grp_members=[np.array([1], dtype=np.int_)],
        grp_rev_type=np.array([1], dtype=np.int_),  # type 1 = none/skip: no modification applied
        grp_srch_spc=[np.array([], dtype=float)],
    )

    WTR_all, MRR_all, _, _, _ = optim_main_rev(baseline, config, no_step=5)
    # Grid still runs (no_step+1 points), but no modification => constant output
    assert WTR_all.shape == (6,)
    assert np.allclose(WTR_all, WTR_all[0]), "rev_type=1 should produce identical ratings at all steps"


# ── optim_postproc ────────────────────────────────────────────────────────────

def test_optim_postproc_1d_finds_correct_max():
    # Construct synthetic 1D % change with a clear peak at index 2
    WTR_chg = np.array([1.0, 3.0, 7.0, 2.0, 0.5])
    MRR_chg = np.array([0.5, 2.0, 6.0, 1.5, 0.2])
    MTR_chg = np.array([0.2, 1.5, 5.0, 1.0, 0.1])
    TOR_chg = np.array([0.1, 1.0, 8.0, 0.5, 0.05])

    result = optim_postproc(no_step=4, no_dim=1,
                            WTR_optim_chg=WTR_chg, MRR_optim_chg=MRR_chg,
                            MTR_optim_chg=MTR_chg, TOR_optim_chg=TOR_chg)

    assert result["WTR_max_idx"] == 2
    assert result["TOR_max_idx"] == 2
    assert "x_inc" in result
    assert len(result["x_inc"]) == 5


def test_optim_postproc_2d_finds_correct_max():
    # 3x3 grid, peak at [1, 2]
    WTR_all = np.zeros((3, 3), dtype=float)
    WTR_all[1, 2] = 10.0
    WTR_chg = WTR_all  # same shape

    result = optim_postproc(no_step=2, no_dim=2,
                            WTR_optim_chg=WTR_chg, MRR_optim_chg=WTR_chg,
                            MTR_optim_chg=WTR_chg, TOR_optim_chg=WTR_chg,
                            WTR_optim_all=WTR_all)

    assert result["WTR_max_idx"] == (1, 2)


def test_optim_postproc_x_inc_range():
    WTR_chg = np.array([1.0, 2.0, 3.0])
    result = optim_postproc(no_step=2, no_dim=1,
                            WTR_optim_chg=WTR_chg, MRR_optim_chg=WTR_chg,
                            MTR_optim_chg=WTR_chg, TOR_optim_chg=WTR_chg)

    x_inc = result["x_inc"]
    assert x_inc[0] == pytest.approx(-1.0)
    assert x_inc[-1] == pytest.approx(1.0)
    assert len(x_inc) == 3


# ── rate_specmot ──────────────────────────────────────────────────────────────

def test_rate_specmot_smoke():
    cs = _six_point_set()
    config = _line_revision_config_cp1(cs)
    specmot = _simple_specmot()

    # x_map for a 1D rev_type=2 (non-2D): x_map = [[1, 0]]
    x_map = np.array([[1, 0]], dtype=np.int_)
    x = np.array([0.0], dtype=float)  # evaluate at x=0 (no shift)

    rating, Ri, mot_proc = rate_specmot(x, x_map, config, cs, specmot)

    assert hasattr(rating, "WTR")
    assert np.isfinite(rating.WTR)
    assert Ri.ndim == 2
    assert mot_proc.ndim == 2
    assert mot_proc.shape[1] == 10


def test_rate_specmot_returns_valid_results():
    """rate_specmot should return finite metrics and correctly shaped arrays."""
    cs = _six_point_set()
    config = _line_revision_config_cp1(cs)
    specmot = _simple_specmot()
    x_map = np.array([[1, 0]], dtype=np.int_)

    for x_val in [0.0, 0.5, 1.0]:
        rating, Ri, mot_proc = rate_specmot(np.array([x_val]), x_map, config, cs, specmot)
        assert hasattr(rating, "WTR")
        assert np.isfinite(rating.WTR)
        assert Ri.ndim == 2
        assert mot_proc.shape[1] == 10


# ── main_specmot_optim ────────────────────────────────────────────────────────

def test_main_specmot_optim_1d_smoke():
    cs = _six_point_set()
    config = _line_revision_config_cp1(cs)
    specmot = _simple_specmot()

    WTR_opt, MRR_opt, MTR_opt, TOR_opt, x_map_out = main_specmot_optim(
        config, cs, specmot, no_step=3
    )

    assert WTR_opt.shape == (4,)
    assert MRR_opt.shape == (4,)
    assert MTR_opt.shape == (4,)
    assert TOR_opt.shape == (4,)
    assert np.all(np.isfinite(WTR_opt))
    assert x_map_out.shape[0] == 1  # one group


def test_main_specmot_optim_empty_groups_no_dim_zero():
    """Empty grp_members → no_dim=0; should fall back to single-point baseline evaluation."""
    cs = _six_point_set()
    # Empty RevisionConfig: no groups → no_dim = 0
    config = RevisionConfig(
        grp_members=[],
        grp_rev_type=np.array([], dtype=np.int_),
        grp_srch_spc=[],
    )
    specmot = _simple_specmot()

    WTR_opt, _, _, _, _ = main_specmot_optim(config, cs, specmot, no_step=3)
    assert WTR_opt.shape == (1,)


# ── search_space functions ────────────────────────────────────────────────────

def _make_cp_arrays(positions, normals=None):
    """Build minimal cp/cpin/clin/cpln arrays for search_space function tests."""
    n = len(positions)
    if normals is None:
        normals = [[0.0, 0.0, 1.0]] * n
    cp = np.zeros((n, 6), dtype=float)
    for i, (pos, nrm) in enumerate(zip(positions, normals)):
        cp[i, 0:3] = pos
        cp[i, 3:6] = nrm
    cpin = np.empty((0, 6), dtype=float)
    clin = np.empty((0, 10), dtype=float)
    cpln = np.empty((0, 7), dtype=float)
    return cp, cpin, clin, cpln


def test_move_lin_srch_changes_position():
    positions = [[-1.0, 0.0, 0.0]]
    cp, cpin, clin, cpln = _make_cp_arrays(positions)
    original_pos = cp[0, 0:3].copy()

    # Move CP1 along X with scale=0.5; at x_grp=1.0 should shift by ~0.5
    lin_srch = np.array([-1.0, 0.0, 0.0,  1.0, 0.0, 0.0,  0.5], dtype=float)
    cp_rev = np.array([1], dtype=np.int_)

    move_lin_srch(1.0, cp_rev, lin_srch, cp, cpin, clin, cpln, 1, 0, 0, 0)

    assert not np.allclose(cp[0, 0:3], original_pos), "Position should change after move_lin_srch"


def test_move_lin_srch_no_change_at_x_zero():
    positions = [[-1.0, 0.0, 0.0]]
    cp, cpin, clin, cpln = _make_cp_arrays(positions)
    original_pos = cp[0, 0:3].copy()

    lin_srch = np.array([-1.0, 0.0, 0.0,  1.0, 0.0, 0.0,  0.5], dtype=float)
    cp_rev = np.array([1], dtype=np.int_)

    # At x=0 with center == current position, delta = 0*scale*direction → no net shift
    move_lin_srch(0.0, cp_rev, lin_srch, cp, cpin, clin, cpln, 1, 0, 0, 0)

    np.testing.assert_allclose(cp[0, 0:3], original_pos, atol=1e-12)


def test_orient1d_srch_changes_normal():
    positions = [[0.0, 0.0, 1.0]]
    normals = [[0.0, 0.0, 1.0]]
    cp, cpin, clin, cpln = _make_cp_arrays(positions, normals)
    original_normal = cp[0, 3:6].copy()

    # Rotate about X axis by 45 deg (x_grp=1.0, angle_deg=45)
    dir1d_srch = np.array([1.0, 0.0, 0.0,  45.0], dtype=float)
    cp_rev = np.array([1], dtype=np.int_)

    orient1d_srch(1.0, cp_rev, dir1d_srch, cp, cpin, clin, cpln, 1, 0, 0, 0)

    assert not np.allclose(cp[0, 3:6], original_normal), "Normal should change after orient1d_srch"
    # Result should still be a unit vector
    assert np.isclose(np.linalg.norm(cp[0, 3:6]), 1.0, atol=1e-10)


def test_orient1d_srch_no_change_at_x_zero():
    positions = [[0.0, 0.0, 0.0]]
    normals = [[0.0, 0.0, 1.0]]
    cp, cpin, clin, cpln = _make_cp_arrays(positions, normals)
    original_normal = cp[0, 3:6].copy()

    dir1d_srch = np.array([1.0, 0.0, 0.0,  45.0], dtype=float)
    cp_rev = np.array([1], dtype=np.int_)

    orient1d_srch(0.0, cp_rev, dir1d_srch, cp, cpin, clin, cpln, 1, 0, 0, 0)

    # At x=0 the rotation angle is 0 — normal should be unchanged (or nearly so)
    np.testing.assert_allclose(np.linalg.norm(cp[0, 3:6]), 1.0, atol=1e-10)
