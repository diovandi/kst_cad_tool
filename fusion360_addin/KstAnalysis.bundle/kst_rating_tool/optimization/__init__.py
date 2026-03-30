"""
Optimization routines ported from MATLAB (optim_main_rev, optim_main_red, etc.).
"""

from .modification import ModificationResult, optimize_modification
from .parameterizations import (
    Orientation1DParameterization,
    PointOnLineParameterization,
    RevisionParameterization,
    build_x_map,
)
from .reduction import (
    ReductionResult,
    constraint_set_without,
    optim_main_red,
    optimize_reduction,
)
from .revision import RevisionConfig, optim_main_rev, optim_rev
from .postproc import optim_postproc, optim_postproc_plot
from .sensitivity import sens_analysis_pos, sens_analysis_orient
from .specmot_optim import main_specmot_optim, rate_specmot
from .search_space import (
    move_lin_srch,
    move_pln_srch,
    move_curvlin_srch,
    orient1d_srch,
    orient2d_srch,
    line_orient1d_srch,
    resize_lin_srch,
    resize_rectpln_srch,
    resize_circpln_srch,
)

__all__ = [
    "RevisionConfig",
    "optim_main_rev",
    "optim_rev",
    "optim_main_red",
    "optim_postproc",
    "optim_postproc_plot",
    "sens_analysis_pos",
    "sens_analysis_orient",
    "rate_specmot",
    "main_specmot_optim",
    "move_lin_srch",
    "move_pln_srch",
    "move_curvlin_srch",
    "orient1d_srch",
    "orient2d_srch",
    "line_orient1d_srch",
    "resize_lin_srch",
    "resize_rectpln_srch",
    "resize_circpln_srch",
    "constraint_set_without",
    "optimize_reduction",
    "ReductionResult",
    "optimize_modification",
    "ModificationResult",
    "PointOnLineParameterization",
    "Orientation1DParameterization",
    "RevisionParameterization",
    "build_x_map",
]

try:
    from .surrogate import SurrogateResult, optimize_modification_surrogate, optimize_surrogate_adaptive
    __all__.extend(["optimize_modification_surrogate", "optimize_surrogate_adaptive", "SurrogateResult"])
except ImportError:
    pass

try:
    from .surrogate_bo import BOResult, optimize_bo
    __all__.extend(["optimize_bo", "BOResult"])
except ImportError:
    pass

try:
    from .surrogate_pareto import ParetoResult, ParetoPoint, optimize_pareto
    __all__.extend(["optimize_pareto", "ParetoResult", "ParetoPoint"])
except ImportError:
    pass

try:
    from .reduction_ml import MLReductionResult, optimize_reduction_ml
    __all__.extend(["optimize_reduction_ml", "MLReductionResult"])
except ImportError:
    pass
