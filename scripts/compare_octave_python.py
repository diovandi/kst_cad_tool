#!/usr/bin/env python3
"""
Run KST analysis in both Python and Octave (or MATLAB) for a case, then compare results.

Usage:
  python scripts/compare_octave_python.py <case_name_or_number> [--full] [--matlab]
  python scripts/compare_octave_python.py all [--full] [--matlab]

Without --full: compare WTR, MRR, MTR, TOR only.
With --full: run Python with --full and Octave/MATLAB (writes full), then compare
  metrics, counts, WTR motion row, and CP table (atol=1e-3, rtol=5%).
With --matlab: use MATLAB R2018b instead of Octave (writes results_matlab_*).
"""

from __future__ import annotations

import math
import subprocess
import sys
from pathlib import Path
from typing import Any


# MATLAB binary: use standard install path if present, else "matlab" from PATH
_MATLAB_CANDIDATES = ("/usr/local/MATLAB/R2018b/bin/matlab", "matlab")
MATLAB_BIN = next((p for p in _MATLAB_CANDIDATES if p == "matlab" or Path(p).is_file()), "matlab")
MATLAB_TIMEOUT = 300  # JVM startup is slower than Octave

# Case name (no .m) to case number 1-21
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


def parse_full_result_file(path: Path) -> dict[str, Any]:
    """Parse results_*_full.txt into metrics, counts, wtr_motion (11 floats), cp_table (list of dicts)."""
    text = path.read_text()
    out: dict[str, Any] = {
        "metrics": {},
        "counts": {},
        "wtr_motion": [],
        "cp_table": [],
    }
    section: str | None = None
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        if line == "METRICS":
            section = "metrics"
            continue
        if line == "COUNTS":
            section = "counts"
            continue
        if line == "WTR_MOTION":
            section = "wtr_motion"
            continue
        if line == "CP_TABLE":
            section = "cp_table"
            continue
        if section == "metrics":
            parts = line.split("\t")
            if len(parts) >= 2:
                key = parts[0].strip()
                try:
                    val = float(parts[1].strip())
                except ValueError:
                    val = parts[1].strip()
                out["metrics"][key] = val
            continue
        if section == "counts":
            parts = line.split("\t")
            if len(parts) >= 2:
                try:
                    out["counts"][parts[0].strip()] = int(float(parts[1].strip()))
                except (ValueError, TypeError):
                    out["counts"][parts[0].strip()] = float(parts[1].strip())
            continue
        if section == "wtr_motion":
            if line.startswith("Om_x") or "Om_x" in line:
                continue
            parts = line.split("\t")
            if len(parts) >= 11:
                try:
                    out["wtr_motion"] = [float(x.strip()) for x in parts[:11]]
                except ValueError:
                    pass
            section = None
            continue
        if section == "cp_table":
            if line.startswith("CP\t") or line.startswith("CP "):
                continue
            parts = line.split("\t")
            if len(parts) >= 4:
                try:
                    out["cp_table"].append({
                        "CP": int(float(parts[0])),
                        "Individual_Rating": float(parts[1]),
                        "Active_Pct": float(parts[2]),
                        "Best_Resistance_Pct": float(parts[3]),
                    })
                except (ValueError, TypeError, IndexError):
                    pass
    return out


def _num_close(p: float, o: float, atol: float = ATOL, rtol: float = RTOL) -> bool:
    if math.isinf(p) and math.isinf(o):
        return True
    if math.isinf(p) or math.isinf(o):
        return False
    if o == 0 and p == 0:
        return True
    if o == 0:
        return abs(p) <= atol
    return abs(p - o) <= atol or abs(p - o) / abs(o) <= rtol


