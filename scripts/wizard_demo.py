#!/usr/bin/env python3
"""
KST Wizard Demo — Skeleton UI showing what the Inventor add-in will look like.

Run with:  python scripts/wizard_demo.py

Uses only the standard library (tkinter). Use this to show your supervisor
the Analysis Wizard and Optimization Wizard flow in a meeting.
"""

import json
import os
import tkinter as tk
from tkinter import ttk, messagebox, filedialog

# Output directory for demo files
OUTPUT_DIR = os.path.join(os.path.expanduser("~"), "KstAnalysis")


def ensure_output_dir():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    return OUTPUT_DIR


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

    def on_select_loc():
        # Demo: in Inventor this would start picking from the model
        messagebox.showinfo(
            "Select Location",
            "In the add-in: user picks a point or face in the CAD model;\n"
            "coordinates are read from the Inventor API.\n\n"
            "Demo: type coordinates in the table or use placeholder below.",
        )
        # Optional: fill placeholder
        sel = tree.selection()
        if sel:
            tree.set(sel[0], "location", "1.0, 2.0, 3.0")

    def on_select_orient():
        messagebox.showinfo(
            "Select Orientation",
            "In the add-in: user picks a face (normal) or edge (axis);\n"
            "orientation is read from the Inventor API.",
        )
        sel = tree.selection()
        if sel:
            tree.set(sel[0], "orientation", "0.0, 0.0, 1.0")

    def on_double_click(event):
        region = tree.identify("region", event.x, event.y)
        col = tree.identify_column(event.x)
        if region == "cell" and col:
            col_idx = int(col.replace("#", ""))
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
        if not point_contacts:
            point_contacts = [[0, 0, 0, 0, 0, 1]]  # placeholder
        data = {"version": 1, "point_contacts": point_contacts, "pins": [], "lines": [], "planes": []}
        out_dir = ensure_output_dir()
        path = os.path.join(out_dir, "wizard_input.json")
        with open(path, "w") as f:
            json.dump(data, f, indent=2)
        result_label.config(text=f"Input file written to:\n{path}\n\n(In add-in: MATLAB or compiled exe runs analysis and shows WTR, MTR, TOR.)")

    ttk.Button(btn_frame, text="Analyze", command=run_analyze).pack(side="left", padx=2)
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
        # Load analysis input if present
        analysis_path = os.path.join(ensure_output_dir(), "wizard_input.json")
        if os.path.exists(analysis_path):
            with open(analysis_path) as f:
                analysis_input = json.load(f)
        else:
            analysis_input = {"version": 1, "point_contacts": [[0, 0, 4, 0, 0, -1]], "pins": [], "lines": [], "planes": []}
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
        messagebox.showinfo(
            "Run optimization",
            "Run in MATLAB:\n  run_wizard_optimization('.../wizard_optimization.json')\n\n"
            "Results will be in results_wizard_optim.txt.\nThen click 'Load results'.",
        )

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
