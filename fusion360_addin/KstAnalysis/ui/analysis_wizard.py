"""
KST Analysis and Optimization Wizard UI for Fusion 360.
Tkinter-based; can be launched from Fusion 360 add-in or standalone.
Supports initial_constraints from Fusion selection (list of (location_str, orientation_str)).
"""

import json
import os
import sys
import threading
import tkinter as tk
from tkinter import ttk, messagebox

# Import shared UI components
try:
    from kst_rating_tool.ui import AnalysisPanel, OptimizationPanel
except ImportError:
    # If running from repo root without install, try adding src to path
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../src")))
    from kst_rating_tool.ui import AnalysisPanel, OptimizationPanel

# Output directory: same as C# add-in (Documents/KstAnalysis)
if sys.platform == "win32":
    _DOCS = os.path.join(os.environ.get("USERPROFILE", ""), "Documents")
else:
    _DOCS = os.path.expanduser("~/Documents")
OUTPUT_DIR = os.path.join(_DOCS, "KstAnalysis")

# CP names from the Analysis Tool constraint table; Optimization Tool uses this for its CP dropdown.
_shared_constraints = []


def _run_python_analysis(path, on_done):
    """Run kst_rating_tool.analyze_constraints_detailed on the input JSON.
    on_done(success, message, result=None) with result = DetailedAnalysisResult when success.
    """
    def run():
        try:
            try:
                import numpy as np
                from kst_rating_tool import analyze_constraints_detailed
                from kst_rating_tool import ConstraintSet, PointConstraint
            except ImportError as e:
                on_done(False, "kst_rating_tool not found. Run from repo or add repo/src to Python path: {}".format(e), None)
                return
            with open(path) as f:
                data = json.load(f)
            pc = data.get("point_contacts", [])
            if not pc:
                on_done(False, "No point_contacts in input.", None)
                return
            cs = ConstraintSet()
            for row in pc:
                if len(row) >= 6:
                    pos = np.array([float(row[0]), float(row[1]), float(row[2])], dtype=float)
                    nrm = np.array([float(row[3]), float(row[4]), float(row[5])], dtype=float)
                    cs.points.append(PointConstraint(pos, nrm))
            result = analyze_constraints_detailed(cs)
            out_path = os.path.join(OUTPUT_DIR, "results_wizard.txt")
            with open(out_path, "w") as f:
                f.write("WTR\tMRR\tMTR\tTOR\n")
                f.write("{}\t{}\t{}\t{}\n".format(
                    result.rating.WTR, result.rating.MRR, result.rating.MTR, result.rating.TOR))
            on_done(True, "Results written to {}".format(out_path), result)
        except Exception as e:
            on_done(False, str(e), None)
    threading.Thread(target=run, daemon=True).start()


def run_analysis_wizard(initial_constraints=None, on_constraint_added=None, on_results=None, on_select_line=None):
    """Open the Analysis Tool window.
    initial_constraints: list of (location_str, orientation_str).
    on_constraint_added: optional callback(constraint_list) for Fusion viewport drawing.
    on_results: optional callback(DetailedAnalysisResult) after Run Analysis.
    on_select_line: optional callback() -> (origin_str, direction_str) for Line type (2-vertex pick in Fusion).
    """
    global _shared_constraints
    root = tk.Tk()
    root.title("KST Analysis Tool")
    root.minsize(720, 520)
    root.geometry("760x560")

    def update_shared_constraints(names):
        _shared_constraints[:] = names

    panel = AnalysisPanel(
        root,
        output_dir=OUTPUT_DIR,
        initial_constraints=initial_constraints,
        on_constraint_added=on_constraint_added,
        on_run_analysis=_run_python_analysis,
        on_select_line=on_select_line,
        on_results=on_results,
        on_constraints_updated=update_shared_constraints
    )
    panel.pack(fill="both", expand=True)

    root.mainloop()


def run_optimization_wizard():
    """Open the Optimization Tool window. CP dropdown uses _shared_constraints from Analysis Tool."""
    main = tk.Tk()
    main.title("KST Optimization Tool")
    main.minsize(680, 520)
    main.geometry("720x560")

    panel = OptimizationPanel(
        main,
        output_dir=OUTPUT_DIR,
        available_constraints=_shared_constraints
    )
    panel.pack(fill="both", expand=True)

    main.mainloop()


if __name__ == "__main__":
    run_analysis_wizard()
