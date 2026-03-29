from __future__ import annotations

import json
from pathlib import Path

import pytest


def _build_panel(tmp_path: Path):
    tk = pytest.importorskip("tkinter")
    from kst_rating_tool.ui.optimization_ui import OptimizationPanel

    try:
        root = tk.Tk()
    except tk.TclError as exc:  # no display in headless environments
        pytest.skip(f"tkinter display is unavailable: {exc}")
    root.withdraw()
    panel = OptimizationPanel(root, output_dir=str(tmp_path), available_constraints=["C_point1"])
    return root, panel


def test_generate_plan_orient1d(tmp_path: Path):
    root, panel = _build_panel(tmp_path)
    try:
        analysis = {
            "version": 2,
            "point_contacts": [[0, 0, 4, 0, 0, -1]],
            "pins": [],
            "lines": [],
            "planes": [],
        }
        (tmp_path / "wizard_input.json").write_text(json.dumps(analysis), encoding="utf-8")
        panel.cp_var.set("C_point1")
        panel.notebook.select(2)  # Orient 1D tab
        panel.orient1_axis_var.set("1,0,0")
        panel.orient1_min_var.set("-10")
        panel.orient1_max_var.set("10")
        panel.steps_orient1_var.set("2")
        panel._add_optim_param()
        panel._generate_plan()
        payload = json.loads((tmp_path / "wizard_optimization.json").read_text(encoding="utf-8"))
        mod = payload["optimization"]["modified_constraints"][0]
        cmat = payload["optimization"]["candidate_matrix"][0]
        assert mod["search_space"]["type"] == "orient_1d"
        assert cmat["type"] == "point"
        assert len(cmat["candidates"]) == 3
        assert len(cmat["candidates"][0]) == 6
    finally:
        root.destroy()


def test_generate_plan_orient2d(tmp_path: Path):
    root, panel = _build_panel(tmp_path)
    try:
        analysis = {
            "version": 2,
            "point_contacts": [[0, 0, 4, 0, 0, -1]],
            "pins": [],
            "lines": [],
            "planes": [],
        }
        (tmp_path / "wizard_input.json").write_text(json.dumps(analysis), encoding="utf-8")
        panel.cp_var.set("C_point1")
        panel.notebook.select(3)  # Orient 2D tab
        panel.orient2_axis1_var.set("1,0,0")
        panel.orient2_axis2_var.set("0,1,0")
        panel.orient2_a1_min_var.set("-5")
        panel.orient2_a1_max_var.set("5")
        panel.orient2_a2_min_var.set("-5")
        panel.orient2_a2_max_var.set("5")
        panel.steps_orient2_var.set("1")
        panel._add_optim_param()
        panel._generate_plan()
        payload = json.loads((tmp_path / "wizard_optimization.json").read_text(encoding="utf-8"))
        mod = payload["optimization"]["modified_constraints"][0]
        cmat = payload["optimization"]["candidate_matrix"][0]
        assert mod["search_space"]["type"] == "orient_2d"
        assert cmat["type"] == "point"
        assert len(cmat["candidates"]) == 4  # (steps+1)^2
        assert len(cmat["candidates"][0]) == 6
    finally:
        root.destroy()
