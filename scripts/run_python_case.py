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
    full = False
    no_snap_value = 0
    positional: list[str] = []
    it = iter(sys.argv[1:])
    for a in it:
        if a == "--full":
            full = True
        elif a == "--no-snap":
            try:
                no_snap_value = int(next(it))
            except Exception:
                print("Usage: python scripts/run_python_case.py <case_name_or_number> [--full] [--no-snap N]", file=sys.stderr)
                return 1
        else:
            positional.append(a)

    if len(positional) != 1:
        print("Usage: python scripts/run_python_case.py <case_name_or_number> [--full] [--no-snap N]", file=sys.stderr)
        print("Example: python scripts/run_python_case.py case1a_chair_height", file=sys.stderr)
        return 1

    arg = positional[0].strip()
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
    from kst_rating_tool.reporting import result_close, result_open, write_full_report_txt, write_report
    import numpy as np

    constraints = load_case_m_file(case_path, no_snap_value=no_snap_value)

    detailed = analyze_constraints_detailed(constraints)
    results = detailed.rating
    if full:
        full_path = repo_root / "results" / "python" / f"results_python_{case_name}_full.txt"
        write_full_report_txt(detailed, full_path)
        print(f"Wrote {full_path} (full report)")

    out_path = repo_root / "results" / "python" / f"results_python_{case_name}.txt"
    with open(out_path, "w") as f:
        f.write(f"WTR\t{results.WTR:.10g}\n")
        f.write(f"MRR\t{results.MRR:.10g}\n")
        f.write(f"MTR\t{results.MTR:.10g}\n")
        f.write(f"TOR\t{results.TOR:.10g}\n")

    # HTML report (MATLAB-style "Result - <inputfile>.html")
    # Use detailed output so the motion + CP tables are available.
    out_dir = repo_root / "results" / "python"
    out_dir.mkdir(parents=True, exist_ok=True)
    mot_all = detailed.mot_all
    if mot_all.size:
        uniq_idx = np.unique(mot_all, axis=0, return_index=True)[1]
        mot_all_uniq = mot_all[uniq_idx, :]
    else:
        mot_all_uniq = np.empty((0, 10), dtype=float)
    html_f = result_open(case_name, output_dir=out_dir)
    try:
        write_report(
            html_f,
            inputfile=case_name,
            rating=detailed.rating,
            mot_all_uniq=mot_all_uniq,
            R_uniq=detailed.Ri,
            total_cp=int(detailed.Ri.shape[1]) if detailed.Ri.size else 0,
            no_mot=int(detailed.Ri.shape[0]) if detailed.Ri.size else 0,
            combo=detailed.combo,
            combo_proc=detailed.combo_proc,
        )
    finally:
        result_close(html_f)

    print(f"Wrote {out_path} (WTR={results.WTR:.4f}, MRR={results.MRR:.4f}, MTR={results.MTR:.4f}, TOR={results.TOR:.4f})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
