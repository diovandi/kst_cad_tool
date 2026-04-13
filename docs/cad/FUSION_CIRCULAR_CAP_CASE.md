# Fusion Circular Cap Validation Case

This is the hands-on Fusion 360 validation procedure requested in the Mar 26 supervisor meeting.

## Goal

Build a simplified circular-cap ("coin") model in Fusion, define constraints in the KST Analysis Wizard, run analysis, and compare against Python CLI.

## Target reference

Use the same logical setup as **`matlab_script/Input_files/case4a_endcap_tradeoff.m` with `no_snap == 2`** (Rusli dissertation / thesis branch: six point contacts at **z = 0.188**, circular plane radius **0.625**, same length units as the MATLAB reference—not necessarily millimetres):

- 6 point contacts (positions and normals as in that branch)
- 1 pin
- 1 circular plane (type 2 with radius **0.625**)

The older `case4_endcap.m` layout uses **z = 0** and different in-plane point placement; the fixture is intentionally aligned with **`case4a_endcap_tradeoff` no_snap==2**, not `case4_endcap.m`.

Reference JSON fixture:

- `test_inputs/endcap_circular_plane.json`

Expected CLI metrics (must match `python scripts/run_python_case.py case4a_endcap_tradeoff --no-snap 2`):

- WTR = 1.0
- MRR = 1.2774
- MTR = 1.8113
- TOR = 1.4179

**Units / geometry check:** The wizard treats JSON lengths as **millimetres** for the recommended minimum feature size (7 mm). Thesis/MATLAB coordinates are **small** (e.g. radius 0.625), so validating this fixture with the CLI requires **`--skip-geometry-check`**. Fusion exports are still typically in mm—you may need to **scale** your CAD so exported coordinates match the same **constraint geometry** as the reference (or compare ratios / re-scale numerically).

## Fusion build steps

1. Create a simple coin/cap body (cylindrical disk).
2. Add enough geometric features to pick:
   - six point-contact vertices/locations,
   - one pin axis (edge/face axis),
   - one circular plane face.
3. Open **KST Analysis Wizard** in Fusion.
4. Add constraints:
   - Point x6
   - Pin x1
   - Plane x1 (circular face)
5. Click **Run Analysis**.
6. Confirm outputs were written to `~/Documents/KstAnalysis/`:
   - `wizard_input.json`
   - `results_wizard.txt`
   - `Result - wizard_input.html`

## Comparison workflow

1. Copy the generated `wizard_input.json` into this repo (for example: `results/python/fusion_circular_cap_wizard_input.json`).
2. Run:

```bash
python scripts/run_wizard_analysis.py results/python/fusion_circular_cap_wizard_input.json results/python/fusion_circular_cap.tsv
```

3. Compare Fusion-run metrics in `results_wizard.txt` with CLI metrics in `results/python/fusion_circular_cap.tsv`.
4. Verify the generated HTML report contains:
   - WTR/MRR/MTR/TOR summary
   - motion table (Om/Mu/Rho/Pitch/Total Resistance)
   - CP summary table

## Pass criteria

- Fusion and CLI metrics agree within tolerance used elsewhere in the project (atol `1e-3`, rtol `5%`).
- No empty `pins`/`lines`/`planes` in generated JSON when those constraints were added.
- HTML report renders all expected sections.

## Latest validation result

CLI re-validation from the fixture JSON (thesis-aligned numerics; geometry check skipped):

```bash
python scripts/run_wizard_analysis.py test_inputs/endcap_circular_plane.json results/python/fusion_circular_cap_validation.tsv --skip-geometry-check
```

Observed:

- WTR = 1.0
- MRR = 1.2774
- MTR = 1.8113
- TOR = 1.4179

Output file:

- `results/python/fusion_circular_cap_validation.tsv`
