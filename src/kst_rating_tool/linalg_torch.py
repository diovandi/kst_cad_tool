"""PyTorch linear algebra matching MATLAB-style rank and mldivide used in rating.

Requires ``torch`` as optional dependency. DirectML and some backends may not
implement ``float64`` linalg ops; functions retry with ``float32`` once on
:class:`RuntimeError`.
"""

from __future__ import annotations

from typing import Any


def _spacing_torch(x: Any) -> Any:
    """``np.spacing(x)`` equivalent for torch tensors (float64/float32)."""
    import torch

    x = torch.abs(x)
    nxt = torch.nextafter(x, torch.full_like(x, float("inf")))
    return nxt - x


def _matlab_rank_batched_torch_impl(A: Any) -> Any:
    """Core batched rank; ``A`` already on correct dtype/device."""
    import torch

    if A.ndim == 2:
        A = A.unsqueeze(0)
    s = torch.linalg.svdvals(A)
    if s.numel() == 0:
        return torch.zeros(A.shape[0], dtype=torch.int64, device=A.device)
    m, n = A.shape[-2], A.shape[-1]
    mx = max(m, n)
    s0 = s[:, 0]
    tol = float(mx) * _spacing_torch(s0)
    return torch.sum(s > tol.unsqueeze(-1), dim=-1).to(torch.int64)


def matlab_rank_batched_torch(A: Any) -> Any:
    """Batched MATLAB rank; A shape (N, m, n) returns (N,) int64 on same device."""
    import torch

    last_err: BaseException | None = None
    for dtype in (torch.float64, torch.float32):
        try:
            Ac = A.to(dtype=dtype)
            return _matlab_rank_batched_torch_impl(Ac)
        except RuntimeError as e:
            last_err = e
            if dtype == torch.float32:
                break
    if last_err:
        raise last_err
    raise RuntimeError("matlab_rank_batched_torch: unreachable")


def matlab_rank_torch(A: Any) -> Any:
    """MATLAB ``rank(A)`` for a single matrix on torch."""
    import torch

    if A.ndim != 2:
        raise ValueError("matlab_rank_torch expects 2D tensor")
    last_err: BaseException | None = None
    for dtype in (torch.float64, torch.float32):
        try:
            Ac = A.to(dtype=dtype)
            s = torch.linalg.svdvals(Ac)
            if s.numel() == 0:
                return torch.tensor(0, dtype=torch.int64, device=Ac.device)
            m, n = Ac.shape
            mx = max(m, n)
            tol = float(mx) * _spacing_torch(s[0])
            return int(torch.sum(s > tol).item())
        except RuntimeError as e:
            last_err = e
            if dtype == torch.float32:
                break
    if last_err:
        raise last_err
    raise RuntimeError("matlab_rank_torch: unreachable")


def matlab_mldivide_torch(A: Any, b: Any) -> Any:
    """Replicate ``rating._matlab_mldivide`` for torch tensors (same device)."""
    import torch

    last_err: BaseException | None = None
    for dtype in (torch.float64, torch.float32):
        try:
            Am = A.to(dtype=dtype)
            b_flat = b.reshape(-1).to(dtype=dtype)
            m, n = Am.shape
            if m == n:
                try:
                    return torch.linalg.solve(Am, b_flat)
                except RuntimeError:
                    pass
            sol = torch.linalg.lstsq(Am, b_flat, rcond=None).solution
            return sol
        except RuntimeError as e:
            last_err = e
            if dtype == torch.float32:
                break
    if last_err:
        raise last_err
    raise RuntimeError("matlab_mldivide_torch: unreachable")


def matlab_mldivide_batched_torch(A: Any, b: Any) -> Any:
    """Batched solve A[i] @ x[i] = b[i]; A (N,m,n), b (N,m)."""
    import torch

    if A.ndim == 2:
        return matlab_mldivide_torch(A, b).reshape(-1)
    b_flat = b.reshape(A.shape[0], -1)
    m, n = A.shape[-2], A.shape[-1]
    last_err: BaseException | None = None
    for dtype in (torch.float64, torch.float32):
        try:
            Am = A.to(dtype=dtype)
            bf = b_flat.to(dtype=dtype)
            if m == n:
                try:
                    return torch.linalg.solve(Am, bf.unsqueeze(-1)).squeeze(-1)
                except RuntimeError:
                    pass
            out = []
            for i in range(Am.shape[0]):
                out.append(matlab_mldivide_torch(Am[i], bf[i]))
            return torch.stack(out, dim=0)
        except RuntimeError as e:
            last_err = e
            if dtype == torch.float32:
                break
    if last_err:
        raise last_err
    raise RuntimeError("matlab_mldivide_batched_torch: unreachable")
