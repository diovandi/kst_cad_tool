# GPU / accelerator runtime (KST)

## Default

`analyze_constraints()` uses **NumPy on CPU** with **batched** point-contact rating (`rating_batched`). No GPU is required.

## Optional PyTorch

Install: `pip install torch` (or `pip install -e ".[gpu]"` if you use the project extra).

- **`accelerator="torch"`** with **`device="cuda"`** on a GPU runs batched point-contact linear algebra on the accelerator when the pivot wrench has exactly five rows (`react_wr_5` shape `(5, 6)`). Other constraint types still use the NumPy kernels in the torch path.
- **`device="cpu"`** runs the same PyTorch ops on CPU (useful for parity tests).
- **`accelerator="auto"`** picks **CUDA** if available, else **MPS** (Apple), else **DirectML** (if `torch-directml` is installed), else **CPU**.

If PyTorch is missing or the problem is too small, the code **falls back to NumPy** (no error).

### AMD ROCm (Ryzen AI / Radeon discrete)

PyTorch’s **ROCm** builds use the **same** `torch.cuda` API for AMD GPUs (HIP under the hood). In this project:

- Use **`device="cuda"`** when `torch.cuda.is_available()` is true on a ROCm install (that is the correct string for AMD on ROCm).
- **`device="hip"`** or **`device="rocm"`** are accepted aliases and are normalized to **`cuda`** when a GPU is visible; otherwise they fall back to **`cpu`**.

**Platform expectations**

| Platform | ROCm + PyTorch |
|----------|------------------|
| **Linux** (incl. many desktop Radeon / some server GPUs) | Install the official **PyTorch for ROCm** wheel from [pytorch.org](https://pytorch.org) for your distro; then `accelerator="torch"`, `device="cuda"` (or `hip`). |
| **Windows 11, Ryzen AI 9 HX 370 (Strix Point iGPU)** | **Native ROCm PyTorch for this iGPU is not broadly available** the way CUDA is for NVIDIA. Expect **`torch.cuda.is_available()` → False** with the default Windows `pip install torch` CPU/CUDA package. Use **DirectML** (below) on Windows for AMD GPU acceleration, or **ROCm on dual-boot Linux**. |

You can detect a ROCm build in Python: `torch.version.hip` is not `None`. The helper **`kst_rating_tool.numeric_backend.is_rocm_pytorch()`** returns the same.

### Windows + AMD / Intel GPU (DirectML)

Use a **dedicated Python 3.12 venv** (recommended): `torch-directml` bundles a compatible PyTorch and can conflict with a separate CUDA PyTorch install.

1. Create and activate a venv with **Python 3.12**.
2. `pip install -e ".[directml]"` (or `pip install torch-directml` then `pip install -e ".[dev]"`).
3. Verify:

   ```text
   python -c "import torch_directml; print(torch_directml.device())"
   ```

4. Run analysis with **`accelerator="torch"`** and **`device="dml"`** (aliases: `directml`). Or **`accelerator="auto"`** to pick DirectML when CUDA/MPS are unavailable.

DirectML uses a `torch.device` with type **`privateuseone`** internally; the project resolves **`dml`** / **`directml`** to that device. If a kernel is unsupported, the batched CP path **falls back to NumPy** automatically.

**Fusion 360:** configure the add-in or external script to call **`venv\Scripts\python.exe`** when running [`scripts/run_wizard_analysis.py`](../../scripts/run_wizard_analysis.py) or [`scripts/run_wizard_optimization.py`](../../scripts/run_wizard_optimization.py).

## Wizard optimization script

`scripts/run_wizard_optimization.py` accepts:

- `--accelerator {numpy,torch,auto}`
- `--device` (e.g. `cuda`, `cpu`, `mps`, `dml`, `directml`, `hip`, `rocm` — see sections above)
- `--workers N` — parallel **threads** for evaluating multiple candidate combinations (in addition to batched math inside each analysis).

## Workstation notes

- **Ryzen AI 9 HX 370 laptop / AMD iGPU on Windows:** use **`pip install torch-directml`** and **`device=dml`** for DirectML; or stay on **NumPy** / PyTorch **CPU**. For ROCm HIP, use **Linux** (dual-boot), not native Windows.
- **RTX 3080 / Windows:** `accelerator=torch` + `device=cuda` is the expected NVIDIA GPU configuration.

## Profiling / benchmarks

- `scripts/profile_kst_hotspots.py` — quick timings / optional `cProfile`.
- `scripts/benchmark_kst_accelerator.py` — numpy vs torch CPU/CUDA/DirectML timing when available.
