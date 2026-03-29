# Fusion Circular Cap Validation Case

This is the hands-on Fusion 360 validation procedure requested in the Mar 26 supervisor meeting.

## Goal

Build a simplified circular-cap ("coin") model in Fusion, define constraints in the KST Analysis Wizard, run analysis, and compare against Python CLI.

## Target reference

Use the same logical setup as `case4_endcap.m`:

- 6 point contacts
- 1 pin
- 1 circular plane (type 2 with radius)

Reference JSON fixture:

- `test_inputs/endcap_circular_plane.json`

Expected CLI metrics:

- WTR = 1.0
- MRR = 1.3333333333333333
- MTR = 1.6272000000000002
- TOR = 1.2204000000000002

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

CLI re-validation was run from the fixture JSON and matches the expected metrics:

```bash
python scripts/run_wizard_analysis.py test_inputs/endcap_circular_plane.json results/python/fusion_circular_cap_validation.tsv
```

Observed:

- WTR = 1.0
- MRR = 1.3333333333333333
- MTR = 1.6272000000000002
- TOR = 1.2204000000000002

Output file:

- `results/python/fusion_circular_cap_validation.tsv`