def compare_full_results(
    py_data: dict[str, Any],
    ref_data: dict[str, Any],
    ref_label: str = "Octave",
) -> tuple[bool, list[str]]:
    """Compare parsed full results; return (all_ok, list of message lines)."""
    msgs: list[str] = []
    all_ok = True

    for key in ["WTR", "MRR", "MTR", "TOR", "LAR_WTR", "LAR_MTR"]:
        p = py_data["metrics"].get(key)
        o = ref_data["metrics"].get(key)
        if key == "LAR_MTR" and (p is None or o is None):
            continue
        if p is None or o is None:
            msgs.append(f"  METRICS {key}: missing in one file")
            all_ok = False
            continue
        if isinstance(p, str) or isinstance(o, str):
            continue
        if not _num_close(float(p), float(o)):
            msgs.append(f"  METRICS {key}: Python={p:.6g}  {ref_label}={o:.6g}  [DIFF]")
            all_ok = False
        else:
            msgs.append(f"  METRICS {key}: OK")

    for key in ["total_combo", "combo_proc_count", "no_mot_half", "no_mot_unique"]:
        p = py_data["counts"].get(key)
        o = ref_data["counts"].get(key)
        if p is None or o is None:
            msgs.append(f"  COUNTS {key}: missing")
            all_ok = False
            continue
        if int(p) != int(o):
            msgs.append(f"  COUNTS {key}: Python={p}  {ref_label}={o}  [DIFF]")
            all_ok = False
        else:
            msgs.append(f"  COUNTS {key}: OK")

    pw = py_data.get("wtr_motion") or []
    ow = ref_data.get("wtr_motion") or []
    if len(pw) != 11 or len(ow) != 11:
        msgs.append(f"  WTR_MOTION: missing or wrong length (py={len(pw)}, ref={len(ow)})")
        all_ok = False
    else:
        diff = False
        for i in range(11):
            if not _num_close(pw[i], ow[i]):
                msgs.append(f"  WTR_MOTION[{i}]: Python={pw[i]:.6g}  {ref_label}={ow[i]:.6g}  [DIFF]")
                diff = True
                all_ok = False
        if not diff:
            msgs.append("  WTR_MOTION: OK")

    pt = py_data.get("cp_table") or []
    ot = ref_data.get("cp_table") or []
    cp_table_ok = True
    if len(pt) != len(ot):
        msgs.append(f"  CP_TABLE: row count Python={len(pt)}  {ref_label}={len(ot)}  [DIFF]")
        all_ok = False
        cp_table_ok = False
    else:
        for i in range(len(pt)):
            for col in ["Individual_Rating", "Active_Pct", "Best_Resistance_Pct"]:
                pv = pt[i].get(col)
                ov = ot[i].get(col)
                if pv is None or ov is None:
                    continue
                if not _num_close(float(pv), float(ov)):
                    msgs.append(f"  CP_TABLE CP{pt[i].get('CP', i+1)} {col}: Python={pv:.6g}  {ref_label}={ov:.6g}  [DIFF]")
                    all_ok = False
                    cp_table_ok = False
    if cp_table_ok:
        msgs.append("  CP_TABLE: OK")

    return all_ok, msgs


