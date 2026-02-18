# Comparing Python and Octave (MATLAB) KST Results

This document describes how to run the same test cases in the Python KST tool and in GNU Octave (MATLAB-compatible) and compare the outputs (WTR, MRR, MTR, TOR).

## Prerequisites

- **Python**: Install the project with `pip install -e .` from the repo root (see [README](../README.md)).
- **GNU Octave**: Install Octave (no MATLAB license required). The original MATLAB scripts in `matlab_script/` run under Octave with minor compatibility fixes (e.g. row/column handling in `react_wr_5_compose.m`).

## Case numbers and names

The batch runner uses the same case numbering as the original MATLAB menu (1–21):

| # | Case name |
|---|-----------|
| 1 | case1a_chair_height |
| 2 | case1b_chair_height_angle |
| 3 | case2a_cube_scalability |
| 4 | case2b_cube_tradeoff |
| 5 | case3a_cover_leverage |
| 6 | case3b_cover_symmetry |
| 7 | case3c_cover_orient |
| 8 | case4a_endcap_tradeoff |
| 9 | case4b_endcap_circlinsrch |
| 10 | case5a_printer_4screws_orient |
| 11 | case5b_printer_4screws_line |
| 12 | case5c_printer_snap_orient |
| 13 | case5d_printer_snap_line |
| 14 | case5e_printer_partingline |
| 15 | case5f1_printer_line_size |
| 16 | case5f2_printer_sideline_size |
| 17 | case5g_printer_5d |
| 18 | case5rev_a_printer_2screws |
| 19 | case5_printer_allscrews |
| 20 | case5rev_d_printer_remove2_bot_screw |
| 21 | case5rev_b_printer_flat_partingline |

## Running the Python pipeline

From the **repository root**:

```bash
# By case number (1–21)
python scripts/run_python_case.py 1

# By case name
python scripts/run_python_case.py case1a_chair_height
```

This loads the corresponding `.m` case file from `matlab_script/Input_files/`, runs the analysis, and writes:

- **`results_python_<casename>.txt`** in the repo root (tab-separated: WTR, MRR, MTR, TOR).

## Running the Octave (MATLAB) pipeline

From the **repository root**:

```bash
cd matlab_script
octave --no-gui run_case_batch.m <case_number>
```

Example for case 1 (case1a_chair_height):

```bash
cd matlab_script
octave --no-gui run_case_batch.m 1
```

This runs the same analysis as `main.m` (without the interactive menu or optimization) and writes:

- **`matlab_script/results_octave_<casename>.txt`** (tab-separated: WTR, MRR, MTR, TOR).

**Note:** Cases that use `input()` in the case file will block in batch unless stdin is provided. The comparison script pipes the following when running "compare all":

| Case | Stdin | Meaning |
|------|--------|--------|
| 3 | `1` | Scaling factor (case2a_cube_scalability) |
| 4 | `7` | ct_2 = 7 constraint points (case2b_cube_tradeoff) |
| 8 | `0` | no_snap = 0: cp-only (non-HOC) branch for case4a_endcap_tradeoff |

For case 8, Python loads the same configuration by parsing the first `cp = [ ... ]` block in the `.m` file, which is the no_snap==0 (24-point cp-only) branch. Octave with stdin `0` thus matches Python. The batch driver sets `no_snap = 0` before running the case script so that non-interactive runs without stdin also use the cp-only branch.

## Comparing results

From the **repository root**:

```bash
python scripts/compare_octave_python.py 1
# or
python scripts/compare_octave_python.py case1a_chair_height
```

This script:

1. Runs the Python pipeline and writes `results_python_<case>.txt`.
2. Runs the Octave batch and writes `results_octave_<case>.txt` in `matlab_script/`.
3. Reads both files and compares WTR, MRR, MTR, TOR with configurable tolerances (default: atol=1e-3, rtol=1e-2).
4. Prints PASS or FAIL.

You can relax or tighten tolerances by editing the `atol` and `rtol` values in `scripts/compare_octave_python.py` if needed (e.g. for floating-point or implementation differences).

