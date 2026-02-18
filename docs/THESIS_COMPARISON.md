# Comparison of Octave and Python Results to Thesis (Ch 10 / Ch 11)

This document summarizes how the numerical results from the **Octave** (MATLAB-compatible) and **Python** implementations compare to the baseline analysis results published in the dissertation (Rusli, OSU 2008): **Chapter 10** (Case Study Baseline Analysis Results) and **Chapter 11** (Design Optimization and Trade-Off Case Study Results).

## Reference values (thesis)

Reference values are taken from the following tables:

| Case | Thesis section | Table | Description |
|------|----------------|-------|-------------|
| **case1a_chair_height** | Ch 10.1 | Table 10.2 | Thompson's chair (exactly constrained) |
| **case2a_cube_scalability** | Ch 10.2.2 | Table 10.7 | Cube scale factor = 1 |
| **case2b_cube_tradeoff** | Ch 10.2.1 | Table 10.6 | Cube 7 constraints (CP2,CP3,CP4,CP5,CP7,CP10,CP12) |
| **case3a_cover_leverage** | Ch 10.3.1 | Table 10.10 | Battery cover assembly (HOC baseline) |

## Thesis reference numbers (excerpt)

### Case 1 – Thompson's chair (Table 10.2)

- **WTR** 0.191 (LAR 5.236)
- **MRR** 1.000  
- **MTR** 1.001 (LAR 0.999)  
- **TOR** 1.001  
- **WTR motion:** ω = (0, 0.708, 0.706), ρ = (2, 1.724, 1.731), h = 0.001, **Total Resistance** = 0.191  
- **Unique screw motions:** 21  
- **CP table:** all CPs 14.3% Active, 14.3% Best Resistance  

### Case 3 – Cube scalability, scale = 1 (Table 10.7)

- **WTR** 0.200 (LAR 5.003)  
- **MRR** 1.000  
- **MTR** 0.486 (LAR 2.057)  
- **TOR** 0.486  

### Case 4 – Cube 7 constraints (Table 10.6)

- Same metrics as case 3 (WTR 0.200, MRR 1.000, MTR 0.486, TOR 0.486).  
- **WTR Motion 1:** ω = (0.577, 0.577, 0.577), ρ = (0.333, 0.750, 0.417), h = 0.083, TR = 0.200.  

### Case 5 – Battery cover baseline (Table 10.10)

- **WTR** 2.000 (LAR 0.500)  
- **MRR** 1.500  
- **MTR** 2.000 (LAR 0.500)  
- **TOR** 1.333  

## Comparison outcome (Python & Octave vs thesis)

For the four cases above, **both Python and Octave** full-report results were compared to the thesis reference values (metrics WTR, MRR, MTR, TOR, LAR_WTR, LAR_MTR; counts; WTR motion total resistance where given). Tolerances: **atol = 1e-3**, **rtol = 5%**.

| Case | Thesis source | Python vs thesis | Octave vs thesis |
|------|----------------|------------------|------------------|
| **case1a_chair_height** | Ch 10 Table 10.2 | **PASS** | **PASS** |
| **case2a_cube_scalability** | Ch 10 Table 10.7 | **PASS** | **PASS** |
| **case2b_cube_tradeoff** | Ch 10 Table 10.6 | **PASS** | **PASS** |
| **case3a_cover_leverage** | Ch 10 Table 10.10 | **PASS** | **PASS** |

- **Metrics:** All of WTR, MRR, MTR, TOR and the LAR values match the thesis within the above tolerances for both Python and Octave.  
- **Counts:** For Thompson's chair, `no_mot_unique` = 21 matches the thesis.  
- **WTR motion:** Total resistance of the WTR motion matches (e.g. 0.191 for case 1; 0.200 for cube). Screw axis (ω, ρ, h) can differ by sign or parameterization (same physical motion); our outputs are consistent between Python and Octave.

## How to reproduce

1. **Generate full results (Python and Octave)**  
   - Python:  
     `python scripts/run_python_case.py <case_num> --full`  
   - Octave (from `matlab_script/`):  
     `octave --no-gui run_case_batch.m <case_num>`  
   For case 3 pipe `1` (scale); for case 4 pipe `7` (number of constraints).

2. **Run the thesis comparison**  
   From repo root:  
   `python scripts/compare_to_thesis.py 1`  
   or for all cases that have thesis references:  
   `python scripts/compare_to_thesis.py all`  

   The script reads `results_python_<case>_full.txt` and `results_octave_<case>_full.txt` and compares them to the stored thesis reference values (Ch 10/11).

## Notes

- **Chapter 11** mainly reports design optimization and trade-off studies (constraint addition/reduction, response surfaces). The **baseline** numbers there (e.g. Table 11.4 for the cube, Table 11.5 for 15-constraint cube) match the Ch 10 baseline tables; our comparison uses the Ch 10 tables as the canonical reference.  
- **Screw motion parameterization:** The thesis and our code can output the same physical WTR motion with opposite sign on ω (and corresponding ρ). Comparing Total Resistance and counts is the main check; screw components are compared only for consistency between Python and Octave.  
- **Other cases (6–21):** Thesis Ch 10/11 do not give explicit baseline tables for every input file (e.g. case3b/3c, endcap, printer variants). For those, validation is done by **Python vs Octave** comparison (`compare_octave_python.py all`). **Python matches Octave for all 21 cases** (atol=1e-3, rtol=5%); see [PARKED.md](PARKED.md) and [PROJECT_STATUS_SUMMARY.md](PROJECT_STATUS_SUMMARY.md).
