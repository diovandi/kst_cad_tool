#!/usr/bin/env python3
"""
Compare wall time for analyze_constraints with numpy vs optional torch accelerator.

Usage:
  python3 scripts/benchmark_kst_accelerator.py [--repeats N]
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path


def _repo_src() -> Path:
    return Path(__file__).resolve().parent.parent / "src"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--repeats", type=int, default=5)
    args = ap.parse_args()

    src = _repo_src()
    if str(src) not in sys.path:
        sys.path.insert(0, str(src))

    import numpy as np
    from kst_rating_tool.constraints import ConstraintSet, PointConstraint
    from kst_rating_tool.pipeline import analyze_constraints

    cs = ConstraintSet()
    for i in range(8):
        x = float(i % 4) * 10.0
        y = float(i // 4) * 10.0
        cs.points.append(
            PointConstraint(
                position=np.array([x, y, 0.0], dtype=float),
                normal=np.array([0.0, 0.0, 1.0], dtype=float),
            )
        )

    def bench(acc: str, dev: str | None) -> float:
        t0 = time.perf_counter()
        for _ in range(args.repeats):
            analyze_constraints(cs, accelerator=acc, device=dev)
        return (time.perf_counter() - t0) / args.repeats

    t_np = bench("numpy", None)
    print(f"accelerator=numpy: {t_np*1000:.2f} ms/run ({args.repeats} repeats)")
    try:
        import torch
        from kst_rating_tool.numeric_backend import is_rocm_pytorch

        hip = getattr(torch.version, "hip", None)
        print(f"torch.version.hip (ROCm build): {hip}")
        print(f"is_rocm_pytorch(): {is_rocm_pytorch()}")
        print(f"torch.cuda.is_available(): {torch.cuda.is_available()}")
        t_tc = bench("torch", "cpu")
        print(f"accelerator=torch device=cpu: {t_tc*1000:.2f} ms/run")
        if t_tc > 0:
            print(f"ratio torch_cpu/numpy: {t_tc/t_np:.2f}x")
        if torch.cuda.is_available():
            t_gpu = bench("torch", "cuda")
            print(f"accelerator=torch device=cuda: {t_gpu*1000:.2f} ms/run")
            if t_gpu > 0:
                print(f"ratio cuda/numpy: {t_gpu/t_np:.2f}x")
        try:
            import torch_directml  # noqa: F401

            t_dml = bench("torch", "dml")
            print(f"accelerator=torch device=dml (DirectML): {t_dml*1000:.2f} ms/run")
            if t_dml > 0:
                print(f"ratio dml/numpy: {t_dml/t_np:.2f}x")
        except ImportError:
            print("torch-directml not installed; pip install torch-directml for DirectML (Windows AMD/Intel)")
    except ImportError:
        print("torch not installed; pip install torch for accelerator comparison")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
