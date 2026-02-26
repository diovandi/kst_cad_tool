#!/usr/bin/env python3
"""
Run KST analysis on a MATLAB case file and write WTR, MRR, MTR, TOR to a text file.

Usage:
  python scripts/run_python_case.py <case_name_or_number> [--full]
  python -m scripts.run_python_case <case_name_or_number> [--full]

Examples:
  python scripts/run_python_case.py case1a_chair_height
  python scripts/run_python_case.py 1 --full

Output:
  results/python/results_python_<casename>.txt (for comparison with Octave).
  With --full: also results/python/results_python_<casename>_full.txt (metrics, counts, WTR motion, CP table).
"""

from __future__ import annotations

import sys
from pathlib import Path

# Ensure src is on path for imports
if __name__ == "__main__":
    repo_root = Path(__file__).resolve().parent.parent
    if str(repo_root / "src") not in sys.path:
        sys.path.insert(0, str(repo_root / "src"))

from kst_rating_tool.reference_data import CASE_NUM_TO_NAME


def main() -> int:
    args = [a for a in sys.argv[1:] if a != "--full"]
    full = "--full" in sys.argv[1:]
    if len(args) != 1:
        print("Usage: python scripts/run_python_case.py <case_name_or_number> [--full]", file=sys.stderr)
        print("Example: python scripts/run_python_case.py case1a_chair_height", file=sys.stderr)
        return 1

    arg = args[0].strip()
    if arg.isdigit():
        n = int(arg)
        if n < 1 or n > 21:
            print(f"Case number must be 1..21, got {n}", file=sys.stderr)
            return 1
        case_name = CASE_NUM_TO_NAME[n]
    else:
        case_name = arg
        if case_name.endswith(".m"):
            case_name = case_name[:-2]

    repo_root = Path(__file__).resolve().parent.parent
    case_path = repo_root / "matlab_script" / "Input_files" / f"{case_name}.m"
    if not case_path.is_file():
        print(f"Case file not found: {case_path}", file=sys.stderr)
        return 1

    from kst_rating_tool.io_legacy import load_case_m_file
    from kst_rating_tool import analyze_constraints, analyze_constraints_detailed
    from kst_rating_tool.reporting import write_full_report_txt

    constraints = load_case_m_file(case_path)

    if full:
        detailed = analyze_constraints_detailed(constraints)
        results = detailed.rating
        full_path = repo_root / "results" / "python" / f"results_python_{case_name}_full.txt"
        write_full_report_txt(detailed, full_path)
        print(f"Wrote {full_path} (full report)")
    else:
        results = analyze_constraints(constraints)

    out_path = repo_root / "results" / "python" / f"results_python_{case_name}.txt"
    with open(out_path, "w") as f:
        f.write(f"WTR\t{results.WTR:.10g}\n")
        f.write(f"MRR\t{results.MRR:.10g}\n")
        f.write(f"MTR\t{results.MTR:.10g}\n")
        f.write(f"TOR\t{results.TOR:.10g}\n")

    print(f"Wrote {out_path} (WTR={results.WTR:.4f}, MRR={results.MRR:.4f}, MTR={results.MTR:.4f}, TOR={results.TOR:.4f})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
