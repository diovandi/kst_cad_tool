#!/usr/bin/env python3
"""
Compare Python and Octave/MATLAB full results to thesis reference values (Ch 10/11).

Reference values are taken from:
  - Chapter 10: Table 10.2 (Thompson's chair), 10.6 (Cube 7cp), 10.7 (Cube scale=1), 10.10 (Battery cover)
  - Chapter 11: Table 11.4 (Cube 7cp same as 10.6), 11.5 (Cube 15cp baseline)

Usage:
  python scripts/compare_to_thesis.py [case_name_or_number] [--matlab]
  python scripts/compare_to_thesis.py all [--matlab]

With no argument, compares case 1 (Thompson) only.
Reads results_python_<case>_full.txt from repo root and results_octave_ or results_matlab_<case>_full.txt
from matlab_script/. With --matlab, uses MATLAB results when available.
"""

from __future__ import annotations

import sys
from pathlib import Path

# Thesis reference values from Chapter 10 and 11 (Rusli dissertation).
# Keys: case name (no .m). Values: dict with WTR, MRR, MTR, TOR, optional LAR_WTR, LAR_MTR,
# optional wtr_motion (list of 11: Om_x..Pitch, TR), optional no_mot_unique, notes.
THESIS_REF: dict[str, dict] = {
    "case1a_chair_height": {
        "source": "Ch 10 Table 10.2",
        "WTR": 0.191,
        "MRR": 1.000,
        "MTR": 1.001,
        "TOR": 1.001,
        "LAR_WTR": 5.236,
        "LAR_MTR": 0.999,
        "wtr_motion": [0.000, 0.708, 0.706, 2.000, 1.724, 1.731, 0.001, 0.191],  # omega(3), rho(3), h, TR (thesis table: 8 values; we use 10 for motion + TR)
        "no_mot_unique": 21,
        "notes": "Thompson's chair. Thesis WTR motion: omega=(0, 0.708, 0.706), rho=(2, 1.724, 1.731), h=0.001, TR=0.191. Sign of omega/rho may differ.",
    },
    "case2a_cube_scalability": {
        "source": "Ch 10 Table 10.7 (scale=1)",
        "WTR": 0.200,
        "MRR": 1.000,
        "MTR": 0.486,
        "TOR": 0.486,
        "LAR_WTR": 5.003,
        "LAR_MTR": 2.057,
        "notes": "Cube scale factor 1.",
    },
    "case2b_cube_tradeoff": {
        "source": "Ch 10 Table 10.6",
        "WTR": 0.200,
        "MRR": 1.000,
        "MTR": 0.486,
        "TOR": 0.486,
        "LAR_WTR": 5.003,
        "LAR_MTR": 2.057,
        "wtr_motion_1": [0.577, 0.577, 0.577, 0.333, 0.750, 0.417, 0.083, 0.200],
        "notes": "Cube 7 constraints (CP2,CP3,CP4,CP5,CP7,CP10,CP12). WTR Motion 1 in thesis.",
    },
    "case3a_cover_leverage": {
        "source": "Ch 10 Table 10.10 (battery cover baseline)",
        "WTR": 2.000,
        "MRR": 1.500,
        "MTR": 2.000,
        "TOR": 1.333,
        "LAR_WTR": 0.500,
        "LAR_MTR": 0.500,
        "notes": "Battery cover assembly (HOC).",
    },
    "case4a_endcap_tradeoff": {
        "source": "Ch 10 Table 10.14 (end cap Non-HOC baseline)",
        "WTR": 1.829,
        "MRR": 3.028,
        "MTR": 2.855,
        "TOR": 0.943,
        "LAR_WTR": 0.547,
        "LAR_MTR": 0.350,
        "no_mot_unique": 148,
        "notes": "End cap assembly, non-HOC (cp-only, 24 points). Processed 282 motions, 148 unique.",
    },
    "case5a_printer_4screws_orient": {
        "source": "Ch 10 Table 10.18 (printer housing baseline)",
        "WTR": 2.437,
        "MRR": 4.555,
        "MTR": 17.628,
        "TOR": 3.870,
        "LAR_WTR": 0.410,
        "LAR_MTR": 0.057,
        "no_mot_unique": 213,
        "wtr_motion": [0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 0.322, 3.25, 0.0, 0.0, 2.437],
        "notes": "Printer housing 4 screws. WTR motion: axis (0,0,1), point (0.322, 3.25, 0), Pitch 0, TR 2.437.",
        "cp_table": [
            {"CP": i, "Active_Pct": a, "Best_Resistance_Pct": b}
            for i, (a, b) in enumerate(
                [
                    (27.2, 2.3), (26.0, 1.5), (27.2, 2.9), (27.2, 2.3), (27.2, 0.3),
                    (23.7, 0.0), (23.7, 0.0), (23.7, 0.0), (23.7, 0.0),
                    (17.9, 0.0), (17.9, 5.5), (17.9, 0.0), (17.9, 5.2),
                    (38.7, 1.5), (38.7, 0.9), (63.6, 6.4), (63.6, 2.9),
                    (45.4, 7.8), (47.4, 6.9), (40.5, 8.1), (39.9, 7.2), (39.0, 5.8), (49.7, 5.5),
                ],
                start=1,
            )
        ],
    },
    "case5e_printer_partingline": {
        "source": "Ch 10 Table 10.18 (printer baseline, same as case5a)",
        "WTR": 2.437,
        "MRR": 4.555,
        "MTR": 17.628,
        "TOR": 3.870,
        "LAR_WTR": 0.410,
        "LAR_MTR": 0.057,
        "no_mot_unique": 213,
        "wtr_motion": [0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 0.322, 3.25, 0.0, 0.0, 2.437],
        "notes": "Printer parting line study; baseline metrics same as case5a.",
        "cp_table": [
            {"CP": i, "Active_Pct": a, "Best_Resistance_Pct": b}
            for i, (a, b) in enumerate(
                [
                    (27.2, 2.3), (26.0, 1.5), (27.2, 2.9), (27.2, 2.3), (27.2, 0.3),
                    (23.7, 0.0), (23.7, 0.0), (23.7, 0.0), (23.7, 0.0),
                    (17.9, 0.0), (17.9, 5.5), (17.9, 0.0), (17.9, 5.2),
                    (38.7, 1.5), (38.7, 0.9), (63.6, 6.4), (63.6, 2.9),
                    (45.4, 7.8), (47.4, 6.9), (40.5, 8.1), (39.9, 7.2), (39.0, 5.8), (49.7, 5.5),
                ],
                start=1,
            )
        ],
    },
}

