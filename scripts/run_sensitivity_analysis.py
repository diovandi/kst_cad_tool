#!/usr/bin/env python3
"""
Run KST constraint sensitivity analysis (sens_analysis_pos / sens_analysis_orient).

Perturbs each constraint's position and/or orientation by a small amount and
measures the resulting change in WTR/MRR/MTR/TOR.  Useful for identifying which
constraints have the most impact on assembly rating.

Usage
-----
  python scripts/run_sensitivity_analysis.py <analysis.json>
         [--mode pos|orient|both]
         [--perturb 0.5]
         [--steps 3]
         [--output results/sensitivity.tsv]

Output TSV columns
------------------
  idx | type | label | max_WTR_chg | max_MRR_chg | max_MTR_chg | max_TOR_chg
  (values are max-absolute-% change across the perturbation grid for each constraint)

Constraints are printed to stdout ranked from most to least sensitive (by TOR change).
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def _setup_src() -> None:
    repo_root = Path(__file__).resolve().parent.parent
    src_dir = repo_root / "src"
    if str(src_dir) not in sys.path:
        sys.path.insert(0, str(src_dir))


def _load_constraints(analysis_input: dict):
    import numpy as np
    from kst_rating_tool import (
        ConstraintSet,
        LineConstraint,
        PinConstraint,
        PlaneConstraint,
        PointConstraint,
    )

    cs = ConstraintSet()
    for row in analysis_input.get("point_contacts", []) or []:
        if len(row) >= 6:
            cs.points.append(
                PointConstraint(np.array(row[0:3], dtype=float), np.array(row[3:6], dtype=float))
            )
    for row in analysis_input.get("pins", []) or []:
        if len(row) >= 6:
            cs.pins.append(
                PinConstraint(np.array(row[0:3], dtype=float), np.array(row[3:6], dtype=float))
            )
    for row in analysis_input.get("lines", []) or []:
        if len(row) >= 10:
            cs.lines.append(
                LineConstraint(
                    np.array(row[0:3], dtype=float),
                    np.array(row[3:6], dtype=float),
                    np.array(row[6:9], dtype=float),
                    float(row[9]),
                )
            )
    for row in analysis_input.get("planes", []) or []:
        if len(row) >= 7:
            cs.planes.append(
                PlaneConstraint(
                    np.array(row[0:3], dtype=float),
                    np.array(row[3:6], dtype=float),
                    int(row[6]),
                    np.array(row[7:], dtype=float),
                )
            )
    return cs


def _constraint_labels(cs) -> list[tuple[int, str, str]]:
    """Return (global_1based_idx, type_str, label) for every constraint."""
    labels = []
    offset = 1
    for i, _ in enumerate(cs.points, 1):
        labels.append((offset, "point", f"CP{i}"))
        offset += 1
    for i, _ in enumerate(cs.pins, 1):
        labels.append((offset, "pin", f"PIN{i}"))
        offset += 1
    for i, _ in enumerate(cs.lines, 1):
        labels.append((offset, "line", f"LINE{i}"))
        offset += 1
    for i, _ in enumerate(cs.planes, 1):
        labels.append((offset, "plane", f"PLANE{i}"))
        offset += 1
    return labels


def main(argv: list[str]) -> int:
    _setup_src()

    parser = argparse.ArgumentParser(
        description="Sensitivity analysis: perturb each constraint and measure rating change."
    )
    parser.add_argument("input_json", help="Path to v2 analysis JSON")
    parser.add_argument(
        "--mode", default="both", choices=["pos", "orient", "both"],
        help="Perturbation mode: pos (position), orient (orientation), or both (default: both)"
    )
    parser.add_argument(
        "--perturb", type=float, default=0.5,
        help="Perturbation magnitude: distance for pos (same units as model), "
             "angle in degrees for orient (default: 0.5)"
    )
    parser.add_argument(
        "--steps", type=int, default=3,
        help="Number of steps per dimension in the perturbation grid (default: 3)"
    )
    parser.add_argument(
        "--output", default=None,
        help="Output TSV path (default: <input_stem>_sensitivity.tsv next to input)"
    )
    args = parser.parse_args(argv[1:])

    import numpy as np
    from kst_rating_tool import analyze_constraints_detailed
    from kst_rating_tool.optimization import sens_analysis_orient, sens_analysis_pos

    input_path = Path(args.input_json).resolve()
    if not input_path.is_file():
        print(f"ERROR: Input JSON not found: {input_path}", file=sys.stderr)
        return 1

    try:
        with input_path.open() as f:
            data = json.load(f)
    except Exception as exc:
        print(f"ERROR: Failed to load JSON: {exc}", file=sys.stderr)
        return 1

    analysis_input = data.get("analysis_input") or data

    try:
        cs = _load_constraints(analysis_input)
    except Exception as exc:
        print(f"ERROR: Failed to build ConstraintSet: {exc}", file=sys.stderr)
        return 1

    if cs.total_cp == 0:
        print("ERROR: No constraints found in analysis_input.", file=sys.stderr)
        return 1

    print(f"Running baseline analysis ({cs.total_cp} constraints)...")
    try:
        baseline = analyze_constraints_detailed(cs)
    except Exception as exc:
        print(f"ERROR: Baseline analysis failed: {exc}", file=sys.stderr)
        return 1

    r = baseline.rating
    print(
        f"Baseline: WTR={r.WTR:.4f}  MRR={r.MRR:.4f}  MTR={r.MTR:.4f}  TOR={r.TOR:.4f}"
    )

    no_step = args.steps
    perturb = args.perturb

    # Per-constraint max absolute % change across the grid (shape: total_cp each)
    max_wtr_pos = max_mrr_pos = max_mtr_pos = max_tor_pos = None
    max_wtr_orient = max_mrr_orient = max_mtr_orient = max_tor_orient = None

    if args.mode in ("pos", "both"):
        print(
            f"Running position sensitivity (perturb={perturb}, steps={no_step})..."
            f"  [{cs.total_cp} constraints, {(no_step+1)**2} grid points each]"
        )
        sap_wtr, sap_mrr, sap_mtr, sap_tor = sens_analysis_pos(
            baseline, cs, pert_dist=perturb, no_step=no_step
        )
        # sap_* shape: (total_cp, no_step+1, no_step+1); max over grid
        max_wtr_pos = np.nanmax(np.abs(sap_wtr.reshape(cs.total_cp, -1)), axis=1)
        max_mrr_pos = np.nanmax(np.abs(sap_mrr.reshape(cs.total_cp, -1)), axis=1)
        max_mtr_pos = np.nanmax(np.abs(sap_mtr.reshape(cs.total_cp, -1)), axis=1)
        max_tor_pos = np.nanmax(np.abs(sap_tor.reshape(cs.total_cp, -1)), axis=1)
        print("  Position sensitivity done.")

    if args.mode in ("orient", "both"):
        print(
            f"Running orientation sensitivity (perturb={perturb} deg, steps={no_step})..."
            f"  [{cs.total_cp} constraints, {(no_step+1)**2} grid points each]"
        )
        sao_wtr, sao_mrr, sao_mtr, sao_tor = sens_analysis_orient(
            baseline, cs, pert_angle=perturb, no_step=no_step
        )
        max_wtr_orient = np.nanmax(np.abs(sao_wtr.reshape(cs.total_cp, -1)), axis=1)
        max_mrr_orient = np.nanmax(np.abs(sao_mrr.reshape(cs.total_cp, -1)), axis=1)
        max_mtr_orient = np.nanmax(np.abs(sao_mtr.reshape(cs.total_cp, -1)), axis=1)
        max_tor_orient = np.nanmax(np.abs(sao_tor.reshape(cs.total_cp, -1)), axis=1)
        print("  Orientation sensitivity done.")

    # Combine pos + orient as max of either mode
    def _combine(a, b):
        if a is None:
            return b
        if b is None:
            return a
        return np.maximum(a, b)

    max_wtr = _combine(max_wtr_pos, max_wtr_orient)
    max_mrr = _combine(max_mrr_pos, max_mrr_orient)
    max_mtr = _combine(max_mtr_pos, max_mtr_orient)
    max_tor = _combine(max_tor_pos, max_tor_orient)

    if max_tor is None:
        print("ERROR: No sensitivity data computed.", file=sys.stderr)
        return 1

    # Build result table
    labels = _constraint_labels(cs)
    rows: list[dict] = []
    for (global_idx, ctype, label), wtr_v, mrr_v, mtr_v, tor_v in zip(
        labels, max_wtr, max_mrr, max_mtr, max_tor
    ):
        rows.append({
            "idx": global_idx,
            "type": ctype,
            "label": label,
            "max_WTR_chg": float(wtr_v) if np.isfinite(wtr_v) else 0.0,
            "max_MRR_chg": float(mrr_v) if np.isfinite(mrr_v) else 0.0,
            "max_MTR_chg": float(mtr_v) if np.isfinite(mtr_v) else 0.0,
            "max_TOR_chg": float(tor_v) if np.isfinite(tor_v) else 0.0,
        })

    # Sort by TOR sensitivity descending
    rows_sorted = sorted(rows, key=lambda r: r["max_TOR_chg"], reverse=True)

    # Determine output path
    if args.output:
        output_path = Path(args.output).resolve()
    else:
        output_path = input_path.with_name(input_path.stem + "_sensitivity.tsv")
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with output_path.open("w", encoding="utf-8", newline="") as f:
        f.write("idx\ttype\tlabel\tmax_WTR_chg\tmax_MRR_chg\tmax_MTR_chg\tmax_TOR_chg\n")
        for row in rows:  # original order in file
            f.write(
                f"{row['idx']}\t{row['type']}\t{row['label']}\t"
                f"{row['max_WTR_chg']:.3f}\t{row['max_MRR_chg']:.3f}\t"
                f"{row['max_MTR_chg']:.3f}\t{row['max_TOR_chg']:.3f}\n"
            )

    print(f"\nWrote sensitivity results to: {output_path}")

    # Print ranked summary
    col_w = max(len(r["label"]) for r in rows_sorted) + 2
    print(f"\nSensitivity ranking (by TOR change, mode={args.mode}):")
    print(f"  {'Rank':<5}  {'Label':<{col_w}}  {'ΔWTR%':>8}  {'ΔMRR%':>8}  {'ΔMTR%':>8}  {'ΔTOR%':>8}")
    print("  " + "-" * (5 + col_w + 40))
    for rank, row in enumerate(rows_sorted, 1):
        print(
            f"  {rank:<5}  {row['label']:<{col_w}}  "
            f"{row['max_WTR_chg']:>8.2f}  {row['max_MRR_chg']:>8.2f}  "
            f"{row['max_MTR_chg']:>8.2f}  {row['max_TOR_chg']:>8.2f}"
        )

    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
