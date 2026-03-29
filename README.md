## KST Rating Tool (Python)

This project is a Python re-implementation of Leonard Rusli's kinematic screw theory (KST) based assembly rating tool, as used in your supervisor's MATLAB scripts and your thesis proposal *"Implementation of Mechanical Assembly Rating Tool Based on Kinematic Screw Theory"*.

The project has two major components:

1. **Python backend math engine** (`src/kst_rating_tool/`):
   - Constraint representation — all four types: **Point, Pin, Line, Plane**
   - Wrench generation and pivot set construction
   - Reciprocal motion computation
   - Resistance calculation and rating metrics (WTR, MRR, MTR, TOR)

2. **CAD integration** (Fusion 360 add-in, Inventor add-in skeleton):
   - **Fusion 360 add-in** (`fusion360_addin/`): Native command-palette wizard for interactive constraint picking and analysis directly inside Fusion 360. Supports all four constraint types with type-aware selection filters and orientation methods.
   - **Inventor add-in skeleton** (`inventor_addin/`): C# skeleton for Autodesk Inventor integration.

### Development environment

It is recommended to use the dedicated conda environment described in the thesis plan:

```bash
conda create -n kst_kst_engine python=3.10 numpy scipy matplotlib pytest -y
conda activate kst_kst_engine
```

### Installation (editable)

From the project root:

```bash
pip install -e .
```

### Running tests

```bash
pip install -e ".[dev]"
pytest
```

If pytest fails due to an external plugin (e.g. ROS `launch_testing`), run from a clean env or run tests directly:

```bash
PYTHONPATH=src python -c "
from tests.test_basic import *
import tests.test_basic as t
for name in dir(t):
    if name.startswith('test_'):
        getattr(t, name)()
print('All tests passed.')
"
```

### Optimization (Phase 1 port)

The optimization algorithms from the MATLAB codebase are ported under `kst_rating_tool.optimization`:

- **Constraint revision** (`optim_main_rev`, `optim_rev`): Factorial search over normalized parameters in [-1, 1] per dimension to revise constraint location/orientation/size using search-space functions (line, plane, curved line, orient 1D/2D, resize line/plane). Use `analyze_constraints_detailed()` to get a baseline, then `RevisionConfig(grp_members, grp_rev_type, grp_srch_spc)` and `optim_main_rev(baseline, config, no_step)`.
- **Constraint reduction** (`optim_main_red`): Try removing `no_red` constraints at a time; returns WTR/MRR/MTR/TOR and percent change per removal combination.
- **Post-processing** (`optim_postproc`): Find optimum indices from optimization result arrays.
- **Constraint addition** (`optim_main_add`): Stub only; the MATLAB version is preliminary and contains errors.

Search-space helpers: `move_lin_srch`, `move_pln_srch`, `move_curvlin_srch`, `orient1d_srch`, `orient2d_srch`, `line_orient1d_srch`, `resize_lin_srch`, `resize_rectpln_srch`, `resize_circpln_srch`.

### Known loading (specmot) — MATLAB option 6

To rate constraints for **specified screw motions** (known loading), use the specmot API (mirrors MATLAB `main_specmot_orig.m`):

```python
from kst_rating_tool import analyze_specified_motions
# specmot: (n, 7) array, each row [omega_x, omega_y, omega_z, rho_x, rho_y, rho_z, h]
result = analyze_specified_motions(constraints, specmot)
# result.rating (WTR, MRR, MTR, TOR), result.Ri, result.mot_proc
```

From the command line:

```bash
python scripts/run_python_specmot.py <case_name_or_number> [motion_index]
# motion_index: 0 = first motion from full analysis; omit to prompt
```

### Running the same test cases in Python and Octave

You can run the original MATLAB test cases in Python (by loading the `.m` case files) and in GNU Octave (no MATLAB license required), then compare WTR, MRR, MTR, TOR. See **[docs/COMPARISON.md](docs/COMPARISON.md)** for:

- **Python**: `python scripts/run_python_case.py <case_name_or_number>` (e.g. `1` or `case1a_chair_height`). Results are written to `results/python/results_python_<case>.txt` (and `_full.txt` with `--full`). A MATLAB-style **`Result - <case>.html`** report is written alongside the text outputs. For legacy `.m` cases with multiple `no_snap` branches, use `--no-snap N` (see `io_legacy.load_case_m_file`).
- **Octave**: `cd matlab_script && octave --no-gui run_case_batch.m <case_number>`
- **Compare**: `python scripts/compare_octave_python.py <case_name_or_number>`

