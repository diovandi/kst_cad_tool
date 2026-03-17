#!/usr/bin/env python3
"""
Run KST analysis for the Fusion 360 wizard input JSON.

Usage:
  python scripts/run_wizard_analysis.py <input_json> <output_txt>

This is used by the Fusion 360 add-in when Fusion's embedded Python does not
have numpy installed. It runs in your normal Python environment where the
`kst_rating_tool` package and its dependencies are available.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path


def main(argv: list[str]) -> int:
    if len(argv) != 3:
        print("Usage: python scripts/run_wizard_analysis.py <input_json> <output_txt>", file=sys.stderr)
        return 1

    input_path = Path(argv[1]).resolve()
    output_path = Path(argv[2]).resolve()

    if not input_path.is_file():
        print(f"Input JSON not found: {input_path}", file=sys.stderr)
        return 1

    repo_root = Path(__file__).resolve().parent.parent
    src_dir = repo_root / "src"
    if str(src_dir) not in sys.path:
        sys.path.insert(0, str(src_dir))

    import numpy as np  # type: ignore
    from kst_rating_tool import (
        analyze_constraints_detailed,
        ConstraintSet,
        PointConstraint,
        PinConstraint,
        LineConstraint,
        PlaneConstraint,
    )

    with input_path.open() as f:
        data = json.load(f)

    cs = ConstraintSet()
    pc = data.get("point_contacts", []) or []
    for row in pc:
        if len(row) >= 6:
            pos = np.array(row[0:3], dtype=float)
            nrm = np.array(row[3:6], dtype=float)
            cs.points.append(PointConstraint(pos, nrm))

    pins = data.get("pins", []) or []
    for row in pins:
        if len(row) >= 6:
            center = np.array(row[0:3], dtype=float)
            axis = np.array(row[3:6], dtype=float)
            cs.pins.append(PinConstraint(center, axis))

    lines = data.get("lines", []) or []
    for row in lines:
        if len(row) >= 10:
            midpoint = np.array(row[0:3], dtype=float)
            line_dir = np.array(row[3:6], dtype=float)
            constraint_dir = np.array(row[6:9], dtype=float)
            length = float(row[9])
            cs.lines.append(LineConstraint(midpoint, line_dir, constraint_dir, length))

    planes = data.get("planes", []) or []
    for row in planes:
        if len(row) >= 7:
            midpoint = np.array(row[0:3], dtype=float)
            normal = np.array(row[3:6], dtype=float)
            ptype = int(row[6])
            prop = np.array(row[7:], dtype=float) if len(row) > 7 else np.array([], dtype=float)
            cs.planes.append(PlaneConstraint(midpoint, normal, ptype, prop))

    if cs.total_cp == 0:
        print("Input JSON has no constraints (points, pins, lines, or planes).", file=sys.stderr)
        return 1

    detailed = analyze_constraints_detailed(cs)
    rating = detailed.rating

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w") as f:
        f.write("WTR\tMRR\tMTR\tTOR\n")
        f.write("{}\t{}\t{}\t{}\n".format(rating.WTR, rating.MRR, rating.MTR, rating.TOR))

    print(f"Wrote {output_path} (WTR={rating.WTR:.4f}, MRR={rating.MRR:.4f}, MTR={rating.MTR:.4f}, TOR={rating.TOR:.4f})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))

