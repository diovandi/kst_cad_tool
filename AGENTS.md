# AGENTS.md

## Cursor Cloud specific instructions

This is a Python library project (no running services, databases, or web servers). The core product is the `kst_rating_tool` package under `src/`.

### Quick reference

- **Install**: `pip install -e ".[dev]"` (editable with test deps)
- **Tests**: `pytest --cov=kst_rating_tool --cov-report=term-missing` (50+ tests across multiple `tests/test_*.py` files)
- **Run a case**: `python3 scripts/run_python_case.py <case_name_or_number>` (e.g. `1`)
- **Lint**: No linter is configured in this project

### Project structure highlights

- `src/kst_rating_tool/` — core Python library (constraints, wrench, motion, rating, optimization).
- `fusion360_addin/KstAnalysis/` — Fusion 360 add-in (Python). Key file: `commands/analysis_command.py` (native command palette UI with Point/Pin/Line/Plane constraint types).
- `scripts/run_wizard_analysis.py` — external analysis script invoked by the Fusion add-in; reads v2 JSON with all four constraint types.
- `scripts/run_wizard_optimization.py` — optimization runner for wizard JSON; supports point/pin/line/plane candidate matrices.
- `fusion360_addin/KstAnalysis/visualizer.py` — Fusion viewport markers for constraint visualization.
- `inventor_addin/` — C# Inventor add-in skeleton (Windows only).

### Non-obvious notes

- The system `python3` (3.12) is used directly; no conda/venv activation is needed in the cloud environment.
- `python` is not on PATH; always use `python3` to run scripts.
- pytest is installed to `~/.local/bin`; ensure `PATH` includes `$HOME/.local/bin` (the update script handles this).
- Results files are written to `results/python/`.
- Fusion analysis command supports save/load constraint config, invert direction, and per-row editing.
- The `scripts/wizard_demo.py` requires a display (tkinter GUI); it will not work headless without `DISPLAY` set.
- CAD add-ins (Inventor, Fusion 360, SolidWorks) are Windows-only and not runnable in this environment.
- The wizard input JSON is now at version 2: it contains `point_contacts`, `pins`, `lines`, and `planes` arrays (see `docs/GENERIC_INPUT_FORMAT.md`).
