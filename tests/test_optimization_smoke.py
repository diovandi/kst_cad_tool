from __future__ import annotations

from pathlib import Path
import subprocess
import sys

import numpy as np

from kst_rating_tool import ConstraintSet, PointConstraint, analyze_constraints_detailed
from kst_rating_tool.optimization import optim_main_red, sens_analysis_orient, sens_analysis_pos
from kst_rating_tool.rating import rate_motset


def _small_constraints() -> ConstraintSet:
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
            PointConstraint(position=np.array(p, dtype=float), normal=np.array([0.0, 0.0, 1.0], dtype=float))
            for p in pts
        ]
    )


def test_optim_main_red_smoke_runs():
    baseline = analyze_constraints_detailed(_small_constraints())
    wtr_all, cp_del_comb, wtr_chg, mrr_chg, mtr_chg, tor_chg = optim_main_red(baseline, no_red=1)
    assert wtr_all.size >= 1
    assert cp_del_comb.ndim == 2
    assert wtr_chg.shape[0] == wtr_all.shape[0]
    assert mrr_chg.shape[0] == wtr_all.shape[0]
    assert mtr_chg.shape[0] == wtr_all.shape[0]
    assert tor_chg.shape[0] == wtr_all.shape[0]


def test_sensitivity_smoke_runs():
    baseline = analyze_constraints_detailed(_small_constraints())
    sap = sens_analysis_pos(baseline, baseline.constraints, pert_dist=0.1, no_step=1)
    sao = sens_analysis_orient(baseline, baseline.constraints, pert_angle=5.0, no_step=1)
    assert len(sap) == 4
    assert len(sao) == 4
    assert sap[0].ndim == 3
    assert sao[0].ndim == 3


def test_rate_motset_supports_hoc_case_if_available():
    repo_root = Path(__file__).resolve().parent.parent
    case_path = repo_root / "matlab_script" / "Input_files" / "case3a_cover_leverage.m"
    if not case_path.is_file():
        return
    from kst_rating_tool.io_legacy import load_case_m_file

    cs = load_case_m_file(case_path)
    detailed = analyze_constraints_detailed(cs)
    if detailed.mot_half.shape[0] == 0:
        return
    combo_set = detailed.combo_proc[: min(3, detailed.combo_proc.shape[0]), 1:6].astype(int)
    mot_half = detailed.mot_half[: combo_set.shape[0], :]
    # case3a: CP indices 1..4, line 5..8, plane 9
    cp_set = np.array([5, 9], dtype=int)
    R = rate_motset(combo_set, mot_half, cp_set, cs, detailed.pts, detailed.max_d)
    assert R.shape == (2 * combo_set.shape[0], cp_set.size)
    assert np.isfinite(R).any() or np.isinf(R).any()


def test_run_wizard_optimization_script_smoke(tmp_path: Path):
    repo_root = Path(__file__).resolve().parent.parent
    script = repo_root / "scripts" / "run_wizard_optimization.py"
    in_json = repo_root / "matlab_script" / "Input_files" / "generic_example_optimization.json"
    if not script.is_file() or not in_json.is_file():
        return
    out_txt = tmp_path / "results_wizard_optim.txt"
    proc = subprocess.run(
        [sys.executable, str(script), str(in_json), str(out_txt)],
        capture_output=True,
        text=True,
        cwd=str(repo_root),
    )
    assert proc.returncode == 0, proc.stderr or proc.stdout
    text = out_txt.read_text(encoding="utf-8")
    assert "candidate\tWTR\tMRR\tMTR\tTOR" in text


def test_run_wizard_optimization_pin_candidate(tmp_path: Path):
    repo_root = Path(__file__).resolve().parent.parent
    script = repo_root / "scripts" / "run_wizard_optimization.py"
    if not script.is_file():
        return
    payload = {
        "analysis_input": {
            "version": 2,
            "point_contacts": [[0.0, 0.0, 0.0, 0.0, 0.0, 1.0]],
            "pins": [[0.0, 0.0, 0.0, 0.0, 0.0, 1.0]],
            "lines": [],
            "planes": [],
        },
        "optimization": {
            "candidate_matrix": [
                {
                    "constraint_type": "pin",
                    "constraint_index": 1,
                    "candidates": [
                        [0.0, 0.0, 0.0, 0.0, 0.0, 1.0],
                        [0.1, 0.0, 0.0, 0.0, 0.0, 1.0],
                    ],
                }
            ]
        },
    }
    in_json = tmp_path / "opt_pin.json"
    in_json.write_text(__import__("json").dumps(payload), encoding="utf-8")
    out_txt = tmp_path / "out_pin.txt"
    proc = subprocess.run(
        [sys.executable, str(script), str(in_json), str(out_txt)],
        capture_output=True,
        text=True,
        cwd=str(repo_root),
    )
    assert proc.returncode == 0, proc.stderr or proc.stdout
    assert "candidate\tWTR\tMRR\tMTR\tTOR" in out_txt.read_text(encoding="utf-8")


def test_run_wizard_optimization_plane_candidate(tmp_path: Path):
    repo_root = Path(__file__).resolve().parent.parent
    script = repo_root / "scripts" / "run_wizard_optimization.py"
    fixture = repo_root / "test_inputs" / "endcap_circular_plane.json"
    if not script.is_file() or not fixture.is_file():
        return
    import json

    data = json.loads(fixture.read_text(encoding="utf-8"))
    plane_row = data["planes"][0]
    alt = list(plane_row)
    alt[2] = float(alt[2]) + 0.01  # nudge midpoint z
    payload = {
        "analysis_input": data,
        "optimization": {
            "candidate_matrix": [
                {
                    "constraint_type": "plane",
                    "constraint_index": 1,
                    "candidates": [plane_row, alt],
                }
            ]
        },
    }
    in_json = tmp_path / "opt_plane.json"
    in_json.write_text(json.dumps(payload), encoding="utf-8")
    out_txt = tmp_path / "out_plane.txt"
    proc = subprocess.run(
        [sys.executable, str(script), str(in_json), str(out_txt)],
        capture_output=True,
        text=True,
        cwd=str(repo_root),
    )
    assert proc.returncode == 0, proc.stderr or proc.stdout
    assert "candidate\tWTR\tMRR\tMTR\tTOR" in out_txt.read_text(encoding="utf-8")
