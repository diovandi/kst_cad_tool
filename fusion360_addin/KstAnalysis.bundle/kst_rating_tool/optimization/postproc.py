"""
Optimization post-processing (optim_postproc): find optimum indices and optional plotting.
Ported from optim_postproc.m.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional, Tuple

import numpy as np
from numpy.typing import NDArray


def optim_postproc(
    no_step: int,
    no_dim: int,
    WTR_optim_chg: NDArray[np.float64],
    MRR_optim_chg: NDArray[np.float64],
    MTR_optim_chg: NDArray[np.float64],
    TOR_optim_chg: NDArray[np.float64],
    WTR_optim_all: Optional[NDArray[np.float64]] = None,
    MRR_optim_all: Optional[NDArray[np.float64]] = None,
    MTR_optim_all: Optional[NDArray[np.float64]] = None,
    TOR_optim_all: Optional[NDArray[np.float64]] = None,
) -> dict:
    """Compute optimum indices and optional summary. No figure saving (use reporting for plots)."""
    out = {
        "WTR_max_idx": None,
        "MRR_max_idx": None,
        "MTR_max_idx": None,
        "TOR_max_idx": None,
        "x_inc": np.linspace(-1, 1, no_step + 1),
    }
    if no_dim == 1:
        out["WTR_max_idx"] = np.argmax(WTR_optim_chg)
        out["MRR_max_idx"] = np.argmax(MRR_optim_chg)
        out["MTR_max_idx"] = np.argmax(MTR_optim_chg)
        out["TOR_max_idx"] = np.argmax(TOR_optim_chg)
        return out

    if WTR_optim_all is None:
        return out
    WTR_flat = WTR_optim_all.ravel()
    valid = np.isfinite(WTR_flat)
    if not np.any(valid):
        return out
    WTR_max = np.nanmax(WTR_flat)
    WTR_max_idx_flat = np.where(np.abs(WTR_flat - WTR_max) < 1e-12)[0]
    out["WTR_max_idx"] = np.unravel_index(WTR_max_idx_flat[0], WTR_optim_all.shape)

    if MRR_optim_all is not None:
        MRR_flat = MRR_optim_all.ravel()
        if np.any(np.isfinite(MRR_flat)):
            MRR_max = np.nanmax(MRR_flat)
            MRR_max_idx_flat = np.where(np.abs(MRR_flat - MRR_max) < 1e-12)[0]
            out["MRR_max_idx"] = np.unravel_index(MRR_max_idx_flat[0], MRR_optim_all.shape)
    if MTR_optim_all is not None:
        MTR_flat = MTR_optim_all.ravel()
        if np.any(np.isfinite(MTR_flat)):
            MTR_max = np.nanmax(MTR_flat)
            MTR_max_idx_flat = np.where(np.abs(MTR_flat - MTR_max) < 1e-12)[0]
            out["MTR_max_idx"] = np.unravel_index(MTR_max_idx_flat[0], MTR_optim_all.shape)
    if TOR_optim_all is not None:
        TOR_flat = TOR_optim_all.ravel()
        if np.any(np.isfinite(TOR_flat)):
            TOR_max = np.nanmax(np.where(np.isfinite(TOR_flat), TOR_flat, -np.inf))
            TOR_max_idx_flat = np.where(np.abs(TOR_flat - TOR_max) < 1e-12)[0]
            out["TOR_max_idx"] = np.unravel_index(TOR_max_idx_flat[0], TOR_optim_all.shape)
    return out


def optim_postproc_plot(
    no_step: int,
    no_dim: int,
    WTR_optim_chg: NDArray[np.float64],
    MRR_optim_chg: NDArray[np.float64],
    MTR_optim_chg: NDArray[np.float64],
    TOR_optim_chg: NDArray[np.float64],
    inputfile: Optional[str] = None,
    output_dir: Optional[Path | str] = None,
) -> None:
    """Plot optimization response (port of optim_postproc.m figure/saveas). Optionally save as .png/.pdf."""
    try:
        import matplotlib.pyplot as plt
    except ImportError:
        return
    x_inc = np.linspace(-1, 1, no_step + 1)
    out_dir = Path(output_dir or ".")
    prefix = (inputfile or "optim").replace(" ", "_")
    if no_dim == 1:
        fig, axes = plt.subplots(2, 2, figsize=(8, 6))
        t = x_inc
        axes[0, 0].plot(t, WTR_optim_chg, "b-", linewidth=2)
        axes[0, 0].set_xlabel("X1")
        axes[0, 0].set_ylabel("WTR Change (%)")
        axes[0, 0].grid(True)
        axes[0, 1].plot(t, MRR_optim_chg, "b-", linewidth=2)
        axes[0, 1].set_xlabel("X1")
        axes[0, 1].set_ylabel("MRR Change (%)")
        axes[0, 1].grid(True)
        axes[1, 0].plot(t, MTR_optim_chg, "b-", linewidth=2)
        axes[1, 0].set_xlabel("X1")
        axes[1, 0].set_ylabel("MTR Change (%)")
        axes[1, 0].grid(True)
        axes[1, 1].plot(t, TOR_optim_chg, "b-", linewidth=2)
        axes[1, 1].set_xlabel("X1")
        axes[1, 1].set_ylabel("TOR Change (%)")
        axes[1, 1].grid(True)
        plt.tight_layout()
        if inputfile:
            fig.savefig(out_dir / f"{prefix}.png", dpi=150)
            fig.savefig(out_dir / f"{prefix}.pdf")
        plt.show()
    elif no_dim == 2:
        try:
            from mpl_toolkits.mplot3d import Axes3D  # noqa: F401
        except ImportError:
            return
        u, v = np.meshgrid(x_inc, x_inc)
        fig, axes = plt.subplots(2, 2, figsize=(10, 8), subplot_kw={"projection": "3d"})
        for ax, data, label in [
            (axes[0, 0], WTR_optim_chg, "WTR Change (%)"),
            (axes[0, 1], MRR_optim_chg, "MRR Change (%)"),
            (axes[1, 0], MTR_optim_chg, "MTR Change (%)"),
            (axes[1, 1], TOR_optim_chg, "TOR Change (%)"),
        ]:
            if data.shape == u.shape:
                ax.plot_surface(u, v, np.where(np.isfinite(data), data, np.nan), cmap="cool")
            ax.set_xlabel("X2")
            ax.set_ylabel("X1")
            ax.set_zlabel(label)
        plt.tight_layout()
        if inputfile:
            fig.savefig(out_dir / f"{prefix}.png", dpi=150)
            fig.savefig(out_dir / f"{prefix}.pdf")
        plt.show()
