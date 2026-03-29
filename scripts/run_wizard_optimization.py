#!/usr/bin/env python3
"""
Run KST optimization from a generic JSON candidate matrix.

Usage:
  python scripts/run_wizard_optimization.py <input_json> [output_txt]
"""

from __future__ import annotations

import json
import sys
from pathlib import Path


def _load_constraints_from_analysis_input(data: dict):
    import numpy as np
    from kst_rating_tool import ConstraintSet, PointConstraint, PinConstraint, LineConstraint, PlaneConstraint

    cs = ConstraintSet()
    for row in data.get("point_contacts", []) or []:
        if len(row) >= 6:
            cs.points.append(PointConstraint(np.array(row[0:3], dtype=float), np.array(row[3:6], dtype=float)))
    for row in data.get("pins", []) or []:
        if len(row) >= 6:
            cs.pins.append(PinConstraint(np.array(row[0:3], dtype=float), np.array(row[3:6], dtype=float)))
    for row in data.get("lines", []) or []:
        if len(row) >= 10:
            cs.lines.append(
                LineConstraint(
                    np.array(row[0:3], dtype=float),
                    np.array(row[3:6], dtype=float),
                    np.array(row[6:9], dtype=float),
                    float(row[9]),
                )
            )
    for row in data.get("planes", []) or []:
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


def main(argv: list[str]) -> int:
    if len(argv) < 2 or len(argv) > 3:
        print("Usage: python scripts/run_wizard_optimization.py <input_json> [output_txt]", file=sys.stderr)
        return 1

    in_path = Path(argv[1]).resolve()
    out_path = Path(argv[2]).resolve() if len(argv) == 3 else in_path.with_name("results_wizard_optim.txt")
    if not in_path.is_file():
        print(f"Input JSON not found: {in_path}", file=sys.stderr)
        return 1

    repo_root = Path(__file__).resolve().parent.parent
    src_dir = repo_root / "src"
    if str(src_dir) not in sys.path:
        sys.path.insert(0, str(src_dir))

    import numpy as np
    from kst_rating_tool import analyze_constraints
    from kst_rating_tool.constraints import PointConstraint

    payload = json.loads(in_path.read_text(encoding="utf-8"))
    analysis_input = payload.get("analysis_input", payload)
    opt = payload.get("optimization", {})
    cmat = opt.get("candidate_matrix", [])
    if not cmat:
        print("Missing optimization.candidate_matrix", file=sys.stderr)
        return 1
    first = cmat[0]
    cp_idx = int(first.get("constraint_index", 0))
    candidates = first.get("candidates", [])
    if cp_idx <= 0 or not candidates:
        print("candidate_matrix must include constraint_index and non-empty candidates", file=sys.stderr)
        return 1

    cs_base = _load_constraints_from_analysis_input(analysis_input)
    n_points = len(cs_base.points)
    if cp_idx > n_points:
        print(
            "run_wizard_optimization.py currently supports point-contact candidates only "
            f"(constraint_index <= {n_points}, got {cp_idx})",
            file=sys.stderr,
        )
        return 1

    rows: list[tuple[int, float, float, float, float]] = []
    for i, cand in enumerate(candidates, start=1):
        if len(cand) < 6:
            continue
        cs = _load_constraints_from_analysis_input(analysis_input)
        cs.points[cp_idx - 1] = PointConstraint(
            position=np.array(cand[0:3], dtype=float),
            normal=np.array(cand[3:6], dtype=float),
        )
        rating = analyze_constraints(cs)
        rows.append((i, float(rating.WTR), float(rating.MRR), float(rating.MTR), float(rating.TOR)))

    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8") as f:
        f.write("candidate\tWTR\tMRR\tMTR\tTOR\n")
        for idx, wtr, mrr, mtr, tor in rows:
            f.write(f"{idx}\t{wtr:.10g}\t{mrr:.10g}\t{mtr:.10g}\t{tor:.10g}\n")
    print(f"Wrote {out_path} ({len(rows)} candidates)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
