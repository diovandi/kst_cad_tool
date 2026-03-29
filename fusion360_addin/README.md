# KST Analysis Wizard -- Fusion 360 Add-in

Python add-in for Fusion 360 that provides the **KST Analysis Tool** and **KST Optimization Tool** (constraint definition, prepare input, run analysis/optimization).

## Supported constraint types

The wizard supports all four KST constraint types:

| Type | Location pick | Orientation pick | Notes |
|------|--------------|-----------------|-------|
| **Point** | Vertex | Face (normal), Edge (direction), or Two Points (vector) | Orientation method selectable via dropdown |
| **Pin** | Vertex | Edge (axis direction) | Pick a line/edge as the pin axis |
| **Line** | Edge | (none needed) | Edge defines midpoint, direction, and length |
| **Plane** | Face | (none needed) | Face defines midpoint and normal |

### Orientation methods (Point type only)

When the constraint type is **Point**, an additional **Orientation method** dropdown is shown:

- **Normal to Plane** (default) -- pick a face; its normal defines orientation
- **Two Points** -- pick two vertices; the vector between them defines orientation
- **Along Line/Axis** -- pick an edge; its direction defines orientation

### Selection filters

Selection filters are adjusted automatically based on the constraint type so you only see valid picks:

- **Point/Pin location**: Vertices only (hovering a circle selects its center vertex)
- **Line location**: Edges only
- **Plane location**: Faces only

### Session controls (Analysis wizard)

- **Save Config** / **Load Config** — Persist or restore the constraint table as `constraint_config.json` in the output folder (`~/Documents/KstAnalysis/` by default).
- **Invert Direction** — When adding a constraint, flip the orientation (and for **Line**, the constraint normal direction).
- **Update Selected** + **Edit Index** — Re-select geometry for an existing row (1-based index in the table).

## Run in Fusion 360 (from repo)

1. **Open Fusion 360** and have a design open (or any document).
2. Go to **UTILITIES** tab > **Scripts and Add-Ins** (or **ADD-INS** > **Scripts and Add-Ins**).
3. In the **Add-Ins** tab, click the **green "+"** (Add script or add-in).
4. Browse to this repo and select the **`KstAnalysis`** folder:
   - Full path example: `C:\Users\<You>\kst_cad_tool\fusion360_addin\KstAnalysis`
   - The folder must contain `KstAnalysis.manifest` and `KstAnalysis.py`.
5. Click **Run** (or enable **Run on startup** if you want it to load every time).
6. In the **SOLID** or **DESIGN** workspace, find **KST Analysis Wizard** and **KST Optimization Wizard** in the **Scripts and Add-Ins** panel (or **Add-Ins** panel) and click to open the wizards.

The add-in expects the rest of the repo (especially `src/kst_rating_tool`) to be present so that **Run Analysis** can run the Python backend. The repo root is inferred from the add-in path; keep the project structure intact.

## If Run Analysis says "kst_rating_tool not found"

- Make sure you added the **`KstAnalysis`** folder that lives **inside** the repo (`kst_cad_tool\fusion360_addin\KstAnalysis`), not a copy elsewhere. The code looks for `repo/src` relative to the add-in path.
- If you copied the add-in to Fusion's ApplicationPlugins folder, you must either run from the repo as above or use the bundle script (see below) so `kst_rating_tool` is included.

## Install as a bundle (optional)

To install so Fusion loads it from its own add-in folder (no need to point at the repo each time):

1. Run the bundle script from the repo root:
   ```bash
   python fusion360_addin/build_bundle.py
   ```
   This creates `fusion360_addin/KstAnalysis.bundle` with the add-in and a copy of `kst_rating_tool`.

2. Copy the folder **`KstAnalysis.bundle`** into Fusion 360's add-in location:
   - **Windows:** `%APPDATA%\Autodesk\ApplicationPlugins\`
   - So the result is: `%APPDATA%\Autodesk\ApplicationPlugins\KstAnalysis.bundle\`

3. Restart Fusion 360. The add-in should appear under **Scripts and Add-Ins** > **Add-Ins**; run it from there.

## Wizard input JSON (v2)

When you click **Run Analysis** (or the command's OK button), the add-in writes a `wizard_input.json` file to `~/Documents/KstAnalysis/` with the following structure:

```json
{
  "version": 2,
  "point_contacts": [[x, y, z, nx, ny, nz]],
  "pins":           [[cx, cy, cz, ax, ay, az]],
  "lines":          [[mx, my, mz, lx, ly, lz, nx, ny, nz, length]],
  "planes":         [
    [px, py, pz, nx, ny, nz, 1, ux, uy, uz, width, vx, vy, vz, height],
    [px, py, pz, nx, ny, nz, 2, radius]
  ]
}
```

The external script `scripts/run_wizard_analysis.py` reads this JSON, builds a `ConstraintSet` with all four constraint types, and runs the analysis.

## Requirements

- Fusion 360 (Windows or Mac).
- The **kst_rating_tool** package (in `../src` when running from repo, or bundled inside the add-in).
- A system Python with `numpy` installed (for the external analysis script).

## Troubleshooting

- **Buttons don't appear:** Confirm the add-in is **Run** (green check) in Scripts and Add-Ins. Try closing and reopening the panel or restarting Fusion.
- **Wizard window doesn't open:** Fusion's Python may block UI. Ensure no modal dialogs are waiting; try running the command again.
- **"No module named 'tkinter'":** Fusion's embedded Python should include tkinter; if not, report the Fusion/Python version.
- **Analysis fails with "Missing external script":** The add-in infers the repo root from the add-in path. Ensure the repo structure is intact and `scripts/run_wizard_analysis.py` exists.
