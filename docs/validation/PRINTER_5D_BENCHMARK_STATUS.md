# Printer Cover 5D Benchmark -- Implementation Status & Troubleshooting Log

## Status: IN PROGRESS (paused for runtime issues)

### What Was Completed

All code changes are implemented and ready. The benchmark has NOT yet run to completion due to per-evaluation cost being higher than initially estimated.

---

## 1. Code Changes Made (all in `optimization` branch worktree at `.cursor/worktrees/kst_cad_tool/fhk`)

### 1.1 `revision.py` -- Fixed N-D factorial search (DONE)

**File**: `src/kst_rating_tool/optimization/revision.py`

**Problem**: The `optim_main_rev` function had hard-coded nested loops for 1D, 2D, and 3D. The `else` branch (4+ dimensions) was broken -- it only iterated over the first 2 dimensions, fixing the remaining dimensions to `a_vals[0]` (i.e., -1). This meant the full 5D case from the dissertation could never be run correctly in Python.

**Fix**: Added `import itertools` at the top of the file. Replaced the `else` branch (lines ~290-304) with:

```python
for count, indices in enumerate(itertools.product(range(n_inc), repeat=no_dim)):
    if progress_callback:
        progress_callback(count + 1, tot_it)
    x = np.array([a_vals[i] for i in indices], dtype=float)
    Rating_all_rev, _, _ = optim_rev(x, x_map, ...)
    WTR_optim_all[indices] = Rating_all_rev[0]
    MRR_optim_all[indices] = Rating_all_rev[1]
    MTR_optim_all[indices] = Rating_all_rev[2]
```

This correctly iterates over all `n_inc^no_dim` grid points for any number of dimensions.

### 1.2 `parameterizations.py` -- Added `RevisionParameterization` and `build_x_map` (DONE)

**File**: `src/kst_rating_tool/optimization/parameterizations.py`

Two additions:

- **`build_x_map(config: RevisionConfig) -> tuple[NDArray, int]`**: Extracts the logic from `optim_main_rev` lines 210-221 into a reusable helper. Given a `RevisionConfig`, it computes the `x_map` array (mapping group index to dimension indices in `x`) and `no_dim` (total number of design variables). Types 4, 6, 9 consume 2 dimensions; all others consume 1.

- **`RevisionParameterization`**: Bridges the MATLAB-style `_apply_search` function with the `Parameterization` protocol used by all surrogate optimizers. On `__call__(x)`:
  1. Copies the base MATLAB-style arrays (cp, cpin, clin, cpln, cpln_prop)
  2. Calls `_apply_search(x, x_map, config, ...)` to modify them in-place
  3. Returns `ConstraintSet.from_matlab_style_arrays(...)` for use with `analyze_constraints`

### 1.3 `modification.py` -- Added `polish` parameter to `optimize_modification` (DONE)

**File**: `src/kst_rating_tool/optimization/modification.py`

**Problem**: `optimize_modification` hard-coded `polish=True` in `differential_evolution`. For 5D problems where each evaluation costs ~2s, the L-BFGS-B polishing step uses numerical gradients (2*d+1 = 11 evaluations per gradient step, ~20-50 gradient steps) causing hundreds of extra evaluations (~400-1000 seconds of hidden overhead).

**Fix**: Added `polish: bool = True` parameter to `optimize_modification()`, passing it through to `differential_evolution(polish=polish, ...)`. Default remains `True` for backward compatibility; the printer benchmark uses `polish=False`.

### 1.4 `__init__.py` -- Exported new symbols (DONE)

**File**: `src/kst_rating_tool/optimization/__init__.py`

Added `RevisionParameterization` and `build_x_map` to imports and `__all__`.

### 1.5 `pyproject.toml` -- Registered `slow` pytest marker (DONE)

Added to `[tool.pytest.ini_options]`:
```toml
markers = [
  "slow: marks tests as slow (deselect with '-m \"not slow\"')",
]
```

### 1.6 `test_benchmark_surrogates.py` -- Added printer 5D benchmark tests (DONE)

**File**: `benchmarks/test_benchmark_surrogates.py`

Added ~220 lines at the end of the file:

- **`_printer_5d_case_path()`**: Resolves the path to `case5g_printer_5d.m` from the repo root.

- **`_printer_5d_setup()`**: Loads the case file, constructs a hardcoded `RevisionConfig` matching the dissertation's 5-group setup:
  - Groups 1-2: type 5 (orient1d), screw clusters, axis [0,1,0], 90 degrees
  - Groups 3-4: type 5 (orient1d), snap pairs, axis [0,1,0], 60 degrees
  - Group 5: type 2 (line move), snap pair, center/direction/scale from case file
  - Returns `(base, config, x_map, param, bounds)` where `param` is a `RevisionParameterization` and `bounds` is `[(-1,1)]*5`.

