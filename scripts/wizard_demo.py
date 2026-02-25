#!/usr/bin/env python3
"""
KST Wizard Demo — Skeleton UI showing what the Inventor add-in will look like.

Run with:  python scripts/wizard_demo.py

Uses only the standard library (tkinter). Use this to show your supervisor
the Analysis Wizard and Optimization Wizard flow in a meeting.
"""

import json
import os
import shutil
import subprocess
import threading
import tkinter as tk
from tkinter import ttk, messagebox, filedialog

# Repo root (script lives in scripts/)
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MATLAB_TOOL_DIR = os.path.join(_REPO_ROOT, "matlab_script", "Analysis and design tool")

# Output directory for demo files
OUTPUT_DIR = os.path.join(os.path.expanduser("~"), "KstAnalysis")


def ensure_output_dir():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    return OUTPUT_DIR


def _parse_xyz(s):
    """Parse 'x, y, z' or 'x y z' into three floats; return ['0','0','0'] for empty/invalid."""
    s = (s or "").strip()
    if not s:
        return ["0", "0", "0"]
    parts = [p.strip() for p in s.replace(",", " ").split()[:3]]
    while len(parts) < 3:
        parts.append("0")
    return parts[:3]


def show_location_orientation_dialog(parent, current_location, current_orientation):
    """
    Show a dialog to enter Location (x,y,z) and Orientation (nx,ny,nz).
    Returns (location_str, orientation_str) on OK, or (None, None) on Cancel.
    Uses plain tk widgets so content is visible on all platforms (ttk can be blank in Toplevel).
    """
    loc_parts = _parse_xyz(current_location)
    orient_parts = _parse_xyz(current_orientation)
    result = [None, None]

    win = tk.Toplevel(parent)
    win.title("Location & Orientation")
    win.transient(parent)
    win.grab_set()
    # Use plain tk widgets so content reliably shows (ttk can render blank in Toplevel on some Linux)
    try:
        default_bg = win.cget("bg")
    except tk.TclError:
        default_bg = "#d9d9d9"
    f = tk.Frame(win, padx=16, pady=16, bg=default_bg)
    f.pack(fill="both", expand=True)

    tk.Label(f, text="Location (x, y, z):", font=("", 10, "bold"), bg=default_bg).grid(row=0, column=0, columnspan=3, sticky="w", pady=(0, 4))
    loc_entries = []
    for i, (label, val) in enumerate(zip(["x", "y", "z"], loc_parts)):
        tk.Label(f, text=label + ":", bg=f["bg"]).grid(row=1, column=i, sticky="w", padx=(0, 4))
        e = tk.Entry(f, width=14)
        e.insert(0, val)
        e.grid(row=2, column=i, sticky="ew", padx=(0, 8))
        loc_entries.append(e)
    tk.Label(f, text="Orientation (nx, ny, nz):", font=("", 10, "bold"), bg=default_bg).grid(row=3, column=0, columnspan=3, sticky="w", pady=(12, 4))
    orient_entries = []
    for i, (label, val) in enumerate(zip(["nx", "ny", "nz"], orient_parts)):
        tk.Label(f, text=label + ":", bg=default_bg).grid(row=4, column=i, sticky="w", padx=(0, 4))
        e = tk.Entry(f, width=14)
        e.insert(0, val)
        e.grid(row=5, column=i, sticky="ew", padx=(0, 8))
        orient_entries.append(e)

    def on_ok():
        loc_str = ", ".join(e.get().strip() or "0" for e in loc_entries)
        orient_str = ", ".join(e.get().strip() or "0" for e in orient_entries)
        result[0], result[1] = loc_str, orient_str
        win.destroy()

    def on_cancel():
        win.destroy()

    btn_f = tk.Frame(f, bg=default_bg)
    btn_f.grid(row=6, column=0, columnspan=3, pady=(16, 0))
    tk.Button(btn_f, text="OK", command=on_ok, width=8).pack(side="left", padx=4)
    tk.Button(btn_f, text="Cancel", command=on_cancel, width=8).pack(side="left", padx=4)

    f.columnconfigure(0, weight=1)
    f.columnconfigure(1, weight=1)
    f.columnconfigure(2, weight=1)
    win.geometry("340x240")
    win.resizable(True, False)
    win.update_idletasks()
    win.lift()
    win.focus_force()
    win.wait_window()
    return (result[0], result[1])


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


# --- Analysis Wizard tab ---