**Run all 21 cases:**

```bash
python scripts/compare_octave_python.py all
```

This runs Python and Octave for each case (1–21), compares WTR/MRR/MTR/TOR (atol=1e-3, rtol=5%), and prints Passed/Failed. Cases that use `input()` (3, 4, 8) are run with stdin piped (1, 7, 0) so Octave does not block.

### Raw numbers and visualization

To dump raw Python vs Octave numbers and generate deviation graphs:

```bash
# Use existing result files (no re-run)
python scripts/visualize_octave_python.py

# Or run all 21 cases first, then dump and plot
python scripts/visualize_octave_python.py --run
```

**Output:**

- **`docs/octave_python_comparison_raw.csv`** — Raw numbers: case number/name, WTR/MRR/MTR/TOR for Python and Octave, absolute and relative differences (%). One row per case.
- **`docs/figures/octave_python_comparison_bars.png`** — Grouped bar charts: Python vs Octave for WTR, MRR, MTR, TOR (one subplot per metric).
- **`docs/figures/octave_python_deviation_rel.png`** — Relative deviation (%) per case per metric (grouped bars).
- **`docs/figures/octave_python_scatter.png`** — Scatter: Python vs Octave (one subplot per metric; diagonal line = agreement).
- **`docs/figures/octave_python_max_deviation.png`** — Max relative deviation per case (green ≤5%, orange ≤20%, red >20%).

### Validation status

With atol=1e-3 and rtol=5%, **all 21 cases pass** (Python vs Octave). The result files in the current workspace have been verified: 21/21 pass. All cases run to completion in both Python and Octave.

### Parity (combo order and duplicate resolution)

The Python port is aligned with MATLAB/Octave so that combo order and duplicate-motion resolution match, giving **full 21-case parity**. The main alignment points: combo order (lexicographic, matching `nchoosek`), first-occurrence semantics for unique motions, and consistent rounding and solver usage. To re-verify: `python scripts/compare_octave_python.py all`. See [PARKED.md](PARKED.md) and [PROJECT_STATUS_SUMMARY.md](PROJECT_STATUS_SUMMARY.md).

*(The following paragraph is kept for reference on why ordering matters.)*

Cases 1–7 and 21 use **point-only** (or mostly point) constraints; cases 8–9 add endcap geometry (case 8 with no_snap=0 is still cp-only but 24 points); cases 10–20 use **pins and lines** (printer housing). The same analytical method should give the same results up to rounding; the observed differences (e.g. WTR ~1.75 Python vs ~2.44 Octave for cases 10–17) come from one or more of:

1. **Combo row order**  
   MATLAB uses `nchoosek(1:total_cp, k)`; Python uses `itertools.combinations(range(1, total_cp+1), k)`. The **set** of combinations is the same, but the **order** of rows can differ. The main loop processes combos in that order and appends motions (and their resistance rows) in that order.

2. **Duplicate motion → which row is kept**  
   When the same screw motion appears from more than one combo, both sides keep a single “unique” motion and one resistance row. MATLAB uses `unique(mot_all_org, 'rows')` and keeps the **first** occurrence (`uniq_idx`); Python uses `np.unique(mot_all, axis=0, return_index=True)` and also keeps the first. Because combo order differs, the “first” occurrence of a duplicate motion can be different in Python vs Octave, so the **resistance (R) row** kept for that motion can differ. WTR is the minimum row-sum over those unique motions, so a different R row for the same motion can change WTR (and MRR/MTR/TOR).

3. **Solver/rounding**  
   Small differences in rank checks, backslash vs `np.linalg.solve`/`pinv`, or rounding (e.g. to 4 decimals) can change R slightly and, after duplicate resolution, change which motion ends up as the worst-case.

So the algorithm is the same; the **ordering** of combos and thus of duplicate resolution is what drives the remaining mismatch for cases 8–20. To get bit-for-bit parity you would need to either (a) sort combo rows in Python to match MATLAB’s `nchoosek` order and/or (b) match the duplicate-resolution rule (e.g. same “first” semantics as MATLAB’s `unique(..., 'rows')`). The current Python port matches this; **all 21 cases pass** at 5% tolerance.