- **`_run_factorial()`**: Wraps `analyze_constraints_detailed` + `optim_main_rev` to run the MATLAB-style factorial grid and extract the best TOR.

- **`TestBenchmarkPrinter5D`**: CI-friendly class (uses `polish=False` for DE, moderate budgets of 80 evals each). Tests: `test_de_baseline`, `test_one_shot_rf`, `test_adaptive_rf`, `test_bayesian_opt`, `test_comparison_report`.

- **`TestBenchmarkPrinter5DSlow`**: Marked `@pytest.mark.slow`. Higher budgets (DE=500, RF=200, ARF=200, BO=200). Includes quality assertion (surrogates within 25% of DE reference).

- **`_run_de()`** helper: Updated to accept `polish: bool = True` and pass it through.

---

## 2. Timing Data (Empirical, from this machine)

These numbers are from the profiling script that ran successfully:

| Operation | Time | Notes |
|-----------|------|-------|
| `analyze_constraints(printer_case)` | **1.909s** | Full analysis of 23 constraints (44,275 combos) |
| `analyze_constraints_detailed(printer_case)` | **2.058s** | Same + returns all intermediate data |
| `optim_rev(x)` -- single incremental eval | **30,631ms** | 30.6 seconds (!) |
| `RevisionParameterization(x)` + `analyze_constraints` | **2.013s** | The surrogate path |
| Baseline TOR for printer case | **3.8700** | At x = [0,0,0,0,0] |

### Key Finding: `optim_rev` is ~15x SLOWER than `analyze_constraints`

This was unexpected and is the central obstacle. The reason:

- **16 out of 23 constraints are revised** by the 5 groups (indices 1,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17).
- `combo_new` (combos involving ANY revised constraint) contains 44,184 out of 44,275 total combos -- essentially ALL of them.
- `optim_rev` runs `run_main_loop(combo_new, ...)` on these 44K combos PLUS `rate_motset` on the base motions PLUS merging/dedup logic. This triple work makes it much slower than a fresh `analyze_constraints`.
- In MATLAB, the same code runs much faster due to compiled inner loops and vectorized operations.

### Consequences for benchmarking:

| Method | Evals | Time/eval | Estimated total |
|--------|-------|-----------|-----------------|
| Factorial grid (`optim_rev`, no_step=4) | 3,125 | 30.6s | **26.6 hours** |
| Factorial grid (`optim_rev`, no_step=10) | 161,051 | 30.6s | **57 days** |
| DE (`analyze_constraints`, popsize=15, 5D) | ~150 | 2.0s | **5 min** |
| DE + L-BFGS-B polish | ~150 + ~300 polish | 2.0s | **15 min** |
| One-shot RF (80 evals) | 80 | 2.0s | **2.7 min** |
| Adaptive RF (80 evals) | 80 | 2.0s | **2.7 min** |
| BO (80 evals) | 80 | 2.0s | **2.7 min** |

The factorial grid is completely impractical in Python for this case. The surrogate path via `analyze_constraints` at 2s/eval is the viable approach.

---

## 3. What Was Attempted (Test Runs)

### Run 1: Factorial baseline test (KILLED)

```
pytest benchmarks/test_benchmark_surrogates.py::TestBenchmarkPrinter5D::test_factorial_baseline
```

- Used the original plan with `no_step=4` and `_run_factorial` (calling `optim_main_rev`)
- Estimated 3,125 evals * 30.6s = 26.6 hours
- Killed after ~10 min with no output (still on first `analyze_constraints_detailed`)

### Run 2: DE baseline with `polish=True` (KILLED)

```
pytest benchmarks/test_benchmark_surrogates.py::TestBenchmarkPrinter5D::test_de_baseline
```

- The `de_reference` fixture (max_eval=200) runs first, then the test (max_eval=80)
- `popsize` in scipy's `differential_evolution` is a MULTIPLIER: `popsize=15` means `15 * 5dim = 75` individuals per generation
- With `polish=True`, L-BFGS-B adds hundreds of gradient-based evaluations (each requiring 2*5+1=11 function evals)
- Total: ~475 evals * 2s = ~16 min, but L-BFGS-B polish added unknown overhead
- Killed after ~27 min with no test output (only saw test name collected)

### Run 3: DE baseline with `polish=False` (KILLED)

```
pytest benchmarks/test_benchmark_surrogates.py::TestBenchmarkPrinter5D::test_de_baseline
```

- After adding `polish=False` to bypass L-BFGS-B polishing
- Expected: reference (max_eval=200): maxiter=4, popsize=75, ~375 evals * 2s = ~12.5 min. Test (max_eval=80): maxiter=1, ~150 evals * 2s = ~5 min. Total ~17.5 min.
- Killed after ~21 min (still running, likely in the fixture)
- The popsize multiplier effect means even small `max_eval` values still produce many evaluations

