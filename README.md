## KST Rating Tool (Python)

This project is a Python re-implementation of Leonard Rusli's kinematic screw theory (KST) based assembly rating tool, as used in your supervisor's MATLAB scripts and your thesis proposal *"Implementation of Mechanical Assembly Rating Tool Based on Kinematic Screw Theory"*.

Phase 1 focuses on the **backend math engine** only:

- Constraint representation (point, pin, line, plane)
- Wrench generation and pivot set construction
- Reciprocal motion computation
- Resistance calculation and rating metrics (WTR, MRR, MTR, TOR)

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

- **Python**: `python scripts/run_python_case.py <case_name_or_number>` (e.g. `1` or `case1a_chair_height`)
- **Octave**: `cd matlab_script && octave --no-gui run_case_batch.m <case_number>`
- **Compare**: `python scripts/compare_octave_python.py <case_name_or_number>`

### Status

This backend is under active development as part of Phase 1 of the thesis and aims to achieve numerical agreement with the original MATLAB implementation and Rusli's published case studies.

