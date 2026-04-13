# Autodesk Inventor Add-in Development

Research notes for building the KST Analysis Wizard as an Inventor add-in. The add-in runs on **Windows** only; build and debug in Visual Studio on a machine with Inventor installed.

---

## Overview

- **Language:** C# (.NET). VB.NET also supported.
- **Inventor 2025:** Supports .NET 8.0 add-ins (migration from .NET Framework).
- **Inventor 2018–2024:** Typically .NET Framework 4.x.
- **SDK location:** `C:\Users\Public\Documents\Autodesk\Inventor <version>\SDK`
- **Templates:** Visual Studio 2022 add-in templates via DeveloperTools.msi (from SDK).

---

## Add-in Architecture

1. **ApplicationAddInServer** – Interface the add-in implements. Inventor loads the DLL and calls `Activate()` / `Deactivate()`.
2. **Ribbon UI** – Add a button to a ribbon tab (e.g. "Add-Ins") that launches the Analysis Wizard.
3. **Custom dialog** – WPF or WinForms window for the Constraint Definition Wizard (table + Select buttons).
4. **Geometry selection** – Use Inventor’s `SelectSet` and interaction events so the user picks faces/edges/points in the model; the add-in then reads coordinates and normals via the API.

---

## Key API Areas

### Document and Application

- `Application` – Root object; `ActiveDocument` gives current part/assembly.
- `PartDocument` / `AssemblyDocument` – `ComponentDefinition.SurfaceBodies`, `Faces`, `Edges`.

### Geometry Selection

- **SelectSet** – Collection of user-selected entities. Use `SelectSet.Select()` or interaction events (e.g. `SelectEvents`) to let the user pick a face, edge, or point.
- **Face** – `Face.Evaluator.GetNormal(Params, Normals)` for normal at a UV point; for planar faces, `Face.Geometry is Plane` and `Plane.Normal`.
- **Point on face** – Use `Face.Evaluator.GetPointAtParam()` or similar to get (x,y,z) at a parametric point; for “point on surface” from user pick, the selection often provides the point.
- **Edge / axis** – For pin constraints, use edge geometry to get axis direction (e.g. line direction).

### Getting Location and Orientation (Constraint Wizard)

| Constraint type | Location source | Orientation source |
|-----------------|-----------------|---------------------|
| Point (CP) | Point on face (e.g. face center or user pick) → (x,y,z) | Face normal → (nx,ny,nz) |
| Pin (CPIN) | Center of circular face or user pick → (x,y,z) | Cylinder axis or edge direction → (ax,ay,az) |
| Line (CLIN) | Midpoint of edge or face → (x,y,z) | Line direction + constraint normal from face |

- **Planar face:** `Face.Geometry as Plane` → `Plane.Normal`, `Plane.RootPoint` (or Evaluator for point on face).
- **Cylindrical face (pin):** Axis from cylinder geometry; center from evaluator.
- **User pick:** Use `InteractionEvents` / `SelectEvents` to trigger “Select in model”; then read the selected `Face` or `Edge` and extract location and orientation.

### Transient Geometry

- `Application.TransientGeometry` – Create vectors, points, etc. (e.g. `CreatePoint()`, `CreateUnitVector()`).

---

## Dialog (WPF vs WinForms)

- **WPF** – Modern UI, data binding; recommended for the constraint table (Type, Location, Orientation columns and Select buttons).
- **WinForms** – Simpler; DataGridView for table, Button for Select.
- The wizard window can be modal or modeless; modal is simpler for “define constraints then run analysis.”

---

## References

- [Inventor 2025 Help – Creating an Add-In](https://help.autodesk.com/view/INVNTOR/2025/ENU/?guid=GUID-52422162-1784-4E8F-B495-CDB7BE9987AB)
- [Inventor 2025 – Introduction to Programming Interface](https://help.autodesk.com/view/INVNTOR/2025/ENU/?guid=GUID-6FD7AA08-1E43-43FC-971B-5F20E56C8846)
- [My First Inventor Plug-in (C#)](https://www.autodesk.com/support/technical/article/caas/tsarticles/ts/29mPk2V7aweIo6eLckSF1k.html)
- [Face normal in Inventor API (ADN)](https://adndevblog.typepad.com/manufacturing/2012/08/what-is-the-best-way-to-compute-a-normal-of-a-face-in-inventor-api.html)
- [Debug Inventor 2025 add-in (launchSettings.json)](https://blog.autodesk.io/debug-new-inventor-2025-add-in/)
- Inventor API Help from Inventor Help menu (local, version-specific)

---

## Project Skeleton (this repo)

See `inventor_addin/` in this repository:

- **KstAnalysisWizardAddIn.csproj** – C# project (target Inventor version via reference paths).
- **ApplicationAddInServer** – Implements Inventor’s add-in interface; registers ribbon button.
- **AnalysisWizard** – Placeholder for the Constraint Definition Wizard dialog (WPF or WinForms).
- **InputFileGenerator** – Stub to generate analysis input file (e.g. JSON or .m) from constraint table data.

Build and run on **Windows** with Inventor and Visual Studio installed. SDK references point to `C:\Users\Public\Documents\Autodesk\Inventor <ver>\SDK`; adjust for your Inventor version.
