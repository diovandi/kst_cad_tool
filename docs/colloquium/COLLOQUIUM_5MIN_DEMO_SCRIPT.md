# Colloquium 5-Minute Demo Script

Use this CLI path as the reliable live demo. If Fusion 360 is stable on the presentation machine, open the add-in first for visual context, then fall back to these commands for reproducible output.

## 0:00-0:45 - Show the Data Contract

```powershell
Get-Content test_inputs\endcap_circular_plane.json
```

Say:

This is the CAD-to-math contract. The end-cap case has six point contacts, one pin, and one circular plane. The plane row uses type `2` for circular plane and radius `0.625`.

## 0:45-2:00 - Run KST Analysis

```powershell
python3 scripts/run_wizard_analysis.py test_inputs\endcap_circular_plane.json results\presentation_endcap.tsv --skip-geometry-check
Get-Content results\presentation_endcap.tsv
```

Expected key line:

```text
1.0    1.277412872841444    1.8112647058823529    1.4179164578111947
```

Say:

The script converts JSON into `ConstraintSet`, builds HOC wrench systems, computes reciprocal motions, solves resistance, and writes TSV, detailed JSON, and a MATLAB-style HTML report.

## 2:00-3:00 - Show Optimization Input

```powershell
Get-Content matlab_script\Input_files\generic_example_optimization.json
```

Say:

The optimization input contains the baseline `analysis_input` plus a `candidate_matrix`. Here point constraint 7 is replaced by five possible candidate rows along a line search.

## 3:00-4:20 - Run Candidate Sweep

```powershell
python3 scripts/run_wizard_optimization.py matlab_script\Input_files\generic_example_optimization.json results\presentation_optimization.tsv
Get-Content results\presentation_optimization.tsv
```

Expected table:

```text
candidate    WTR      MRR    MTR          TOR
1            0.191    1      1.008292857  1.008292857
2            0.191    1      1.00557381   1.00557381
3            0.191    1      1.000669048  1.000669048
4            0.191    1      0.9969095238 0.9969095238
5            0.191    1      0.9945428571 0.9945428571
```

Say:

This is the simple discrete sweep. The larger optimization work uses the same KST objective but reduces the number of objective calls with Differential Evolution or surrogate-guided sampling.

## 4:20-5:00 - Close

Say:

The demo shows the three main claims: the input data is explicit, the analysis engine is reproducible, and optimization changes candidate constraints while keeping the verified KST rating engine underneath.

## Optional Fusion Visual

If time permits, show the Fusion 360 wizard screenshot or live add-in:

- Constraint type dropdown: Point, Pin, Line, Plane
- Constraint list and confirm dialog
- Plane workflow with rectangular/circular property extraction
- Result fields: WTR/MRR/MTR/TOR

Do not depend on Fusion for the live numerical result unless the machine has already been tested.
