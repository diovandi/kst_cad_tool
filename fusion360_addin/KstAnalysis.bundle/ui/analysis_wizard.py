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

# CP names from the Analysis Tool constraint table; Optimization Tool uses this for its CP dropdown.
_shared_constraints = []


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

    main = ttk.Frame(root, padding=10)
    main.pack(fill="both", expand=True)

    ttk.Label(main, text="KST Analysis Tool", font=("", 12, "bold")).pack(anchor="w")
    ttk.Label(main, text="Define constraints (CP name, type, location, orientation), then Prepare Input File and Run Analysis.").pack(anchor="w")

    # --- Form ---
    form = ttk.LabelFrame(main, text="Form", padding=6)
    form.pack(fill="x", pady=(8, 4))
    row0 = ttk.Frame(form)
    row0.pack(fill="x")
    ttk.Label(row0, text="CP Name:").pack(side="left", padx=(0, 6))
    cp_name_var = tk.StringVar(value="")
    ttk.Entry(row0, textvariable=cp_name_var, width=20).pack(side="left", padx=(0, 16))
    ttk.Label(row0, text="Type:").pack(side="left", padx=(0, 6))
    type_var = tk.StringVar(value="Point")
    type_combo = ttk.Combobox(row0, textvariable=type_var, values=["Point", "Pin", "Line", "Plane"], state="readonly", width=8)
    type_combo.pack(side="left", padx=(0, 8))

    point_pin_frame = ttk.Frame(form)
    point_pin_frame.pack(fill="x", pady=(6, 0))
    ttk.Label(point_pin_frame, text="Location (x,y,z):").grid(row=0, column=0, sticky="w", padx=(0, 4), pady=2)
    loc_var = tk.StringVar(value="")
    ttk.Entry(point_pin_frame, textvariable=loc_var, width=24).grid(row=0, column=1, sticky="w", padx=(0, 4))
    def on_select_loc():
        if (type_var.get() or "").strip() == "Line" and on_select_line:
            try:
                result = on_select_line()
                if result and len(result) >= 2 and result[0] is not None and result[1] is not None:
                    loc_var.set(result[0])
                    orient_var.set(result[1])
                    return
            except Exception:
                pass
        loc_str, orient_str = _show_location_orientation_dialog(root, loc_var.get(), orient_var.get())
        if loc_str is not None:
            loc_var.set(loc_str)
        if orient_str is not None:
            orient_var.set(orient_str)
    ttk.Button(point_pin_frame, text="Select", command=on_select_loc).grid(row=0, column=2, padx=2)
    ttk.Label(point_pin_frame, text="Orientation (nx,ny,nz):").grid(row=1, column=0, sticky="w", padx=(0, 4), pady=2)
    orient_var = tk.StringVar(value="")
    ttk.Entry(point_pin_frame, textvariable=orient_var, width=24).grid(row=1, column=1, sticky="w", padx=(0, 4))
    def on_select_orient():
        loc_str, orient_str = _show_location_orientation_dialog(root, loc_var.get(), orient_var.get())
        if loc_str is not None:
            loc_var.set(loc_str)
        if orient_str is not None:
            orient_var.set(orient_str)
    ttk.Button(point_pin_frame, text="Set", command=on_select_orient).grid(row=1, column=2, padx=2)

    btn_form = ttk.Frame(form)
    btn_form.pack(fill="x", pady=(6, 0))
    def clear_form():
        cp_name_var.set("")
        type_var.set("Point")
        loc_var.set("")
        orient_var.set("")
    ttk.Button(btn_form, text="Add Constraint", command=lambda: None).pack(side="left", padx=(0, 8))
    ttk.Button(btn_form, text="Clear Form", command=clear_form).pack(side="left")

    # --- Constraint table ---
    table_frame = ttk.Frame(main)
    table_frame.pack(fill="both", expand=True, pady=(8, 4))
    col_names = ("#", "cp_name", "type", "location", "orientation")
    tree = ttk.Treeview(table_frame, columns=col_names, show="headings", height=6)
    tree.heading("#", text="#")
    tree.heading("cp_name", text="CP Name")
    tree.heading("type", text="Type")
    tree.heading("location", text="Location")
    tree.heading("orientation", text="Orientation")
    for c in col_names:
        tree.column(c, width=100)
    tree.column("location", width=160)
    tree.column("orientation", width=120)
    tree.pack(side="left", fill="both", expand=True)
    scroll = ttk.Scrollbar(table_frame, orient="vertical", command=tree.yview)
    scroll.pack(side="right", fill="y")
    tree.configure(yscrollcommand=scroll.set)

    def _constraint_list_from_tree():
        rows = []
        for item in tree.get_children():
            row = tree.item(item)["values"]
            if len(row) >= 5:
                rows.append({"cp_name": row[1], "type": row[2], "location": row[3], "orientation": row[4]})
        return rows

    row_index = [0]
    def add_constraint():
        cp = (cp_name_var.get() or "").strip() or "CP{}".format(row_index[0] + 1)
        typ = type_var.get() or "Point"
        loc = loc_var.get() or ""
        orient = orient_var.get() or ""
        tree.insert("", "end", values=(row_index[0] + 1, cp, typ, loc, orient))
        row_index[0] += 1
        clear_form()
        if on_constraint_added:
            try:
                on_constraint_added(_constraint_list_from_tree())
            except Exception:
                pass

    for btn in btn_form.winfo_children():
        if isinstance(btn, ttk.Button) and btn.cget("text") == "Add Constraint":
            btn.configure(command=add_constraint)
            break

    def remove_selected():
        sel = tree.selection()
        if sel:
            for item in sel:
                tree.delete(item)
        row_index[0] = 0
        for i, item in enumerate(tree.get_children()):
            tree.set(item, "#", i + 1)
            row_index[0] = i + 1
        if on_constraint_added:
            try:
                on_constraint_added(_constraint_list_from_tree())
            except Exception:
                pass

    ttk.Button(main, text="Remove Selected", command=remove_selected).pack(anchor="w", pady=(0, 4))

    # Pre-populate from initial_constraints
    for pair in (initial_constraints or []):
        loc = pair[0] if isinstance(pair, (list, tuple)) else ""
        orient = pair[1] if isinstance(pair, (list, tuple)) and len(pair) > 1 else "0, 0, 1"
        tree.insert("", "end", values=(row_index[0] + 1, "CP{}".format(row_index[0] + 1), "Point", loc, orient))
        row_index[0] += 1
    if on_constraint_added and _constraint_list_from_tree():
        try:
            on_constraint_added(_constraint_list_from_tree())
        except Exception:
            pass

    # --- Actions: Prepare Input File, Run Analysis ---
    action_frame = ttk.Frame(main)
    action_frame.pack(fill="x", pady=(8, 4))
    def prepare_input_file():
        rows = []
        for item in tree.get_children():
            row = tree.item(item)["values"]
            if len(row) >= 5:
                rows.append({"cp_name": row[1], "type": row[2], "location": row[3], "orientation": row[4]})
        if not rows:
            messagebox.showinfo("Analysis Tool", "Add at least one constraint.")
            return
        point_contacts = []
        for r in rows:
            loc = (r.get("location") or "").strip()
            orient = (r.get("orientation") or "").strip()
            if loc and orient:
                try:
                    loc_vals = [float(x.strip()) for x in loc.replace(",", " ").split()[:3]]
                    orient_vals = [float(x.strip()) for x in orient.replace(",", " ").split()[:3]]
                    if len(loc_vals) == 3 and len(orient_vals) == 3:
                        point_contacts.append(loc_vals + orient_vals)
                except ValueError:
                    pass
        cp_names_for_dropdown = [(r.get("cp_name") or "").strip() or "CP{}".format(i + 1) for i, r in enumerate(rows)]
        _shared_constraints[:] = cp_names_for_dropdown
        if len(point_contacts) < 2:
            point_contacts.extend([[0, 0, 0, 0, 0, 1], [0, 0, 1, 0, 0, 1]])
        data = {"version": 1, "point_contacts": point_contacts, "pins": [], "lines": [], "planes": []}
        _ensure_output_dir()
        path = os.path.join(OUTPUT_DIR, "wizard_input.json")
        with open(path, "w") as f:
            json.dump(data, f, indent=2)
        messagebox.showinfo("Analysis Tool", "Input file written to:\n{}".format(path))

    def run_analysis():
        path = os.path.join(OUTPUT_DIR, "wizard_input.json")
        if not os.path.isfile(path):
            messagebox.showinfo("Analysis Tool", "Prepare Input File first.")
            return
        def when_done(success, message, result=None):
            def update():
                if success:
                    res_path = os.path.join(OUTPUT_DIR, "results_wizard.txt")
                    if os.path.isfile(res_path):
                        for r in results_tree.get_children():
                            results_tree.delete(r)
                        with open(res_path) as f:
                            lines = f.readlines()
                        if len(lines) >= 2:
                            parts = lines[1].strip().split("\t")
                            if len(parts) >= 4:
                                results_tree.insert("", "end", values=("Summary", parts[0], parts[1], parts[2], parts[3]))
                    if on_results and result is not None:
                        try:
                            on_results(result)
                        except Exception:
                            pass
                status_lbl.config(text=message)
            root.after(0, update)
        status_lbl.config(text="Running analysis...")
        _run_python_analysis(path, when_done)

    ttk.Button(action_frame, text="Prepare Input File", command=prepare_input_file).pack(side="left", padx=(0, 8))
    ttk.Button(action_frame, text="Run Analysis", command=run_analysis).pack(side="left")
    status_lbl = ttk.Label(main, text="")
    status_lbl.pack(anchor="w", fill="x")

    # --- Results (in-window table) ---
    ttk.Label(main, text="Results", font=("", 10, "bold")).pack(anchor="w", pady=(8, 2))
    res_frame = ttk.Frame(main)
    res_frame.pack(fill="both", expand=True)
    res_cols = ("cp_name", "WTR", "MRR", "MTR", "TOR")
    results_tree = ttk.Treeview(res_frame, columns=res_cols, show="headings", height=4)
    for c in res_cols:
        results_tree.heading(c, text=c)
        results_tree.column(c, width=80)
    results_tree.column("cp_name", width=100)
    results_tree.pack(side="left", fill="both", expand=True)
    res_scroll = ttk.Scrollbar(res_frame, orient="vertical", command=results_tree.yview)
    res_scroll.pack(side="right", fill="y")
    results_tree.configure(yscrollcommand=res_scroll.set)

    root.mainloop()


