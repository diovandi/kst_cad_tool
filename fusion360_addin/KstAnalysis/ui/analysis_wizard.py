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

# Output directory: same as C# add-in (Documents/KstAnalysis)
if sys.platform == "win32":
    _DOCS = os.path.join(os.environ.get("USERPROFILE", ""), "Documents")
else:
    _DOCS = os.path.expanduser("~/Documents")
OUTPUT_DIR = os.path.join(_DOCS, "KstAnalysis")


def _ensure_output_dir():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    return OUTPUT_DIR


def _parse_xyz(s):
    s = (s or "").strip()
    if not s:
        return ["0", "0", "0"]
    parts = [p.strip() for p in s.replace(",", " ").split()[:3]]
    while len(parts) < 3:
        parts.append("0")
    return parts[:3]


def _show_location_orientation_dialog(parent, current_location, current_orientation):
    loc_parts = _parse_xyz(current_location)
    orient_parts = _parse_xyz(current_orientation)
    result = [None, None]
    win = tk.Toplevel(parent)
    win.title("Location & Orientation")
    win.transient(parent)
    win.grab_set()
    try:
        default_bg = win.cget("bg")
    except tk.TclError:
        default_bg = "#d9d9d9"
    f = tk.Frame(win, padx=16, pady=16, bg=default_bg)
    f.pack(fill="both", expand=True)
    tk.Label(f, text="Location (x, y, z):", font=("", 10, "bold"), bg=default_bg).grid(row=0, column=0, columnspan=3, sticky="w", pady=(0, 4))
    loc_entries = []
    for i, (label, val) in enumerate(zip(["x", "y", "z"], loc_parts)):
        tk.Label(f, text=label + ":", bg=default_bg).grid(row=1, column=i, sticky="w", padx=(0, 4))
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
        result[0] = ", ".join(e.get().strip() or "0" for e in loc_entries)
        result[1] = ", ".join(e.get().strip() or "0" for e in orient_entries)
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


def _run_python_analysis(path, on_done):
    """Run kst_rating_tool.analyze_constraints on the input JSON; on_done(success, message)."""
    def run():
        try:
            from kst_rating_tool import analyze_constraints_detailed
            with open(path) as f:
                data = json.load(f)
            pc = data.get("point_contacts", [])
            if not pc:
                on_done(False, "No point_contacts in input.")
                return
            from kst_rating_tool import ConstraintSet, PointConstraint
            cs = ConstraintSet()
            for row in pc:
                if len(row) >= 6:
                    cs.add(PointConstraint([row[0], row[1], row[2]], [row[3], row[4], row[5]]))
            results = analyze_constraints_detailed(cs)
            out_path = os.path.join(OUTPUT_DIR, "results_wizard.txt")
            with open(out_path, "w") as f:
                f.write("WTR\tMRR\tMTR\tTOR\n")
                f.write("{}\t{}\t{}\t{}\n".format(
                    results.wtr, results.mrr, results.mtr, results.tor))
            on_done(True, "Results written to {}".format(out_path))
        except Exception as e:
            on_done(False, str(e))
    threading.Thread(target=run, daemon=True).start()