def build_analysis_tab(parent):
    frame = ttk.Frame(parent, padding=10)

    # Title
    ttk.Label(frame, text="KST Constraint Definition Wizard", font=("", 12, "bold")).pack(anchor="w")
    ttk.Label(frame, text="(In Inventor: constraints are picked from the CAD model.)").pack(anchor="w")

    # Table: Type | Location | Orientation | Select Loc | Select Orient
    columns = ("type", "location", "orientation", "sel_loc", "sel_orient")
    tree = ttk.Treeview(frame, columns=columns, show="headings", height=5)
    tree.heading("type", text="Type")
    tree.heading("location", text="Location (x, y, z)")
    tree.heading("orientation", text="Orientation (nx, ny, nz)")
    tree.heading("sel_loc", text="Select Loc")
    tree.heading("sel_orient", text="Select Orient")
    tree.column("type", width=80)
    tree.column("location", width=180)
    tree.column("orientation", width=180)
    tree.column("sel_loc", width=80)
    tree.column("sel_orient", width=80)
    tree.pack(fill="x", pady=(10, 5))

    def add_row():
        tree.insert("", "end", values=("Point", "", "", "Select", "Select"))

    def remove_row():
        sel = tree.selection()
        if sel:
            tree.delete(sel)

    def open_location_orientation_dialog(initial_focus="location"):
        """Open the Location & Orientation dialog for the selected row; update row on OK."""
        sel = tree.selection()
        if not sel:
            children = tree.get_children()
            if children:
                tree.selection_set(children[0])
                sel = tree.selection()
        if not sel:
            messagebox.showinfo("No row", "Add a constraint row first, then double-click Select Loc or Select Orient.")
            return
        item = sel[0]
        row_vals = list(tree.item(item, "values"))
        if len(row_vals) < 5:
            row_vals.extend([""] * (5 - len(row_vals)))
        cur_loc = row_vals[1] if len(row_vals) > 1 else ""
        cur_orient = row_vals[2] if len(row_vals) > 2 else ""
        loc_str, orient_str = show_location_orientation_dialog(frame.winfo_toplevel(), cur_loc, cur_orient)
        if loc_str is not None and orient_str is not None:
            tree.set(item, "location", loc_str)
            tree.set(item, "orientation", orient_str)

    def on_select_loc():
        open_location_orientation_dialog(initial_focus="location")

    def on_select_orient():
        open_location_orientation_dialog(initial_focus="orientation")

    def on_double_click(event):
        item = tree.identify_row(event.y)
        col = tree.identify_column(event.x)
        if not item or not col:
            return
        # Ensure the clicked row is selected so on_select_* can update it
        tree.selection_set(item)
        try:
            col_idx = int(col.replace("#", ""))
        except ValueError:
            return
        if col_idx == 4:
            on_select_loc()
        elif col_idx == 5:
            on_select_orient()

    tree.bind("<Double-1>", on_double_click)

    btn_frame = ttk.Frame(frame)
    ttk.Button(btn_frame, text="Add constraint", command=add_row).pack(side="left", padx=2)
    ttk.Button(btn_frame, text="Remove selected", command=remove_row).pack(side="left", padx=2)

    result_label = ttk.Label(frame, text="Define constraints, then click Analyze.")

    def run_analyze():
        rows = []
        for item in tree.get_children():
            row = tree.item(item)["values"]
            if len(row) >= 5:
                rows.append({"type": row[0], "location": row[1], "orientation": row[2]})
        if not rows:
            result_label.config(text="Add at least one constraint.")
            return
        # Build minimal JSON (point_contacts from location, orientation)
        point_contacts = []
        for r in rows:
            loc = r.get("location", "").strip()
            orient = r.get("orientation", "").strip()
            if loc and orient:
                try:
                    loc_vals = [float(x.strip()) for x in loc.replace(",", " ").split()[:3]]
                    orient_vals = [float(x.strip()) for x in orient.replace(",", " ").split()[:3]]
                    if len(loc_vals) == 3 and len(orient_vals) == 3:
                        point_contacts.append(loc_vals + orient_vals)
                except ValueError:
                    pass
        # MATLAB cp_to_wrench needs at least 2 points for nchoosek(...,2)
        if len(point_contacts) < 2:
            point_contacts = [
                [0, 0, 0, 0, 0, 1],
                [0, 0, 1, 0, 0, 1],
            ]  # two placeholders
        data = {"version": 1, "point_contacts": point_contacts, "pins": [], "lines": [], "planes": []}
        out_dir = ensure_output_dir()
        path = os.path.join(out_dir, "wizard_input.json")
        with open(path, "w") as f:
            json.dump(data, f, indent=2)
        result_label.config(text=f"Input file written to:\n{path}\n\nClick 'Run MATLAB' to run analysis headless, or run manually in MATLAB.")

    def run_matlab_analysis():
        path = os.path.join(ensure_output_dir(), "wizard_input.json")
        if not os.path.isfile(path):
            result_label.config(text="Write the input file first (click Analyze).")
            return
        abs_path = os.path.abspath(path).replace("\\", "/").replace("'", "''")
        matlab_call = f"run_wizard_analysis('{abs_path}')"
        root = frame.winfo_toplevel()
        result_label.config(text="Running MATLAB (headless)...")
        def when_done(success, message):
            def update():
                if success:
                    out_path = os.path.join(OUTPUT_DIR, "results_wizard.txt")
                    result_label.config(text=f"Analysis done.\nResults: {out_path}\n\n{message}")
                else:
                    result_label.config(text=f"Analysis failed.\n\n{message}")
            root.after(0, update)
        run_matlab_headless(matlab_call, MATLAB_TOOL_DIR, when_done)

    ttk.Button(btn_frame, text="Analyze", command=run_analyze).pack(side="left", padx=2)
    ttk.Button(btn_frame, text="Run MATLAB", command=run_matlab_analysis).pack(side="left", padx=2)
    btn_frame.pack(pady=5)
    result_label.pack(anchor="w", fill="x", pady=10)

    add_row()
    return frame


