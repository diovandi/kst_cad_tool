# AGENTS.md

## Cursor Cloud specific instructions

This is a Python library project (no running services, databases, or web servers). The core product is the `kst_rating_tool` package under `src/`.

### Quick reference

- **Install**: `pip install -e ".[dev]"` (editable with test deps)
- **Tests**: `pytest` (9 tests in `tests/test_basic.py`)
- **Run a case**: `python3 scripts/run_python_case.py <case_name_or_number>` (e.g. `1`)
- **Lint**: No linter is configured in this project

### Non-obvious notes

- The system `python3` (3.12) is used directly; no conda/venv activation is needed in the cloud environment.
- `python` is not on PATH; always use `python3` to run scripts.
- pytest is installed to `~/.local/bin`; ensure `PATH` includes `$HOME/.local/bin` (the update script handles this).
- Results files are written to `results/python/`.
- The `scripts/wizard_demo.py` requires a display (tkinter GUI); it will not work headless without `DISPLAY` set.
- CAD add-ins (Inventor, Fusion 360, SolidWorks) are Windows-only and not runnable in this environment.
