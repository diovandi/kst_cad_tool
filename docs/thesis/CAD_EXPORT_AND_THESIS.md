# CAD export, unit vectors, and thesis narrative

This note summarizes how **Fusion 360** data becomes **wizard JSON** and then **MATLAB-style constraint arrays** in `kst_rating_tool`, so you can describe the **integration contribution** (automatic geometry from CAD vs manual numeric entry).

## Units

- Fusion’s internal length unit for BRep geometry is **centimetres**.
- The KST Analysis Wizard converts positions and lengths to **millimetres** before writing `wizard_input.json` (see `CM_TO_MM = 10.0` in `fusion360_addin/KstAnalysis/commands/analysis_command.py`).

## Point / Pin

- **Location**: a point on a face, vertex, or edge midpoint (`_get_point_from_entity`).
- **Orientation**:
  - Point: face **normal**, edge direction, or two-point vector depending on the orientation method.
  - Pin: **axis** from a straight edge, circular edge, or cylindrical face (`_try_get_axis_dir_from_entity`).

## Line

- **Location**: midpoint of a **straight** edge in mm.
- **Line direction**: unit vector along the edge.
- **Constraint normal**: from an adjacent face normal when possible (`_get_constraint_normal_for_edge`), else a perpendicular to the line.
- **Length**: edge length in mm (`line_length` in JSON).

## Plane

- **Location**: a point on the selected face (`pointOnFace` or centroid from vertices/box).
- **Orientation**: face **normal** (unit vector).
- **Size / type** (`plane_type`, `plane_prop`):
  - Type **1 (rectangular)**: in-plane basis from Fusion `uDirection`/`vDirection` when present, else from the normal; width/height from projected vertices (mm), stored as  
    `[ux,uy,uz, xlen, vx,vy,vz, ylen]` in `cpln_prop`.
  - Type **2 (circular)**: detected from cylindrical/conical/spherical face types, or forced in the UI; **radius** in mm in `cpln_prop`.

The core library interprets these the same way as the MATLAB reference (`PlaneConstraint` in `src/kst_rating_tool/constraints.py`, wrench sampling in `wrench.py`).

## JSON → `ConstraintSet`

- `scripts/run_wizard_analysis.py` reads v2 JSON (`point_contacts`, `pins`, `lines`, `planes`) and builds `ConstraintSet`, then runs `analyze_constraints_detailed`.

## Geometry size check

- Before analysis/optimization, line lengths and plane in-plane sizes are checked against a **minimum recommended size** (7 mm by default); see `src/kst_rating_tool/wizard_geometry.py` and the error path in `run_wizard_analysis.py` / `run_wizard_optimization.py`.
