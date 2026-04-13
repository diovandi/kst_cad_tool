# AGENTS.md

This document provides comprehensive guidance for AI coding agents working on the KST Rating Tool project. The reader of this file is expected to know nothing about the project.

## Cursor Cloud / Development Environment Quick Reference

### Install (editable with test deps)
```bash
pip install -e ".[dev]"
```

### Tests
```bash
pytest --cov=kst_rating_tool --cov-report=term-missing
```
(50+ tests across multiple `tests/test_*.py` files)

### Run a case
```bash
# By case number or name
python3 scripts/run_python_case.py <case_name_or_number>  # e.g., 1

# Optional --no-snap N for legacy .m branches
python3 scripts/run_python_case.py 1 --no-snap 5

# Writes Result - <case>.html with text outputs
```

### Wizard optimization sweep
```bash
python3 scripts/run_wizard_optimization.py <optimization.json> [out.tsv]
```
Supports candidate matrices for all constraint types (point/pin/line/plane). See `docs/dev/GENERIC_INPUT_FORMAT.md`.

### Lint
No linter is configured in this project.

### Key Environment Notes
- The system `python3` (3.12) is used directly; no conda/venv activation needed in the cloud environment
- `python` is not on PATH; always use `python3` to run scripts
- pytest is installed to `~/.local/bin`; ensure PATH includes `$HOME/.local/bin` (handled by environment)
- Results files are written to `results/python/`
- CAD add-ins (Inventor, Fusion 360, SolidWorks) are Windows-only and not runnable in this environment
- The wizard input JSON is at version 2: contains `point_contacts`, `pins`, `lines`, and `planes` arrays
- `scripts/wizard_demo.py` requires a display (tkinter GUI) and will not work headless

## Project Overview

**KST Rating Tool** is a Python re-implementation of Leonard Rusli's kinematic screw theory (KST) based mechanical assembly rating tool, originally implemented in MATLAB. The project is part of a thesis titled *"Implementation of Mechanical Assembly Rating Tool Based on Kinematic Screw Theory."*

The core purpose is to analyze mechanical assemblies by rating constraint sets using four metrics:
- **WTR** (Worst Transfer Rate): Minimum resistance across all motion sets
- **MRR** (Mean Resistance Ratio): Average resistance normalized by maximum
- **MTR** (Mean Transfer Rate): Average resistance across all motions
- **TOR** (Transfer Opportunity Ratio): MTR/MRR ratio

## Technology Stack

- **Primary Language**: Python 3.10+ (developed and tested with Python 3.12)
- **Core Dependencies**: NumPy (≥1.23), SciPy (≥1.10), Matplotlib (≥3.7)
- **Optional Dependencies** (install via `pip install -e ".[extra_name]"`):
  - `dev`: pytest, pytest-cov, ruff, mypy
  - `optimization`: scikit-learn (≥1.2) for surrogate/ML optimization
  - `gpu`: torch (≥2.0) for GPU acceleration
  - `directml`: torch-directml for Windows AMD/Intel GPU via DirectX 12