def run_one_case(
    case_num: int,
    case_name: str,
    repo_root: Path,
    quiet: bool = False,
    full: bool = False,
    engine: str = "octave",
) -> bool:
    """Run Python and Octave (or MATLAB) for one case, compare; return True if match."""
    engine_prefix = "matlab" if engine == "matlab" else "octave"
    ref_label = "MATLAB" if engine == "matlab" else "Octave"
    py_result_path = repo_root / f"results_python_{case_name}.txt"
    ref_result_path = repo_root / "matlab_script" / f"results_{engine_prefix}_{case_name}.txt"
    py_full_path = repo_root / f"results_python_{case_name}_full.txt"
    ref_full_path = repo_root / "matlab_script" / f"results_{engine_prefix}_{case_name}_full.txt"

    # 1. Run Python
    if not quiet:
        print(f"  Python...", end=" ", flush=True)
    py_cmd = [sys.executable, str(repo_root / "scripts" / "run_python_case.py"), str(case_num)]
    if full:
        py_cmd.append("--full")
    r = subprocess.run(
        py_cmd,
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

    # 2. Run Octave or MATLAB
    if not quiet:
        print(f"{ref_label}...", end=" ", flush=True)
    if engine == "matlab":
        matlab_r = (
            f"try; cp_set={case_num}; run('run_case_batch'); "
            "catch e; fprintf(2, '%s\\n', e.message); exit(1); end; exit(0);"
        )
        r = subprocess.run(
            [MATLAB_BIN, "-nosplash", "-nodesktop", "-r", matlab_r],
            cwd=repo_root / "matlab_script",
            capture_output=True,
            text=True,
            timeout=MATLAB_TIMEOUT,
        )
    else:
        stdin_input: str | None = None
        if case_num == 3:
            stdin_input = "1\n"  # scale
        elif case_num == 4:
            stdin_input = "7\n"  # ct_2
        elif case_num == 8:
            stdin_input = "0\n"  # no_snap
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
            print(f"FAIL ({ref_label} error)")
            print((r.stderr or r.stdout or "")[:500])
        return False
    if not quiet:
        print("ok", end=" ")

    # 3. Compare
    if full:
        if not py_full_path.is_file() or not ref_full_path.is_file():
            if not quiet:
                print("FAIL (missing full result file)")
            return False
        py_data = parse_full_result_file(py_full_path)
        ref_data = parse_full_result_file(ref_full_path)
        all_ok, _ = compare_full_results(py_data, ref_data, ref_label=ref_label)
    else:
        if not py_result_path.is_file() or not ref_result_path.is_file():
            if not quiet:
                print("FAIL (missing result file)")
            return False
        py_vals = parse_result_file(py_result_path)
        ref_vals = parse_result_file(ref_result_path)
        all_ok = True
        for m in ["WTR", "MRR", "MTR", "TOR"]:
            p = py_vals.get(m)
            o = ref_vals.get(m)
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
    argv = [a for a in sys.argv[1:] if a not in ("--full", "--matlab")]
    full = "--full" in sys.argv[1:]
    use_matlab = "--matlab" in sys.argv[1:]
    engine = "matlab" if use_matlab else "octave"
    ref_label = "MATLAB" if use_matlab else "Octave"
    engine_prefix = "matlab" if use_matlab else "octave"
    if len(argv) != 1:
        print("Usage: python scripts/compare_octave_python.py <case_name_or_number|all> [--full] [--matlab]", file=sys.stderr)
        return 1

    arg = argv[0].strip().lower()
    repo_root = Path(__file__).resolve().parent.parent

    if arg == "all":
        passed = []
        failed = []
        for case_num in range(1, 22):
            case_name = next(k for k, v in CASE_NAME_TO_NUM.items() if v == case_num)
            print(f"Case {case_num:2d} {case_name}:", end=" ", flush=True)
            ok = run_one_case(case_num, case_name, repo_root, quiet=False, full=full, engine=engine)
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
    ref_result_path = repo_root / "matlab_script" / f"results_{engine_prefix}_{case_name}.txt"
    py_full_path = repo_root / f"results_python_{case_name}_full.txt"
    ref_full_path = repo_root / "matlab_script" / f"results_{engine_prefix}_{case_name}_full.txt"

    # 1. Run Python
    print("Running Python pipeline" + (" (full)" if full else "") + "...")
    py_cmd = [sys.executable, str(repo_root / "scripts" / "run_python_case.py"), str(case_num)]
    if full:
        py_cmd.append("--full")
    r = subprocess.run(
        py_cmd,
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

    # 2. Run Octave or MATLAB
    print(f"Running {ref_label} batch...")
    if use_matlab:
        matlab_r = (
            f"try; cp_set={case_num}; run('run_case_batch'); "
            "catch e; fprintf(2, '%s\\n', e.message); exit(1); end; exit(0);"
        )
        r = subprocess.run(
            [MATLAB_BIN, "-nosplash", "-nodesktop", "-r", matlab_r],
            cwd=repo_root / "matlab_script",
            capture_output=True,
            text=True,
            timeout=MATLAB_TIMEOUT,
        )
    else:
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

    if full:
        if not py_full_path.is_file():
            print(f"Python full result file not found: {py_full_path}", file=sys.stderr)
            return 1
        if not ref_full_path.is_file():
            print(f"{ref_label} full result file not found: {ref_full_path}", file=sys.stderr)
            return 1
        py_data = parse_full_result_file(py_full_path)
        ref_data = parse_full_result_file(ref_full_path)
        all_ok, msgs = compare_full_results(py_data, ref_data, ref_label=ref_label)
        print("\nFull comparison (atol=%.0e, rtol=%.0e):" % (ATOL, RTOL))
        print("-" * 60)
        for m in msgs:
            print(m)
        print("-" * 60)
        print("PASS" if all_ok else "FAIL")
        return 0 if all_ok else 1

    if not py_result_path.is_file():
        print(f"Python result file not found: {py_result_path}", file=sys.stderr)
        return 1
    if not ref_result_path.is_file():
        print(f"{ref_label} result file not found: {ref_result_path}", file=sys.stderr)
        return 1

    py_vals = parse_result_file(py_result_path)
    ref_vals = parse_result_file(ref_result_path)

    metrics = ["WTR", "MRR", "MTR", "TOR"]
    all_ok = True
    print("\nComparison (atol=%.0e, rtol=%.0e):" % (ATOL, RTOL))
    print("-" * 60)
    for m in metrics:
        p = py_vals.get(m)
        o = ref_vals.get(m)
        if p is None or o is None:
            print(f"  {m}: Python={p}  {ref_label}={o}  (missing)")
            all_ok = False
            continue
        if o == 0:
            ok = abs(p - o) <= ATOL
        else:
            ok = abs(p - o) <= ATOL or abs(p - o) / abs(o) <= RTOL
        status = "OK" if ok else "DIFF"
        if not ok:
            all_ok = False
        print(f"  {m}: Python={p:.6g}  {ref_label}={o:.6g}  [{status}]")
    print("-" * 60)
    print("PASS" if all_ok else "FAIL")
    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())
