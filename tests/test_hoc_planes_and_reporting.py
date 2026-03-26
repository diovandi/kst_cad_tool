from __future__ import annotations

from pathlib import Path

import numpy as np

from kst_rating_tool import analyze_constraints_detailed
from kst_rating_tool.io_legacy import load_case_m_file
from kst_rating_tool.reporting import result_close, result_open, write_report
from kst_rating_tool.reference_data import THESIS_REF


def _assert_close(a: float, b: float, *, atol: float = 1e-3) -> None:
    assert abs(a - b) <= atol, f"{a} != {b} within atol={atol}"


def test_case3a_cover_leverage_matches_reference_metrics_if_present():
    repo_root = Path(__file__).resolve().parent.parent
    case_path = repo_root / "matlab_script" / "Input_files" / "case3a_cover_leverage.m"
    if not case_path.is_file():
        return

    cs = load_case_m_file(case_path)
    detailed = analyze_constraints_detailed(cs)
    rating = detailed.rating

    ref = THESIS_REF["case3a_cover_leverage"]
    _assert_close(rating.WTR, float(ref["WTR"]), atol=2e-3)
    _assert_close(rating.MRR, float(ref["MRR"]), atol=2e-3)
    _assert_close(rating.MTR, float(ref["MTR"]), atol=2e-3)
    _assert_close(rating.TOR, float(ref["TOR"]), atol=2e-3)


def test_case4a_endcap_tradeoff_no_snap6_matches_matlab_html_repo_value_if_present(tmp_path: Path):
    """Regression: ensure we can parse no_snap branches and match the repo's MATLAB HTML output."""
    repo_root = Path(__file__).resolve().parent.parent
    case_path = repo_root / "matlab_script" / "Input_files" / "case4a_endcap_tradeoff.m"
    if not case_path.is_file():
        return

    cs = load_case_m_file(case_path, no_snap_value=6)
    detailed = analyze_constraints_detailed(cs)
    rating = detailed.rating

    # From matlab_script/Result - case4a_endcap_tradeoff.html in this repo.
    _assert_close(rating.WTR, 2.0000, atol=1e-4)
    _assert_close(rating.MRR, 2.9348, atol=1e-4)
    _assert_close(rating.MTR, 3.5437, atol=1e-4)
    _assert_close(rating.TOR, 1.2075, atol=1e-4)

    # Also smoke-test HTML generation (ported result_open/report/result_close).
    mot_all = detailed.mot_all
    if mot_all.size:
        uniq_idx = np.unique(mot_all, axis=0, return_index=True)[1]
        mot_all_uniq = mot_all[uniq_idx, :]
    else:
        mot_all_uniq = np.empty((0, 10), dtype=float)
    f = result_open("case4a_endcap_tradeoff_no_snap6", output_dir=tmp_path)
    try:
        write_report(
            f,
            inputfile="case4a_endcap_tradeoff_no_snap6",
            rating=rating,
            mot_all_uniq=mot_all_uniq,
            R_uniq=detailed.Ri,
            total_cp=int(detailed.Ri.shape[1]) if detailed.Ri.size else 0,
            no_mot=int(detailed.Ri.shape[0]) if detailed.Ri.size else 0,
            combo=detailed.combo,
            combo_proc=detailed.combo_proc,
        )
    finally:
        result_close(f)

    html_path = tmp_path / "Result - case4a_endcap_tradeoff_no_snap6.html"
    html = html_path.read_text(encoding="utf-8")
    assert "Weakest Total Resistance rating (WTR)" in html
    assert "<TABLE BORDER=2>" in html