def run_analysis_wizard(initial_constraints=None):
    """Open the Analysis Wizard window. initial_constraints: list of (location_str, orientation_str)."""
    root = tk.Tk()
    root.title("KST Constraint Definition Wizard (Fusion 360)")
    root.minsize(700, 450)
    root.geometry("750x500")

    frame = ttk.Frame(root, padding=10)
    frame.pack(fill="both", expand=True)
    ttk.Label(frame, text="KST Constraint Definition Wizard", font=("", 12, "bold")).pack(anchor="w")
    ttk.Label(frame, text="Define constraints (from Fusion selection or manual entry), then Analyze.").pack(anchor="w")

    columns = ("type", "location", "orientation", "sel_loc", "sel_orient")
    tree = ttk.Treeview(frame, columns=columns, show="headings", height=6)
    tree.heading("type", text="Type")
    tree.heading("location", text="Location (x, y, z)")
    tree.heading("orientation", text="Orientation (nx, ny, nz)")
    tree.heading("sel_loc", text="Select Loc")
    tree.heading("sel_orient", text="Select Orient")
    for c in columns:
        tree.column(c, width=120)
    tree.pack(fill="x", pady=(10, 5))

    for pair in (initial_constraints or []):
        loc = pair[0] if isinstance(pair, (list, tuple)) else ""
        orient = pair[1] if isinstance(pair, (list, tuple)) and len(pair) > 1 else "0, 0, 1"
        tree.insert("", "end", values=("Point", loc, orient, "Select", "Select"))
    if not (initial_constraints and len(initial_constraints) > 0):
        tree.insert("", "end", values=("Point", "", "", "Select", "Select"))

    def add_row():
        tree.insert("", "end", values=("Point", "", "", "Select", "Select"))

    def remove_row():
        sel = tree.selection()
        if sel:
            tree.delete(sel)

    def on_double_click(event):
        item = tree.identify_row(event.y)
        col = tree.identify_column(event.x)
        if not item or not col:
            return
        tree.selection_set(item)
        try:
            col_idx = int(col.replace("#", ""))
        except ValueError:
            return
        if col_idx == 4:
            row_vals = list(tree.item(item, "values"))
            cur_loc = row_vals[1] if len(row_vals) > 1 else ""
            cur_orient = row_vals[2] if len(row_vals) > 2 else ""
            loc_str, orient_str = _show_location_orientation_dialog(root, cur_loc, cur_orient)
            if loc_str is not None and orient_str is not None:
                tree.set(item, "location", loc_str)
                tree.set(item, "orientation", orient_str)
        elif col_idx == 5:
            row_vals = list(tree.item(item, "values"))
            cur_loc = row_vals[1] if len(row_vals) > 1 else ""
            cur_orient = row_vals[2] if len(row_vals) > 2 else ""
            loc_str, orient_str = _show_location_orientation_dialog(root, cur_loc, cur_orient)
            if loc_str is not None and orient_str is not None:
                tree.set(item, "location", loc_str)
                tree.set(item, "orientation", orient_str)
    tree.bind("<Double-1>", on_double_click)

    result_label = ttk.Label(frame, text="Define constraints, then click Analyze.")
    btn_frame = ttk.Frame(frame)
    ttk.Button(btn_frame, text="Add constraint", command=add_row).pack(side="left", padx=2)
    ttk.Button(btn_frame, text="Remove selected", command=remove_row).pack(side="left", padx=2)

    def run_analyze():
        rows = []
        for item in tree.get_children():
            row = tree.item(item)["values"]
            if len(row) >= 5:
                rows.append({"type": row[0], "location": row[1], "orientation": row[2]})
        if not rows:
            result_label.config(text="Add at least one constraint.")
            return
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
        if len(point_contacts) < 2:
            point_contacts.extend([[0, 0, 0, 0, 0, 1], [0, 0, 1, 0, 0, 1]])
        data = {"version": 1, "point_contacts": point_contacts, "pins": [], "lines": [], "planes": []}
        _ensure_output_dir()
        path = os.path.join(OUTPUT_DIR, "wizard_input.json")
        with open(path, "w") as f:
            json.dump(data, f, indent=2)
        result_label.config(text="Input file written to:\n{}\n\nClick 'Run Python' to analyze.".format(path))

    def run_python_analysis():
        path = os.path.join(OUTPUT_DIR, "wizard_input.json")
        if not os.path.isfile(path):
            result_label.config(text="Write the input file first (click Analyze).")
            return
        result_label.config(text="Running Python analysis...")
        def when_done(success, message):
            def update():
                result_label.config(text=message)
            root.after(0, update)
        _run_python_analysis(path, when_done)

    ttk.Button(btn_frame, text="Analyze", command=run_analyze).pack(side="left", padx=2)
    ttk.Button(btn_frame, text="Run Python", command=run_python_analysis).pack(side="left", padx=2)
    btn_frame.pack(pady=5)
    result_label.pack(anchor="w", fill="x", pady=10)
    root.mainloop()


