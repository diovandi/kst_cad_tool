#!/usr/bin/env python3
"""
Run KST analysis in both Python and Octave for a case, then compare WTR, MRR, MTR, TOR.

Usage:
  python scripts/compare_octave_python.py <case_name_or_number>

Examples:
  python scripts/compare_octave_python.py 1
  python scripts/compare_octave_python.py case1a_chair_height

Steps:
  1. Run Python pipeline, write results_python_<case>.txt
  2. Run Octave batch (octave run_case_batch.m <num>), write results_octave_<case>.txt
  3. Read both files and compare with configurable tolerances
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


# Case name (no .m) to Octave case number 1-21
CASE_NAME_TO_NUM = {
    "case1a_chair_height": 1,
    "case1b_chair_height_angle": 2,
    "case2a_cube_scalability": 3,
    "case2b_cube_tradeoff": 4,
    "case3a_cover_leverage": 5,
    "case3b_cover_symmetry": 6,
    "case3c_cover_orient": 7,
    "case4a_endcap_tradeoff": 8,
    "case4b_endcap_circlinsrch": 9,
    "case5a_printer_4screws_orient": 10,
    "case5b_printer_4screws_line": 11,
    "case5c_printer_snap_orient": 12,
    "case5d_printer_snap_line": 13,
    "case5e_printer_partingline": 14,
    "case5f1_printer_line_size": 15,
    "case5f2_printer_sideline_size": 16,
    "case5g_printer_5d": 17,
    "case5rev_a_printer_2screws": 18,
    "case5_printer_allscrews": 19,
    "case5rev_d_printer_remove2_bot_screw": 20,
    "case5rev_b_printer_flat_partingline": 21,
}


def parse_result_file(path: Path) -> dict[str, float]:
    """Parse a results_*.txt file (tab-separated: WTR\tvalue)."""
    out: dict[str, float] = {}
    for line in path.read_text().strip().splitlines():
        line = line.strip()
        if not line:
            continue
        parts = line.split("\t")
        if len(parts) >= 2:
            try:
                out[parts[0].strip()] = float(parts[1].strip())
            except ValueError:
                pass
    return out


# Tolerances for comparison (rtol 5% for solver/rounding/combo-order differences)
ATOL = 1e-3
RTOL = 0.05


def run_one_case(case_num: int, case_name: str, repo_root: Path, quiet: bool = False) -> bool:
    """Run Python and Octave for one case, compare; return True if match."""
    py_result_path = repo_root / f"results_python_{case_name}.txt"
    octave_result_path = repo_root / "matlab_script" / f"results_octave_{case_name}.txt"

    # 1. Run Python
    if not quiet:
        print(f"  Python...", end=" ", flush=True)
    r = subprocess.run(
        [sys.executable, str(repo_root / "scripts" / "run_python_case.py"), str(case_num)],
        cwd=repo_root,
        capture_output=True,
        text=True,
        timeout=120,
    )
    if r.returncode != 0:
        if not quiet:
            print("FAIL (Python error)")
            print((r.stderr or r.stdout or "")[:500])
        return False
    if not quiet:
        print("ok", end=" ")

    # 2. Run Octave (pipe stdin for cases that use input())
    if not quiet:
        print("Octave...", end=" ", flush=True)
    stdin_input: str | None = None
    if case_num == 3:
        stdin_input = "1\n"  # scale
    elif case_num == 4:
        stdin_input = "7\n"  # ct_2 (number of constraint points)
    elif case_num == 8:
        stdin_input = "0\n"  # no_snap (0 = non-HOC model)
    r = subprocess.run(
        ["octave", "--no-gui", "run_case_batch.m", str(case_num)],
        cwd=repo_root / "matlab_script",
        capture_output=True,
        text=True,
        timeout=120,
        input=stdin_input,
    )
    if r.returncode != 0:
        if not quiet:
            print("FAIL (Octave error)")
            print((r.stderr or r.stdout or "")[:500])
        return False
    if not quiet:
        print("ok", end=" ")

    # 3. Compare
    if not py_result_path.is_file() or not octave_result_path.is_file():
        if not quiet:
            print("FAIL (missing result file)")
        return False
    py_vals = parse_result_file(py_result_path)
    oct_vals = parse_result_file(octave_result_path)
    all_ok = True
    for m in ["WTR", "MRR", "MTR", "TOR"]:
        p = py_vals.get(m)
        o = oct_vals.get(m)
        if p is None or o is None:
            all_ok = False
            break
        if o == 0:
            ok = abs(p - o) <= ATOL
        else:
            ok = abs(p - o) <= ATOL or abs(p - o) / abs(o) <= RTOL
        if not ok:
            all_ok = False
            break
    if not quiet:
        print("PASS" if all_ok else "FAIL")
    return all_ok


def main() -> int:
    if len(sys.argv) != 2:
        print("Usage: python scripts/compare_octave_python.py <case_name_or_number|all>", file=sys.stderr)
        return 1

    arg = sys.argv[1].strip().lower()
    repo_root = Path(__file__).resolve().parent.parent

    if arg == "all":
        # Run all cases 1..21
        passed = []
        failed = []
        for case_num in range(1, 22):
            case_name = next(k for k, v in CASE_NAME_TO_NUM.items() if v == case_num)
            print(f"Case {case_num:2d} {case_name}:", end=" ", flush=True)
            ok = run_one_case(case_num, case_name, repo_root, quiet=False)
            if ok:
                passed.append((case_num, case_name))
            else:
                failed.append((case_num, case_name))
        print()
        print(f"Passed: {len(passed)}/21")
        if failed:
            print("Failed:", ", ".join(f"{n} ({name})" for n, name in failed))
        return 0 if not failed else 1

    # Single case
    if arg.isdigit():
        case_num = int(arg)
        if case_num < 1 or case_num > 21:
            print(f"Case number must be 1..21, got {case_num}", file=sys.stderr)
            return 1
        case_name = next(k for k, v in CASE_NAME_TO_NUM.items() if v == case_num)
    else:
        case_name = arg.replace(".m", "").strip()
        if case_name not in CASE_NAME_TO_NUM:
            print(f"Unknown case: {case_name}", file=sys.stderr)
            return 1
        case_num = CASE_NAME_TO_NUM[case_name]

    py_result_path = repo_root / f"results_python_{case_name}.txt"
    octave_result_path = repo_root / "matlab_script" / f"results_octave_{case_name}.txt"

    # 1. Run Python
    print("Running Python pipeline...")
    r = subprocess.run(
        [sys.executable, str(repo_root / "scripts" / "run_python_case.py"), str(case_num)],
        cwd=repo_root,
        capture_output=True,
        text=True,
        timeout=120,
    )
    if r.returncode != 0:
        print(r.stderr or r.stdout, file=sys.stderr)
        return 1
    if r.stdout:
        print(r.stdout.strip())

    # 2. Run Octave (pipe stdin for cases that use input())
    print("Running Octave batch...")
    stdin_input = None
    if case_num == 3:
        stdin_input = "1\n"
    elif case_num == 4:
        stdin_input = "7\n"
    elif case_num == 8:
        stdin_input = "0\n"
    r = subprocess.run(
        ["octave", "--no-gui", "run_case_batch.m", str(case_num)],
        cwd=repo_root / "matlab_script",
        capture_output=True,
        text=True,
        timeout=120,
        input=stdin_input,
    )
    if r.returncode != 0:
        print(r.stderr or r.stdout, file=sys.stderr)
        return 1
    if r.stdout:
        print(r.stdout.strip())

    # 3. Compare
    if not py_result_path.is_file():
        print(f"Python result file not found: {py_result_path}", file=sys.stderr)
        return 1
    if not octave_result_path.is_file():
        print(f"Octave result file not found: {octave_result_path}", file=sys.stderr)
        return 1

    py_vals = parse_result_file(py_result_path)
    oct_vals = parse_result_file(octave_result_path)

    metrics = ["WTR", "MRR", "MTR", "TOR"]
    all_ok = True
    print("\nComparison (atol=%.0e, rtol=%.0e):" % (ATOL, RTOL))
    print("-" * 60)
    for m in metrics:
        p = py_vals.get(m)
        o = oct_vals.get(m)
        if p is None or o is None:
            print(f"  {m}: Python={p}  Octave={o}  (missing)")
            all_ok = False
            continue
        if o == 0:
            ok = abs(p - o) <= ATOL
        else:
            ok = abs(p - o) <= ATOL or abs(p - o) / abs(o) <= RTOL
        status = "OK" if ok else "DIFF"
        if not ok:
            all_ok = False
        print(f"  {m}: Python={p:.6g}  Octave={o:.6g}  [{status}]")
    print("-" * 60)
    print("PASS" if all_ok else "FAIL")
    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())
