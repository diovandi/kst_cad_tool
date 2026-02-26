"""
Optimization Wizard UI component.
"""

import json
import os
import tkinter as tk
from tkinter import ttk, messagebox
from .dialogs import show_location_orientation_dialog

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
        ttk.Label(orient1_tab, text="(Placeholder for orientation 1D search)").pack(anchor="w")
        orient2_tab = ttk.Frame(self.notebook, padding=4)
        self.notebook.add(orient2_tab, text="Orient 2D")
        ttk.Label(orient2_tab, text="(Placeholder for orientation 2D search)").pack(anchor="w")

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
            space = ["Orient 1D", "Orient 2D"][tab - 2]
            orig = ""
            direc = ""
            st = 0
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
        for r in rows:
            cp_name = r.get("cp_name") or "CP1"
            try:
                idx = self.available_constraints.index(cp_name) + 1
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