---

## 4. Root Causes & Remaining Issues

### Issue A: `optim_rev` is too slow for the printer case

The incremental `optim_rev` was designed for cases where a small fraction of constraints are revised (e.g., 2 out of 10). When 16/23 constraints are revised, the "incremental" approach is worse than recomputing from scratch. This makes the factorial grid completely impractical in Python for this case.

**Status**: Cannot be fixed without fundamentally changing the algorithm. The factorial path should be removed from the printer 5D benchmark or reserved for a MATLAB-only comparison.

**Current code**: The `_run_factorial` helper and `TestBenchmarkPrinter5D` have already been updated to use DE as the reference instead. The factorial helper is kept for potential future use with simpler cases.

### Issue B: `popsize` in scipy's DE is a multiplier, not an absolute count

`optimize_modification` uses `popsize=min(15, max(5, 5*dim))` = 15 for 5D. But scipy's `differential_evolution` treats `popsize` as a multiplier: actual population = `popsize * len(x)` = `15 * 5 = 75`. So even `max_eval=80` → `maxiter=1` still produces `75 * 2 = 150` function evaluations.

**Status**: The `polish=False` fix partially addresses this, but the popsize issue remains. For a 5D problem at 2s/eval, minimum DE run = 150 evals * 2s = 5 min.

**Possible fixes**:
1. Add a `popsize` parameter to `optimize_modification` (similar to `polish`)
2. Use `maxfun` instead of `maxiter` to hard-cap total function evaluations
3. Use a smaller popsize for expensive problems (e.g., `popsize=3` → 15 individuals)

### Issue C: No tests have actually completed yet

None of the printer 5D tests have run to completion. The code is written and should be correct (no import/syntax errors were found by the linter), but runtime verification is pending.

---

## 5. Recommended Next Steps

### Quick wins (to get tests passing):

1. **Reduce popsize**: Add `popsize` parameter to `optimize_modification` and use `popsize=3` for the printer benchmark. This cuts DE from 150 to 30 evaluations per call (~60s total).

2. **Reduce reference budget**: Change the `de_reference` fixture to `max_eval=50` with `popsize=3` and `polish=False`. This gives ~30 evals at 2s = 60s. Acceptable for CI.

3. **Run the surrogate-only tests first**: `test_one_shot_rf`, `test_adaptive_rf`, `test_bayesian_opt` don't depend on the DE reference fixture. They should complete in 2-3 minutes each. Run these first to verify `RevisionParameterization` works.

### Medium-term improvements:

4. **Use `maxfun` instead of `maxiter`**: scipy's `differential_evolution` has a `maxfun` parameter that hard-caps total function evaluations. This would make `max_eval` actually mean what it says.

5. **Profile `optim_rev`**: Investigate why the Python `run_main_loop` called from `optim_rev` is 15x slower than `analyze_constraints`. The `rate_motset` function or the merge/dedup logic might have a performance bug.

6. **Add caching to `RevisionParameterization`**: For the surrogate methods, many evaluations are at similar x values. Caching the MATLAB array copies or partial results could reduce per-eval cost.

### For the full MATLAB comparison:

7. **Run factorial in MATLAB**: The dissertation's 15-minute runtime is only achievable in MATLAB. Use Octave or MATLAB to run the full `no_step=10` factorial and record the optimal TOR. Then compare against Python surrogates at much fewer evaluations.

---

## 6. File Inventory

### Modified files (all in worktree `.cursor/worktrees/kst_cad_tool/fhk`):

| File | Change |
|------|--------|
| `pyproject.toml` | Added `markers = ["slow: ..."]` to pytest config |
| `src/kst_rating_tool/optimization/__init__.py` | Added `RevisionParameterization`, `build_x_map` exports |
| `src/kst_rating_tool/optimization/modification.py` | Added `polish: bool = True` parameter |
| `src/kst_rating_tool/optimization/parameterizations.py` | Added `build_x_map()`, `RevisionParameterization` class |
| `src/kst_rating_tool/optimization/revision.py` | Fixed N-D factorial with `itertools.product` |
| `src/kst_rating_tool/optimization/surrogate.py` | (from previous session: adaptive RF) |

### New untracked files:

| File | Description |
|------|-------------|
| `src/kst_rating_tool/optimization/surrogate_bo.py` | Bayesian Optimization (from previous session) |
| `src/kst_rating_tool/optimization/surrogate_pareto.py` | Multi-output Pareto (from previous session) |
| `benchmarks/test_benchmark_surrogates.py` | All benchmarks including new printer 5D tests |
| `tests/test_surrogate_strategies.py` | Unit tests for surrogate strategies (from previous session) |

### Git branch: `optimization` (via worktree)

None of the changes from this session have been committed.
