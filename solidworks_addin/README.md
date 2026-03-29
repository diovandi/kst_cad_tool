# KST SolidWorks Add-in (Prototype)

This folder contains a prototype SolidWorks add-in host wired to the shared CAD wizard UI layer.

## Purpose

- Host command/ribbon integration in SolidWorks.
- Delegate wizard behavior and JSON generation to `shared_cad_ui`.
- Keep KST math execution outside the add-in host (Python runner recommended).

## Key files

- `KstSwAddIn.cs` - `ISwAddin` implementation and SolidWorks command integration.
- `SwGeometrySelector.cs` - SolidWorks-specific geometry picking bridge.
- `SelectPromptForm.cs` - Selection prompt UI helper.
- `KstSwAddIn.csproj` - Build configuration for the add-in assembly.

## Runtime expectation

1. User defines constraints in wizard UI.
2. Add-in serializes generic input JSON via `shared_cad_ui`.
3. External script runs analysis/optimization:
   - Preferred: `scripts/run_wizard_analysis.py` or `scripts/run_wizard_optimization.py`
   - Optional legacy path: MATLAB batch/compiled executable.
4. Results are loaded back into the wizard UI.

## Status

- Prototype integration path for CAD host wiring.
- Not exercised in CI (Windows CAD runtime dependency).
- Use this with `shared_cad_ui` as a paired component.