def run_optimization_wizard():
    """Open the Optimization Wizard window."""
    root = tk.Tk()
    root.title("KST Optimization Wizard (Fusion 360)")
    root.minsize(600, 450)
    root.geometry("650x480")

    frame = ttk.Frame(root, padding=10)
    frame.pack(fill="both", expand=True)
    ttk.Label(frame, text="KST Optimization Wizard", font=("", 12, "bold")).pack(anchor="w")
    ttk.Label(frame, text="Select constraint to optimize, search space; generate plan and run (Python or MATLAB).").pack(anchor="w")

    opts = ttk.Frame(frame)
    ttk.Label(opts, text="Constraint:").grid(row=0, column=0, sticky="w", padx=(0, 5))
    constraint_var = tk.StringVar(value="CP7")
    ttk.Combobox(opts, textvariable=constraint_var, values=[f"CP{i}" for i in range(1, 25)], state="readonly", width=8).grid(row=0, column=1, sticky="w", pady=2)
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

    status_label = ttk.Label(frame, text="Generate optimization plan, then run Python or MATLAB.")

    def generate_plan():
        try:
            steps = max(1, min(100, int(steps_var.get())))
        except ValueError:
            steps = 5
        try:
            constraint_index = int(constraint_var.get().replace("CP", ""))
        except ValueError:
            constraint_index = 7
        analysis_path = os.path.join(OUTPUT_DIR, "wizard_input.json")
        if os.path.exists(analysis_path):
            with open(analysis_path) as f:
                analysis_input = json.load(f)
        else:
            analysis_input = {"version": 1, "point_contacts": [], "pins": [], "lines": [], "planes": []}
        pc = list(analysis_input.get("point_contacts", []))
        if len(pc) < 2:
            analysis_input = dict(analysis_input)
            analysis_input["point_contacts"] = pc + [[0, 0, 4, 0, 0, -1], [0, 0, 5, 0, 0, -1]][: 2 - len(pc)]
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
            candidates.append([o[0] + t*d[0], o[1] + t*d[1], o[2] + t*d[2], 0, 0, -1])
        optim = {
            "version": 1,
            "analysis_input": analysis_input,
            "optimization": {
                "modified_constraints": [{"type": "point", "index": constraint_index, "search_space": {"type": "line", "num_steps": steps}}],
                "candidate_matrix": [{"constraint_index": constraint_index, "candidates": candidates}],
            },
        }
        _ensure_output_dir()
        out_path = os.path.join(OUTPUT_DIR, "wizard_optimization.json")
        with open(out_path, "w") as f:
            json.dump(optim, f, indent=2)
        status_label.config(text="Optimization plan written to:\n{}".format(out_path))

    results_frame = ttk.Frame(frame)
    res_columns = ("candidate", "WTR", "MTR", "TOR")
    res_tree = ttk.Treeview(results_frame, columns=res_columns, show="headings", height=6)
    for c in res_columns:
        res_tree.heading(c, text=c)
        res_tree.column(c, width=80)
    res_tree.pack(fill="both", expand=True)

    def load_results():
        path = os.path.join(OUTPUT_DIR, "results_wizard_optim.txt")
        if not os.path.exists(path):
            status_label.config(text="No results file. Run optimization first.")
            return
        for row in res_tree.get_children():
            res_tree.delete(row)
        with open(path) as f:
            lines = f.readlines()
        for line in lines[1:]:
            parts = line.strip().split("\t")
            if len(parts) >= 4:
                res_tree.insert("", "end", values=(parts[0], parts[1], parts[2], parts[3]))
        status_label.config(text="Loaded {} result(s).".format(len(res_tree.get_children())))

    btn_row = ttk.Frame(frame)
    ttk.Button(btn_row, text="Generate optimization plan", command=generate_plan).pack(side="left", padx=2)
    ttk.Button(btn_row, text="Load results", command=load_results).pack(side="left", padx=2)
    btn_row.pack(pady=5)
    results_frame.pack(fill="both", expand=True, pady=5)
    status_label.pack(anchor="w", fill="x")
    root.mainloop()


if __name__ == "__main__":
    run_analysis_wizard()
