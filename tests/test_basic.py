"""Basic tests for KST rating tool pipeline and API."""

from pathlib import Path
from unittest.mock import patch

import numpy as np

from kst_rating_tool import (
    ConstraintSet,
    PointConstraint,
    analyze_constraints,
    analyze_constraints_detailed,
    analyze_specified_motions,
)
from kst_rating_tool.combination import combo_preproc
from kst_rating_tool.motion import ScrewMotion
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


def _make_fixed_screw_motion() -> ScrewMotion:
    """Return a fixed ScrewMotion whose as_array() gives a stable 10-element vector."""
    omu = np.array([0.0, 0.0, 1.0])
    mu = np.array([0.0, 0.0, 0.0])
    rho = np.array([0.0, 0.0, 0.0])
    return ScrewMotion(omu=omu, mu=mu, rho=rho, h=np.inf)


def _make_multi_point_cs(n: int = 7) -> ConstraintSet:
    """Return a ConstraintSet with n evenly-spaced PointConstraints (generates > 1 combo)."""
    angles = np.linspace(0, 2 * np.pi, n, endpoint=False)
    return ConstraintSet(
        points=[
            PointConstraint(
                position=np.array([np.cos(a), np.sin(a), 0.0]),
                normal=np.array([0.0, 0.0, 1.0]),
            )
            for a in angles
        ]
    )


def test_duplicate_motion_skipped_sequential():
    """Duplicate motions are skipped; combo_dup_idx uses 1-based indexing where 0 means unique
    and a positive value points to the index of the first occurrence of that motion."""
    cs = _make_multi_point_cs(7)
    fixed_mot = _make_fixed_screw_motion()
    fixed_arr = fixed_mot.as_array().ravel()
    fixed_arr = np.round(fixed_arr * 1e4) / 1e4

    dummy_rating = np.ones(cs.total_cp, dtype=float) * np.inf
    dummy_input_wr = np.zeros((6, 1))
    dummy_W = np.ones((6, 5))  # non-empty, rank check is patched

    with (
        patch("kst_rating_tool.pipeline.form_combo_wrench", return_value=dummy_W),
        patch("kst_rating_tool.pipeline.matlab_rank", return_value=5),
        patch("kst_rating_tool.pipeline.rec_mot", return_value=fixed_mot),
        patch("kst_rating_tool.pipeline.input_wr_compose", return_value=(dummy_input_wr, None)),
        patch("kst_rating_tool.pipeline.react_wr_5_compose", return_value=np.zeros((5, 6))),
        patch(
            "kst_rating_tool.pipeline._rate_motion_all_constraints",
            return_value=(dummy_rating, dummy_rating, dummy_rating, dummy_rating, dummy_rating, dummy_rating, dummy_rating),
        ),
    ):
        detailed = analyze_constraints_detailed(cs, n_workers=1)

    # Only one unique motion should be stored
    assert detailed.mot_half.shape[0] == 1
    assert np.allclose(detailed.mot_half[0], fixed_arr)

    # All combos beyond the first that were processed should be flagged as duplicates
    dup_mask = detailed.combo_dup_idx > 0
    assert dup_mask.sum() > 0, "Expected at least one duplicate combo_dup_idx entry"
    # All duplicate indices must point to the first unique motion (1-based index = 1)
    assert np.all(detailed.combo_dup_idx[dup_mask] == 1)


def test_duplicate_motion_skipped_parallel():
    """Same duplicate-detection check via the n_workers>1 path."""
    from unittest.mock import MagicMock

    cs = _make_multi_point_cs(7)
    combo = combo_preproc(cs)
    n_combo = combo.shape[0]

    fixed_mot = _make_fixed_screw_motion()
    fixed_arr = np.round(fixed_mot.as_array().ravel() * 1e4) / 1e4

    dummy_rating = np.ones(cs.total_cp, dtype=float) * np.inf
    dummy_R_two = np.full((2, cs.total_cp), np.inf)

    # Build fake chunk results: every combo produces the same motion
    fake_chunk_results = [[(i, fixed_arr.copy(), dummy_R_two) for i in range(n_combo)]]

    mock_pool = MagicMock()
    mock_pool.__enter__ = lambda s: s
    mock_pool.__exit__ = MagicMock(return_value=False)
    mock_pool.map.return_value = fake_chunk_results

    with patch("kst_rating_tool.pipeline.Pool", return_value=mock_pool):
        detailed = analyze_constraints_detailed(cs, n_workers=2)

    # Only one unique motion should be stored
    assert detailed.mot_half.shape[0] == 1
    assert np.allclose(detailed.mot_half[0], fixed_arr)

    dup_mask = detailed.combo_dup_idx > 0
    assert dup_mask.sum() > 0, "Expected at least one duplicate combo_dup_idx entry"
    assert np.all(detailed.combo_dup_idx[dup_mask] == 1)