### Optimization from generic JSON (Python)

For a **discrete candidate matrix** (same shape as `matlab_script/Input_files/generic_example_optimization.json`), run:

```bash
python scripts/run_wizard_optimization.py <input_json> [output_tsv]
```

Use `optimization.candidate_matrix[0].constraint_type` set to `point`, `pin`, `line`, or `plane` when the revised constraint is not a point contact; `constraint_index` is 1-based **within that type**. Omit `constraint_type` for backward compatibility (indices count point contacts only). See **[docs/GENERIC_INPUT_FORMAT.md](docs/GENERIC_INPUT_FORMAT.md)**.

### Fusion 360 add-in

The primary CAD integration is the **Fusion 360 add-in** (`fusion360_addin/KstAnalysis/`). It provides a native command palette wizard inside Fusion 360 where you can:

- Select constraint type (**Point**, **Pin**, **Line**, or **Plane**)
- Pick location and orientation directly from the 3D model using type-appropriate selection filters
- Choose orientation method for Point constraints: **Normal to Plane**, **Two Points**, or **Along Line/Axis**
- **Save Config** / **Load Config** (writes `constraint_config.json`), **Invert Direction**, and **Update Selected** + **Edit Index** for per-row edits
- Build a constraint table, then run analysis to get WTR/MRR/MTR/TOR

After changing add-in source, rebuild the bundle for `%APPDATA%\\Autodesk\\ApplicationPlugins\\`: `python fusion360_addin/build_bundle.py`.

See **[fusion360_addin/README.md](fusion360_addin/README.md)** for setup instructions.

### Wizard demo (meeting preview)

A **Python skeleton** of the planned add-in (Analysis + Optimization wizards) runs without Fusion 360 or MATLAB:

```bash
python scripts/wizard_demo.py
```

Two tabs: **Analysis Wizard** (constraint table, Select, Analyze → JSON) and **Optimization Wizard** (constraint selection, search space, generate plan, load results). See **[docs/PROJECT_STATUS_SUMMARY.md](docs/PROJECT_STATUS_SUMMARY.md)** for project status.

### Windows Quick Start

1. Install [Miniconda](https://docs.conda.io/en/latest/miniconda.html) for Windows.
2. Install MATLAB for Windows; during or after install, add its `bin` folder to the system PATH (e.g. `C:\Program Files\MATLAB\R202Xb\bin`). Verify with `matlab -batch "disp('ok')"` in a terminal.
3. Clone the repo:

   ```bash
   git clone <remote-url> kst_cad_tool
   cd kst_cad_tool
   ```

4. Create and activate the Python environment:

   ```bash
   conda create -n kst_kst_engine python=3.10 numpy scipy matplotlib pytest -y
   conda activate kst_kst_engine
   pip install -e .
   ```

5. Run the wizard:

   ```bash
   python scripts\wizard_demo.py
   ```

   Output files are written under the `results/wizard/` directory in the repo.

### Status

- **Python engine:** Primary analysis backend; validated against Octave/MATLAB for **all 21 benchmark cases** (atol=1e-3, rtol=5%). See [docs/PARKED.md](docs/PARKED.md) for validation status.
- **Fusion 360 add-in:** Supports all four constraint types (Point, Pin, Line, Plane) with type-aware selection filters, orientation method selection for Point, save/load/invert/update UX, and JSON export for analysis via external Python. See [fusion360_addin/README.md](fusion360_addin/README.md).
- **Wizard input JSON:** Version 2 format with `point_contacts`, `pins`, `lines`, and `planes` arrays. See [docs/GENERIC_INPUT_FORMAT.md](docs/GENERIC_INPUT_FORMAT.md).
- **CLI:** `scripts/run_wizard_analysis.py` (analysis + HTML), `scripts/run_wizard_optimization.py` (candidate-matrix sweep).
- **Inventor add-in:** C# skeleton for Autodesk Inventor; see [docs/PROJECT_STATUS_SUMMARY.md](docs/PROJECT_STATUS_SUMMARY.md).

