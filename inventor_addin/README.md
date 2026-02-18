# KST Analysis Wizard – Inventor Add-in

Autodesk Inventor add-in that provides the **Constraint Definition Wizard** for KST assembly rating analysis. Build and run on **Windows** with Inventor and Visual Studio installed.

## Requirements

- Windows (Inventor is Windows-only)
- Autodesk Inventor (e.g. 2024 or 2025)
- Visual Studio 2022 (or 2019) with .NET desktop development workload
- Inventor SDK (installed with Inventor at `C:\Users\Public\Documents\Autodesk\Inventor <ver>\SDK`)

## Setup

1. Open `KstAnalysisWizardAddIn.csproj` in Visual Studio.
2. Adjust the **Inventor Interop** reference path in the .csproj if your Inventor version is not 2024:
   - Replace `Inventor 2024` with e.g. `Inventor 2025` in the `HintPath` for `Autodesk.Inventor.Interop`.
3. Build the solution (Debug or Release).
4. Register the add-in with Inventor (see Inventor SDK docs: add-in registration, or use the DeveloperTools installer to register the DLL).

## Project layout

- **ApplicationAddInServer.cs** – Implements `Inventor.ApplicationAddInServer`. Registers the "KST Analysis Wizard" ribbon button and launches the wizard.
- **AnalysisWizard/ConstraintDefinitionWizard.cs** – WinForms dialog: constraint table (Type, Location, Orientation, Select buttons), Add/Remove rows, Analyze button.
- **InputFileGenerator.cs** – Writes the constraint set to a JSON input file (generic format for the analysis script).

## Optimization Wizard

A second ribbon button opens the **Optimization Wizard**:

- Select constraint to optimize (CP1–CP24).
- Search space: Line, Discrete, Orient 1D, Orient 2D.
- Parameters: steps, line origin/direction (for line search).
- **Generate optimization plan** writes `wizard_optimization.json` (generic format with candidate matrix).
- **Run optimization** instructs to run MATLAB `run_wizard_optimization.m` with that file.
- **Load results** reads `results_wizard_optim.txt` (candidate, WTR, MTR, TOR) into the grid.

## Next steps (integration)

- **Geometry selection:** Implement "Select" button handlers that use Inventor `SelectSet` / `InteractionEvents` to let the user pick a face or point in the model, then fill Location/Orientation from the API (e.g. face normal, point coordinates).
- **MATLAB integration:** From the wizard, call MATLAB or a compiled executable with the generated input file and display WTR/MTR/TOR results (see main repo docs for MATLAB batch usage).

## References

- [docs/INVENTOR_ADDIN_DEVELOPMENT.md](../docs/INVENTOR_ADDIN_DEVELOPMENT.md) – API notes, geometry selection, links.
