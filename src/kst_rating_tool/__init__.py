"""
kst_rating_tool
---------------

Python backend for kinematic screw theory (KST) based mechanical assembly
rating, ported from Leonard Rusli's MATLAB implementation.
"""

from .constraints import (  # noqa: F401
    PointConstraint,
    PinConstraint,
    LineConstraint,
    PlaneConstraint,
    ConstraintSet,
)
from .pipeline import (  # noqa: F401
    DetailedAnalysisResult,
    SpecmotResult,
    analyze_constraints,
    analyze_constraints_detailed,
    analyze_specified_motions,
)
from .optimization import (  # noqa: F401
    RevisionConfig,
    optim_main_rev,
    optim_main_red,
    optim_postproc,
)

