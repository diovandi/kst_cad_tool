"""Pluggable linear-algebra backend: NumPy (CPU) or PyTorch (CPU/CUDA/HIP/DirectML).

Used by batched rating and optional GPU analysis. PyTorch is optional; import fails
fall back to NumPy-only paths.

**ROCm / AMD (Linux):** Official PyTorch ROCm wheels use ``torch.cuda`` for HIP;
``device="cuda"`` when ``torch.cuda.is_available()``. Aliases ``hip`` / ``rocm``
normalize to ``cuda``.

**DirectML (Windows, AMD/Intel/NVIDIA via DX12):** Use ``pip install torch-directml`` and
``device="dml"`` or ``accelerator="auto"`` (after CUDA/MPS). Resolves to a
``torch.device`` from ``torch_directml.device()``.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import TYPE_CHECKING, Any, Literal

import numpy as np
from numpy.typing import NDArray

if TYPE_CHECKING:
    import torch

from . import linalg_torch


class AcceleratorKind(str, Enum):
    NUMPY = "numpy"
    TORCH = "torch"
    AUTO = "auto"


@dataclass(frozen=True)
class BackendState:
    """Resolved accelerator after AUTO and availability checks.

    ``device`` is either a string (``cpu``, ``cuda``, ``mps``) or a ``torch.device``
    (e.g. DirectML ``privateuseone``).
    """

    kind: Literal["numpy", "torch"]
    device: str | Any  # torch.device when using DirectML
    torch_module: Any | None = None


def _torch_available() -> bool:
    try:
        import torch  # noqa: F401

        return True
    except ImportError:
        return False


def _directml_available() -> bool:
    try:
        import torch_directml  # noqa: F401

        return True
    except ImportError:
        return False


def resolve_directml_device() -> Any:
    """Default DirectML device (``torch_directml.device()``)."""
    import torch_directml

    return torch_directml.device()


def is_rocm_pytorch() -> bool:
    """True if this PyTorch build is linked against ROCm (AMD), not NVIDIA CUDA-only."""
    if not _torch_available():
        return False
    import torch

    hip = getattr(torch.version, "hip", None)
    return bool(hip)


def _device_type_name(device: str | Any) -> str:
    """Normalize device to a string for heuristics (``privateuseone``, ``cuda``, ...)."""
    if isinstance(device, str):
        return device
    t = getattr(device, "type", None)
    if t is not None:
        return str(t)
    return str(device)


def normalize_pytorch_device(device: str, torch_module: Any) -> str | Any:
    """Map user-facing names to PyTorch ``device`` strings or ``torch.device`` objects.

    ROCm: ``hip`` / ``rocm`` → ``cuda`` when available.
    DirectML: ``dml`` / ``directml`` → ``torch_directml.device()`` when available.
    """
    d = str(device).lower().strip()
    if d in ("hip", "rocm"):
        return "cuda" if torch_module.cuda.is_available() else "cpu"
    if d in ("dml", "directml"):
        if _directml_available():
            return resolve_directml_device()
        return "cpu"
    return device


def resolve_accelerator(
    accelerator: str | AcceleratorKind = "numpy",
    device: str | None = None,
) -> BackendState:
    """Choose NumPy or PyTorch device. AUTO order: CUDA > MPS > DirectML > CPU."""
    acc = accelerator if isinstance(accelerator, AcceleratorKind) else AcceleratorKind(str(accelerator).lower())
    if acc == AcceleratorKind.AUTO:
        if _torch_available():
            import torch

            if torch.cuda.is_available():
                return BackendState("torch", "cuda", torch)
            if getattr(torch.backends, "mps", None) is not None and torch.backends.mps.is_available():
                return BackendState("torch", "mps", torch)
            if _directml_available():
                try:
                    return BackendState("torch", resolve_directml_device(), torch)
                except Exception:
                    pass
            return BackendState("torch", "cpu", torch)
        return BackendState("numpy", "cpu", None)

    if acc == AcceleratorKind.NUMPY:
        return BackendState("numpy", "cpu", None)

    if acc == AcceleratorKind.TORCH:
        if not _torch_available():
            raise ImportError("accelerator='torch' requires PyTorch: pip install torch")
        import torch

        if device is None:
            dev: str | Any = "cuda" if torch.cuda.is_available() else "cpu"
        else:
            dev = normalize_pytorch_device(device, torch)
        return BackendState("torch", dev, torch)

    raise ValueError(f"Unknown accelerator: {accelerator}")


def matlab_rank_for_backend(
    A: NDArray[np.float64],
    state: BackendState,
) -> int | Any:
    """Single-matrix rank; returns int (NumPy) or 0-dim torch tensor (torch)."""
    if state.kind == "numpy":
        from .utils import matlab_rank

        return matlab_rank(A)

    assert state.torch_module is not None
    t = state.torch_module
    tt = t.as_tensor(A, dtype=t.float64, device=state.device)
    return linalg_torch.matlab_rank_torch(tt)


def matlab_rank_batched_for_backend(
    A: NDArray[np.float64],
    state: BackendState,
) -> NDArray[np.int_] | Any:
    """Batched rank; shape (N, m, n) -> (N,) counts."""
    if state.kind == "numpy":
        from .utils import matlab_rank_batched

        return matlab_rank_batched(A)

    assert state.torch_module is not None
    t = state.torch_module
    tt = t.as_tensor(A, dtype=t.float64, device=state.device)
    return linalg_torch.matlab_rank_batched_torch(tt)


def mldivide_for_backend(
    A: NDArray[np.float64],
    b: NDArray[np.float64],
    state: BackendState,
) -> NDArray[np.float64] | Any:
    """MATLAB ``A \\ b`` semantics (mirrors ``rating._matlab_mldivide`` for NumPy)."""
    if state.kind == "numpy":
        from .rating import _matlab_mldivide  # local import avoids import cycle

        return _matlab_mldivide(A, b)

    assert state.torch_module is not None
    t = state.torch_module
    At = t.as_tensor(A, dtype=t.float64, device=state.device)
    bt = t.as_tensor(b, dtype=t.float64, device=state.device).reshape(-1)
    return linalg_torch.matlab_mldivide_torch(At, bt)


def should_fallback_torch_to_numpy(state: BackendState, sample_A_shape: tuple[int, ...]) -> bool:
    """Heuristic: tiny batches rarely amortize GPU transfer/launch for small 6×6 blocks."""
    if state.kind != "torch":
        return False
    n = sample_A_shape[0] if len(sample_A_shape) >= 3 else 1
    dt = _device_type_name(state.device)
    if n < 4 and dt in ("cuda", "mps", "privateuseone"):
        return True
    return False


def is_directml_device(device: str | Any) -> bool:
    """True if ``device`` is a DirectML ``torch.device`` (typically ``privateuseone``)."""
    if isinstance(device, str):
        return False
    return _device_type_name(device) == "privateuseone"
