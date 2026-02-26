#!/usr/bin/env python3
"""
KST Wizard Demo — Skeleton UI showing what the Inventor add-in will look like.
Updated to use shared UI components from kst_rating_tool.ui.
"""

import os
import shutil
import subprocess
import threading
import tkinter as tk
from tkinter import ttk, messagebox

# Import shared UI components
try:
    from kst_rating_tool.ui import AnalysisPanel, OptimizationPanel
except ImportError:
    import sys
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../src")))
    from kst_rating_tool.ui import AnalysisPanel, OptimizationPanel

# Repo root
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MATLAB_TOOL_DIR = os.path.join(_REPO_ROOT, "matlab_script", "Analysis and design tool")
OUTPUT_DIR = os.path.join(_REPO_ROOT, "results", "wizard")

def get_matlab_cmd():
    """Return [matlab_exe, '-batch'] for subprocess, or None if MATLAB not found."""
    for name in ("matlab", "matlab.exe"):
        exe = shutil.which(name)
        if exe:
            return [exe, "-batch"]
    return None

def run_matlab_headless(matlab_call, cwd, on_done):
    """
    Run MATLAB headless in a background thread. on_done(success, message) is
    invoked on the main thread when finished.
    """
    def run():
        cmd = get_matlab_cmd()
        if not cmd:
            on_done(False, "MATLAB not found on PATH. Install MATLAB or add it to PATH.")
            return
        if not os.path.isdir(cwd):
            on_done(False, f"MATLAB script directory not found: {cwd}")
            return
        try:
            # Path for MATLAB: use forward slashes and escape single quotes
            proc = subprocess.run(
                cmd + [matlab_call],
                cwd=cwd,
                capture_output=True,
                text=True,
                timeout=600,
            )
            if proc.returncode == 0:
                on_done(True, "MATLAB finished successfully.")
            else:
                err = (proc.stderr or proc.stdout or "").strip() or f"Exit code {proc.returncode}"
                on_done(False, f"MATLAB failed:\n{err[:500]}")
        except subprocess.TimeoutExpired:
            on_done(False, "MATLAB timed out (10 min).")
        except Exception as e:
            on_done(False, str(e))

    threading.Thread(target=run, daemon=True).start()


def main():
    root = tk.Tk()
    root.title("KST Wizard Demo — Preview of Inventor Add-in")
    root.minsize(700, 550)
    root.geometry("750x650")

    notebook = ttk.Notebook(root)

    # State sharing
    optim_panel = None

    def update_constraints(names):
        if optim_panel:
            optim_panel.update_constraints(names)

    def run_matlab_analysis_wrapper(input_path, on_done_callback):
        abs_path = os.path.abspath(input_path).replace("\\", "/").replace("'", "''")
        matlab_call = f"run_wizard_analysis('{abs_path}')"
        def inner_done(success, message):
            on_done_callback(success, message, None)
        run_matlab_headless(matlab_call, MATLAB_TOOL_DIR, inner_done)

    analysis_tab = AnalysisPanel(
        notebook,
        output_dir=OUTPUT_DIR,
        on_run_analysis=run_matlab_analysis_wrapper,
        on_constraints_updated=update_constraints
    )
    notebook.add(analysis_tab, text="Analysis Wizard")

    def run_matlab_optim_wrapper(input_path, on_done_callback):
        abs_path = os.path.abspath(input_path).replace("\\", "/").replace("'", "''")
        matlab_call = f"run_wizard_optimization('{abs_path}')"
        run_matlab_headless(matlab_call, MATLAB_TOOL_DIR, on_done_callback)

    optim_panel = OptimizationPanel(
        notebook,
        output_dir=OUTPUT_DIR,
        on_run_optimization=run_matlab_optim_wrapper
    )
    notebook.add(optim_panel, text="Optimization Wizard")

    notebook.pack(fill="both", expand=True, padx=10, pady=10)

    ttk.Label(root, text="This is a Python skeleton of the Inventor add-in. The real add-in runs inside Autodesk Inventor and reads geometry from the model.", font=("", 9), foreground="gray").pack(pady=(0, 10))

    root.mainloop()


if __name__ == "__main__":
    main()
