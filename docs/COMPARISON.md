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

**Note:** Cases that use `input()` in the case file (e.g. case 3 for scaling factor, case 8 for number of snaps) will block in batch. For those, either provide input via stdin (e.g. `echo 1 | octave --no-gui run_case_batch.m 3`) or use a batch-safe wrapper that sets the variable before running the case script.

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

### Validation status

With atol=1e-3 and rtol=5%, **cases 1–7 and 21** pass consistently. Cases 8–20 may show larger numerical differences (combo order, unique motion ordering, or solver/rounding). All cases run to completion in both Python and Octave.

### One-to-one parity (MATLAB/Octave vs Python)

The Python port is aligned for numerical convergence with the MATLAB/Octave reference:

- **rate_cp**: `react_wr` is built with **columns = wrenches** (transpose of `[react_wr_5; wr_pt_set]`) and solved with `react_wr @ x = b` to match MATLAB `react_wr \ input_wr`. Rank is checked with a Frobenius-norm–based tolerance; full rank uses `np.linalg.solve`, with `np.linalg.pinv` as fallback.
- **input_wr_compose**: **Pure translation (h=inf)** is handled first: `fi=mu`, `ti=0`, so `input_wr = -[mu; 0]`. This avoids using the rotation branch when `hw=1/h` is set to inf and producing non-finite wrenches. **h=0** (rotation-dominant) uses the branch `abs(hw)>=d` so `fi=hs*d*omu`, `ti=d*omu`.
- **Motion rounding**: `mot_arr` and `mot_all` are rounded to 4 decimal places before duplicate checks and `np.unique`, matching MATLAB `round(mot.*1e4)./1e4`.
- **Ri and rating**: `Ri = 1./R` with inf/nan set to 0, rounded to 4 decimals; `min(rowsum)==0` forces WTR=MRR=MTR=TOR=0 (free motion), otherwise WTR=min(rowsum), MRR=mean(rowsum./max_of_row), MTR=mean(rowsum), TOR=MTR/MRR.

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
