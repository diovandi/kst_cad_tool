from __future__ import annotations

from pathlib import Path
import subprocess
import sys
import json

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


def test_run_wizard_optimization_supports_pin_candidate(tmp_path: Path):
    repo_root = Path(__file__).resolve().parent.parent
    script = repo_root / "scripts" / "run_wizard_optimization.py"
    if not script.is_file():
        return
    payload = {
        "version": 1,
        "analysis_input": {
            "version": 2,
            "point_contacts": [
                [0, 0, 0, 0, 0, 1],
                [20, 0, 0, 0, 0, 1],
                [0, 20, 0, 0, 0, 1],
            ],
            "pins": [[5, 5, 0, 0, 1, 0]],
            "lines": [],
            "planes": [],
        },
        "optimization": {
            "modified_constraints": [{"type": "pin", "index": 1, "search_space": {"type": "line", "num_steps": 1}}],
            "candidate_matrix": [
                {
                    "type": "pin",
                    "index": 1,
                    "constraint_index": 4,
                    "candidates": [
                        [5, 5, 0, 0, 1, 0],
                        [6, 5, 0, 0, 1, 0],
                    ],
                }
            ],
        },
    }
    in_json = tmp_path / "optim_pin.json"
    out_txt = tmp_path / "results_wizard_optim_pin.txt"
    in_json.write_text(json.dumps(payload), encoding="utf-8")
    proc = subprocess.run(
        [sys.executable, str(script), str(in_json), str(out_txt)],
        capture_output=True,
        text=True,
        cwd=str(repo_root),
    )
    assert proc.returncode == 0, proc.stderr or proc.stdout
    lines = out_txt.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) >= 3  # header + 2 candidates


def test_run_wizard_optimization_supports_mixed_candidate_product(tmp_path: Path):
    repo_root = Path(__file__).resolve().parent.parent
    script = repo_root / "scripts" / "run_wizard_optimization.py"
    if not script.is_file():
        return
    payload = {
        "version": 1,
        "analysis_input": {
            "version": 2,
            "point_contacts": [
                [0, 0, 0, 0, 0, 1],
                [20, 0, 0, 0, 0, 1],
                [0, 20, 0, 0, 0, 1],
            ],
            "pins": [[5, 5, 0, 0, 1, 0]],
            "lines": [],
            "planes": [],
        },
        "optimization": {
            "modified_constraints": [
                {"type": "point", "index": 1, "search_space": {"type": "discrete", "num_steps": 1}},
                {"type": "pin", "index": 1, "search_space": {"type": "discrete", "num_steps": 1}},
            ],
            "candidate_matrix": [
                {"type": "point", "index": 1, "constraint_index": 1, "candidates": [[0, 0, 0, 0, 0, 1], [1, 0, 0, 0, 0, 1]]},
                {"type": "pin", "index": 1, "constraint_index": 4, "candidates": [[5, 5, 0, 0, 1, 0], [6, 5, 0, 0, 1, 0]]},
            ],
        },
    }
    in_json = tmp_path / "optim_mixed.json"
    out_txt = tmp_path / "results_wizard_optim_mixed.txt"
    in_json.write_text(json.dumps(payload), encoding="utf-8")
    proc = subprocess.run(
        [sys.executable, str(script), str(in_json), str(out_txt)],
        capture_output=True,
        text=True,
        cwd=str(repo_root),
    )
    assert proc.returncode == 0, proc.stderr or proc.stdout
    lines = out_txt.read_text(encoding="utf-8").strip().splitlines()
    # 2x2 Cartesian product + header
    assert len(lines) >= 5


def test_run_wizard_optimization_supports_hoc_line_and_plane_candidates(tmp_path: Path):
    repo_root = Path(__file__).resolve().parent.parent
    script = repo_root / "scripts" / "run_wizard_optimization.py"
    if not script.is_file():
        return
    payload = {
        "version": 1,
        "analysis_input": {
            "version": 2,
            "point_contacts": [
                [0, 0, 0, 0, 0, 1],
                [20, 0, 0, 0, 0, 1],
                [0, 20, 0, 0, 0, 1],
            ],
            "pins": [],
            "lines": [[10, 10, 0, 1, 0, 0, 0, 0, 1, 12]],
            "planes": [[0, 0, -5, 0, 0, 1, 2, 10]],
        },
        "optimization": {
            "modified_constraints": [
                {"type": "line", "index": 1, "search_space": {"type": "discrete", "num_steps": 1}},
                {"type": "plane", "index": 1, "search_space": {"type": "discrete", "num_steps": 1}},
            ],
            "candidate_matrix": [
                {
                    "type": "line",
                    "index": 1,
                    "constraint_index": 4,
                    "candidates": [
                        [10, 10, 0, 1, 0, 0, 0, 0, 1, 12],
                        [12, 10, 0, 1, 0, 0, 0, 0, 1, 12],
                    ],
                },
                {
                    "type": "plane",
                    "index": 1,
                    "constraint_index": 5,
                    "candidates": [
                        [0, 0, -5, 0, 0, 1, 2, 10],
                        [0, 0, -6, 0, 0, 1, 2, 10],
                    ],
                },
            ],
        },
    }
    in_json = tmp_path / "optim_hoc_mixed.json"
    out_txt = tmp_path / "results_wizard_optim_hoc.txt"
    in_json.write_text(json.dumps(payload), encoding="utf-8")
    proc = subprocess.run(
        [sys.executable, str(script), str(in_json), str(out_txt)],
        capture_output=True,
        text=True,
        cwd=str(repo_root),
    )
    assert proc.returncode == 0, proc.stderr or proc.stdout
    lines = out_txt.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) >= 5  # header + 2x2 candidates
