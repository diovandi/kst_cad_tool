#!/usr/bin/env python3
"""
Reproducible Python optimization sweep for side-by-side comparison with MATLAB.

Run the same JSON the MATLAB wizard would use, then print WTR/MRR/MTR/TOR per
candidate so you can screenshot or diff against MATLAB output.

Usage:
  python3 scripts/run_optimization_parity_demo.py \\
      [path/to/generic_example_optimization.json]

Default input: matlab_script/Input_files/generic_example_optimization.json
Output: results/python/optimization_parity_demo.tsv (under repo root)
"""

from __future__ import annotations

import json
import sys
from pathlib import Path


def main(argv: list[str]) -> int:
    repo = Path(__file__).resolve().parent.parent
    default_in = repo / "matlab_script" / "Input_files" / "generic_example_optimization.json"
    in_path = Path(argv[1]).resolve() if len(argv) > 1 else default_in
    out_dir = repo / "results" / "python"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "optimization_parity_demo.tsv"

    if not in_path.is_file():
        print(f"Input not found: {in_path}", file=sys.stderr)
        return 1

    src = repo / "src"
    if str(src) not in sys.path:
        sys.path.insert(0, str(src))

    import importlib.util

    opt_script = repo / "scripts" / "run_wizard_optimization.py"
    spec = importlib.util.spec_from_file_location("run_wizard_optimization", opt_script)
    if spec is None or spec.loader is None:
        print(f"Cannot load {opt_script}", file=sys.stderr)
        return 1
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)

    argv_run = ["run_wizard_optimization.py", str(in_path), str(out_path)]
    code = mod.main(argv_run)
    if code != 0:
        return code

    print(f"Wrote: {out_path}")
    print("Compare these rows to MATLAB/Octave output for the same JSON (same candidate order).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