- **Build System**: setuptools (pyproject.toml-based)
- **CAD Integration**: Fusion 360 (Python add-in), Inventor (C#/.NET), SolidWorks (C# prototype)
- **MATLAB Compatibility**: Validated against MATLAB 2018b and GNU Octave

## Project Structure

```
kst_cad_tool/
├── src/kst_rating_tool/          # Core Python library
│   ├── constraints.py            # Constraint dataclasses (Point, Pin, Line, Plane)
│   ├── pipeline.py               # Main analysis pipeline (analyze_constraints, etc.)
│   ├── wrench.py                 # Wrench system generation from constraints
│   ├── motion.py                 # Screw motion computation and reciprocal motion
│   ├── rating.py                 # Rating metrics calculation (WTR, MRR, MTR, TOR)
│   ├── rating_batched.py         # Batched rating with NumPy/Torch backends
│   ├── input_wr.py               # Input wrench composition
│   ├── react_wr.py               # Reaction wrench composition
│   ├── combination.py            # Combination preprocessing for constraint sets
│   ├── numeric_backend.py        # GPU/CPU backend selection (NumPy/Torch)
│   ├── linalg_torch.py           # PyTorch linear algebra utilities
│   ├── utils.py                  # Utility functions (matlab_rank, matlab_null)
│   ├── io_legacy.py              # Legacy MATLAB .m file loading
│   ├── reference_data.py         # Reference constraint data
│   ├── wizard_geometry.py        # Geometry validation for wizard inputs
│   ├── reporting.py              # HTML/text report generation
│   ├── optimization/             # Optimization algorithms
│   │   ├── revision.py           # Constraint revision (optim_main_rev)
│   │   ├── reduction.py          # Constraint reduction (optim_main_red)
│   │   ├── addition.py           # Constraint addition (optim_main_add)
│   │   ├── modification.py       # Generic constraint modification
│   │   ├── search_space.py       # Search space parameterizations
│   │   ├── parameterizations.py  # Parameterization builders
│   │   ├── postproc.py           # Optimization post-processing
│   │   ├── sensitivity.py        # Sensitivity analysis
│   │   ├── surrogate.py          # Surrogate model optimization
│   │   ├── surrogate_bo.py       # Bayesian optimization
│   │   ├── surrogate_pareto.py   # Pareto frontier optimization
│   │   ├── reduction_ml.py       # ML-based reduction
│   │   └── specmot_optim.py      # Specified motion optimization
│   └── ui/                       # UI components (wizard demo)
│       ├── analysis_ui.py        # Analysis wizard UI
│       ├── optimization_ui.py    # Optimization wizard UI
│       └── dialogs.py            # Dialog helpers
├── tests/                        # Test suite (50+ tests across 15+ test files)
├── scripts/                      # CLI scripts and utilities
│   ├── run_python_case.py        # Run analysis on legacy cases
│   ├── run_wizard_analysis.py    # Run analysis on wizard JSON input
│   ├── run_wizard_optimization.py # Run optimization sweep
│   ├── run_wizard_revision.py    # Parametric constraint revision
│   ├── run_sensitivity_analysis.py # Constraint sensitivity analysis
│   ├── run_python_specmot.py     # Specified motion analysis
│   ├── wizard_demo.py            # Standalone GUI demo (tkinter; needs display)
│   ├── compare_octave_python.py  # Compare Python vs Octave results
│   ├── profile_kst_hotspots.py   # Performance profiling
│   └── benchmark_kst_accelerator.py # Benchmark GPU/CPU backends
├── fusion360_addin/              # Fusion 360 add-in (Python)
│   ├── KstAnalysis/              # Source code
│   │   └── commands/analysis_command.py  # Main palette UI with all 4 constraint types
│   └── KstAnalysis.bundle/       # Built bundle for distribution
├── inventor_addin/               # Inventor add-in (C#/.NET)
├── solidworks_addin/             # SolidWorks add-in prototype (C#)
├── shared_cad_ui/                # Shared .NET wizard layer
├── matlab_script/                # Original MATLAB/Octave code
│   ├── Analysis and design tool/ # Main MATLAB scripts
│   └── Input_files/              # Case files (.m and .json)
├── docs/                         # Documentation
│   ├── dev/                      # Developer docs
│   │   ├── GENERIC_INPUT_FORMAT.md  # v2 JSON spec
│   │   ├── PROJECT_STATUS_SUMMARY.md
│   │   ├── GPU_RUNTIME.md        # GPU/DirectML setup
│   │   └── CAD_RUNTIME_PATHS.md  # CAD integration paths
│   ├── validation/               # Validation results (21/21 cases pass)
│   ├── cad/                      # CAD integration docs
│   └── thesis/                   # Thesis-related docs
└── results/                      # Output directory (gitignored local artifacts)
```

## Build and Installation

### Install (editable with dev dependencies)
```bash
pip install -e ".[dev]"
```

### Install with all optional features
```bash
pip install -e ".[dev,optimization,gpu]"
```

### Install with DirectML (Windows AMD/Intel GPU)
```bash
# Use a dedicated Python 3.12 venv for torch-directml (avoids CUDA conflicts)
python3 -m venv .venv-directml
source .venv-directml/bin/activate  # On Windows: .venv-directml\Scripts\Activate.ps1
pip install torch-directml
pip install -e ".[dev]"
```
See `docs/dev/GPU_RUNTIME.md` for GPU backend details.

### Verify installation
```bash
python3 -c "from kst_rating_tool import analyze_constraints; print('OK')"

# Verify DirectML (if installed)
python3 -c "import torch_directml; print(torch_directml.device())"
```

## Testing

### Run all tests with coverage
```bash
pytest --cov=kst_rating_tool --cov-report=term-missing
```

### Run tests without coverage
```bash
pytest
```

### Run specific test files
```bash
pytest tests/test_basic.py
pytest tests/test_constraints.py
```

### Run slow tests (benchmarks)
```bash
pytest -m slow
```

### Skip slow tests
```bash
pytest -m "not slow"
```

### Run benchmark tests (manual only)
```bash
pytest benchmarks/test_benchmark_surrogates.py -v -s --no-cov
```

## Code Style and Linting

This project uses **Ruff** for linting and formatting:

```bash
# Run linter (critical errors only)
ruff check src tests scripts --select E9,F821,F822,F823

# Run full linter
ruff check src tests scripts
```

This project uses **mypy** for type checking:

```bash
mypy src/kst_rating_tool
```

Configuration in `pyproject.toml`:
- Line length: 100 characters
- Target Python version: 3.10
- Excluded: `fusion360_addin/KstAnalysis.bundle`

## Running the Application

### Run a legacy case (1-21)
```bash
# By case number
python scripts/run_python_case.py 1

# By case name
python scripts/run_python_case.py case1a_chair_height

# With full output
python scripts/run_python_case.py 1 --full
```

### Run analysis from wizard JSON
```bash
python scripts/run_wizard_analysis.py <input.json> <output.txt>
```

### Run optimization sweep
```bash
python scripts/run_wizard_optimization.py <optimization.json> [output.tsv]
```

### Run wizard demo (GUI)
```bash
python scripts/wizard_demo.py
```

### Compare Python vs Octave results
```bash
# Single case
python scripts/compare_octave_python.py 1

# All 21 cases
python scripts/compare_octave_python.py all
```

## Core Module Architecture

### Constraints (`constraints.py`)
Four constraint types are supported:

1. **PointConstraint** (`cp`): `[x, y, z, nx, ny, nz]` - position and unit normal
2. **PinConstraint** (`cpin`): `[x, y, z, ax, ay, az]` - center and axis
3. **LineConstraint** (`clin`): `[mx, my, mz, lx, ly, lz, nx, ny, nz, length]` - midpoint, line dir, constraint normal, length
4. **PlaneConstraint** (`cpln`): `[px, py, pz, nx, ny, nz, type, ...props]` - midpoint, normal, type (1=rect, 2=circ), properties

### Pipeline (`pipeline.py`)
Main entry points:
- `analyze_constraints(constraints)` - Basic analysis returning rating metrics
- `analyze_constraints_detailed(constraints)` - Full analysis with all intermediate results
- `analyze_constraints_gpu(constraints)` - GPU-accelerated analysis
- `analyze_specified_motions(constraints, specmot)` - Analysis for known loading conditions

### Wrench System (`wrench.py`)
- `cp_to_wrench(constraints)` - Converts constraints to wrench systems
- Returns `WrenchSystem` dataclass containing (k×6) wrench matrices

### Motion (`motion.py`)
- `ScrewMotion` dataclass representing screw motions
- `rec_mot(W)` - Computes reciprocal motion from wrench matrix
- `specmot_row_to_screw(row)` - Converts specified motion array to screw

### Rating (`rating.py`)
- `RatingResults` dataclass containing WTR, MRR, MTR, TOR
- `aggregate_ratings(R)` - Aggregates resistance matrix to rating metrics
- Individual constraint rating functions: `rate_cp`, `rate_cpin`, `rate_clin`, `rate_cpln`

## Optimization Module

The `optimization` package provides algorithms ported from MATLAB:

### Constraint Revision (`revision.py`)
- `RevisionConfig` - Configuration for revision runs
- `optim_main_rev(baseline, config, no_step)` - Main revision loop
- `optim_rev(...)` - Single revision step

### Constraint Reduction (`reduction.py`)
- `optim_main_red(baseline, no_red)` - Try removing `no_red` constraints
- Returns WTR/MRR/MTR/TOR and percent change per removal combination

### Constraint Addition (`addition.py`)
- `optim_main_add(...)` - Stub for constraint addition (MATLAB version preliminary)

### Search Spaces (`search_space.py`)
- `move_lin_srch` - Move along a line
- `move_pln_srch` - Move on a plane
- `orient1d_srch` - 1D orientation search
- `orient2d_srch` - 2D orientation search
- `resize_lin_srch` - Resize line length
- `resize_rectpln_srch` - Resize rectangular plane
- `resize_circpln_srch` - Resize circular plane

## Wizard Input Format (v2)

The generic input format for CAD add-ins is JSON with the following structure:

```json
{
  "version": 2,
  "point_contacts": [[x, y, z, nx, ny, nz], ...],
  "pins": [[x, y, z, ax, ay, az], ...],
  "lines": [[mx, my, mz, lx, ly, lz, nx, ny, nz, length], ...],
  "planes": [
    [px, py, pz, nx, ny, nz, 1, ux, uy, uz, xlen, vx, vy, vz, ylen],
    [px, py, pz, nx, ny, nz, 2, radius]
  ]
}
```

See `docs/dev/GENERIC_INPUT_FORMAT.md` for full specification.

## Fusion 360 Add-in

### Development
Source code: `fusion360_addin/KstAnalysis/`

### Build bundle
```bash
python fusion360_addin/build_bundle.py
```

### Verify bundle sync
```bash
python fusion360_addin/build_bundle.py --verify
```

### Install bundle
Copy `fusion360_addin/KstAnalysis.bundle/` to `%APPDATA%\Autodesk\ApplicationPlugins\`

### Features
- All four constraint types: Point, Pin, Line, Plane
- Type-aware selection filters
- Orientation methods for Point: Normal to Plane, Two Points, Along Line/Axis
- Save/Load config, Invert Direction, Update Selected, Edit Index
- Writes v2 JSON for external analysis
- **Fusion analysis command supports**: save/load constraint config, invert direction, and per-row editing
- The `scripts/run_wizard_analysis.py` reads v2 JSON with all four constraint types and writes HTML reports
- `scripts/run_wizard_optimization.py` supports point/pin/line/plane candidate matrices with global `constraint_index` and mixed products

## CI/CD (GitHub Actions)

The `.github/workflows/pytest.yml` workflow runs:
1. **Quality checks**: Ruff lint, mypy type check, Fusion bundle verify, markdown link check
2. **Tests**: pytest with coverage
3. **Benchmarks** (manual trigger): Surrogate benchmark tests

## Key Conventions

### Import Style
```python
from __future__ import annotations  # Always include for type annotations
import numpy as np
from numpy.typing import NDArray
```

### Array Shapes
- Screw motions: `(10,)` or `(n, 10)` - `[omega(3), rho(3), h, n(3)]`
- Wrenches: `(k, 6)` - rows are `[omega(3), mu(3)]`
- Constraint positions: `(N, 3)`
- Resistance matrix R: `(no_mot_all, total_cp)`

### MATLAB Compatibility
The code is designed to match MATLAB/Octave behavior:
- Uses `matlab_rank()` and `matlab_null()` for consistent linear algebra
- Rounds to 4 decimal places before duplicate checks
- Uses `_matlab_mldivide()` to replicate MATLAB's `A \ b`
- Combo order matches MATLAB's `nchoosek` (lexicographic)

### Numerical Backend Selection
```python
from kst_rating_tool.numeric_backend import resolve_accelerator

backend = resolve_accelerator("auto")  # "numpy", "torch", "torch_cuda", "auto"
```

## Testing Strategy

- **Unit tests**: Individual module functionality in `tests/test_*.py`
- **Integration tests**: End-to-end workflows (e.g., `test_run_wizard_analysis_integration.py`)
- **Parity tests**: Compare against MATLAB/Octave reference (21 benchmark cases)
- **GPU tests**: GPU acceleration validation (`test_gpu_acceleration.py`)
- **Optimization tests**: Algorithm correctness and smoke tests

All 21 benchmark cases pass parity validation (atol=1e-3, rtol=5%).

## Result Files

Analysis outputs are written to:
- `results/python/results_python_<case>.txt` - Tab-separated metrics
- `results/python/Result - <case>.html` - HTML report
- `results/python/<case>_detailed.json` - Full analysis results

## Common Tasks

### Add a new constraint type
1. Add dataclass in `constraints.py`
2. Add to `ConstraintSet` and `to_matlab_style_arrays()`
3. Add wrench generation in `wrench.py`
4. Add rating functions in `rating.py`
5. Add to `react_wr_5_compose` in `react_wr.py`
6. Update tests and documentation

### Add an optimization algorithm
1. Create module in `optimization/`
2. Export from `optimization/__init__.py`
3. Add tests in `tests/test_optimization_*.py`
4. Update `scripts/run_wizard_optimization.py` if CLI needed

### Debug a case mismatch
```bash
python scripts/deep_comparison.py <case_number>
python scripts/debug_case1_parity.py
```

## Environment Notes

### Cursor Cloud Environment
- The system `python3` (3.12) is used directly; no conda/venv activation needed
- `python` is not on PATH; **always use `python3`** to run scripts
- pytest is installed to `~/.local/bin`; PATH includes `$HOME/.local/bin` by default
- Results files are written to `results/python/`
- CAD add-ins (Fusion 360, Inventor, SolidWorks) are Windows-only and **not runnable** in headless/cloud environments
- `scripts/wizard_demo.py` requires a display (tkinter GUI) and **will not work headless** without `DISPLAY` set

### General Environment
- Use `python3` (not `python`) on systems where both exist
- The cloud environment uses Python 3.12 directly; no conda activation needed
- pytest is installed to `~/.local/bin`; ensure PATH includes `$HOME/.local/bin`
- CAD add-ins are Windows-only and not runnable in headless/cloud environments
- `wizard_demo.py` requires a display (tkinter GUI)

## References

- `docs/dev/GENERIC_INPUT_FORMAT.md` - Input JSON specification
- `docs/dev/PROJECT_STATUS_SUMMARY.md` - Current status and parity
- `docs/validation/COMPARISON.md` - Python vs Octave comparison guide
- `docs/validation/PARKED.md` - Validation status (21/21 cases pass)
- `fusion360_addin/README.md` - Fusion add-in setup
- `inventor_addin/README.md` - Inventor add-in setup
- `solidworks_addin/README.md` - SolidWorks add-in setup
