#!/usr/bin/env python3
"""
Run KST known-loading (specified motion) analysis (Python equivalent of MATLAB option 6).

Usage:
  python scripts/run_python_specmot.py <case_name_or_number> [motion_index]
  motion_index: 0 = use first motion from full analysis; 1..N = use that row from
                the unique motion set. Omit to prompt.

Example:
  python scripts/run_python_specmot.py 1 0
  python scripts/run_python_specmot.py case1a_chair_height 1

Output: prints WTR, MRR, MTR, TOR for the specified loading; optionally writes
  results_python_specmot_<casename>.txt
"""

from __future__ import annotations

import sys
from pathlib import Path

# Case number (1-21) to case file name (no .m)
CASE_NUM_TO_NAME = {
    1: "case1a_chair_height",
    2: "case1b_chair_height_angle",
    3: "case2a_cube_scalability",
    4: "case2b_cube_tradeoff",
    5: "case3a_cover_leverage",
    6: "case3b_cover_symmetry",
    7: "case3c_cover_orient",
    8: "case4a_endcap_tradeoff",
    9: "case4b_endcap_circlinsrch",
    10: "case5a_printer_4screws_orient",
    11: "case5b_printer_4screws_line",
    12: "case5c_printer_snap_orient",
    13: "case5d_printer_snap_line",
    14: "case5e_printer_partingline",
    15: "case5f1_printer_line_size",
    16: "case5f2_printer_sideline_size",
    17: "case5g_printer_5d",
    18: "case5rev_a_printer_2screws",
    19: "case5_printer_allscrews",
    20: "case5rev_d_printer_remove2_bot_screw",
    21: "case5rev_b_printer_flat_partingline",
}


def mot_row_to_specmot_row(mot_row: "np.ndarray") -> "np.ndarray":
    """Convert one motion row (10 elements: omu, mu, rho, h) to specmot row (7: omega, rho, h)."""
    import numpy as np
    return np.concatenate([mot_row[0:3], mot_row[6:9], np.array([mot_row[9]], dtype=float)])


def main() -> int:
    if len(sys.argv) < 2:
        print("Usage: python scripts/run_python_specmot.py <case_name_or_number> [motion_index]", file=sys.stderr)
        print("  motion_index: 0 = first motion, 1..N = row from unique motion set; omit to prompt.", file=sys.stderr)
        return 1

    arg = sys.argv[1].strip()
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

    if str(repo_root / "src") not in sys.path:
        sys.path.insert(0, str(repo_root / "src"))

    import numpy as np
    from kst_rating_tool import analyze_constraints_detailed, analyze_specified_motions
    from kst_rating_tool.io_legacy import load_case_m_file

    constraints = load_case_m_file(case_path)
    detailed = analyze_constraints_detailed(constraints)
    mot_all = detailed.mot_all
    _, uniq_idx = np.unique(mot_all, axis=0, return_index=True)
    mot_all_uniq = mot_all[np.sort(uniq_idx)]
    n_mot = mot_all_uniq.shape[0]
    if n_mot == 0:
        print("No motions from full analysis; cannot run specmot.", file=sys.stderr)
        return 1

    if len(sys.argv) >= 3:
        try:
            motion_index = int(sys.argv[2])
        except ValueError:
            motion_index = 0
    else:
        motion_index = None
    if motion_index is None:
        try:
            motion_index = int(input(f"Motion index (0..{n_mot - 1}, 0 = first): ") or "0")
        except (ValueError, EOFError):
            motion_index = 0
    motion_index = max(0, min(motion_index, n_mot - 1))
    specmot_row = mot_row_to_specmot_row(mot_all_uniq[motion_index, :])
    specmot = np.atleast_2d(specmot_row)

    result = analyze_specified_motions(constraints, specmot)
    r = result.rating
    print(f"Specmot (motion index {motion_index}): WTR={r.WTR:.6f} MRR={r.MRR:.6f} MTR={r.MTR:.6f} TOR={r.TOR:.6f}")

    out_path = repo_root / f"results_python_specmot_{case_name}.txt"
    with open(out_path, "w") as f:
        f.write(f"WTR\t{r.WTR:.10g}\n")
        f.write(f"MRR\t{r.MRR:.10g}\n")
        f.write(f"MTR\t{r.MTR:.10g}\n")
        f.write(f"TOR\t{r.TOR:.10g}\n")
    print(f"Wrote {out_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