# --- Optimization Wizard tab ---


def build_optimization_tab(parent):
    frame = ttk.Frame(parent, padding=10)

    ttk.Label(frame, text="KST Optimization Wizard", font=("", 12, "bold")).pack(anchor="w")
    ttk.Label(frame, text="Select constraint to optimize and search space; generate plan and run (MATLAB).").pack(anchor="w")

    opts = ttk.Frame(frame)
    ttk.Label(opts, text="Constraint:").grid(row=0, column=0, sticky="w", padx=(0, 5))
    constraint_var = tk.StringVar(value="CP7")
    constraint_combo = ttk.Combobox(opts, textvariable=constraint_var, values=[f"CP{i}" for i in range(1, 25)], state="readonly", width=8)
    constraint_combo.grid(row=0, column=1, sticky="w", pady=2)
    ttk.Label(opts, text="Search space:").grid(row=1, column=0, sticky="w", padx=(0, 5))
    search_var = tk.StringVar(value="Line")
    ttk.Combobox(opts, textvariable=search_var, values=["Line", "Discrete", "Orient 1D", "Orient 2D"], state="readonly", width=12).grid(row=1, column=1, sticky="w", pady=2)
    ttk.Label(opts, text="Steps:").grid(row=2, column=0, sticky="w", padx=(0, 5))
    steps_var = tk.StringVar(value="5")
    ttk.Entry(opts, textvariable=steps_var, width=6).grid(row=2, column=1, sticky="w", pady=2)
    ttk.Label(opts, text="Line origin (x,y,z):").grid(row=3, column=0, sticky="w", padx=(0, 5))
    origin_var = tk.StringVar(value="0, 0, 4")
    ttk.Entry(opts, textvariable=origin_var, width=20).grid(row=3, column=1, sticky="w", pady=2)
    ttk.Label(opts, text="Line direction (x,y,z):").grid(row=4, column=0, sticky="w", padx=(0, 5))
    direction_var = tk.StringVar(value="0, 0, 1")
    ttk.Entry(opts, textvariable=direction_var, width=20).grid(row=4, column=1, sticky="w", pady=2)
    opts.pack(anchor="w", pady=10)

    status_label = ttk.Label(frame, text="Generate optimization plan, then run MATLAB run_wizard_optimization.m.")

    def generate_plan():
        try:
            steps = max(1, min(100, int(steps_var.get())))
        except ValueError:
            steps = 5
        cp_num = constraint_var.get().replace("CP", "")
        try:
            constraint_index = int(cp_num)
        except ValueError:
            constraint_index = 7
        # Load analysis input if present (MATLAB needs at least 2 point_contacts for nchoosek)
        analysis_path = os.path.join(ensure_output_dir(), "wizard_input.json")
        if os.path.exists(analysis_path):
            with open(analysis_path) as f:
                analysis_input = json.load(f)
        else:
            analysis_input = {"version": 1, "point_contacts": [], "pins": [], "lines": [], "planes": []}
        pc = list(analysis_input.get("point_contacts", []))
        if len(pc) < 2:
            analysis_input = dict(analysis_input)
            placeholders = [[0, 0, 4, 0, 0, -1], [0, 0, 5, 0, 0, -1]]
            analysis_input["point_contacts"] = pc + placeholders[: 2 - len(pc)]
        try:
            o = [float(x.strip()) for x in origin_var.get().split(",")[:3]]
            d = [float(x.strip()) for x in direction_var.get().split(",")[:3]]
        except ValueError:
            o, d = [0, 0, 4], [0, 0, 1]
        n = (d[0]**2 + d[1]**2 + d[2]**2) ** 0.5
        if n > 1e-10:
            d = [d[0]/n, d[1]/n, d[2]/n]
        candidates = []
        for k in range(steps + 1):
            t = k / steps
            pt = [o[0] + t*d[0], o[1] + t*d[1], o[2] + t*d[2], 0, 0, -1]
            candidates.append(pt)
        optim = {
            "version": 1,
            "analysis_input": analysis_input,
            "optimization": {
                "modified_constraints": [{"type": "point", "index": constraint_index, "search_space": {"type": "line", "num_steps": steps}}],
                "candidate_matrix": [{"constraint_index": constraint_index, "candidates": candidates}],
            },
        }
        out_path = os.path.join(ensure_output_dir(), "wizard_optimization.json")
        with open(out_path, "w") as f:
            json.dump(optim, f, indent=2)
        status_label.config(text=f"Optimization plan written to:\n{out_path}")

    def run_optim():
        out_path = os.path.join(ensure_output_dir(), "wizard_optimization.json")
        if not os.path.isfile(out_path):
            status_label.config(text="Generate optimization plan first.")
            return
        abs_path = os.path.abspath(out_path).replace("\\", "/").replace("'", "''")
        matlab_call = f"run_wizard_optimization('{abs_path}')"
        root = frame.winfo_toplevel()
        status_label.config(text="Running MATLAB (headless)...")
        def when_done(success, message):
            def update():
                if success:
                    load_results()
                    status_label.config(text=f"Optimization done. Results loaded.\n\n{message}")
                else:
                    status_label.config(text=f"Optimization failed.\n\n{message}")
            root.after(0, update)
        run_matlab_headless(matlab_call, MATLAB_TOOL_DIR, when_done)

    results_frame = ttk.Frame(frame)
    res_columns = ("candidate", "WTR", "MTR", "TOR")
    res_tree = ttk.Treeview(results_frame, columns=res_columns, show="headings", height=6)
    for c in res_columns:
        res_tree.heading(c, text=c)
        res_tree.column(c, width=80)
    res_tree.pack(fill="both", expand=True)

    def load_results():
        path = os.path.join(ensure_output_dir(), "results_wizard_optim.txt")
        if not os.path.exists(path):
            status_label.config(text="No results file. Run MATLAB run_wizard_optimization.m first.")
            return
        for row in res_tree.get_children():
            res_tree.delete(row)
        with open(path) as f:
            lines = f.readlines()
        for i, line in enumerate(lines[1:], 1):
            parts = line.strip().split("\t")
            if len(parts) >= 4:
                res_tree.insert("", "end", values=(parts[0], parts[1], parts[2], parts[3]))
        status_label.config(text=f"Loaded {len(res_tree.get_children())} result(s) from results_wizard_optim.txt.")

    btn_row = ttk.Frame(frame)
    ttk.Button(btn_row, text="Generate optimization plan", command=generate_plan).pack(side="left", padx=2)
    ttk.Button(btn_row, text="Run optimization", command=run_optim).pack(side="left", padx=2)
    ttk.Button(btn_row, text="Load results", command=load_results).pack(side="left", padx=2)
    btn_row.pack(pady=5)
    results_frame.pack(fill="both", expand=True, pady=5)
    status_label.pack(anchor="w", fill="x")

    return frame


# --- Main window ---


def main():
    root = tk.Tk()
    root.title("KST Wizard Demo — Preview of Inventor Add-in")
    root.minsize(700, 550)
    root.geometry("750x580")

    notebook = ttk.Notebook(root)
    analysis_tab = build_analysis_tab(notebook)
    notebook.add(analysis_tab, text="Analysis Wizard")
    optim_tab = build_optimization_tab(notebook)
    notebook.add(optim_tab, text="Optimization Wizard")
    notebook.pack(fill="both", expand=True, padx=10, pady=10)

    ttk.Label(root, text="This is a Python skeleton of the Inventor add-in. The real add-in runs inside Autodesk Inventor and reads geometry from the model.", font=("", 9), foreground="gray").pack(pady=(0, 10))

    root.mainloop()


if __name__ == "__main__":
    main()
