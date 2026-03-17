# KST CAD Tool — Project Status Summary

**Date:** March 2026 (updated)  
**Purpose:** Summary of work done so far and current status for supervisor meetings.

---

## 1. MATLAB / Octave / Python Parity

### 1.1 Current state

- **MATLAB 2018b** and **Octave** match the dissertation (Rusli, OSU 2008) for all validated cases (Ch 10 / Ch 11).
- **Python** matches **Octave** (and thus MATLAB) for **all 21 cases** (WTR, MRR, MTR, TOR within atol=1e-3, rtol=5%).

Verification: the result files in the workspace (`results_python_<case>.txt` and `matlab_script/results_octave_<case>.txt`) have been compared; **21/21 cases pass**. To re-verify:

```bash
python scripts/compare_octave_python.py all
```

### 1.2 Thesis reference cases

For the cases with explicit thesis references (Ch 10 tables), both Python and Octave match the thesis:

| Case | Thesis source | Python vs thesis | Octave vs thesis |
|------|----------------|-------------------|------------------|
| case1a_chair_height | Ch 10 Table 10.2 | PASS | PASS |
| case2a_cube_scalability | Ch 10 Table 10.7 | PASS | PASS |
| case2b_cube_tradeoff | Ch 10 Table 10.6 | PASS | PASS |
| case3a_cover_leverage | Ch 10 Table 10.10 | PASS | PASS |

See [THESIS_COMPARISON.md](THESIS_COMPARISON.md) and `python scripts/compare_to_thesis.py all`.

### 1.3 Historical note

Earlier docs (e.g. DEEP_COMPARISON.md) described a snapshot where Python diverged for some cases (endcap, printer). Parity work has since achieved agreement for all 21 cases; the current codebase and results reflect that.

---

## 2. Work Completed (CAD add-in and generic pipeline)

### 2.1 Archive and documentation

- **PARKED.md** — Now documents **parity achieved** (21/21) and how to verify; historical note on earlier divergence.
- **PROJECT_STATUS_SUMMARY.md** (this file) — Current status and parity for meetings.

### 2.2 Fusion 360 add-in — Full constraint type support

- **Location:** `fusion360_addin/KstAnalysis/` (source), `fusion360_addin/KstAnalysis.bundle/` (built bundle).
- **Analysis Wizard** (native Fusion command palette):
  - Type dropdown: **Point**, **Pin**, **Line**, **Plane**.
  - Orientation method dropdown (Point only): Normal to Plane, Two Points, Along Line/Axis.
  - Dynamic selection filters per constraint type (vertices for Point/Pin, edges for Line, faces for Plane).
  - Per-type geometry extraction with visual feedback (constraint markers in viewport).
  - Writes v2 JSON (`wizard_input.json`) with all four constraint arrays.
- **External analysis script** (`scripts/run_wizard_analysis.py`): Reads v2 JSON, builds `ConstraintSet` with `PointConstraint`, `PinConstraint`, `LineConstraint`, `PlaneConstraint`, and runs `analyze_constraints_detailed`.
- **Visualizer** (`visualizer.py`): Draws constraint markers for all four types and weakest screw motions.

### 2.3 CAD add-in (Inventor) — Skeleton and design

- **Research:** [INVENTOR_ADDIN_DEVELOPMENT.md](INVENTOR_ADDIN_DEVELOPMENT.md) — C#/.NET, ApplicationAddInServer, ribbon, geometry selection, WPF/WinForms.
- **Project skeleton:** `inventor_addin/` — C# Analysis Wizard and Optimization Wizard, ribbon buttons, generic JSON output.
- **Wizard demo (Python):** `scripts/wizard_demo.py` — Standalone GUI (tkinter) that mimics the two wizards for meetings. Run: `python scripts/wizard_demo.py`.

### 2.4 Generic input and scripts

- **Generic input format:** [GENERIC_INPUT_FORMAT.md](GENERIC_INPUT_FORMAT.md) — JSON for analysis (point_contacts, pins, lines, planes) and optimization (candidate_matrix, modified_constraints).
- **Example files:** `matlab_script/Input_files/generic_example_analysis.json`, `generic_example_optimization.json`.
- **MATLAB:** `load_generic_input.m`, `run_wizard_analysis.m`, `run_wizard_optimization.m`; base motion set helpers `get_base_motion_set.m`, `optim_rev_from_candidates.m`.

### 2.5 Optimization logic — Base motion set

- **get_base_motion_set.m**, **optim_rev_from_candidates.m** — Generic constraint revision from a candidate matrix; only motion sets involving the modified constraint are recomputed.
- **run_wizard_optimization.m** — Loads generic optimization JSON, runs baseline + optim_rev_from_candidates, writes results.

### 2.6 MATLAB integration and compiler

- **MATLAB_INTEGRATION.md** — Calling MATLAB or compiled exe from the add-in.
- **MATLAB_COMPILER.md** — Compiling the analysis pipeline to a standalone exe.
- **benchmark_wizard_analysis.m** — Timing for run_wizard_analysis.

---

## 3. What exists today (quick reference)

| Item | Location |
|------|----------|
| Parity (21/21 Python vs Octave) | Result files in repo; `python scripts/compare_octave_python.py all` |
| Parity status doc | [docs/PARKED.md](PARKED.md) |
| Fusion 360 add-in (all 4 types) | `fusion360_addin/KstAnalysis/` — run in Fusion 360 |
| Wizard demo (meeting) | `python scripts/wizard_demo.py` |
| Inventor add-in skeleton | `inventor_addin/` (build on Windows with VS + Inventor) |
| Generic input spec (v2) | [docs/GENERIC_INPUT_FORMAT.md](GENERIC_INPUT_FORMAT.md) |
| Analysis from JSON (Python) | `scripts/run_wizard_analysis.py` — reads v2 JSON, all 4 types |
| Analysis from JSON (MATLAB) | `matlab_script/Analysis and design tool/run_wizard_analysis.m` |
| Optimization from JSON | `matlab_script/Analysis and design tool/run_wizard_optimization.m` |

---

## 4. Next steps (from plan)

1. **Fusion 360 add-in refinements:** Test all four constraint types with real CAD models; refine Line/Plane property extraction; add constraint editing.
2. **Constraint modeling guidance:** Define canonical mapping table (pin/point/line/plane to DOF effects); add UX tooltips.
3. **Example validation cases:** Implement 4-bolt plate, lip edge contact, threaded insert in Fusion to validate modeling.
4. **Optional — Inventor add-in (Windows):** Build and register; implement geometry selection.
5. **Python:** No parity work pending; all 21 cases match. Can be used for further tooling or optimization research if desired.

---

## 5. Running the wizard demo (for meetings)

From the project root:

```bash
python scripts/wizard_demo.py
```

- **Analysis Wizard tab:** Add constraints (Point/Pin/Line/Plane), use Select (or type coordinates), click **Analyze** → writes `~/KstAnalysis/wizard_input.json`.
- **Optimization Wizard tab:** Choose constraint, search type, steps; **Generate optimization plan** → `wizard_optimization.json`; **Run optimization** (MATLAB command); **Load results** → grid.

No Fusion 360, Inventor, or MATLAB required for the demo.