# Case number to name (match run_python_case.py)
CASE_NUM_TO_NAME: dict[int, str] = {
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

ATOL = 1e-3
RTOL = 0.05


def _close(a: float, b: float) -> bool:
    if b == 0:
        return abs(a) <= ATOL
    return abs(a - b) <= ATOL or abs(a - b) / abs(b) <= RTOL


def main() -> int:
    repo_root = Path(__file__).resolve().parent.parent
    if str(repo_root) not in sys.path:
        sys.path.insert(0, str(repo_root))
    from scripts.compare_octave_python import parse_full_result_file

    use_matlab = "--matlab" in sys.argv
    argv = [a for a in sys.argv[1:] if a != "--matlab"]
    engine_prefix = "matlab" if use_matlab else "octave"
    ref_label = "MATLAB" if use_matlab else "Octave"
    alt_prefix = "octave" if use_matlab else "matlab"
    alt_label = "Octave" if use_matlab else "MATLAB"

    if len(argv) >= 1 and argv[0].strip().lower() == "all":
        cases = [(i, CASE_NUM_TO_NAME[i]) for i in range(1, 22)]
    elif len(argv) >= 1:
        arg = argv[0].strip()
        if arg.isdigit():
            n = int(arg)
            if n < 1 or n > 21:
                print(f"Case number must be 1..21, got {n}", file=sys.stderr)
                return 1
            cases = [(n, CASE_NUM_TO_NAME[n])]
        else:
            name = arg.replace(".m", "").strip()
            num = next((k for k, v in CASE_NUM_TO_NAME.items() if v == name), None)
            if num is None:
                print(f"Unknown case: {arg}", file=sys.stderr)
                return 1
            cases = [(num, name)]
    else:
        cases = [(1, "case1a_chair_height")]

    lines: list[str] = []
    for case_num, case_name in cases:
        ref = THESIS_REF.get(case_name)
        py_path = repo_root / f"results_python_{case_name}_full.txt"
        ref_path = repo_root / "matlab_script" / f"results_{engine_prefix}_{case_name}_full.txt"
        ref_label_this = ref_label
        if not ref_path.is_file() and (repo_root / "matlab_script" / f"results_{alt_prefix}_{case_name}_full.txt").is_file():
            ref_path = repo_root / "matlab_script" / f"results_{alt_prefix}_{case_name}_full.txt"
            ref_label_this = alt_label

        if not py_path.is_file():
            lines.append(f"\n{case_name} (case {case_num}): Python full result not found. Run: python scripts/run_python_case.py {case_num} --full")
            continue
        if not ref_path.is_file():
            lines.append(f"\n{case_name} (case {case_num}): {ref_label} full result not found. Run batch for case {case_num} (e.g. with --matlab for MATLAB).")
            continue

        py_data = parse_full_result_file(py_path)
        ref_data = parse_full_result_file(ref_path)

        lines.append(f"\n{'='*70}")
        lines.append(f"Case {case_num}: {case_name}")
        if ref:
            lines.append(f"Thesis reference: {ref.get('source', '')}  {ref.get('notes', '')}")
        lines.append("")

        # Metrics: Thesis vs Python vs Octave/MATLAB
        metrics = ["WTR", "MRR", "MTR", "TOR", "LAR_WTR", "LAR_MTR"]
        lines.append(f"METRICS (Thesis | Python | {ref_label_this})")
        lines.append("-" * 60)
        for m in metrics:
            th = ref.get(m) if ref else None
            py = py_data["metrics"].get(m)
            oc = ref_data["metrics"].get(m)
            if th is not None:
                py_ok = _close(float(py), float(th)) if py is not None else False
                oc_ok = _close(float(oc), float(th)) if oc is not None else False
                status = "OK" if (py_ok and oc_ok) else "DIFF"
                lines.append(f"  {m:8}  Thesis={th:.4f}  Python={py}  {ref_label_this}={oc}  [{status}]")
            else:
                lines.append(f"  {m:8}  (no ref)  Python={py}  {ref_label_this}={oc}")
        lines.append("")

        # Counts
        if ref and "no_mot_unique" in ref:
            th_n = ref["no_mot_unique"]
            py_n = py_data["counts"].get("no_mot_unique")
            oc_n = ref_data["counts"].get("no_mot_unique")
            lines.append(f"COUNTS  no_mot_unique  Thesis={th_n}  Python={py_n}  {ref_label_this}={oc_n}")
        lines.append("")

        # WTR motion (if thesis has it): compare TR and approximate screw
        if ref and "wtr_motion" in ref:
            th_m = ref["wtr_motion"]
            py_m = py_data.get("wtr_motion") or []
            oc_m = ref_data.get("wtr_motion") or []
            lines.append("WTR_MOTION  (Thesis has omega(3), rho(3), h, TR)")
            if len(th_m) >= 8:
                lines.append(f"  Thesis TR={th_m[-1]:.4f}  Python TR={py_m[10] if len(py_m)>=11 else '?'}  {ref_label_this} TR={oc_m[10] if len(oc_m)>=11 else '?'}")
            if len(py_m) >= 11 and len(oc_m) >= 11:
                tr_ok = _close(py_m[10], oc_m[10])
                lines.append(f"  Python vs {ref_label_this} TR: {'OK' if tr_ok else 'DIFF'}")
        lines.append("")

    print("\n".join(lines))

    # Summary: for cases with thesis ref, report match
    with_ref = [c for c in cases if THESIS_REF.get(c[1])]
    if with_ref:
        print("\n" + "="*70)
        print("Summary vs thesis (cases with Ch 10/11 reference)")
        for _num, name in with_ref:
            ref = THESIS_REF[name]
            py_path = repo_root / f"results_python_{name}_full.txt"
            ref_path = repo_root / "matlab_script" / f"results_{engine_prefix}_{name}_full.txt"
            if not ref_path.is_file() and use_matlab:
                ref_path = repo_root / "matlab_script" / f"results_{alt_prefix}_{name}_full.txt"
            if not py_path.is_file() or not ref_path.is_file():
                continue
            py_data = parse_full_result_file(py_path)
            ok = True
            for m in ["WTR", "MRR", "MTR", "TOR"]:
                if ref.get(m) is None:
                    continue
                if not _close(py_data["metrics"].get(m) or 0, ref[m]):
                    ok = False
                    break
            print(f"  {name}: {'PASS' if ok else 'DIFF'} (vs {ref.get('source', '')})")

    return 0


if __name__ == "__main__":
    sys.exit(main())
