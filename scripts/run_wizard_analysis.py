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
    from kst_rating_tool import analyze_constraints_detailed, ConstraintSet, PointConstraint

    with input_path.open() as f:
        data = json.load(f)

    pc = data.get("point_contacts", [])
    if not pc:
        print("Input JSON has no 'point_contacts' entries.", file=sys.stderr)
        return 1

    cs = ConstraintSet()
    for row in pc:
        if len(row) >= 6:
            pos = np.array([float(row[0]), float(row[1]), float(row[2])], dtype=float)
            nrm = np.array([float(row[3]), float(row[4]), float(row[5])], dtype=float)
            cs.points.append(PointConstraint(pos, nrm))

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

