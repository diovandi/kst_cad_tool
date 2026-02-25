# KST CAD Tool — Progress and Orientation

**Date:** February 25, 2026  
**Purpose:** Snapshot of the current state of the project so you can quickly regain context and resume work.

---

## 1. Big-picture goal

This repository is a Python-centric, CAD-integrated reimplementation of Leonard Rusli’s kinematic screw theory (KST) assembly rating tool:

- **Python backend** (`src/kst_rating_tool/`): Numerical engine for constraint-based assembly rating and optimization.
- **MATLAB/Octave reference** (`matlab_script/`): Original OSU scripts used as the ground truth for parity.
- **Inventor add-in skeleton** (`inventor_addin/`): C# add-in for Autodesk Inventor that will drive the analysis/optimization wizards.
- **Wizard demo** (`scripts/wizard_demo.py`): Standalone Python GUI that mimics the planned Inventor wizards for meetings/demos.

Today, the **backend math engine is complete and validated** against Octave/MATLAB for the full 21-case benchmark set. The main remaining work is around **CAD integration, UX, and potential future optimization improvements**.

For a concise project-level summary see also:

- `docs/PROJECT_STATUS_SUMMARY.md`
- `docs/THESIS_PROGRESS_UPDATE.md`

This document is aimed at you as the active developer: **what exists, where it lives, how to rerun it, and what’s next.**

---

## 2. Code structure (Python side)

### 2.1 Package layout

- **`src/kst_rating_tool/constraints.py`**: Constraint data structures (point contacts, pins, lines, planes) mirroring MATLAB `cp`, `cpin`, `clin`, `cpln`.
- **`src/kst_rating_tool/wrench.py`**: Wrench generation from constraints; pivot set and motion set construction.
- **`src/kst_rating_tool/motion.py`**: Reciprocal motion computation and motion enumeration.
- **`src/kst_rating_tool/rating.py`**: Aggregation of motion resistance into WTR, MRR, MTR, TOR and local/aggregate resistance (LAR_*).
- **`src/kst_rating_tool/combination.py`**: Combination logic (e.g. 5-constraint motion-generating sets); mirrors MATLAB `combo_preproc` and related routines.
- **`src/kst_rating_tool/react_wr.py` / `input_wr.py`**: Reaction vs input wrench handling.
- **`src/kst_rating_tool/io_legacy.py`**: Loader for the original MATLAB `.m` case files in `matlab_script/Input_files/` (parses `cp`, `cpin`, `clin`, `cpln`, etc.).
- **`src/kst_rating_tool/pipeline.py`**: High-level analysis entry points (`analyze_constraints`, `analyze_constraints_detailed`).
- **`src/kst_rating_tool/reporting.py`**: Text report writers (`write_full_report_txt`), used to generate the `_full` result files.
- **`src/kst_rating_tool/utils.py`**: Shared helpers, small numerical utilities.

Key API functions you actually call:

- **`analyze_constraints(constraints)`** → `RatingResult` (WTR, MRR, MTR, TOR).  
- **`analyze_constraints_detailed(constraints)`** → includes:
  - `rating` (same metrics),
  - `counts` (total_combo, combo_proc_count, no_mot_half, no_mot_unique),
  - `mot_all` and `mot_proc`,
  - CP-level breakdowns.

These are what the command-line scripts wrap.

### 2.2 Optimization and specified motion

Under `src/kst_rating_tool/optimization/`:

- **`revision.py`**: Factorial search over normalized parameters in \[-1, 1\] to revise constraint geometry. Wraps the `optim_main_rev` logic.
- **`reduction.py`**: Constraint removal (`optim_main_red`-style).
- **`specmot_optim.py`**: Optimization for specified motions.
- **`sensitivity.py`**: Position/orientation sensitivity analysis.
- **`search_space.py`, `parameterizations.py`, `postproc.py`, `surrogate.py`, `modification.py`**: Helpers for search spaces, parameter encodings, post-processing, and (future) surrogate approaches.

Specified-motion (known loading) is exposed at the top level:

- **`analyze_specified_motions(constraints, specmot)`**: Mirror of MATLAB `main_specmot_orig.m` and option 6.

---

## 3. Scripts you actually run

All commands below assume you are in the repo root (`kst_cad_tool/`) with the editable install active:

```bash
conda activate kst_kst_engine   # or your env
pip install -e .
```

### 3.1 Run a single case (Python only)

Script: `scripts/run_python_case.py`

- **What it does**: Loads a MATLAB `.m` case file via `io_legacy`, runs the Python engine, and writes result files.
- **Usage**:

```bash
python scripts/run_python_case.py 1
python scripts/run_python_case.py case1a_chair_height
python scripts/run_python_case.py 1 --full
```

