"""
Analysis Wizard UI component.
"""

import json
import os
import tkinter as tk
from tkinter import ttk, messagebox
from .dialogs import show_location_orientation_dialog

class AnalysisPanel(ttk.Frame):
    def __init__(self, parent, output_dir,
                 initial_constraints=None,
                 on_constraint_added=None,
                 on_run_analysis=None,
                 on_select_line=None,
                 on_results=None,
                 on_constraints_updated=None):
        """
        :param parent: Parent widget.
        :param output_dir: Directory to save input/output files.
        :param initial_constraints: List of (location_str, orientation_str).
        :param on_constraint_added: Callback(constraint_list) when constraints change.
        :param on_run_analysis: Function(input_path, on_done_callback) to run analysis.
               on_done_callback(success, message, result=None).
        :param on_select_line: Callback() -> (origin_str, direction_str).
        :param on_results: Callback(result) when analysis completes.
        :param on_constraints_updated: Callback(constraint_names_list) when constraints change.
        """
        super().__init__(parent, padding=10)
        self.output_dir = output_dir
        self.on_constraint_added = on_constraint_added
        self.on_run_analysis_backend = on_run_analysis
        self.on_select_line = on_select_line
        self.on_results = on_results
        self.on_constraints_updated = on_constraints_updated

        self._build_ui(initial_constraints)

    def _ensure_output_dir(self):
        os.makedirs(self.output_dir, exist_ok=True)
        return self.output_dir

    def _build_ui(self, initial_constraints):
        ttk.Label(self, text="KST Analysis Tool", font=("", 12, "bold")).pack(anchor="w")
        ttk.Label(self, text="Define constraints (CP name, type, location, orientation), then Prepare Input File and Run Analysis.").pack(anchor="w")

        # --- Form ---
        form = ttk.LabelFrame(self, text="Form", padding=6)
        form.pack(fill="x", pady=(8, 4))
        row0 = ttk.Frame(form)
        row0.pack(fill="x")
        ttk.Label(row0, text="CP Name:").pack(side="left", padx=(0, 6))
        self.cp_name_var = tk.StringVar(value="")
        ttk.Entry(row0, textvariable=self.cp_name_var, width=20).pack(side="left", padx=(0, 16))
        ttk.Label(row0, text="Type:").pack(side="left", padx=(0, 6))
        self.type_var = tk.StringVar(value="Point")
        type_combo = ttk.Combobox(row0, textvariable=self.type_var, values=["Point", "Pin", "Line", "Plane"], state="readonly", width=8)
        type_combo.pack(side="left", padx=(0, 8))

        point_pin_frame = ttk.Frame(form)
        point_pin_frame.pack(fill="x", pady=(6, 0))
        ttk.Label(point_pin_frame, text="Location (x,y,z):").grid(row=0, column=0, sticky="w", padx=(0, 4), pady=2)
        self.loc_var = tk.StringVar(value="")
        ttk.Entry(point_pin_frame, textvariable=self.loc_var, width=24).grid(row=0, column=1, sticky="w", padx=(0, 4))
        ttk.Button(point_pin_frame, text="Select", command=self._on_select_loc).grid(row=0, column=2, padx=2)

        ttk.Label(point_pin_frame, text="Orientation (nx,ny,nz):").grid(row=1, column=0, sticky="w", padx=(0, 4), pady=2)
        self.orient_var = tk.StringVar(value="")
        ttk.Entry(point_pin_frame, textvariable=self.orient_var, width=24).grid(row=1, column=1, sticky="w", padx=(0, 4))
        ttk.Button(point_pin_frame, text="Set", command=self._on_select_orient).grid(row=1, column=2, padx=2)

        btn_form = ttk.Frame(form)
        btn_form.pack(fill="x", pady=(6, 0))
        ttk.Button(btn_form, text="Add Constraint", command=self._add_constraint).pack(side="left", padx=(0, 8))
        ttk.Button(btn_form, text="Clear Form", command=self._clear_form).pack(side="left")

        # --- Constraint table ---
        table_frame = ttk.Frame(self)
        table_frame.pack(fill="both", expand=True, pady=(8, 4))
        col_names = ("#", "cp_name", "type", "location", "orientation")
        self.tree = ttk.Treeview(table_frame, columns=col_names, show="headings", height=6)
        self.tree.heading("#", text="#")
        self.tree.heading("cp_name", text="CP Name")
        self.tree.heading("type", text="Type")
        self.tree.heading("location", text="Location")
        self.tree.heading("orientation", text="Orientation")
        for c in col_names:
            self.tree.column(c, width=100)
        self.tree.column("location", width=160)
        self.tree.column("orientation", width=120)
        self.tree.pack(side="left", fill="both", expand=True)
        scroll = ttk.Scrollbar(table_frame, orient="vertical", command=self.tree.yview)
        scroll.pack(side="right", fill="y")
        self.tree.configure(yscrollcommand=scroll.set)

        self.row_index = 0

        ttk.Button(self, text="Remove Selected", command=self._remove_selected).pack(anchor="w", pady=(0, 4))

        # Pre-populate
        if initial_constraints:
            for pair in initial_constraints:
                loc = pair[0] if isinstance(pair, (list, tuple)) else ""
                orient = pair[1] if isinstance(pair, (list, tuple)) and len(pair) > 1 else "0, 0, 1"
                self.tree.insert("", "end", values=(self.row_index + 1, "CP{}".format(self.row_index + 1), "Point", loc, orient))
                self.row_index += 1
            self._notify_constraints_changed()

        # --- Actions ---
        action_frame = ttk.Frame(self)
        action_frame.pack(fill="x", pady=(8, 4))
        ttk.Button(action_frame, text="Prepare Input File", command=self._prepare_input_file).pack(side="left", padx=(0, 8))
        ttk.Button(action_frame, text="Run Analysis", command=self._run_analysis).pack(side="left")
        self.status_lbl = ttk.Label(self, text="")
        self.status_lbl.pack(anchor="w", fill="x")

        # --- Results ---
        ttk.Label(self, text="Results", font=("", 10, "bold")).pack(anchor="w", pady=(8, 2))
        res_frame = ttk.Frame(self)
        res_frame.pack(fill="both", expand=True)
        res_cols = ("cp_name", "WTR", "MRR", "MTR", "TOR")
        self.results_tree = ttk.Treeview(res_frame, columns=res_cols, show="headings", height=4)
        for c in res_cols:
            self.results_tree.heading(c, text=c)
            self.results_tree.column(c, width=80)
        self.results_tree.column("cp_name", width=100)
        self.results_tree.pack(side="left", fill="both", expand=True)
        res_scroll = ttk.Scrollbar(res_frame, orient="vertical", command=self.results_tree.yview)
        res_scroll.pack(side="right", fill="y")
        self.results_tree.configure(yscrollcommand=res_scroll.set)

    def _on_select_loc(self):
        if (self.type_var.get() or "").strip() == "Line" and self.on_select_line:
            try:
                result = self.on_select_line()
                if result and len(result) >= 2 and result[0] is not None and result[1] is not None:
                    self.loc_var.set(result[0])
                    self.orient_var.set(result[1])
                    return
            except Exception:
                pass
        loc_str, orient_str = show_location_orientation_dialog(self.winfo_toplevel(), self.loc_var.get(), self.orient_var.get())
        if loc_str is not None:
            self.loc_var.set(loc_str)
        if orient_str is not None:
            self.orient_var.set(orient_str)

    def _on_select_orient(self):
        loc_str, orient_str = show_location_orientation_dialog(self.winfo_toplevel(), self.loc_var.get(), self.orient_var.get())
        if loc_str is not None:
            self.loc_var.set(loc_str)
        if orient_str is not None:
            self.orient_var.set(orient_str)

    def _clear_form(self):
        self.cp_name_var.set("")
        self.type_var.set("Point")
        self.loc_var.set("")
        self.orient_var.set("")

    def _constraint_list_from_tree(self):
        rows = []
        for item in self.tree.get_children():
            row = self.tree.item(item)["values"]
            if len(row) >= 5:
                rows.append({"cp_name": row[1], "type": row[2], "location": row[3], "orientation": row[4]})
        return rows

    def _notify_constraints_changed(self):
        rows = self._constraint_list_from_tree()
        if self.on_constraint_added:
            try:
                self.on_constraint_added(rows)
            except Exception:
                pass
        if self.on_constraints_updated:
            names = [(r.get("cp_name") or "").strip() or "CP{}".format(i + 1) for i, r in enumerate(rows)]
            try:
                self.on_constraints_updated(names)
            except Exception:
                pass

    def _add_constraint(self):
        cp = (self.cp_name_var.get() or "").strip() or "CP{}".format(self.row_index + 1)
        typ = self.type_var.get() or "Point"
        loc = self.loc_var.get() or ""
        orient = self.orient_var.get() or ""
        self.tree.insert("", "end", values=(self.row_index + 1, cp, typ, loc, orient))
        self.row_index += 1
        self._clear_form()
        self._notify_constraints_changed()

    def _remove_selected(self):
        sel = self.tree.selection()
        if sel:
            for item in sel:
                self.tree.delete(item)
        # Re-index
        for i, item in enumerate(self.tree.get_children()):
            self.tree.set(item, "#", i + 1)
        self.row_index = len(self.tree.get_children())
        self._notify_constraints_changed()

    def _prepare_input_file(self):
        rows = self._constraint_list_from_tree()
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

        # Notify updated names (used by Optimization)
        self._notify_constraints_changed()

        if len(point_contacts) < 2:
            point_contacts.extend([[0, 0, 0, 0, 0, 1], [0, 0, 1, 0, 0, 1]])
        data = {"version": 1, "point_contacts": point_contacts, "pins": [], "lines": [], "planes": []}
        self._ensure_output_dir()
        path = os.path.join(self.output_dir, "wizard_input.json")
        with open(path, "w") as f:
            json.dump(data, f, indent=2)
        messagebox.showinfo("Analysis Tool", "Input file written to:\n{}".format(path))

    def _run_analysis(self):
        path = os.path.join(self.output_dir, "wizard_input.json")
        if not os.path.isfile(path):
            messagebox.showinfo("Analysis Tool", "Prepare Input File first.")
            return

        def when_done(success, message, result=None):
            def update():
                if success:
                    res_path = os.path.join(self.output_dir, "results_wizard.txt")
                    if os.path.isfile(res_path):
                        for r in self.results_tree.get_children():
                            self.results_tree.delete(r)
                        with open(res_path) as f:
                            lines = f.readlines()
                        if len(lines) >= 2:
                            parts = lines[1].strip().split("\t")
                            if len(parts) >= 4:
                                self.results_tree.insert("", "end", values=("Summary", parts[0], parts[1], parts[2], parts[3]))
                    if self.on_results and result is not None:
                        try:
                            self.on_results(result)
                        except Exception:
                            pass
                self.status_lbl.config(text=message)
            self.after(0, update)

        self.status_lbl.config(text="Running analysis...")
        if self.on_run_analysis_backend:
            self.on_run_analysis_backend(path, when_done)
        else:
            when_done(False, "No analysis backend configured.")

    def get_constraint_names(self):
        return [self.tree.item(item)["values"][1] for item in self.tree.get_children()]