def run_optimization_wizard():
    """Open the Optimization Tool window. CP dropdown uses _shared_constraints from Analysis Tool."""
    main = tk.Tk()
    main.title("KST Optimization Tool")
    main.minsize(680, 520)
    main.geometry("720x560")

    frame = ttk.Frame(main, padding=10)
    frame.pack(fill="both", expand=True)
    ttk.Label(frame, text="KST Optimization Tool", font=("", 12, "bold")).pack(anchor="w")
    ttk.Label(frame, text="Select CP, choose search space (tab), add parameters to the table; then Generate Plan and Run Optimization.").pack(anchor="w")

    # --- Form: CP dropdown ---
    form = ttk.LabelFrame(frame, text="Form", padding=6)
    form.pack(fill="x", pady=(8, 4))
    cp_values = list(_shared_constraints) if _shared_constraints else [f"CP{i}" for i in range(1, 25)]
    cp_var = tk.StringVar(value=cp_values[0] if cp_values else "CP1")
    ttk.Label(form, text="CP:").pack(side="left", padx=(0, 6))
    cp_combo = ttk.Combobox(form, textvariable=cp_var, values=cp_values, state="readonly", width=14)
    cp_combo.pack(side="left", padx=(0, 16))

    # --- Search space tabs ---
    notebook = ttk.Notebook(form)
    notebook.pack(fill="x", pady=(8, 0))

    line_tab = ttk.Frame(notebook, padding=4)
    notebook.add(line_tab, text="Line")
    ttk.Label(line_tab, text="Origin (x,y,z):").grid(row=0, column=0, sticky="w", padx=(0, 4), pady=2)
    origin_var = tk.StringVar(value="0, 0, 4")
    ttk.Entry(line_tab, textvariable=origin_var, width=22).grid(row=0, column=1, sticky="w", padx=(0, 4))
    def select_line_cad():
        loc_str, orient_str = _show_location_orientation_dialog(main, origin_var.get(), direction_var.get())
        if loc_str is not None:
            origin_var.set(loc_str)
        if orient_str is not None:
            direction_var.set(orient_str)
    ttk.Button(line_tab, text="Select", command=select_line_cad).grid(row=0, column=2, padx=2)
    ttk.Label(line_tab, text="Direction (x,y,z):").grid(row=1, column=0, sticky="w", padx=(0, 4), pady=2)
    direction_var = tk.StringVar(value="0, 0, 1")
    ttk.Entry(line_tab, textvariable=direction_var, width=22).grid(row=1, column=1, sticky="w", padx=(0, 4))
    ttk.Label(line_tab, text="Steps:").grid(row=2, column=0, sticky="w", padx=(0, 4), pady=2)
    steps_line_var = tk.StringVar(value="5")
    ttk.Entry(line_tab, textvariable=steps_line_var, width=8).grid(row=2, column=1, sticky="w")

    discrete_tab = ttk.Frame(notebook, padding=4)
    notebook.add(discrete_tab, text="Discrete")
    ttk.Label(discrete_tab, text="Positions (one x,y,z per line):").grid(row=0, column=0, sticky="nw", padx=(0, 4), pady=2)
    positions_text = tk.Text(discrete_tab, height=4, width=32)
    positions_text.grid(row=1, column=0, columnspan=2, sticky="ew", pady=2)
    positions_text.insert("1.0", "0, 0, 4\n0, 0, 5")
    ttk.Label(discrete_tab, text="Steps:").grid(row=2, column=0, sticky="w", padx=(0, 4), pady=2)
    steps_disc_var = tk.StringVar(value="2")
    ttk.Entry(discrete_tab, textvariable=steps_disc_var, width=8).grid(row=2, column=1, sticky="w")
    discrete_tab.columnconfigure(1, weight=1)

    orient1_tab = ttk.Frame(notebook, padding=4)
    notebook.add(orient1_tab, text="Orient 1D")
    ttk.Label(orient1_tab, text="(Placeholder for orientation 1D search)").pack(anchor="w")
    orient2_tab = ttk.Frame(notebook, padding=4)
    notebook.add(orient2_tab, text="Orient 2D")
    ttk.Label(orient2_tab, text="(Placeholder for orientation 2D search)").pack(anchor="w")

    add_param_btn = ttk.Button(form, text="Add Optimization Parameter", command=lambda: None)
    add_param_btn.pack(anchor="w", pady=(8, 0))

    # --- Parameter table ---
    table_frame = ttk.Frame(frame)
    table_frame.pack(fill="both", expand=True, pady=(8, 4))
    param_cols = ("cp_name", "search_space", "origin_positions", "direction", "steps")
    param_tree = ttk.Treeview(table_frame, columns=param_cols, show="headings", height=5)
    param_tree.heading("cp_name", text="CP Name")
    param_tree.heading("search_space", text="Search Space")
    param_tree.heading("origin_positions", text="Origin/Positions")
    param_tree.heading("direction", text="Direction")
    param_tree.heading("steps", text="Steps")
    for c in param_cols:
        param_tree.column(c, width=90)
    param_tree.column("origin_positions", width=140)
    param_tree.pack(side="left", fill="both", expand=True)
    param_scroll = ttk.Scrollbar(table_frame, orient="vertical", command=param_tree.yview)
    param_scroll.pack(side="right", fill="y")
    param_tree.configure(yscrollcommand=param_scroll.set)

    def add_optim_param():
        cp = cp_var.get() or "CP1"
        tab = notebook.index(notebook.select())
        if tab == 0:
            space = "Line"
            orig = origin_var.get() or ""
            direc = direction_var.get() or ""
            try:
                st = max(1, min(100, int(steps_line_var.get())))
            except ValueError:
                st = 5
        elif tab == 1:
            space = "Discrete"
            orig = positions_text.get("1.0", "end").strip().replace("\n", "; ")
            direc = ""
            try:
                st = max(1, int(steps_disc_var.get()))
            except ValueError:
                st = 2
        else:
            space = ["Orient 1D", "Orient 2D"][tab - 2]
            orig = ""
            direc = ""
            st = 0
        param_tree.insert("", "end", values=(cp, space, orig, direc, st))

    add_param_btn.configure(command=add_optim_param)

    def remove_param_selected():
        sel = param_tree.selection()
        if sel:
            for item in sel:
                param_tree.delete(item)

    ttk.Button(frame, text="Remove Selected", command=remove_param_selected).pack(anchor="w", pady=(0, 4))

    status_lbl = ttk.Label(frame, text="")

    def generate_plan():
        rows = []
        for item in param_tree.get_children():
            row = param_tree.item(item)["values"]
            if len(row) >= 5:
                rows.append({"cp_name": row[0], "search_space": row[1], "origin_positions": row[2], "direction": row[3], "steps": row[4]})
        if not rows:
            messagebox.showinfo("Optimization Tool", "Add at least one optimization parameter.")
            return
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
        modified = []
        candidate_matrix = []
        for r in rows:
            cp_name = r.get("cp_name") or "CP1"
            try:
                idx = _shared_constraints.index(cp_name) + 1
            except (ValueError, AttributeError):
                idx = 1
            space = (r.get("search_space") or "Line").strip()
            try:
                steps = int(r.get("steps") or 5)
            except (ValueError, TypeError):
                steps = 5
            steps = max(1, min(100, steps))
            if space == "Line":
                try:
                    o = [float(x.strip()) for x in (r.get("origin_positions") or "0,0,4").replace(",", " ").split()[:3]]
                    d = [float(x.strip()) for x in (r.get("direction") or "0,0,1").replace(",", " ").split()[:3]]
                except ValueError:
                    o, d = [0, 0, 4], [0, 0, 1]
                n = (d[0]**2 + d[1]**2 + d[2]**2) ** 0.5
                if n > 1e-10:
                    d = [d[0]/n, d[1]/n, d[2]/n]
                candidates = []
                for k in range(steps + 1):
                    t = k / steps
                    candidates.append([o[0] + t*d[0], o[1] + t*d[1], o[2] + t*d[2], 0, 0, -1])
                modified.append({"type": "point", "index": idx, "search_space": {"type": "line", "num_steps": steps}})
                candidate_matrix.append({"constraint_index": idx, "candidates": candidates})
            elif space == "Discrete":
                pos_text = (r.get("origin_positions") or "").replace(";", "\n")
                positions = []
                for line in pos_text.splitlines():
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        vals = [float(x.strip()) for x in line.replace(",", " ").split()[:3]]
                        if len(vals) == 3:
                            positions.append(vals + [0, 0, -1])
                    except ValueError:
                        pass
                if not positions:
                    positions = [[0, 0, 4, 0, 0, -1], [0, 0, 5, 0, 0, -1]]
                modified.append({"type": "point", "index": idx, "search_space": {"type": "discrete", "num_steps": len(positions)}})
                candidate_matrix.append({"constraint_index": idx, "candidates": positions})
            else:
                modified.append({"type": "point", "index": idx, "search_space": {"type": "line", "num_steps": steps}})
                o, d = [0, 0, 4], [0, 0, 1]
                candidates = [[o[0] + k/steps*d[0], o[1] + k/steps*d[1], o[2] + k/steps*d[2], 0, 0, -1] for k in range(steps + 1)]
                candidate_matrix.append({"constraint_index": idx, "candidates": candidates})
        optim = {
            "version": 1,
            "analysis_input": analysis_input,
            "optimization": {"modified_constraints": modified, "candidate_matrix": candidate_matrix},
        }
        _ensure_output_dir()
        out_path = os.path.join(OUTPUT_DIR, "wizard_optimization.json")
        with open(out_path, "w") as f:
            json.dump(optim, f, indent=2)
        status_lbl.config(text="Optimization plan written to: " + out_path)

    def run_optimization():
        messagebox.showinfo("Optimization Tool", "Run Python or MATLAB with wizard_optimization.json. Then click Load Results.")

    action_row = ttk.Frame(frame)
    ttk.Button(action_row, text="Generate Optimization Plan", command=generate_plan).pack(side="left", padx=(0, 8))
    ttk.Button(action_row, text="Run Optimization", command=run_optimization).pack(side="left")
    action_row.pack(fill="x", pady=(8, 4))
    status_lbl.pack(anchor="w", fill="x")

    # --- Results table ---
    ttk.Label(frame, text="Results", font=("", 10, "bold")).pack(anchor="w", pady=(8, 2))
    res_frame = ttk.Frame(frame)
    res_frame.pack(fill="both", expand=True)
    res_cols = ("candidate", "WTR", "MTR", "TOR")
    res_tree = ttk.Treeview(res_frame, columns=res_cols, show="headings", height=5)
    for c in res_cols:
        res_tree.heading(c, text=c)
        res_tree.column(c, width=90)
    res_tree.pack(side="left", fill="both", expand=True)
    res_scroll = ttk.Scrollbar(res_frame, orient="vertical", command=res_tree.yview)
    res_scroll.pack(side="right", fill="y")
    res_tree.configure(yscrollcommand=res_scroll.set)

    def load_results():
        path = os.path.join(OUTPUT_DIR, "results_wizard_optim.txt")
        if not os.path.exists(path):
            status_lbl.config(text="No results file. Run optimization first.")
            return
        for item in res_tree.get_children():
            res_tree.delete(item)
        with open(path) as f:
            lines = f.readlines()
        for line in lines[1:]:
            parts = line.strip().split("\t")
            if len(parts) >= 4:
                res_tree.insert("", "end", values=(parts[0], parts[1], parts[2], parts[3]))
        status_lbl.config(text="Loaded {} result(s).".format(len(res_tree.get_children())))

    ttk.Button(frame, text="Load Results", command=load_results).pack(anchor="w", pady=(4, 0))
    main.mainloop()


if __name__ == "__main__":
    run_analysis_wizard()