- **Output (now organized under `results/python/`):**
  - `results/python/results_python_<casename>.txt`
  - `results/python/results_python_<casename>_full.txt` (with `--full`)

The `_full` variant contains:

- `METRICS` (WTR, MRR, MTR, TOR, LAR_WTR, LAR_MTR)
- `COUNTS` (total_combo, combo_proc_count, no_mot_half, no_mot_unique)
- `WTR_MOTION` (11 numbers: Om, Mu, Rho, Pitch, Total_Resistance)
- `CP_TABLE` (per-contact ratings)

### 3.2 Python vs Octave/MATLAB comparison

Script: `scripts/compare_octave_python.py`

- **What it does**: Runs Python and Octave (or MATLAB) for one or all cases and compares WTR/MRR/MTR/TOR (and optionally full tables).
- **Basic usage**:

```bash
# Single case, summary metrics only
python scripts/compare_octave_python.py 1

# All 21 cases, summary metrics
python scripts/compare_octave_python.py all

# All cases, full report comparison (requires *_full.txt for both engines)
python scripts/compare_octave_python.py all --full
```

- **Paths used**:
  - Python: `results/python/results_python_<case>.txt` and `_full.txt`
  - Octave/MATLAB: `matlab_script/results_octave_<case>.txt` / `results_matlab_<case>.txt`

This is the main entry point to **reconfirm parity**.

### 3.3 Compare vs thesis tables

Script: `scripts/compare_to_thesis.py`

- **What it does**: For the thesis-reference cases (Chapter 10/11), compares Python and Octave/MATLAB full outputs to the values recorded in the dissertation.
- **Usage**:

```bash
# All thesis-reference cases
python scripts/compare_to_thesis.py all

# Single case (e.g. Thompson’s chair)
python scripts/compare_to_thesis.py 1
```

- **Python input**: `results/python/results_python_<case>_full.txt`
- **Octave/MATLAB input**: `matlab_script/results_octave_<case>_full.txt` or `results_matlab_<case>_full.txt`

See also `docs/THESIS_COMPARISON.md` for written notes.

### 3.4 Deep four-way comparison (thesis vs MATLAB vs Octave vs Python)

Script: `scripts/deep_comparison.py`

- **What it does**: Parses all `_full` results and generates `docs/DEEP_COMPARISON.md` with multi-column tables:
  - Metrics, counts, WTR motion, and CP tables,
  - Classification (exact, within_tol, significant, major).
- **Usage**:

```bash
python scripts/deep_comparison.py          # Octave vs thesis vs Python
python scripts/deep_comparison.py --matlab # include MATLAB results if present
```

- **Python input**: `results/python/results_python_<case>_full.txt`

Good for **diagnosing any non-trivial parity issues**.

### 3.5 Visualization

Script: `scripts/visualize_octave_python.py`

- **What it does**: Aggregates WTR/MRR/MTR/TOR from Python and Octave for all cases and produces:
  - `docs/octave_python_comparison_raw.csv`
  - Figures under `docs/figures/` (bar charts, scatter plots, worst-case deviations).
- **Usage**:

```bash
# Use existing results (faster)
python scripts/visualize_octave_python.py

# Regenerate all results then visualize
python scripts/visualize_octave_python.py --run
```

- **Python input**: `results/python/results_python_<case>.txt`

### 3.6 Specified-motion (known loading) analysis

Script: `scripts/run_python_specmot.py`

- **What it does**: Reuses the motions from a full analysis, picks one motion screw, and runs a specified-motion rating.
- **Usage**:

```bash
# Case 1, motion index 0 (first unique motion)
python scripts/run_python_specmot.py 1 0

# Prompt for motion index
python scripts/run_python_specmot.py 1
```

- **Output**:
  - Console: WTR/MRR/MTR/TOR for the chosen motion.
  - File: `results/python/results_python_specmot_<casename>.txt`

---

## 4. Validation status (where things stand)

### 4.1 Python vs Octave/MATLAB

- **Status**: As of Feb 2025 (see `docs/PROJECT_STATUS_SUMMARY.md` and `docs/PARKED.md`), **all 21 benchmark cases pass**:
  - WTR, MRR, MTR, TOR match within `atol = 1e-3`, `rtol = 5%`.
  - This has been re-verified using `python scripts/compare_octave_python.py all`.
- **Reference cases (with thesis tables)**:
  - `case1a_chair_height` (Thompson’s chair),
  - `case2a_cube_scalability`, `case2b_cube_tradeoff`,
  - `case3a_cover_leverage`,
  - printer baselines (`case5a_printer_4screws_orient`, `case5e_printer_partingline`).

For details, see:

- `docs/PROJECT_STATUS_SUMMARY.md` (high-level),
- `docs/THESIS_PROGRESS_UPDATE.md` (supervisor meeting notes),
- `docs/COMPARISON.md` and `docs/MATLAB_TO_PYTHON_COVERAGE.md` (mapping between MATLAB and Python functions).