### MATLAB 7.7 verification (optional)

To confirm that Octave results match the original thesis (2008), run the same 21 cases on MATLAB 7.7 (or 7.6–7.x) when available (e.g. lab license or legacy install). Record WTR, MRR, MTR, TOR for each case and compare to Octave. If they match, Octave is an acceptable reference for the Python port; if they differ, document the differences and choose MATLAB 7.7 or Octave as the canonical reference for 1:1 parity work. See **THESIS_PROGRESS_UPDATE.md** (Post–Pak Leo meeting) for the full plan.

### One-to-one parity (MATLAB/Octave vs Python)

The Python port is aligned for numerical convergence with the MATLAB/Octave reference:

- **combo_preproc**: For pin/line cases (no planes), MATLAB builds combo3, combo4, and combo5; the Python port does the same (5-constraint combinations are included in the pin/line branch). Combo rows are **sorted lexicographically** (by columns 0..4) after building so the order matches MATLAB `nchoosek(1:total_cp, k)` output. For case 8, batch runs use stdin `0` (no_snap=0, cp-only) so Python and Octave use the same configuration; Python parses the first `cp = [ ... ]` block in the `.m` file (no_snap==0 branch).
- **Duplicate motion resolution**: Python uses `np.unique(mot_all, axis=0, return_index=True)`, which returns the **first occurrence** of each unique motion (same as MATLAB `unique(..., 'rows')` with default first-occurrence index).
- **rate_cp**: `react_wr` is built with **columns = wrenches** (transpose of `[react_wr_5; wr_pt_set]`) and solved with `react_wr @ x = b` to match MATLAB `react_wr \ input_wr`. Rank is checked with a Frobenius-norm–based tolerance; full rank uses `np.linalg.solve`, with `np.linalg.pinv` as fallback.
- **input_wr_compose**: **Pure translation (h=inf)** is handled first: `fi=mu`, `ti=0`, so `input_wr = -[mu; 0]`. This avoids using the rotation branch when `hw=1/h` is set to inf and producing non-finite wrenches. **h=0** (rotation-dominant) uses the branch `abs(hw)>=d` so `fi=hs*d*omu`, `ti=d*omu`.
- **Motion rounding**: `mot_arr` and `mot_all` are rounded to 4 decimal places before duplicate checks and `np.unique`, matching MATLAB `round(mot.*1e4)./1e4`.
- **Ri and rating**: `Ri = 1./R` with inf/nan set to 0, rounded to 4 decimals; `min(rowsum)==0` forces WTR=MRR=MTR=TOR=0 (free motion), otherwise WTR=min(rowsum), MRR=mean(rowsum./max_of_row), MTR=mean(rowsum), TOR=MTR/MRR.
- **Higher-order constraints**: `rate_cpin`, `rate_clin`, `rate_cpln1`, `rate_cpln2` mirror the MATLAB formulas (line of action, reaction wrench, `react_wr\\input_wr`, reciprocal sum for pos/neg). `react_wr_5_compose` uses the same constraint order (point → pin → line → plane) and indexing (1-based combo indices, `idx <= no_cp` for point, etc.) as MATLAB.

Case 1 (case1a_chair_height) is validated to match Octave: WTR=0.1910, MRR=1.0000, MTR=1.0008, TOR=1.0008.

### Known loading (specmot) — Python only script

The Python port includes a script that mirrors MATLAB option 6 (Known loading condition study):

```bash
python scripts/run_python_specmot.py <case_name_or_number> [motion_index]
```

- `motion_index`: `0` = first motion from the full analysis; `1..N` = row from the unique motion set; omit to be prompted.
- Writes `results_python_specmot_<casename>.txt` with WTR, MRR, MTR, TOR for the specified loading.

## Result file format

Both Python and Octave write a simple tab-separated file:

```
WTR	<value>
MRR	<value>
MTR	<value>
TOR	<value>
```

The comparison script parses this format and compares the four metrics.
