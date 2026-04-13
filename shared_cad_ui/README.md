# Shared CAD Wizard UI

Reusable .NET UI and data-contract layer shared by CAD add-ins.

## Purpose

- Provide host-agnostic wizard forms for analysis and optimization.
- Serialize a consistent JSON payload (`KstInputFile`) regardless of CAD host.
- Isolate CAD host adapters (Inventor/SolidWorks selectors) from wizard logic.

## Key components

- `AnalysisWizard/ConstraintDefinitionWizard.cs` - Constraint-entry wizard UI.
- `OptimizationWizard/OptimizationWizardForm.cs` - Optimization setup/results UI.
- `InputFileGenerator.cs` and `KstInputFile.cs` - JSON serialization contract.
- `IGeometrySelector.cs` - Host adapter interface for geometry picking.
- `Logger.cs` - Shared logging utility.

## Host integration

- `inventor_addin` and `solidworks_addin` are expected to implement `IGeometrySelector`.
- Both hosts should emit the same generic JSON contract documented in `docs/dev/GENERIC_INPUT_FORMAT.md`.

## Backend integration

- Preferred execution backend:
  - `scripts/run_wizard_analysis.py`
  - `scripts/run_wizard_optimization.py`
- MATLAB integration remains supported for legacy workflows, but Python is the primary engine path.
