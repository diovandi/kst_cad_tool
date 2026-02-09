"""Run a minimal KST analysis (single point constraint). Use --full to write full report (metrics, counts, WTR motion, CP table)."""

import sys
from pathlib import Path

import numpy as np

from kst_rating_tool import (
    ConstraintSet,
    PointConstraint,
    analyze_constraints,
    analyze_constraints_detailed,
)
from kst_rating_tool.reporting import print_summary, write_full_report_txt


def main() -> None:
    full = "--full" in sys.argv

    cs = ConstraintSet(
        points=[PointConstraint(position=np.array([0.0, 0.0, 0.0]), normal=np.array([0.0, 0.0, 1.0]))]
    )

    if full:
        detailed = analyze_constraints_detailed(cs)
        print_summary(detailed.rating)
        out_path = Path(__file__).resolve().parent.parent / "results_simple_full.txt"
        write_full_report_txt(detailed, out_path)
        print(f"Wrote full report to {out_path}")
    else:
        results = analyze_constraints(cs)
        print_summary(results)


if __name__ == "__main__":
    main()

