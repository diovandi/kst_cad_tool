"""
Optimization Wizard UI component.
"""

import json
import os
import math
import tkinter as tk
from tkinter import ttk, messagebox

try:
    from .dialogs import show_location_orientation_dialog  # type: ignore
except ImportError:
    from dialogs import show_location_orientation_dialog  # type: ignore

class OptimizationPanel(ttk.Frame):
    def __init__(self, parent, output_dir, available_constraints=None, on_run_optimization=None):
        super().__init__(parent, padding=10)
        self.output_dir = output_dir
        self.available_constraints = available_constraints or []
        self.on_run_optimization = on_run_optimization

        self._build_ui()

    def update_constraints(self, constraint_names):
        self.available_constraints = constraint_names or []
        vals = self.available_constraints if self.available_constraints else ["CP{}".format(i) for i in range(1, 25)]
        self.cp_combo['values'] = vals
        if vals:
            self.cp_var.set(vals[0])
        else:
            self.cp_var.set("")

    def _ensure_output_dir(self):
        os.makedirs(self.output_dir, exist_ok=True)
        return self.output_dir

    def _build_ui(self):
        ttk.Label(self, text="KST Optimization Tool", font=("", 12, "bold")).pack(anchor="w")
        ttk.Label(self, text="Select CP, choose search space (tab), add parameters to the table; then Generate Plan and Run Optimization.").pack(anchor="w")

        # --- Form: CP dropdown ---
        form = ttk.LabelFrame(self, text="Form", padding=6)
        form.pack(fill="x", pady=(8, 4))

        vals = self.available_constraints if self.available_constraints else ["CP{}".format(i) for i in range(1, 25)]
        self.cp_var = tk.StringVar(value=vals[0] if vals else "CP1")
        ttk.Label(form, text="CP:").pack(side="left", padx=(0, 6))
        self.cp_combo = ttk.Combobox(form, textvariable=self.cp_var, values=vals, state="readonly", width=14)
        self.cp_combo.pack(side="left", padx=(0, 16))

        # --- Search space tabs ---
        self.notebook = ttk.Notebook(form)
        self.notebook.pack(fill="x", pady=(8, 0))

        line_tab = ttk.Frame(self.notebook, padding=4)
        self.notebook.add(line_tab, text="Line")
        ttk.Label(line_tab, text="Origin (x,y,z):").grid(row=0, column=0, sticky="w", padx=(0, 4), pady=2)
        self.origin_var = tk.StringVar(value="0, 0, 4")
        ttk.Entry(line_tab, textvariable=self.origin_var, width=22).grid(row=0, column=1, sticky="w", padx=(0, 4))
        ttk.Button(line_tab, text="Select", command=self._select_line_cad).grid(row=0, column=2, padx=2)

        ttk.Label(line_tab, text="Direction (x,y,z):").grid(row=1, column=0, sticky="w", padx=(0, 4), pady=2)
        self.direction_var = tk.StringVar(value="0, 0, 1")
        ttk.Entry(line_tab, textvariable=self.direction_var, width=22).grid(row=1, column=1, sticky="w", padx=(0, 4))

        ttk.Label(line_tab, text="Steps:").grid(row=2, column=0, sticky="w", padx=(0, 4), pady=2)
        self.steps_line_var = tk.StringVar(value="5")
        ttk.Entry(line_tab, textvariable=self.steps_line_var, width=8).grid(row=2, column=1, sticky="w")

        discrete_tab = ttk.Frame(self.notebook, padding=4)
        self.notebook.add(discrete_tab, text="Discrete")
        ttk.Label(discrete_tab, text="Positions (one x,y,z per line):").grid(row=0, column=0, sticky="nw", padx=(0, 4), pady=2)
        self.positions_text = tk.Text(discrete_tab, height=4, width=32)
        self.positions_text.grid(row=1, column=0, columnspan=2, sticky="ew", pady=2)
        self.positions_text.insert("1.0", "0, 0, 4\n0, 0, 5")
        ttk.Label(discrete_tab, text="Steps:").grid(row=2, column=0, sticky="w", padx=(0, 4), pady=2)
        self.steps_disc_var = tk.StringVar(value="2")
        ttk.Entry(discrete_tab, textvariable=self.steps_disc_var, width=8).grid(row=2, column=1, sticky="w")
        discrete_tab.columnconfigure(1, weight=1)

        orient1_tab = ttk.Frame(self.notebook, padding=4)
        self.notebook.add(orient1_tab, text="Orient 1D")
        ttk.Label(orient1_tab, text="Axis (x,y,z):").grid(row=0, column=0, sticky="w", padx=(0, 4), pady=2)
        self.orient1_axis_var = tk.StringVar(value="1, 0, 0")
        ttk.Entry(orient1_tab, textvariable=self.orient1_axis_var, width=22).grid(row=0, column=1, sticky="w", padx=(0, 4))
        ttk.Label(orient1_tab, text="Angle min (deg):").grid(row=1, column=0, sticky="w", padx=(0, 4), pady=2)
        self.orient1_min_var = tk.StringVar(value="-30")
        ttk.Entry(orient1_tab, textvariable=self.orient1_min_var, width=10).grid(row=1, column=1, sticky="w")
        ttk.Label(orient1_tab, text="Angle max (deg):").grid(row=2, column=0, sticky="w", padx=(0, 4), pady=2)
        self.orient1_max_var = tk.StringVar(value="30")
        ttk.Entry(orient1_tab, textvariable=self.orient1_max_var, width=10).grid(row=2, column=1, sticky="w")
        ttk.Label(orient1_tab, text="Steps:").grid(row=3, column=0, sticky="w", padx=(0, 4), pady=2)
        self.steps_orient1_var = tk.StringVar(value="5")
        ttk.Entry(orient1_tab, textvariable=self.steps_orient1_var, width=10).grid(row=3, column=1, sticky="w")
        orient2_tab = ttk.Frame(self.notebook, padding=4)
        self.notebook.add(orient2_tab, text="Orient 2D")
        ttk.Label(orient2_tab, text="Axis 1 (x,y,z):").grid(row=0, column=0, sticky="w", padx=(0, 4), pady=2)
        self.orient2_axis1_var = tk.StringVar(value="1, 0, 0")
        ttk.Entry(orient2_tab, textvariable=self.orient2_axis1_var, width=22).grid(row=0, column=1, sticky="w", padx=(0, 4))
        ttk.Label(orient2_tab, text="Axis 2 (x,y,z):").grid(row=1, column=0, sticky="w", padx=(0, 4), pady=2)
        self.orient2_axis2_var = tk.StringVar(value="0, 1, 0")
        ttk.Entry(orient2_tab, textvariable=self.orient2_axis2_var, width=22).grid(row=1, column=1, sticky="w", padx=(0, 4))
        ttk.Label(orient2_tab, text="Angle1 min/max (deg):").grid(row=2, column=0, sticky="w", padx=(0, 4), pady=2)
        self.orient2_a1_min_var = tk.StringVar(value="-20")
        self.orient2_a1_max_var = tk.StringVar(value="20")
        a1_row = ttk.Frame(orient2_tab)
        a1_row.grid(row=2, column=1, sticky="w")
        ttk.Entry(a1_row, textvariable=self.orient2_a1_min_var, width=8).pack(side="left")
        ttk.Label(a1_row, text=" / ").pack(side="left")
        ttk.Entry(a1_row, textvariable=self.orient2_a1_max_var, width=8).pack(side="left")
        ttk.Label(orient2_tab, text="Angle2 min/max (deg):").grid(row=3, column=0, sticky="w", padx=(0, 4), pady=2)
        self.orient2_a2_min_var = tk.StringVar(value="-20")
        self.orient2_a2_max_var = tk.StringVar(value="20")
        a2_row = ttk.Frame(orient2_tab)
        a2_row.grid(row=3, column=1, sticky="w")
        ttk.Entry(a2_row, textvariable=self.orient2_a2_min_var, width=8).pack(side="left")
        ttk.Label(a2_row, text=" / ").pack(side="left")
        ttk.Entry(a2_row, textvariable=self.orient2_a2_max_var, width=8).pack(side="left")
        ttk.Label(orient2_tab, text="Steps (each axis):").grid(row=4, column=0, sticky="w", padx=(0, 4), pady=2)
        self.steps_orient2_var = tk.StringVar(value="3")
        ttk.Entry(orient2_tab, textvariable=self.steps_orient2_var, width=10).grid(row=4, column=1, sticky="w")

        ttk.Button(form, text="Add Optimization Parameter", command=self._add_optim_param).pack(anchor="w", pady=(8, 0))

        # --- Parameter table ---
        table_frame = ttk.Frame(self)
        table_frame.pack(fill="both", expand=True, pady=(8, 4))
        param_cols = ("cp_name", "search_space", "origin_positions", "direction", "steps")
        self.param_tree = ttk.Treeview(table_frame, columns=param_cols, show="headings", height=5)
        self.param_tree.heading("cp_name", text="CP Name")
        self.param_tree.heading("search_space", text="Search Space")
        self.param_tree.heading("origin_positions", text="Origin/Positions")
        self.param_tree.heading("direction", text="Direction")
        self.param_tree.heading("steps", text="Steps")
        for c in param_cols:
            self.param_tree.column(c, width=90)
        self.param_tree.column("origin_positions", width=140)
        self.param_tree.pack(side="left", fill="both", expand=True)
        param_scroll = ttk.Scrollbar(table_frame, orient="vertical", command=self.param_tree.yview)
        param_scroll.pack(side="right", fill="y")
        self.param_tree.configure(yscrollcommand=param_scroll.set)

        ttk.Button(self, text="Remove Selected", command=self._remove_param_selected).pack(anchor="w", pady=(0, 4))

        self.status_lbl = ttk.Label(self, text="")

        action_row = ttk.Frame(self)
        ttk.Button(action_row, text="Generate Optimization Plan", command=self._generate_plan).pack(side="left", padx=(0, 8))
        ttk.Button(action_row, text="Run Optimization", command=self._run_optimization_action).pack(side="left")
        action_row.pack(fill="x", pady=(8, 4))
        self.status_lbl.pack(anchor="w", fill="x")

        # --- Results table ---
        ttk.Label(self, text="Results", font=("", 10, "bold")).pack(anchor="w", pady=(8, 2))
        res_frame = ttk.Frame(self)
        res_frame.pack(fill="both", expand=True)
        res_cols = ("candidate", "WTR", "MTR", "TOR")
        self.res_tree = ttk.Treeview(res_frame, columns=res_cols, show="headings", height=5)
        for c in res_cols:
            self.res_tree.heading(c, text=c)
            self.res_tree.column(c, width=90)
        self.res_tree.pack(side="left", fill="both", expand=True)
        res_scroll = ttk.Scrollbar(res_frame, orient="vertical", command=self.res_tree.yview)
        res_scroll.pack(side="right", fill="y")
        self.res_tree.configure(yscrollcommand=res_scroll.set)

        ttk.Button(self, text="Load Results", command=self._load_results).pack(anchor="w", pady=(4, 0))

    def _select_line_cad(self):
        loc_str, orient_str = show_location_orientation_dialog(self.winfo_toplevel(), self.origin_var.get(), self.direction_var.get())
        if loc_str is not None:
            self.origin_var.set(loc_str)
        if orient_str is not None:
            self.direction_var.set(orient_str)

    def _add_optim_param(self):
        cp = self.cp_var.get() or "CP1"
        try:
            tab = self.notebook.index(self.notebook.select())
        except tk.TclError:
            tab = 0

        if tab == 0:
            space = "Line"
            orig = self.origin_var.get() or ""
            direc = self.direction_var.get() or ""
            try:
                st = max(1, min(100, int(self.steps_line_var.get())))
            except ValueError:
                st = 5
        elif tab == 1:
            space = "Discrete"
            orig = self.positions_text.get("1.0", "end").strip().replace("\n", "; ")
            direc = ""
            try:
                st = max(1, int(self.steps_disc_var.get()))
            except ValueError:
                st = 2
        else:
            if tab == 2:
                space = "Orient 1D"
                orig = self.orient1_axis_var.get() or ""
                direc = "{},{}".format(self.orient1_min_var.get() or "-30", self.orient1_max_var.get() or "30")
                try:
                    st = max(1, min(100, int(self.steps_orient1_var.get())))
                except ValueError:
                    st = 5
            else:
                space = "Orient 2D"
                orig = "{};{}".format(self.orient2_axis1_var.get() or "", self.orient2_axis2_var.get() or "")
                direc = "{},{};{},{}".format(
                    self.orient2_a1_min_var.get() or "-20",
                    self.orient2_a1_max_var.get() or "20",
                    self.orient2_a2_min_var.get() or "-20",
                    self.orient2_a2_max_var.get() or "20",
                )
                try:
                    st = max(1, min(50, int(self.steps_orient2_var.get())))
                except ValueError:
                    st = 3
        self.param_tree.insert("", "end", values=(cp, space, orig, direc, st))

    def _remove_param_selected(self):
        sel = self.param_tree.selection()
        if sel:
            for item in sel:
                self.param_tree.delete(item)

    def _generate_plan(self):
        rows = []
        for item in self.param_tree.get_children():
            row = self.param_tree.item(item)["values"]
            if len(row) >= 5:
                rows.append({"cp_name": row[0], "search_space": row[1], "origin_positions": row[2], "direction": row[3], "steps": row[4]})
        if not rows:
            messagebox.showinfo("Optimization Tool", "Add at least one optimization parameter.")
            return

        analysis_path = os.path.join(self.output_dir, "wizard_input.json")
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
        n_point = len(analysis_input.get("point_contacts", []) or [])
        n_pin = len(analysis_input.get("pins", []) or [])
        n_line = len(analysis_input.get("lines", []) or [])
        n_plane = len(analysis_input.get("planes", []) or [])

        def _parse_vec3(text, default=None):
            default = default or [0.0, 0.0, 1.0]
            try:
                vals = [float(x.strip()) for x in str(text).replace(",", " ").split()[:3]]
                if len(vals) == 3:
                    return vals
            except Exception:
                pass
            return list(default)

        def _norm(v):
            m = math.sqrt(v[0] * v[0] + v[1] * v[1] + v[2] * v[2])
            if m <= 1e-12:
                return [0.0, 0.0, 1.0]
            return [v[0] / m, v[1] / m, v[2] / m]

        def _rotate(vec, axis, angle_deg):
            axis_u = _norm(axis)
            x, y, z = vec
            ux, uy, uz = axis_u
            th = math.radians(angle_deg)
            c = math.cos(th)
            s = math.sin(th)
            dot = ux * x + uy * y + uz * z
            return [
                x * c + (uy * z - uz * y) * s + ux * dot * (1 - c),
                y * c + (uz * x - ux * z) * s + uy * dot * (1 - c),
                z * c + (ux * y - uy * x) * s + uz * dot * (1 - c),
            ]

        def _target_from_cp_name(cp_name):
            name = str(cp_name or "").strip()
            if name in self.available_constraints:
                global_idx = self.available_constraints.index(name) + 1
            else:
                global_idx = 1
            digits = "".join(ch for ch in name if ch.isdigit())
            typed_idx = int(digits) if digits else 1
            lower = name.lower()
            if "pin" in lower:
                ctype = "pin"
            elif "line" in lower:
                ctype = "line"
            elif "plane" in lower:
                ctype = "plane"
            else:
                ctype = "point"

            if ctype == "point":
                local_idx = typed_idx if 1 <= typed_idx <= max(1, n_point) else min(global_idx, max(1, n_point))
                global_from_local = local_idx
            elif ctype == "pin":
                local_idx = typed_idx if 1 <= typed_idx <= max(1, n_pin) else 1
                global_from_local = n_point + local_idx
            elif ctype == "line":
                local_idx = typed_idx if 1 <= typed_idx <= max(1, n_line) else 1
                global_from_local = n_point + n_pin + local_idx
            else:
                local_idx = typed_idx if 1 <= typed_idx <= max(1, n_plane) else 1
                global_from_local = n_point + n_pin + n_line + local_idx

            if 1 <= global_idx <= (n_point + n_pin + n_line + n_plane):
                return ctype, local_idx, global_idx
            return ctype, local_idx, global_from_local

        def _base_row(ctype, idx):
            if ctype == "point" and 1 <= idx <= n_point:
                return list(analysis_input["point_contacts"][idx - 1])
            if ctype == "pin" and 1 <= idx <= n_pin:
                return list(analysis_input["pins"][idx - 1])
            if ctype == "line" and 1 <= idx <= n_line:
                return list(analysis_input["lines"][idx - 1])
            if ctype == "plane" and 1 <= idx <= n_plane:
                return list(analysis_input["planes"][idx - 1])
            if ctype in ("point", "pin"):
                return [0, 0, 4, 0, 0, -1]
            if ctype == "line":
                return [0, 0, 4, 1, 0, 0, 0, 0, 1, 1]
            return [0, 0, 0, 0, 0, 1, 1, 1]

        for r in rows:
            cp_name = r.get("cp_name") or "CP1"
            ctype, idx, global_idx = _target_from_cp_name(cp_name)
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
                d = _norm(d)
                base = _base_row(ctype, idx)
                candidates = []
                for k in range(steps + 1):
                    t = k / steps
                    pos = [o[0] + t * d[0], o[1] + t * d[1], o[2] + t * d[2]]
                    if ctype in ("point", "pin"):
                        candidates.append(pos + list(base[3:6]))
                    elif ctype == "line":
                        candidates.append(pos + list(base[3:10]))
                    else:
                        candidates.append(pos + list(base[3:]))
                modified.append({"type": ctype, "index": idx, "search_space": {"type": "line", "num_steps": steps}})
                candidate_matrix.append({"type": ctype, "index": idx, "constraint_index": global_idx, "candidates": candidates})
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
                            positions.append(vals)
                    except ValueError:
                        pass
                if not positions:
                    positions = [[0, 0, 4], [0, 0, 5]]
                base = _base_row(ctype, idx)
                candidates = []
                for pos in positions:
                    if ctype in ("point", "pin"):
                        candidates.append(pos + list(base[3:6]))
                    elif ctype == "line":
                        candidates.append(pos + list(base[3:10]))
                    else:
                        candidates.append(pos + list(base[3:]))
                modified.append({"type": ctype, "index": idx, "search_space": {"type": "discrete", "num_steps": len(candidates)}})
                candidate_matrix.append({"type": ctype, "index": idx, "constraint_index": global_idx, "candidates": candidates})
            elif space == "Orient 1D":
                axis = _parse_vec3(r.get("origin_positions") or "1,0,0", [1.0, 0.0, 0.0])
                angle_txt = str(r.get("direction") or "-30,30").replace(";", ",")
                try:
                    a_vals = [float(x.strip()) for x in angle_txt.split(",") if x.strip()]
                    a_min, a_max = (a_vals[0], a_vals[1]) if len(a_vals) >= 2 else (-30.0, 30.0)
                except Exception:
                    a_min, a_max = -30.0, 30.0
                base = _base_row(ctype, idx)
                if ctype in ("point", "pin"):
                    base_ori = list(base[3:6])
                elif ctype == "line":
                    base_ori = list(base[3:6])
                else:
                    base_ori = list(base[3:6])
                candidates = []
                for k in range(steps + 1):
                    t = 0.0 if steps == 0 else (k / steps)
                    ang = a_min + (a_max - a_min) * t
                    new_ori = _norm(_rotate(base_ori, axis, ang))
                    if ctype in ("point", "pin"):
                        candidates.append(list(base[0:3]) + new_ori)
                    elif ctype == "line":
                        candidates.append(list(base[0:3]) + new_ori + list(base[6:10]))
                    else:
                        candidates.append(list(base[0:3]) + new_ori + list(base[6:]))
                modified.append({"type": ctype, "index": idx, "search_space": {"type": "orient_1d", "num_steps": steps}})
                candidate_matrix.append({"type": ctype, "index": idx, "constraint_index": global_idx, "candidates": candidates})
            elif space == "Orient 2D":
                axis_txt = str(r.get("origin_positions") or "1,0,0;0,1,0")
                axis_parts = axis_txt.split(";")
                axis1 = _parse_vec3(axis_parts[0] if axis_parts else "1,0,0", [1.0, 0.0, 0.0])
                axis2 = _parse_vec3(axis_parts[1] if len(axis_parts) > 1 else "0,1,0", [0.0, 1.0, 0.0])
                range_txt = str(r.get("direction") or "-20,20;-20,20")
                range_parts = range_txt.split(";")
                try:
                    p1 = [float(x.strip()) for x in range_parts[0].split(",") if x.strip()]
                    a1_min, a1_max = (p1[0], p1[1]) if len(p1) >= 2 else (-20.0, 20.0)
                except Exception:
                    a1_min, a1_max = -20.0, 20.0
                try:
                    p2 = [float(x.strip()) for x in (range_parts[1] if len(range_parts) > 1 else "-20,20").split(",") if x.strip()]
                    a2_min, a2_max = (p2[0], p2[1]) if len(p2) >= 2 else (-20.0, 20.0)
                except Exception:
                    a2_min, a2_max = -20.0, 20.0
                base = _base_row(ctype, idx)
                base_ori = list(base[3:6])
                candidates = []
                for i in range(steps + 1):
                    t1 = 0.0 if steps == 0 else (i / steps)
                    a1 = a1_min + (a1_max - a1_min) * t1
                    for j in range(steps + 1):
                        t2 = 0.0 if steps == 0 else (j / steps)
                        a2 = a2_min + (a2_max - a2_min) * t2
                        v = _rotate(base_ori, axis1, a1)
                        v = _norm(_rotate(v, axis2, a2))
                        if ctype in ("point", "pin"):
                            candidates.append(list(base[0:3]) + v)
                        elif ctype == "line":
                            candidates.append(list(base[0:3]) + v + list(base[6:10]))
                        else:
                            candidates.append(list(base[0:3]) + v + list(base[6:]))
                modified.append({"type": ctype, "index": idx, "search_space": {"type": "orient_2d", "num_steps": steps}})
                candidate_matrix.append({"type": ctype, "index": idx, "constraint_index": global_idx, "candidates": candidates})
            else:
                modified.append({"type": ctype, "index": idx, "search_space": {"type": "line", "num_steps": steps}})
                o, d = [0, 0, 4], [0, 0, 1]
                base = _base_row(ctype, idx)
                candidates = []
                for k in range(steps + 1):
                    pos = [o[0] + k / steps * d[0], o[1] + k / steps * d[1], o[2] + k / steps * d[2]]
                    if ctype in ("point", "pin"):
                        candidates.append(pos + list(base[3:6]))
                    elif ctype == "line":
                        candidates.append(pos + list(base[3:10]))
                    else:
                        candidates.append(pos + list(base[3:]))
                candidate_matrix.append({"type": ctype, "index": idx, "constraint_index": global_idx, "candidates": candidates})

        optim = {
            "version": 1,
            "analysis_input": analysis_input,
            "optimization": {"modified_constraints": modified, "candidate_matrix": candidate_matrix},
        }
        self._ensure_output_dir()
        out_path = os.path.join(self.output_dir, "wizard_optimization.json")
        with open(out_path, "w") as f:
            json.dump(optim, f, indent=2)
        self.status_lbl.config(text="Optimization plan written to: " + out_path)

    def _run_optimization_action(self):
        path = os.path.join(self.output_dir, "wizard_optimization.json")
        if not os.path.isfile(path):
            self.status_lbl.config(text="Generate optimization plan first.")
            return

        def when_done(success, message):
            def update():
                if success:
                    self._load_results()
                    self.status_lbl.config(text="Optimization done. Results loaded.\n" + message)
                else:
                    self.status_lbl.config(text="Optimization failed.\n" + message)
            self.after(0, update)

        self.status_lbl.config(text="Running optimization...")
        if self.on_run_optimization:
            self.on_run_optimization(path, when_done)
        else:
            messagebox.showinfo("Optimization Tool", "Run Python or MATLAB with wizard_optimization.json. Then click Load Results.")
            self.status_lbl.config(text="External run required.")

    def _load_results(self):
        path = os.path.join(self.output_dir, "results_wizard_optim.txt")
        if not os.path.exists(path):
            self.status_lbl.config(text="No results file. Run optimization first.")
            return
        for item in self.res_tree.get_children():
            self.res_tree.delete(item)
        with open(path) as f:
            lines = f.readlines()
        for line in lines[1:]:
            parts = line.strip().split("\t")
            if len(parts) >= 4:
                self.res_tree.insert("", "end", values=(parts[0], parts[1], parts[2], parts[3]))
        self.status_lbl.config(text="Loaded {} result(s).".format(len(self.res_tree.get_children())))
