"""CPU vs optional PyTorch accelerator parity for analyze_constraints."""

from __future__ import annotations

import numpy as np
import pytest

from kst_rating_tool.constraints import ConstraintSet, PointConstraint
from kst_rating_tool.pipeline import analyze_constraints, analyze_constraints_gpu


def _eight_point_cs() -> ConstraintSet:
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
    return cs


def test_batched_numpy_twice_identical():
    cs = _eight_point_cs()
    a = analyze_constraints(cs, accelerator="numpy")
    b = analyze_constraints(cs, accelerator="numpy")
    assert a.WTR == pytest.approx(b.WTR, rel=0, abs=1e-12)


def test_torch_cpu_parity():
    cs = _eight_point_cs()
    r_cpu = analyze_constraints(cs, accelerator="numpy")
    try:
        r_acc = analyze_constraints(cs, accelerator="torch", device="cpu")
    except ImportError:
        pytest.skip("PyTorch not installed")
    assert r_cpu.WTR == pytest.approx(r_acc.WTR, rel=0, abs=1e-6)
    assert r_cpu.MRR == pytest.approx(r_acc.MRR, rel=0, abs=1e-6)
    assert r_cpu.MTR == pytest.approx(r_acc.MTR, rel=0, abs=1e-6)
    if r_cpu.TOR == float("inf") or r_acc.TOR == float("inf"):
        assert r_cpu.TOR == r_acc.TOR or (
            r_cpu.TOR == float("inf") and r_acc.TOR == float("inf")
        )
    else:
        assert r_cpu.TOR == pytest.approx(r_acc.TOR, rel=0, abs=1e-4)


def test_rocm_device_aliases_normalize():
    try:
        import torch
    except ImportError:
        pytest.skip("PyTorch not installed")
    from kst_rating_tool.numeric_backend import is_rocm_pytorch, normalize_pytorch_device

    _ = is_rocm_pytorch()  # smoke
    assert normalize_pytorch_device("HIP", torch) == normalize_pytorch_device("rocm", torch)


def test_analyze_constraints_gpu_alias():
    cs = _eight_point_cs()
    try:
        r = analyze_constraints_gpu(cs, device="cpu")
    except ImportError:
        pytest.skip("PyTorch not installed")
    r0 = analyze_constraints(cs, accelerator="torch", device="cpu")
    assert r.WTR == pytest.approx(r0.WTR, rel=0, abs=1e-9)


def test_directml_device_aliases_and_smoke():
    pytest.importorskip("torch_directml")
    import torch

    from kst_rating_tool.numeric_backend import is_directml_device, normalize_pytorch_device
    from kst_rating_tool.pipeline import analyze_constraints

    d0 = normalize_pytorch_device("dml", torch)
    d1 = normalize_pytorch_device("directml", torch)
    assert str(type(d0)) == str(type(d1))
    if str(d0) != "cpu":
        assert is_directml_device(d0)

    cs = _eight_point_cs()
    r_np = analyze_constraints(cs, accelerator="numpy")
    r_dml = analyze_constraints(cs, accelerator="torch", device="dml")
    assert r_np.WTR == pytest.approx(r_dml.WTR, rel=0, abs=1e-4)
    assert r_np.MRR == pytest.approx(r_dml.MRR, rel=0, abs=1e-4)
    assert r_np.MTR == pytest.approx(r_dml.MTR, rel=0, abs=1e-4)