### 4.2 Known historical quirks

Earlier snapshots had divergences mainly in:

- **Endcap case (case4a)**: combo ordering / duplicate-motion handling,
- **Printer cases (10–20)**: which motion is selected as WTR-minimizing when there are many similar motions.

These have been brought within tolerance in the current code, and the result files under `results/python/` reflect the passing state.

---

## 5. Filesystem organization (after cleanup)

To reduce clutter and make it obvious where artifacts live, results are now organized as follows:

```text
kst_cad_tool/
├── results/
│   └── python/
│       ├── results_python_<case>.txt
│       ├── results_python_<case>_full.txt
│       ├── results_python_specmot_<case>.txt
│       └── results_simple_full.txt
├── matlab_script/
│   ├── Analysis and design tool/
│   ├── Input_files/
│   └── results_octave_*_full.txt, results_matlab_*_full.txt, etc.
├── docs/
│   ├── PROJECT_STATUS_SUMMARY.md
│   ├── THESIS_PROGRESS_UPDATE.md
│   ├── COMPARISON.md
│   ├── MATLAB_TO_PYTHON_COVERAGE.md
│   ├── DEEP_COMPARISON.md         # generated
│   ├── octave_python_comparison_raw.csv
│   └── figures/
├── scripts/
├── src/kst_rating_tool/
└── inventor_addin/
```

**Key point:** anything beginning with `results_python_*.txt` now lives under `results/python/`, and all scripts have been updated accordingly.

---

## 6. Inventor add-in and wizard demo status

### 6.1 Inventor add-in (`inventor_addin/`)

What exists:

- C# project `KstAnalysisWizardAddIn.csproj` with:
  - `ApplicationAddInServer.cs` (Inventor add-in entry),
  - `AnalysisWizard/ConstraintDefinitionWizard.cs`,
  - `OptimizationWizard/OptimizationWizardForm.cs`,
  - `InputFileGenerator.cs` (writes the same generic JSON format used by MATLAB/Python).
- `Autodesk.KstAnalysisWizard.Inventor.addin` manifest for Inventor registration.

High-level flow:

1. User selects geometry in Inventor.
2. Add-in builds a JSON file matching `docs/GENERIC_INPUT_FORMAT.md`.
3. External engine (MATLAB or Python) runs analysis/optimization.
4. Results are displayed back in the wizard UI.

### 6.2 Wizard demo (`scripts/wizard_demo.py`)

- Pure-Python GUI (tkinter) that mimics the planned add-in:
  - **Analysis Wizard tab**: define constraints, select, analyze → writes JSON.
  - **Optimization Wizard tab**: select constraints, choose search space, generate optimization plan, and load results.
- Designed to run on any machine without Inventor or MATLAB for demos.

To run:

```bash
python scripts/wizard_demo.py
```

Output JSONs are written to your user directory (see the README for the exact path on Windows).

---

## 7. How to pick up where you left off

When you come back to this project, a typical “resume work” sequence:

1. **Recreate/activate the env** (if needed):
   ```bash
   conda create -n kst_kst_engine python=3.10 numpy scipy matplotlib pytest -y
   conda activate kst_kst_engine
   pip install -e .
   pip install -e ".[dev]"  # if you want tests and extras
   ```
2. **Verify the engine still passes parity**:
   ```bash
   python scripts/compare_octave_python.py all
   ```
3. **Refresh your memory of thesis mapping and coverage**:
   - Skim `docs/PROJECT_STATUS_SUMMARY.md`,
   - Skim `docs/MATLAB_TO_PYTHON_COVERAGE.md`,
   - Skim `docs/THESIS_PROGRESS_UPDATE.md`.
4. **Run the wizard demo** if you’re focusing on CAD UX:
   ```bash
   python scripts/wizard_demo.py
   ```

---

## 8. Next likely steps (suggested)

These are the most natural next tasks, consistent with existing docs:

- **CAD integration**:
  - Finish wiring the Inventor add-in so it can export constraints and call MATLAB or Python.
  - Decide whether the first deployed backend is MATLAB (compiled) or Python.
- **Performance / parallelism**:
  - Add optional multiprocessing to `analyze_constraints_detailed` (per-combination or per-motion evaluation).
  - Benchmark against the existing Octave pipeline.
- **Smarter optimization** (future work):
  - Implement a 1D line search (single parameter along a line) on top of the existing black-box rating.
  - Explore surrogate or heuristic methods for high-dimensional searches.

For all of these, the existing scripts (`run_python_case.py`, `compare_octave_python.py`, `deep_comparison.py`) and organized results under `results/python/` should give you **fast feedback** that nothing regresses numerically.

