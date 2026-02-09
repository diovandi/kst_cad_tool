"""Basic tests for KST rating tool pipeline and API."""

from pathlib import Path

import numpy as np

from kst_rating_tool import (
    ConstraintSet,
    PointConstraint,
    analyze_constraints,
    analyze_constraints_detailed,
    analyze_specified_motions,
)
from kst_rating_tool.combination import combo_preproc
from kst_rating_tool.rating import aggregate_ratings


def test_analyze_constraints_runs_for_simple_point():
    cs = ConstraintSet(
        points=[PointConstraint(position=np.array([0.0, 0.0, 0.0]), normal=np.array([0.0, 0.0, 1.0]))]
    )

    results = analyze_constraints(cs)

    assert np.isfinite(results.WTR) or np.isinf(results.WTR)
    assert results.R.shape[0] == 1


def test_analyze_constraints_detailed_returns_expected_fields():
    cs = ConstraintSet(
        points=[
            PointConstraint(position=np.array([0.0, 0.0, 0.0]), normal=np.array([0.0, 0.0, 1.0])),
            PointConstraint(position=np.array([1.0, 0.0, 0.0]), normal=np.array([0.0, 1.0, 0.0])),
        ]
    )
    detailed = analyze_constraints_detailed(cs)

    assert hasattr(detailed, "R") and detailed.R.ndim == 2
    assert hasattr(detailed, "mot_half") and detailed.mot_half.ndim == 2
    assert detailed.mot_half.shape[1] == 10
    assert hasattr(detailed, "mot_all") and detailed.mot_all.shape[1] == 10
    assert hasattr(detailed, "combo_proc") and hasattr(detailed, "combo_dup_idx")
    assert hasattr(detailed, "rating") and hasattr(detailed.rating, "WTR")
    assert hasattr(detailed, "wr_all") and hasattr(detailed, "pts") and hasattr(detailed, "max_d")
    assert detailed.constraints.total_cp == 2
    assert detailed.combo.shape[1] == 5


def test_combo_preproc_points_only():
    cs = ConstraintSet(
        points=[
            PointConstraint(position=np.array([0.0, 0.0, 0.0]), normal=np.array([0.0, 0.0, 1.0])),
            PointConstraint(position=np.array([1.0, 0.0, 0.0]), normal=np.array([0.0, 1.0, 0.0])),
        ]
    )
    combo = combo_preproc(cs)
    assert combo.ndim == 2
    assert combo.shape[1] == 5
    assert cs.total_cp == 2
    assert combo.size == 0 or combo.shape[0] >= 0


def test_aggregate_ratings_empty():
    R = np.full((1, 1), np.inf, dtype=float)
    res = aggregate_ratings(R)
    assert res.WTR == 0.0
    assert res.MRR == 0.0
    assert res.MTR == 0.0
    assert res.TOR == 0.0 or np.isinf(res.TOR)


def test_aggregate_ratings_finite():
    Ri = np.array([[1.0, 0.5], [0.5, 1.0]], dtype=float)
    R = 1.0 / np.maximum(Ri, 1e-12)
    res = aggregate_ratings(R)
    assert np.isfinite(res.WTR)
    assert np.isfinite(res.MRR)
    assert np.isfinite(res.MTR)
    assert np.isfinite(res.TOR)


def test_analyze_specified_motions_single_motion():
    cs = ConstraintSet(
        points=[PointConstraint(position=np.array([0.0, 0.0, 0.0]), normal=np.array([0.0, 0.0, 1.0]))]
    )
    specmot = np.array([[1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 1.0]], dtype=float)
    result = analyze_specified_motions(cs, specmot)

    assert hasattr(result, "rating")
    assert hasattr(result.rating, "WTR")
    assert result.Ri.ndim == 2
    assert result.mot_proc.shape[1] == 10
    assert result.mot_proc.shape[0] == 2


def test_analyze_specified_motions_invalid_specmot_columns():
    cs = ConstraintSet(
        points=[PointConstraint(position=np.array([0.0, 0.0, 0.0]), normal=np.array([0.0, 0.0, 1.0]))]
    )
    specmot_bad = np.array([[1.0, 0.0, 0.0, 0.0, 0.0]], dtype=float)
    try:
        analyze_specified_motions(cs, specmot_bad)
        raised = False
    except ValueError as e:
        raised = True
        assert "7 columns" in str(e)
    assert raised


def test_specmot_row_to_screw():
    from kst_rating_tool.motion import specmot_row_to_screw

    row = np.array([1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 2.0], dtype=float)
    screw = specmot_row_to_screw(row)
    assert screw.omu.shape == (3,)
    assert screw.mu.shape == (3,)
    assert screw.rho.shape == (3,)
    assert screw.h == 2.0
    arr = screw.as_array()
    assert arr.shape == (10,)


def test_load_case_m_file_if_exists():
    repo_root = Path(__file__).resolve().parent.parent
    case_path = repo_root / "matlab_script" / "Input_files" / "case1a_chair_height.m"
    if not case_path.is_file():
        return
    from kst_rating_tool.io_legacy import load_case_m_file

    cs = load_case_m_file(case_path)
    assert cs.total_cp >= 1
    results = analyze_constraints(cs)
    assert np.isfinite(results.WTR) or np.isinf(results.WTR)
