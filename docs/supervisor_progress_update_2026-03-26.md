# Supervisor Progress Update (2026-03-26)

## Summary
Implemented a set of Fusion 360 “KST Analysis Wizard” improvements to make the add-in more reliable and easier to debug end-to-end (constraint picking -> JSON -> external analysis -> UI results).

## What’s done
- Improved wizard execution reliability:
  - More robust external script path resolution.
  - Safer subprocess execution (multiple Python candidates + timeout).
  - Added a pre-run confirmation step that lists all chosen constraints.
- Standardized length units at the Fusion extraction boundary:
  - Converted Fusion internal cm coordinates to mm before writing `wizard_input.json`.
  - Updated viewport visualization marker scales to match mm.
- Improved constraint usability:
  - Type-aware auto-naming: `C_point1`, `C_pin1`, `C_line1`, `C_plane1`.
  - Stronger selection validation (e.g., straight edges for `Line`/`Pin`, orientation-method mismatch checks).
- Added comprehensive run-scoped debugging:
  - Added `run_id` + `START/SUCCESS/SKIP/FAIL` step logging throughout the Fusion command.
  - Enhanced subprocess/result parsing logging (including output existence + file size checks).
  - Updated the external `scripts/run_wizard_analysis.py` runner so it always writes `results_wizard.txt` on failure (includes an `ERROR` line).

## Current debugging finding
- When the wizard input contains only `point_contacts` + one `plane` (with `pins` and `lines` empty), the solver returns `WTR/MRR/MTR/TOR = 0.0`.
- This is not an “output missing” issue anymore; the updated logs make it clear what constraint arrays were actually serialized into `wizard_input.json`.

## Next steps
- In Fusion: verify that `Pin` and `Line` constraints are being successfully added/serialized (so `pins` and `lines` are non-empty in `wizard_input.json`).
- Use the new logs to quickly pinpoint any cases where constraint rows are skipped during `Add Constraint` or dropped during JSON serialization.
- Once constraint sets are complete, proceed with the end-to-end comparison test workflow.

