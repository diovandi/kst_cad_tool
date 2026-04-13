#!/usr/bin/env python3
"""
Lightweight hotspot timing for KST analysis (wizard-style path).

Measures wall time for analyze_constraints and optional breakdown via cProfile.
Usage:
  python3 scripts/profile_kst_hotspots.py [path/to/case.json]
  python3 scripts/profile_kst_hotspots.py --cprofile [path/to/case.json]

If no JSON is given, uses a small built-in point-only fixture.
"""

from __future__ import annotations

import argparse
import cProfile
import io
import json
import pstats
import sys
import time
from pathlib import Path


def _repo_src() -> Path:
    return Path(__file__).resolve().parent.parent / "src"


def _default_fixture() -> dict:
    """Minimal valid analysis_input (7+ point contacts) for profiling."""
    pts = []
    for i in range(8):
        x = float(i % 4) * 10.0
        y = float(i // 4) * 10.0
        pts.append([x, y, 0.0, 0.0, 0.0, 1.0])
    return {"point_contacts": pts, "pins": [], "lines": [], "planes": []}


def _load_constraints(data: dict):
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


def main() -> int:
    ap = argparse.ArgumentParser(description="Profile KST analyze_constraints hotspots")
    ap.add_argument("json", nargs="?", default=None, help="Wizard/analysis JSON (analysis_input or full payload)")
    ap.add_argument("--cprofile", action="store_true", help="Run cProfile and print top functions")
    ap.add_argument("--repeats", type=int, default=3, help="Repeated timings (non-cprofile)")
    args = ap.parse_args()

    src = _repo_src()
    if str(src) not in sys.path:
        sys.path.insert(0, str(src))

    from kst_rating_tool import analyze_constraints

    if args.json:
        path = Path(args.json)
        data = json.loads(path.read_text(encoding="utf-8"))
        analysis_input = data.get("analysis_input", data)
    else:
        analysis_input = _default_fixture()

    cs = _load_constraints(analysis_input)

    def run_once() -> None:
        analyze_constraints(cs)

    if args.cprofile:
        pr = cProfile.Profile()
        pr.enable()
        run_once()
        pr.disable()
        s = io.StringIO()
        ps = pstats.Stats(pr, stream=s).sort_stats(pstats.SortKey.CUMULATIVE)
        ps.print_stats(40)
        print(s.getvalue())
        return 0

    times: list[float] = []
    for _ in range(max(1, args.repeats)):
        t0 = time.perf_counter()
        run_once()
        times.append(time.perf_counter() - t0)
    mean = sum(times) / len(times)
    print(f"analyze_constraints: {mean*1000:.2f} ms mean over {len(times)} run(s) (min {min(times)*1000:.2f} ms)")
    print("Tip: use --cprofile to see cumulative time by function (pipeline, rating, utils).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
