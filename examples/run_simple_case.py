import numpy as np

from kst_rating_tool import (
    ConstraintSet,
    PointConstraint,
    analyze_constraints,
)
from kst_rating_tool.reporting import print_summary


def main() -> None:
    cs = ConstraintSet(
        points=[PointConstraint(position=np.array([0.0, 0.0, 0.0]), normal=np.array([0.0, 0.0, 1.0]))]
    )

    results = analyze_constraints(cs)
    print_summary(results)


if __name__ == "__main__":
    main()

