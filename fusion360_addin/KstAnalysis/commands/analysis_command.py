"""
Fusion 360 command: KST Analysis Wizard.
Native (Fusion) command palette UI to:
- interactively pick (location, orientation) pairs from the model
- build a constraint list (CP table) inside the command
- write wizard_input.json
- run analysis via external Python (since Fusion's Python lacks numpy)
"""

import adsk.core
import adsk.fusion
import os
import json
import subprocess
import sys
import logging
import uuid

# Ensure add-in and (if not bundled) repo src are on path
_ADDIN_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ADDIN_DIR not in sys.path:
    sys.path.insert(0, _ADDIN_DIR)
if not os.path.exists(os.path.join(_ADDIN_DIR, "kst_rating_tool")):
    _REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(_ADDIN_DIR)))
    _src = os.path.join(_REPO_ROOT, "src")
    if _src not in sys.path:
        sys.path.insert(0, _src)


def _get_point_from_entity(entity):
    """Return (x,y,z) from a face, edge, or vertex.

    Fusion internal length units are centimeters; we convert them to millimeters
    so the JSON + external analysis use a consistent mm coordinate system.
    """
    CM_TO_MM = 10.0
    def _cm_to_mm(v):
        return float(v) * CM_TO_MM
    if hasattr(entity, "pointOnFace"):
        p = entity.pointOnFace
        return (_cm_to_mm(p.x), _cm_to_mm(p.y), _cm_to_mm(p.z))
    if hasattr(entity, "geometry"):
        geom = entity.geometry
        # BRepVertex.geometry → Point3D (has x/y/z but no origin or startPoint)
        if hasattr(geom, "x") and hasattr(geom, "y") and hasattr(geom, "z") and not hasattr(geom, "origin"):
            return (_cm_to_mm(geom.x), _cm_to_mm(geom.y), _cm_to_mm(geom.z))
        if hasattr(geom, "origin"):
            o = geom.origin
            return (_cm_to_mm(o.x), _cm_to_mm(o.y), _cm_to_mm(o.z))
        if hasattr(geom, "startPoint"):
            s, e = geom.startPoint, geom.endPoint
            return (
                _cm_to_mm((s.x + e.x) / 2),
                _cm_to_mm((s.y + e.y) / 2),
                _cm_to_mm((s.z + e.z) / 2),
            )
    if hasattr(entity, "boundingBox"):
        box = entity.boundingBox
        p = box.minPoint
        return (
            _cm_to_mm((p.x + box.maxPoint.x) / 2),
            _cm_to_mm((p.y + box.maxPoint.y) / 2),
            _cm_to_mm((p.z + box.maxPoint.z) / 2),
        )
    return (0.0, 0.0, 0.0)


def _normalize_vec3(vx, vy, vz):
    """Return a unit vector or None if too small."""
    L = (vx * vx + vy * vy + vz * vz) ** 0.5
    if L > 1e-10:
        return (vx / L, vy / L, vz / L)
    return None


def _try_get_axis_dir_from_entity(entity):
    """
    Return a unit vector along the geometric axis for:
    - straight line edges
    - circular edges (hole circumference) via their circle axis
    - cylindrical/conical faces via their cylinder/cone axis
    Returns None if it cannot infer an axis direction.
    """
    geom = getattr(entity, "geometry", None)
    if geom is None:
        return None

    # Many Fusion curve/surface geometry types expose an `axis`.
    if hasattr(geom, "axis"):
        a = geom.axis
        # axis may be a Line3D (direction property)...
        if hasattr(a, "direction"):
            d = a.direction
            v = _normalize_vec3(d.x, d.y, d.z)
            if v is not None:
                return v
        # ...or a Vector3D with x/y/z.
        if hasattr(a, "x") and hasattr(a, "y") and hasattr(a, "z"):
            v = _normalize_vec3(a.x, a.y, a.z)
            if v is not None:
                return v
        # ...or a line-like object with start/end points.
        if hasattr(a, "startPoint") and hasattr(a, "endPoint"):
            s, e = a.startPoint, a.endPoint
            v = _normalize_vec3(e.x - s.x, e.y - s.y, e.z - s.z)
            if v is not None:
                return v

    # Straight edge direction from start/end points.
    if hasattr(geom, "startPoint") and hasattr(geom, "endPoint"):
        s, e = geom.startPoint, geom.endPoint
        v = _normalize_vec3(e.x - s.x, e.y - s.y, e.z - s.z)
        if v is not None:
            return v

    if hasattr(geom, "direction"):
        d = geom.direction
        v = _normalize_vec3(d.x, d.y, d.z)
        if v is not None:
            return v

    return None


def _get_normal_or_axis_from_entity(entity):
    """
    Return a unit vector for a picked entity:
    - cylindrical/circular geometry -> axis direction (pin axis / hole centerline)
    - planar faces -> face normal
    - straight line edges -> edge direction
    """
    axis = _try_get_axis_dir_from_entity(entity)
    if axis is not None:
        return axis

    geom = getattr(entity, "geometry", None)
    if geom is not None and hasattr(geom, "normal"):
        n = geom.normal
        v = _normalize_vec3(n.x, n.y, n.z)
        if v is not None:
            return v

    if hasattr(entity, "pointOnFace") and hasattr(entity, "normal"):
        n = entity.normal
        if n:
            v = _normalize_vec3(n.x, n.y, n.z)
            if v is not None:
                return v

    return (0.0, 0.0, 1.0)


def _compute_orthonormal_basis_from_normal(nx, ny, nz):
    """Return two unit vectors (ux, uy, uz), (vx, vy, vz) orthogonal to (nx, ny, nz)."""
    # Pick an arbitrary vector not parallel to the normal
    if abs(nx) < 0.9:
        ax, ay, az = 1.0, 0.0, 0.0
    else:
        ax, ay, az = 0.0, 1.0, 0.0
    # u = normal x a
    ux = ny * az - nz * ay
    uy = nz * ax - nx * az
    uz = nx * ay - ny * ax
    L = (ux * ux + uy * uy + uz * uz) ** 0.5
    if L < 1e-10:
        # Fallback to a fixed direction
        ux, uy, uz = 1.0, 0.0, 0.0
        L = 1.0
    ux /= L
    uy /= L
    uz /= L
    # v = normal x u
    vx = ny * uz - nz * uy
    vy = nz * ux - nx * uz
    vz = nx * uy - ny * ux
    L2 = (vx * vx + vy * vy + vz * vz) ** 0.5
    if L2 < 1e-10:
        vx, vy, vz = 0.0, 1.0, 0.0
        L2 = 1.0
    vx /= L2
    vy /= L2
    vz /= L2
    return (ux, uy, uz), (vx, vy, vz)


def _get_plane_properties_from_face(face_ent, force_type=None):
    """Compute (plane_type, plane_prop_str) for a Fusion face.

    - Rectangular (type 1): plane_prop_str has 8 values
      ux, uy, uz, width, vx, vy, vz, height
    - Circular (type 2): plane_prop_str has 1 value: radius

    force_type:
        None  — auto-detect circular faces from Fusion geometry type name
        1     — always use rectangular in-plane bounds (even on cylindrical faces)
        2     — always use circular approximation from sampled points

    Falls back to a small default rectangle if geometry details are unavailable.
    """
    try:
        CM_TO_MM = 10.0
        geom = getattr(face_ent, "geometry", None)
        # Normal as unit vector
        nx, ny, nz = _get_normal_or_axis_from_entity(face_ent)

        # Detect circular faces (cylinders / cones, etc.) via geometry type name if available
        geom_type = type(geom).__name__ if geom is not None else ""
        if force_type == 1:
            is_circular = False
        elif force_type == 2:
            is_circular = True
        else:
            is_circular = geom_type.lower().startswith(("cylinder", "cone", "sphere"))

        # Gather sample points on the face from its vertices (or use bounding box as fallback)
        pts = []
        try:
            edges = list(getattr(face_ent, "edges", []))
            for e in edges:
                g = getattr(e, "geometry", None)
                # Prefer explicit vertices if available
                if hasattr(g, "startPoint") and hasattr(g, "endPoint"):
                    s, ed = g.startPoint, g.endPoint
                    pts.append((s.x, s.y, s.z))
                    pts.append((ed.x, ed.y, ed.z))
        except Exception:
            pts = []

        if not pts and hasattr(face_ent, "boundingBox"):
            box = face_ent.boundingBox
            pmin = box.minPoint
            pmax = box.maxPoint
            pts = [
                (pmin.x, pmin.y, pmin.z),
                (pmax.x, pmax.y, pmax.z),
            ]

        # Face center
        if hasattr(face_ent, "pointOnFace"):
            c = face_ent.pointOnFace
            cx, cy, cz = c.x, c.y, c.z
        else:
            if pts:
                sx = sum(p[0] for p in pts) / len(pts)
                sy = sum(p[1] for p in pts) / len(pts)
                sz = sum(p[2] for p in pts) / len(pts)
            else:
                sx = sy = sz = 0.0
            cx, cy, cz = sx, sy, sz

        if not pts:
            # No geometry detail; return small default rectangle
            (ux, uy, uz), (vx, vy, vz) = _compute_orthonormal_basis_from_normal(nx, ny, nz)
            width = height = 1.0
            prop_str = f"{ux}, {uy}, {uz}, {width * CM_TO_MM}, {vx}, {vy}, {vz}, {height * CM_TO_MM}"
            return 1, prop_str

        # Build in-plane basis: use uDirection/vDirection when available, else algebraic basis.
        # Fusion's uDirection/vDirection are NOT guaranteed unit; normalize them.
        if geom is not None and hasattr(geom, "uDirection") and hasattr(geom, "vDirection"):
            udir = geom.uDirection
            vdir = geom.vDirection
            uL = (udir.x**2 + udir.y**2 + udir.z**2) ** 0.5
            vL = (vdir.x**2 + vdir.y**2 + vdir.z**2) ** 0.5
            if uL > 1e-10 and vL > 1e-10:
                (ux, uy, uz) = (udir.x / uL, udir.y / uL, udir.z / uL)
                (vx, vy, vz) = (vdir.x / vL, vdir.y / vL, vdir.z / vL)
            else:
                (ux, uy, uz), (vx, vy, vz) = _compute_orthonormal_basis_from_normal(nx, ny, nz)
        else:
            (ux, uy, uz), (vx, vy, vz) = _compute_orthonormal_basis_from_normal(nx, ny, nz)

        # Project points into the in-plane basis
        def _dot(ax, ay, az, bx, by, bz):
            return ax * bx + ay * by + az * bz

        u_vals = []
        v_vals = []
        for (px, py, pz) in pts:
            rx, ry, rz = px - cx, py - cy, pz - cz
            u_vals.append(_dot(rx, ry, rz, ux, uy, uz))
            v_vals.append(_dot(rx, ry, rz, vx, vy, vz))

        if not u_vals or not v_vals:
            width = height = 1.0
        else:
            width = max(u_vals) - min(u_vals)
            height = max(v_vals) - min(v_vals)
            # Guard against degenerate ranges
            if abs(width) < 1e-6:
                width = 1.0
            if abs(height) < 1e-6:
                height = 1.0

        if is_circular:
            # Approximate radius from average distance to center projected in plane
            radii = []
            for (px, py, pz) in pts:
                rx, ry, rz = px - cx, py - cy, pz - cz
                # remove normal component
                n_dot = _dot(rx, ry, rz, nx, ny, nz)
                tx, ty, tz = rx - n_dot * nx, ry - n_dot * ny, rz - n_dot * nz
                r = (tx * tx + ty * ty + tz * tz) ** 0.5
                radii.append(r)
            radius = sum(radii) / len(radii) if radii else min(width, height) / 2.0
            if radius <= 0:
                radius = 1.0
            return 2, f"{radius * CM_TO_MM}"

        # Rectangular plane
        prop_str = f"{ux}, {uy}, {uz}, {width * CM_TO_MM}, {vx}, {vy}, {vz}, {height * CM_TO_MM}"
        return 1, prop_str
    except Exception:
        # Fallback: small default rectangle aligned with computed normal
        nx, ny, nz = _get_normal_or_axis_from_entity(face_ent)
        (ux, uy, uz), (vx, vy, vz) = _compute_orthonormal_basis_from_normal(nx, ny, nz)
        width = height = 1.0
        prop_str = f"{ux}, {uy}, {uz}, {width * CM_TO_MM}, {vx}, {vy}, {vz}, {height * CM_TO_MM}"
        return 1, prop_str


def _get_constraint_normal_for_edge(edge_ent, line_dir):
    """Return a unit vector perpendicular to line_dir for a Line constraint.

    Tries to use the normal of an adjacent face first (the physically
    meaningful contact direction).  Falls back to an algebraic perpendicular.
    """
    try:
        faces = getattr(edge_ent, "faces", None)
        if faces and faces.count > 0:
            face = faces.item(0)
            fn = _get_normal_or_axis_from_entity(face)
            # Ensure the face normal is actually perpendicular to line_dir.
            # Remove the component parallel to line_dir and renormalize.
            dot = fn[0] * line_dir[0] + fn[1] * line_dir[1] + fn[2] * line_dir[2]
            px = fn[0] - dot * line_dir[0]
            py = fn[1] - dot * line_dir[1]
            pz = fn[2] - dot * line_dir[2]
            pL = (px * px + py * py + pz * pz) ** 0.5
            if pL > 1e-10:
                return (px / pL, py / pL, pz / pL)
    except Exception:
        pass
    # Algebraic fallback: pick any vector perpendicular to line_dir
    (u, _v) = _compute_orthonormal_basis_from_normal(*line_dir)
    return u


def _pick_two_vertices_for_line(app):
    """Prompt user to select two vertices in Fusion; return (origin_str, direction_str) or (None, None)."""
    ui = app.userInterface
    try:
        sel1 = ui.selectEntity("Select first vertex (line start)", "Vertices")
        if not sel1:
            return (None, None)
        sel2 = ui.selectEntity("Select second vertex (line end)", "Vertices")
        if not sel2:
            return (None, None)
        p1 = _get_point_from_entity(sel1.entity)
        p2 = _get_point_from_entity(sel2.entity)
        dx = p2[0] - p1[0]
        dy = p2[1] - p1[1]
        dz = p2[2] - p1[2]
        L = (dx*dx + dy*dy + dz*dz) ** 0.5
        if L < 1e-10:
            return (None, None)
        nx, ny, nz = dx / L, dy / L, dz / L
        origin_str = "{}, {}, {}".format(p1[0], p1[1], p1[2])
        direction_str = "{}, {}, {}".format(nx, ny, nz)
        return (origin_str, direction_str)
    except Exception:
        return (None, None)


class AnalysisCommand:
    _handlers = []

    @classmethod
    def register(cls, cmd_id, panel):
        app = adsk.core.Application.get()
        ui = app.userInterface
        cmd_defs = ui.commandDefinitions
        cmd_def = cmd_defs.addButtonDefinition(
            cmd_id,
            "KST Analysis Wizard",
            "Open KST Constraint Analysis Wizard",
            ""
        )

        # Fusion API (recent versions) requires an EventHandler object, not a bare function.
        class _CommandCreatedHandler(adsk.core.CommandCreatedEventHandler):
            def __init__(self):
                super().__init__()

            def notify(self, args):
                cls._on_command_created(args)

        created_handler = _CommandCreatedHandler()
        cmd_def.commandCreated.add(created_handler)
        cls._handlers.append(created_handler)

        if panel:
            panel.controls.addCommand(cmd_def)

    @classmethod
    def _on_command_created(cls, args):
        app = adsk.core.Application.get()
        ui = app.userInterface
        cmd = args.command
        cmd_inputs = cmd.commandInputs

        # ---- Output dir (Documents/KstAnalysis) ----
        if sys.platform == "win32":
            docs = os.path.join(os.environ.get("USERPROFILE", ""), "Documents")
        else:
            docs = os.path.expanduser("~/Documents")
        output_dir = os.path.join(docs, "KstAnalysis")

        # Best-effort script resolution for external analysis execution.
        # Fusion add-ins are sometimes bundled, so the relative repo layout can differ.
        repo_root_guess = os.path.abspath(os.path.join(_ADDIN_DIR, os.pardir, os.pardir))
        wizard_script_candidates = [
            os.path.join(repo_root_guess, "scripts", "run_wizard_analysis.py"),
            os.path.join(os.path.abspath(os.path.join(_ADDIN_DIR, os.pardir)), "scripts", "run_wizard_analysis.py"),
            os.path.join(
                os.path.abspath(os.path.join(_ADDIN_DIR, os.pardir, os.pardir, os.pardir)),
                "scripts",
                "run_wizard_analysis.py",
            ),
        ]
        wizard_script = next(
            (p for p in wizard_script_candidates if os.path.isfile(p)),
            wizard_script_candidates[0],
        )

        # ---- In-command state ----
        state = {
            "constraints": [],  # list[dict]: {cp_name,type,location,orientation}
            "output_dir": output_dir,
            "wizard_script": wizard_script,
            "wizard_script_candidates": wizard_script_candidates,
        }

        # ---- Logging ----
        log_path = os.path.join(output_dir, "fusion_wizard.log")
        logger = logging.getLogger("kst_fusion_wizard")
        run_id = uuid.uuid4().hex
        state["run_id"] = run_id
        if not logger.handlers:
            logger.setLevel(logging.DEBUG)
            try:
                fh = logging.FileHandler(log_path, encoding="utf-8")
                fmt = logging.Formatter(
                    "%(asctime)s [%(levelname)s] %(message)s", datefmt="%Y-%m-%d %H:%M:%S"
                )
                fh.setFormatter(fmt)
                logger.addHandler(fh)
            except Exception:
                # If logging setup fails, continue silently; Fusion UI is primary feedback channel.
                pass

        def _step(step_name, event, **fields):
            """Write a single trace line for a step in this run."""
            try:
                # Avoid huge blobs; callers may still pass full_values on purpose.
                field_parts = []
                for k, v in fields.items():
                    if v is None:
                        continue
                    field_parts.append(f"{k}={v}")
                extra = " ".join(field_parts)
                if extra:
                    logger.debug("run=%s step=%s event=%s %s", run_id, step_name, event, extra)
                else:
                    logger.debug("run=%s step=%s event=%s", run_id, step_name, event)
            except Exception:
                pass

        # ---- UI: Pickers ----
        cmd_inputs.addTextBoxCommandInput(
            "kst_help",
            "How to use",
            "For each CP: (1) set CP Name + Type, (2) pick a <b>location</b>, (3) pick an <b>orientation</b>, (4) click <b>Add Constraint</b> to save. Repeat for more CPs, then click <b>OK</b> to run analysis.",
            4,
            True,
        )

        name_in = cmd_inputs.addStringValueInput("kst_cp_name", "CP Name", "C_point1")

        type_in = cmd_inputs.addDropDownCommandInput("kst_cp_type", "Type", adsk.core.DropDownStyles.TextListDropDownStyle)
        for t in ("Point", "Pin", "Line", "Plane"):
            type_in.listItems.add(t, t == "Point")

        orient_method = cmd_inputs.addDropDownCommandInput(
            "kst_orient_method",
            "Orientation method",
            adsk.core.DropDownStyles.TextListDropDownStyle,
        )
        for name in ("Normal to Plane", "Two Points", "Along Line/Axis"):
            orient_method.listItems.add(name, name == "Normal to Plane")

        loc_sel = cmd_inputs.addSelectionInput(
            "kst_loc",
            "Location pick",
            "Pick a vertex / edge / face to define the CP location."
        )
        orient_sel = cmd_inputs.addSelectionInput(
            "kst_orient",
            "Orientation pick",
            "Pick a face (normal) or edge (direction) to define orientation."
        )
        try:
            # Start with broad filters; we will narrow them dynamically based on type.
            loc_sel.addSelectionFilter("Vertices")
            loc_sel.addSelectionFilter("Edges")
            loc_sel.addSelectionFilter("Faces")
            orient_sel.addSelectionFilter("Faces")
            orient_sel.addSelectionFilter("Edges")
        except Exception:
            pass
        loc_sel.setSelectionLimits(0, 1)
        orient_sel.setSelectionLimits(0, 1)

        # Use BoolValue inputs as "action buttons" (Fusion renders them reliably without icon resources).
        add_action = cmd_inputs.addBoolValueInput("kst_add", "Add Constraint", False, "", False)
        update_action = cmd_inputs.addBoolValueInput("kst_update", "Update Selected", False, "", False)
        remove_last_action = cmd_inputs.addBoolValueInput("kst_remove_last", "Remove Last", False, "", False)
        clear_all_action = cmd_inputs.addBoolValueInput("kst_clear_all", "Clear All", False, "", False)
        save_cfg_action = cmd_inputs.addBoolValueInput("kst_save_cfg", "Save Config", False, "", False)
        load_cfg_action = cmd_inputs.addBoolValueInput("kst_load_cfg", "Load Config", False, "", False)
        invert_dir = cmd_inputs.addBoolValueInput("kst_invert_dir", "Invert Direction", True, "", False)
        edit_index_in = cmd_inputs.addStringValueInput("kst_edit_index", "Edit Index", "1")

        plane_shape_in = cmd_inputs.addDropDownCommandInput(
            "kst_plane_shape",
            "Plane size mode",
            adsk.core.DropDownStyles.TextListDropDownStyle,
        )
        for name in ("Auto (from face)", "Rectangular", "Circular"):
            plane_shape_in.listItems.add(name, name == "Auto (from face)")
        plane_shape_in.isVisible = False

        plane_prop_manual = cmd_inputs.addStringValueInput(
            "kst_plane_prop_manual",
            "Plane prop override (optional, mm)",
            "Leave empty to use face + mode above. Rectangular: 8 numbers "
            "(ux,uy,uz, xlen, vx,vy,vz, ylen). Circular: 1 number (radius).",
        )
        plane_prop_manual.isVisible = False

        pick_feedback = cmd_inputs.addTextBoxCommandInput(
            "kst_pick_feedback",
            "Selection info",
            "(pick a location)",
            2,
            True,
        )

        constraints_box = cmd_inputs.addTextBoxCommandInput(
            "kst_constraints",
            "Constraints",
            "(none yet)",
            10,
            True,
        )

        # Run analysis without closing the dialog (OK will close the command).
        run_analysis_action = cmd_inputs.addBoolValueInput("kst_run_analysis", "Run Analysis", False, "", False)

        cmd_inputs.addTextBoxCommandInput(
            "kst_results",
            "Results",
            "(run analysis to see WTR/MRR/MTR/TOR)",
            4,
            True,
        )

        # ---- Helpers ----
        def _plane_force_type_from_ui():
            sel = plane_shape_in.selectedItem.name if plane_shape_in.selectedItem else "Auto (from face)"
            if sel.startswith("Rectangular"):
                return 1
            if sel.startswith("Circular"):
                return 2
            return None

        def _format_plane_detail_line(r):
            if (r.get("type") or "").strip() != "Plane":
                return ""
            try:
                pt = int(str(r.get("plane_type", "1")).strip())
            except Exception:
                pt = 1
            prop = (r.get("plane_prop") or "").strip()
            if pt == 1:
                parts = [float(x) for x in prop.replace(",", " ").split() if str(x).strip()]
                if len(parts) >= 8:
                    w, h = parts[3], parts[7]
                    return f"\n   rectangular: width={w:.4g} mm  height={h:.4g} mm  (cpln_prop)"
                return f"\n   rectangular: prop={prop}"
            if pt == 2:
                parts = [float(x) for x in prop.replace(",", " ").split() if str(x).strip()]
                if len(parts) >= 1:
                    rad = parts[0]
                    return f"\n   circular: radius={rad:.4g} mm  diameter={2.0 * rad:.4g} mm"
            return f"\n   plane_type={pt}  prop={prop}"

        def _parse_plane_manual_override(text):
            """Return (plane_type_int, plane_prop_str) or (None, None) if empty/invalid."""
            raw = (text or "").strip()
            if not raw:
                return None, None
            try:
                vals = [float(x.strip()) for x in raw.replace(",", " ").split() if str(x).strip()]
            except Exception:
                return None, None
            if len(vals) == 8:
                return 1, raw
            if len(vals) == 1:
                return 2, raw
            return None, None

        def _format_constraints_text(rows):
            if not rows:
                return "(none yet)"
            lines = []
            for i, r in enumerate(rows, start=1):
                line = (
                    f"{i}. {r.get('cp_name','CP')}  {r.get('type','Point')}  "
                    f"loc=({r.get('location','')}) mm  orient=({r.get('orientation','')})"
                )
                line += _format_plane_detail_line(r)
                lines.append(line)
            return "\n".join(lines)

        def _update_constraints_box():
            constraints_box.text = _format_constraints_text(state["constraints"])

        def _config_path():
            return os.path.join(state["output_dir"], "constraint_config.json")

        def _save_constraints_config():
            _ensure_output_dir()
            path = _config_path()
            with open(path, "w", encoding="utf-8") as f:
                json.dump({"version": 1, "constraints": state["constraints"]}, f, indent=2)
            return path

        def _load_constraints_config():
            path = _config_path()
            with open(path, "r", encoding="utf-8") as f:
                payload = json.load(f)
            rows = payload.get("constraints", [])
            if not isinstance(rows, list):
                raise RuntimeError("Invalid constraint config format.")
            state["constraints"] = rows
            _update_constraints_box()
            try:
                import visualizer
                visualizer.draw_constraint_markers(app, state["constraints"])
                visualizer.clear_kst_weakest_constraint_arrows(app)
            except Exception:
                pass
            return path

        def _is_auto_name(value):
            v = (value or "").strip()
            return (
                v.startswith("CP")
                or v.startswith("C_point")
                or v.startswith("C_pin")
                or v.startswith("C_line")
                or v.startswith("C_plane")
            )

        def _next_cp_name(ctype):
            ctype = (ctype or "Point").strip()
            prefix_map = {
                "Point": "C_point",
                "Pin": "C_pin",
                "Line": "C_line",
                "Plane": "C_plane",
            }
            prefix = prefix_map.get(ctype, "C_point")
            type_count = sum(1 for r in state["constraints"] if (r.get("type") or "").strip() == ctype)
            return f"{prefix}{type_count + 1}"

        def _fmt_vec3(vec):
            try:
                return "{}, {}, {}".format(vec[0], vec[1], vec[2])
            except Exception:
                return "0, 0, 0"

        def _parse_vec3(text):
            try:
                vals = [float(x.strip()) for x in str(text).replace(",", " ").split()[:3]]
                if len(vals) != 3:
                    return [0.0, 0.0, 1.0]
                return vals
            except Exception:
                return [0.0, 0.0, 1.0]

        def _vec3_to_str(v):
            return "{}, {}, {}".format(float(v[0]), float(v[1]), float(v[2]))

        def _apply_invert_to_row(row):
            if not row or not getattr(invert_dir, "value", False):
                return row
            out = dict(row)
            ori = _parse_vec3(out.get("orientation", "0, 0, 1"))
            out["orientation"] = _vec3_to_str([-ori[0], -ori[1], -ori[2]])
            if (out.get("type") or "").strip() == "Line":
                cdir = _parse_vec3(out.get("constraint_dir", "0, 0, 1"))
                out["constraint_dir"] = _vec3_to_str([-cdir[0], -cdir[1], -cdir[2]])
            return out

        def _update_pick_feedback():
            try:
                loc_txt = "(none)"
                ori_txt = "(none)"
                loc_missing = True
                ori_missing = True
                if loc_sel and loc_sel.selectionCount > 0:
                    loc_ent = loc_sel.selection(0).entity
                    loc_txt = _fmt_vec3(_get_point_from_entity(loc_ent))
                    loc_missing = False
                if orient_sel and orient_sel.selectionCount > 0:
                    orient_ent = orient_sel.selection(0).entity
                    ori_txt = _fmt_vec3(_get_normal_or_axis_from_entity(orient_ent))
                    ori_missing = False
                pick_feedback.text = f"loc=({loc_txt}) mm\norient=({ori_txt})"
                if loc_missing and ori_missing:
                    _step("update_pick_feedback", "SKIP", reason="No location/orientation selected")
            except Exception:
                try:
                    pick_feedback.text = "(selection info unavailable)"
                except Exception:
                    pass

        def _configure_selection_filters_for_type():
            """Adjust selection filters and visibility based on current constraint type."""
            ctype = type_in.selectedItem.name if type_in.selectedItem else "Point"
            point_method = orient_method.selectedItem.name if orient_method.selectedItem else "Normal to Plane"
            _step("configure_selection_filters", "START", ctype=ctype, point_method=point_method)
            try:
                if hasattr(loc_sel, "clearSelectionFilters"):
                    loc_sel.clearSelectionFilters()
                if hasattr(orient_sel, "clearSelectionFilters"):
                    orient_sel.clearSelectionFilters()
            except Exception:
                pass

            # Defaults
            orient_sel.isVisible = True
            orient_method.isVisible = True
            try:
                plane_shape_in.isVisible = False
                plane_prop_manual.isVisible = False
            except Exception:
                pass

            try:
                if ctype == "Point":
                    # Location: vertices only for precise CPs
                    loc_sel.addSelectionFilter("Vertices")
                    # Orientation depends on method: Normal-to-plane wants a face normal;
                    # Along-line wants an edge direction.
                    if point_method == "Normal to Plane":
                        orient_sel.isVisible = True
                        orient_sel.addSelectionFilter("Faces")
                    elif point_method == "Along Line/Axis":
                        orient_sel.isVisible = True
                        orient_sel.addSelectionFilter("Edges")
                        # Allow cylindrical faces too (hole wall -> cylinder axis)
                        orient_sel.addSelectionFilter("Faces")
                    elif point_method == "Two Points":
                        # Two-point orientation uses a separate modal picker; hide this selection box.
                        orient_sel.isVisible = False
                    else:
                        # Fallback: allow both.
                        orient_sel.isVisible = True
                        orient_sel.addSelectionFilter("Faces")
                        orient_sel.addSelectionFilter("Edges")
                elif ctype == "Pin":
                    orient_method.isVisible = False
                    # Location: vertex for pin center
                    loc_sel.addSelectionFilter("Vertices")
                    # Orientation: edge (line/circle) or cylindrical face as pin axis
                    orient_sel.addSelectionFilter("Edges")
                    orient_sel.addSelectionFilter("Faces")
                elif ctype == "Line":
                    orient_method.isVisible = False
                    orient_sel.isVisible = False
                    # Location: edge that defines the line contact
                    loc_sel.addSelectionFilter("Edges")
                elif ctype == "Plane":
                    orient_method.isVisible = False
                    orient_sel.isVisible = False
                    # Location: face that defines the plane contact
                    loc_sel.addSelectionFilter("Faces")
                    try:
                        plane_shape_in.isVisible = True
                        plane_prop_manual.isVisible = True
                    except Exception:
                        pass
            except Exception:
                # If filter configuration fails, keep whatever defaults Fusion provides.
                _step("configure_selection_filters", "FAIL", ctype=ctype, point_method=point_method)
                pass
            _step("configure_selection_filters", "SUCCESS", ctype=ctype, point_method=point_method)

        def _ensure_output_dir():
            try:
                os.makedirs(state["output_dir"], exist_ok=True)
            except Exception:
                pass

        def _write_input_json():
            _ensure_output_dir()
            _step("serialize_input_json", "START", constraints_count=len(state["constraints"]))
            logger.debug("Writing wizard_input.json to %s", state["output_dir"])
            point_contacts = []
            pins = []
            lines = []
            planes = []
            for r in state["constraints"]:
                try:
                    ctype = (r.get("type") or "Point").strip()
                    loc = [float(x.strip()) for x in (r.get("location") or "").replace(",", " ").split()[:3]]
                    ori = [float(x.strip()) for x in (r.get("orientation") or "").replace(",", " ").split()[:3]]
                    if len(loc) != 3 or len(ori) != 3:
                        continue
                    if ctype == "Point":
                        point_contacts.append(loc + ori)
                    elif ctype == "Pin":
                        pins.append(loc + ori)
                    elif ctype == "Line":
                        # Expect optional constraint_dir and line_length.
                        try:
                            cdir_vals = [
                                float(x.strip())
                                for x in (r.get("constraint_dir") or r.get("orientation") or "").replace(",", " ").split()[:3]
                            ]
                            if len(cdir_vals) != 3:
                                cdir_vals = ori
                        except Exception:
                            cdir_vals = ori
                        try:
                            length = float(str(r.get("line_length", "0")).strip())
                        except Exception:
                            length = 0.0
                        lines.append(loc + ori + cdir_vals + [length])
                    elif ctype == "Plane":
                        try:
                            ptype = int(str(r.get("plane_type", "1")).strip())
                        except Exception:
                            ptype = 1
                        try:
                            prop_vals = [
                                float(x.strip())
                                for x in (r.get("plane_prop") or "").replace(",", " ").split()
                                if x.strip()
                            ]
                        except Exception:
                            prop_vals = []
                        planes.append(loc + ori + [ptype] + prop_vals)
                        logger.debug(
                            "Plane row: loc=%s ori=%s type=%s prop=%s",
                            r.get("location"),
                            r.get("orientation"),
                            ptype,
                            prop_vals,
                        )
                except Exception as exc:
                    logger.exception("Failed to serialize constraint row %s: %s", r, exc)
                    continue
            data = {
                "version": 2,
                "point_contacts": point_contacts,
                "pins": pins,
                "lines": lines,
                "planes": planes,
            }
            in_path = os.path.join(state["output_dir"], "wizard_input.json")
            try:
                with open(in_path, "w") as f:
                    json.dump(data, f, indent=2)
                logger.info("Wrote wizard_input.json with %d constraints", len(state["constraints"]))
                _step(
                    "serialize_input_json",
                    "SUCCESS",
                    wizard_input=in_path,
                    point_contacts=len(point_contacts),
                    pins=len(pins),
                    lines=len(lines),
                    planes=len(planes),
                )
            except Exception as exc:
                logger.exception("Failed to write wizard_input.json: %s", exc)
                _step("serialize_input_json", "FAIL", error=str(exc))
                raise
            return in_path

        def _run_external_analysis(in_path):
            _step("external_analysis", "START", in_path=in_path, wizard_script=state["wizard_script"])
            if not os.path.isfile(state["wizard_script"]):
                tried = "\n".join(state.get("wizard_script_candidates") or [state["wizard_script"]])
                msg = f"Missing external script: {state['wizard_script']}\nTried:\n{tried}"
                logger.error(msg)
                _step("external_analysis", "FAIL", error=msg)
                raise RuntimeError(msg)

            out_path = os.path.join(state["output_dir"], "results_wizard.txt")

            # Try multiple Python executables.
            # Note: when running inside Fusion, `sys.executable` can be `Fusion360.exe`
            # (not an actual python interpreter). So we only use it if it looks python-ish.
            timeout_s = 120

            def _looks_like_python(exec_path):
                name = os.path.basename(str(exec_path)).lower()
                return (
                    name.startswith("python")
                    or name.endswith("python.exe")
                    or "python" in name
                    or name == "py.exe"
                )

            python_candidates = []
            # On Windows, `py` is often the most reliable launcher.
            python_candidates.append("py")
            python_candidates.extend(["python3", "python"])
            if _looks_like_python(sys.executable):
                python_candidates.append(sys.executable)

            last_error = None
            for py_exec in python_candidates:
                cmdline = [py_exec, state["wizard_script"], in_path, out_path]
                logger.info("Running external analysis: %s", " ".join(cmdline))
                _step("external_analysis_python_attempt", "START", python=py_exec)
                try:
                    proc = subprocess.run(
                        cmdline,
                        capture_output=True,
                        text=True,
                        timeout=timeout_s,
                    )
                except FileNotFoundError:
                    _step("external_analysis_python_attempt", "SKIP", python=py_exec, reason="FileNotFoundError")
                    continue
                except subprocess.TimeoutExpired as e:
                    msg = f"External analysis timed out after {timeout_s}s."
                    logger.error("%s Cmd=%s", msg, cmdline)
                    _step("external_analysis_python_attempt", "FAIL", python=py_exec, error=msg)
                    raise RuntimeError(msg) from e

                if proc.returncode == 0:
                    # Even if the process returns 0, verify the expected output was produced.
                    out_exists = os.path.isfile(out_path)
                    out_size = os.path.getsize(out_path) if out_exists else 0
                    try:
                        if out_exists and out_size > 0:
                            logger.info(
                                "External analysis completed successfully, wrote %s (python=%s)",
                                out_path,
                                py_exec,
                            )
                            _step(
                                "external_analysis_python_attempt",
                                "SUCCESS",
                                python=py_exec,
                                out_path=out_path,
                                out_size=os.path.getsize(out_path),
                            )
                            return out_path
                    except Exception:
                        pass

                    last_error = (
                        f"Subprocess returned 0 but output was missing/empty: {out_path} "
                        f"(python={py_exec})"
                    )
                    logger.error(last_error)
                    _step(
                        "external_analysis_python_attempt",
                        "FAIL",
                        python=py_exec,
                        out_path=out_path,
                        out_exists=out_exists,
                        out_size=out_size,
                        error=last_error,
                    )
                    continue

                stderr = (proc.stderr or "").strip()
                stdout = (proc.stdout or "").strip()
                stderr_len = len(stderr)
                stdout_len = len(stdout)
                stderr_preview = stderr[:500]
                stdout_preview = stdout[:500]
                msg = stderr or stdout or f"exit code {proc.returncode}"
                logger.error(
                    "External analysis failed (code %s) with %s: %s",
                    proc.returncode,
                    py_exec,
                    msg,
                )
                _step(
                    "external_analysis_python_attempt",
                    "FAIL",
                    python=py_exec,
                    returncode=proc.returncode,
                    error=msg[:2000],
                    stderr_len=stderr_len,
                    stdout_len=stdout_len,
                    stderr_preview=stderr_preview,
                    stdout_preview=stdout_preview,
                )

                # If the chosen interpreter doesn't have numpy, try the next one.
                if "No module named" in msg and "numpy" in msg:
                    last_error = msg
                    continue

                # Other failures likely won't be fixed by swapping interpreters.
                last_error = msg
                break

            raise RuntimeError(last_error or "External analysis failed unexpectedly.")

        def _update_results_box_from_file(path):
            _step("update_results_box", "START", path=path)
            try:
                if not os.path.isfile(path):
                    _step("update_results_box", "FAIL", path=path, error="file missing")
                    cmd_inputs.itemById("kst_results").text = f"(missing results file: {path})"
                    return
                out_size = os.path.getsize(path)
                _step("update_results_box", "START", path=path, out_size=out_size)
                with open(path) as f:
                    lines = f.read().strip().splitlines()
                if len(lines) >= 2:
                    parts = lines[1].split("\t")
                    if len(parts) >= 4:
                        maybe_error_line = lines[2] if len(lines) >= 3 else ""
                        cmd_inputs.itemById("kst_results").text = (
                            f"WTR={parts[0]}\nMRR={parts[1]}\nMTR={parts[2]}\nTOR={parts[3]}\n\n{path}"
                        )
                        if maybe_error_line.startswith("ERROR"):
                            cmd_inputs.itemById("kst_results").text = (
                                cmd_inputs.itemById("kst_results").text + f"\n\n{maybe_error_line}"
                            )
                        _step("update_results_box", "SUCCESS", path=path)
                        return
                _step("update_results_box", "SKIP", reason="Could not parse results", path=path)
                cmd_inputs.itemById("kst_results").text = f"(wrote {path}, but could not parse results)"
            except Exception as e:
                _step("update_results_box", "FAIL", error=str(e), path=path)
                cmd_inputs.itemById("kst_results").text = f"Failed to read results: {e}"

        # ---- Event handlers ----
        # Configure filters once based on the default type.
        _configure_selection_filters_for_type()
        class _InputChangedHandler(adsk.core.InputChangedEventHandler):
            def __init__(self):
                super().__init__()

            def notify(self, event_args):
                try:
                    changed = event_args.input
                    if not changed:
                        return

                    if changed.id in ("kst_loc", "kst_orient"):
                        _update_pick_feedback()
                        return

                    # React to type/method changes for dynamic UI behavior.
                    if changed.id in ("kst_cp_type", "kst_orient_method"):
                        # Type changes may also update the CP name (auto-naming only).
                        if changed.id == "kst_cp_type":
                            _configure_selection_filters_for_type()
                            if _is_auto_name(name_in.value):
                                new_type = type_in.selectedItem.name if type_in.selectedItem else "Point"
                                name_in.value = _next_cp_name(new_type)
                            _update_pick_feedback()
                            return

                        _configure_selection_filters_for_type()
                        _update_pick_feedback()
                        return

                    if changed.id == "kst_add" and getattr(add_action, "value", False):
                        add_action.value = False
                        ctype = type_in.selectedItem.name if type_in.selectedItem else "Point"
                        cp_name = (name_in.value or "").strip() or _next_cp_name(ctype)
                        _step(
                            "ui_add_constraint",
                            "START",
                            ctype=ctype,
                            cp_name=cp_name,
                            orient_method=orient_method.selectedItem.name if orient_method.selectedItem else None,
                        )

                        # Per-type handling
                        if ctype == "Point":
                            method = orient_method.selectedItem.name if orient_method.selectedItem else "Normal to Plane"
                            if method == "Two Points":
                                origin_str, direction_str = _pick_two_vertices_for_line(app)
                                if not origin_str or not direction_str:
                                    _step("ui_add_constraint", "SKIP", ctype=ctype, cp_name=cp_name, reason="Two-point orientation cancelled")
                                    ui.messageBox("Two-point orientation cancelled or invalid.")
                                    return
                                loc_str = origin_str
                                orient_str = direction_str
                            else:
                                try:
                                    loc_ent = loc_sel.selection(0).entity
                                    orient_ent = orient_sel.selection(0).entity
                                except Exception:
                                    _step("ui_add_constraint", "SKIP", ctype=ctype, cp_name=cp_name, reason="Missing location or orientation selection")
                                    ui.messageBox("Pick both Location and Orientation before adding.")
                                    return
                                loc_geom = getattr(loc_ent, "geometry", None)
                                # If Fusion gives you an edge for "Vertex", warn explicitly.
                                if loc_geom is not None and hasattr(loc_geom, "startPoint") and hasattr(loc_geom, "endPoint"):
                                    _step("ui_add_constraint", "FAIL", ctype=ctype, cp_name=cp_name, reason="Point location picked an edge geometry")
                                    ui.messageBox("For a Point constraint location, pick a vertex (point), not an edge.")
                                    return
                                orient_geom = getattr(orient_ent, "geometry", None)
                                if method == "Normal to Plane":
                                    if orient_geom is None or not hasattr(orient_geom, "normal"):
                                        _step("ui_add_constraint", "FAIL", ctype=ctype, cp_name=cp_name, reason="Normal-to-plane missing face normal")
                                        ui.messageBox("Normal to Plane requires selecting a face (for the face normal).")
                                        return
                                elif method == "Along Line/Axis":
                                    axis_dir = _try_get_axis_dir_from_entity(orient_ent)
                                    if axis_dir is None:
                                        _step("ui_add_constraint", "FAIL", ctype=ctype, cp_name=cp_name, reason="Along-line missing axis geometry")
                                        ui.messageBox("Along Line/Axis requires selecting an edge/face that has an axis (straight edge, circular edge, or cylindrical face).")
                                        return
                                pt = _get_point_from_entity(loc_ent)
                                if method == "Along Line/Axis":
                                    # Reuse the validated axis direction from above (avoid a second
                                    # unsecured call that could return None).
                                    normal = axis_dir
                                    if normal is None:
                                        _step(
                                            "ui_add_constraint",
                                            "FAIL",
                                            ctype=ctype,
                                            cp_name=cp_name,
                                            reason="Along-line missing axis geometry (recheck)",
                                        )
                                        ui.messageBox(
                                            "Along Line/Axis requires selecting an edge/face that has an axis (straight edge, circular edge, or cylindrical face)."
                                        )
                                        return
                                else:
                                    normal = _get_normal_or_axis_from_entity(orient_ent)
                                loc_str = "{}, {}, {}".format(pt[0], pt[1], pt[2])
                                orient_str = "{}, {}, {}".format(normal[0], normal[1], normal[2])

                            row = {
                                "cp_name": cp_name,
                                "type": ctype,
                                "location": loc_str,
                                "orientation": orient_str,
                            }

                        elif ctype == "Pin":
                            try:
                                loc_ent = loc_sel.selection(0).entity
                                orient_ent = orient_sel.selection(0).entity
                            except Exception:
                                _step("ui_add_constraint", "SKIP", ctype=ctype, cp_name=cp_name, reason="Missing pin location or axis selection")
                                ui.messageBox("For a Pin, pick a vertex (location) and an edge (line/circle) or cylindrical face (axis).")
                                return
                            axis = _try_get_axis_dir_from_entity(orient_ent)
                            if axis is None:
                                _step("ui_add_constraint", "FAIL", ctype=ctype, cp_name=cp_name, reason="Pin axis missing axis geometry")
                                ui.messageBox("For a Pin, select geometry that defines an axis (straight edge, circular edge, or cylindrical face).")
                                return
                            pt = _get_point_from_entity(loc_ent)
                            row = {
                                "cp_name": cp_name,
                                "type": ctype,
                                "location": "{}, {}, {}".format(pt[0], pt[1], pt[2]),
                                "orientation": "{}, {}, {}".format(axis[0], axis[1], axis[2]),
                            }

                        elif ctype == "Line":
                            try:
                                loc_ent = loc_sel.selection(0).entity
                            except Exception:
                                _step("ui_add_constraint", "SKIP", ctype=ctype, cp_name=cp_name, reason="Missing line edge selection")
                                ui.messageBox("For a Line, pick an edge to define the contact.")
                                return
                            geom = getattr(loc_ent, "geometry", None)
                            if not geom or not hasattr(geom, "startPoint") or not hasattr(geom, "endPoint"):
                                _step("ui_add_constraint", "FAIL", ctype=ctype, cp_name=cp_name, reason="Selected entity invalid edge geometry")
                                ui.messageBox("Selected entity is not a valid edge for Line constraint.")
                                return
                            geom_type_name = type(geom).__name__.lower()
                            if "line" not in geom_type_name:
                                _step("ui_add_constraint", "FAIL", ctype=ctype, cp_name=cp_name, reason="Selected edge not straight line geometry")
                                ui.messageBox("Selected edge is not a straight line for Line constraint.")
                                return
                            s, e = geom.startPoint, geom.endPoint
                            mx = (s.x + e.x) / 2.0 * 10.0
                            my = (s.y + e.y) / 2.0 * 10.0
                            mz = (s.z + e.z) / 2.0 * 10.0
                            dx = e.x - s.x
                            dy = e.y - s.y
                            dz = e.z - s.z
                            L = (dx * dx + dy * dy + dz * dz) ** 0.5
                            if L < 1e-10:
                                _step("ui_add_constraint", "FAIL", ctype=ctype, cp_name=cp_name, reason="Line edge too short")
                                ui.messageBox("Selected edge is too short for Line constraint.")
                                return
                            nx, ny, nz = dx / L, dy / L, dz / L
                            loc_str = "{}, {}, {}".format(mx, my, mz)
                            orient_str = "{}, {}, {}".format(nx, ny, nz)
                            cn = _get_constraint_normal_for_edge(loc_ent, (nx, ny, nz))
                            cdir_str = "{}, {}, {}".format(cn[0], cn[1], cn[2])
                            L_mm = L * 10.0
                            row = {
                                "cp_name": cp_name,
                                "type": ctype,
                                "location": loc_str,
                                "orientation": orient_str,
                                "line_length": L_mm,
                                "constraint_dir": cdir_str,
                            }

                        elif ctype == "Plane":
                            try:
                                loc_ent = loc_sel.selection(0).entity
                            except Exception:
                                _step("ui_add_constraint", "SKIP", ctype=ctype, cp_name=cp_name, reason="Missing plane face selection")
                                ui.messageBox("For a Plane, pick a face to define the contact.")
                                return
                            pt = _get_point_from_entity(loc_ent)
                            normal = _get_normal_or_axis_from_entity(loc_ent)
                            loc_str = "{}, {}, {}".format(pt[0], pt[1], pt[2])
                            orient_str = "{}, {}, {}".format(normal[0], normal[1], normal[2])
                            manual_txt = (plane_prop_manual.value or "").strip()
                            pt_override, _prop_ok = _parse_plane_manual_override(manual_txt)
                            if manual_txt:
                                if pt_override is None:
                                    _step(
                                        "ui_add_constraint",
                                        "FAIL",
                                        ctype=ctype,
                                        cp_name=cp_name,
                                        reason="Invalid plane_prop override",
                                    )
                                    ui.messageBox(
                                        "Plane prop override must be 8 numbers (rectangular: "
                                        "ux,uy,uz,xlen,vx,vy,vz,ylen) or 1 number (circular radius), mm."
                                    )
                                    return
                                plane_type, plane_prop = pt_override, manual_txt
                            else:
                                plane_type, plane_prop = _get_plane_properties_from_face(
                                    loc_ent, force_type=_plane_force_type_from_ui()
                                )
                            row = {
                                "cp_name": cp_name,
                                "type": ctype,
                                "location": loc_str,
                                "orientation": orient_str,
                                "plane_type": plane_type,
                                "plane_prop": plane_prop,
                                "plane_size_mode": (
                                    plane_shape_in.selectedItem.name
                                    if plane_shape_in.selectedItem
                                    else "Auto (from face)"
                                ),
                            }
                        else:
                            _step("ui_add_constraint", "FAIL", ctype=ctype, cp_name=cp_name, reason="Unknown constraint type")
                            ui.messageBox(f"Unknown constraint type: {ctype}")
                            return

                        row = _apply_invert_to_row(row)
                        state["constraints"].append(row)
                        _step("ui_add_constraint", "SUCCESS", ctype=ctype, cp_name=cp_name, constraints_total=len(state["constraints"]), row=row)
                        _update_constraints_box()

                        # Visual feedback
                        try:
                            import visualizer
                            visualizer.draw_constraint_markers(app, state["constraints"])
                            visualizer.clear_kst_weakest_constraint_arrows(app)
                        except Exception:
                            pass

                        # Prepare next name and clear picks
                        name_in.value = _next_cp_name(ctype)
                        try:
                            loc_sel.clearSelection()
                            orient_sel.clearSelection()
                        except Exception:
                            pass
                        _update_pick_feedback()

                    elif changed.id == "kst_update" and getattr(update_action, "value", False):
                        update_action.value = False
                        if not state["constraints"]:
                            ui.messageBox("No constraints to update.")
                            return
                        try:
                            idx = int((edit_index_in.value or "1").strip()) - 1
                        except Exception:
                            ui.messageBox("Edit Index must be an integer.")
                            return
                        if idx < 0 or idx >= len(state["constraints"]):
                            ui.messageBox(f"Edit Index must be between 1 and {len(state['constraints'])}.")
                            return
                        existing = dict(state["constraints"][idx])
                        ctype = type_in.selectedItem.name if type_in.selectedItem else existing.get("type", "Point")
                        cp_name = (name_in.value or "").strip() or existing.get("cp_name", _next_cp_name(ctype))
                        row = dict(existing)
                        row["cp_name"] = cp_name
                        row["type"] = ctype
                        try:
                            if ctype in ("Point", "Pin"):
                                if loc_sel and loc_sel.selectionCount > 0:
                                    pt = _get_point_from_entity(loc_sel.selection(0).entity)
                                    row["location"] = _fmt_vec3(pt)
                                if ctype == "Point" and orient_method.selectedItem and orient_method.selectedItem.name == "Two Points":
                                    origin_str, direction_str = _pick_two_vertices_for_line(app)
                                    if origin_str and direction_str:
                                        row["location"] = origin_str
                                        row["orientation"] = direction_str
                                elif orient_sel and orient_sel.selectionCount > 0:
                                    orient_ent = orient_sel.selection(0).entity
                                    if ctype == "Pin":
                                        axis = _try_get_axis_dir_from_entity(orient_ent)
                                        if axis is not None:
                                            row["orientation"] = _fmt_vec3(axis)
                                    else:
                                        row["orientation"] = _fmt_vec3(_get_normal_or_axis_from_entity(orient_ent))
                            elif ctype == "Line":
                                if loc_sel and loc_sel.selectionCount > 0:
                                    loc_ent = loc_sel.selection(0).entity
                                    geom = getattr(loc_ent, "geometry", None)
                                    if geom and hasattr(geom, "startPoint") and hasattr(geom, "endPoint"):
                                        s, e = geom.startPoint, geom.endPoint
                                        mx = (s.x + e.x) / 2.0 * 10.0
                                        my = (s.y + e.y) / 2.0 * 10.0
                                        mz = (s.z + e.z) / 2.0 * 10.0
                                        dx = e.x - s.x
                                        dy = e.y - s.y
                                        dz = e.z - s.z
                                        L = (dx * dx + dy * dy + dz * dz) ** 0.5
                                        if L > 1e-10:
                                            nx, ny, nz = dx / L, dy / L, dz / L
                                            row["location"] = "{}, {}, {}".format(mx, my, mz)
                                            row["orientation"] = "{}, {}, {}".format(nx, ny, nz)
                                            cn = _get_constraint_normal_for_edge(loc_ent, (nx, ny, nz))
                                            row["constraint_dir"] = "{}, {}, {}".format(cn[0], cn[1], cn[2])
                                            row["line_length"] = L * 10.0
                            elif ctype == "Plane":
                                if loc_sel and loc_sel.selectionCount > 0:
                                    loc_ent = loc_sel.selection(0).entity
                                    pt = _get_point_from_entity(loc_ent)
                                    normal = _get_normal_or_axis_from_entity(loc_ent)
                                    manual_txt = (plane_prop_manual.value or "").strip()
                                    pt_override, _ok = _parse_plane_manual_override(manual_txt)
                                    if manual_txt:
                                        if pt_override is None:
                                            ui.messageBox(
                                                "Plane prop override must be 8 numbers (rectangular) "
                                                "or 1 number (radius), mm."
                                            )
                                            return
                                        plane_type, plane_prop = pt_override, manual_txt
                                    else:
                                        plane_type, plane_prop = _get_plane_properties_from_face(
                                            loc_ent, force_type=_plane_force_type_from_ui()
                                        )
                                    row["location"] = _fmt_vec3(pt)
                                    row["orientation"] = _fmt_vec3(normal)
                                    row["plane_type"] = plane_type
                                    row["plane_prop"] = plane_prop
                                    row["plane_size_mode"] = (
                                        plane_shape_in.selectedItem.name
                                        if plane_shape_in.selectedItem
                                        else "Auto (from face)"
                                    )
                        except Exception:
                            pass
                        row = _apply_invert_to_row(row)
                        state["constraints"][idx] = row
                        _update_constraints_box()
                        try:
                            import visualizer
                            visualizer.draw_constraint_markers(app, state["constraints"])
                            visualizer.clear_kst_weakest_constraint_arrows(app)
                        except Exception:
                            pass
                        _update_pick_feedback()

                    elif changed.id == "kst_save_cfg" and getattr(save_cfg_action, "value", False):
                        save_cfg_action.value = False
                        try:
                            path = _save_constraints_config()
                            ui.messageBox(f"Saved config:\n{path}")
                        except Exception as e:
                            ui.messageBox(f"Failed to save config: {e}")

                    elif changed.id == "kst_load_cfg" and getattr(load_cfg_action, "value", False):
                        load_cfg_action.value = False
                        try:
                            path = _load_constraints_config()
                            ui.messageBox(f"Loaded config:\n{path}")
                        except Exception as e:
                            ui.messageBox(f"Failed to load config: {e}")

                    elif changed.id == "kst_run_analysis" and getattr(run_analysis_action, "value", False):
                        # Momentary button behavior
                        run_analysis_action.value = False

                        if not state["constraints"]:
                            _step("run_analysis_in_dialog", "SKIP", reason="No constraints")
                            ui.messageBox("Add at least one constraint before running analysis.")
                            return

                        # Clear stale arrows until we re-render from the latest analysis.
                        try:
                            import visualizer
                            visualizer.clear_kst_weakest_constraint_arrows(app)
                        except Exception:
                            pass

                        # Pre-run summary: let the user verify that constraint picks are correct.
                        _step("run_analysis_in_dialog", "START", constraints_total=len(state["constraints"]))
                        summary_lines = []
                        for i, r in enumerate(state["constraints"], start=1):
                            cp_name = r.get("cp_name", "")
                            ctype = r.get("type", "Point")
                            loc = r.get("location", "")
                            ori = r.get("orientation", "")
                            line = f"{i}. {cp_name} [{ctype}] loc=({loc}) mm  orient=({ori})"
                            line += _format_plane_detail_line(r)
                            summary_lines.append(line)
                        summary_text = (
                            "KST Analysis inputs (units: mm)\n\n"
                            + "\n".join(summary_lines)
                            + "\n\nProceed with analysis?"
                        )

                        try:
                            confirm = ui.messageBox(
                                summary_text,
                                "Confirm Constraints",
                                adsk.core.MessageBoxButtonTypes.OKCancelButtonType,
                            )
                            if hasattr(adsk.core, "MessageBoxResult") and confirm != adsk.core.MessageBoxResult.OK:
                                _step("run_analysis_in_dialog_preconfirm", "SKIP", reason="User cancelled")
                                return
                        except Exception:
                            # If OK/Cancel isn't available, show OK-only summary.
                            ui.messageBox(summary_text, "Confirm Constraints")

                        in_path = _write_input_json()
                        out_path = _run_external_analysis(in_path)
                        _update_results_box_from_file(out_path)

                        # If the external analysis produced a detailed sidecar JSON,
                        # render one weakest-resistance motion arrow per constraint.
                        try:
                            detail_path = os.path.join(state["output_dir"], "results_wizard_detailed.json")
                            if os.path.isfile(detail_path):
                                with open(detail_path, "r", encoding="utf-8") as f:
                                    detail = json.load(f)
                                if detail.get("success") and detail.get("Ri") and detail.get("mot_all") and detail.get("constraints"):
                                    Ri = detail["Ri"]
                                    mot_all = detail["mot_all"]
                                    constraints_detail = detail["constraints"]

                                    n_motions = len(Ri)
                                    n_constraints = len(constraints_detail)
                                    if n_motions > 0 and n_constraints > 0:
                                        weakest_arrows = []
                                        for j in range(n_constraints):
                                            best_i = 0
                                            best_val = None
                                            for i in range(n_motions):
                                                row = Ri[i]
                                                if not row or j >= len(row):
                                                    continue
                                                v = row[j]
                                                try:
                                                    vf = float(v)
                                                except Exception:
                                                    continue
                                                if best_val is None or vf > best_val:
                                                    best_val = vf
                                                    best_i = i

                                            best_val_f = float(best_val) if best_val is not None else 0.0

                                            c = constraints_detail[j]
                                            loc = c.get("location") or [0.0, 0.0, 0.0]
                                            # mot_all layout: [omu(3), mu(3), rho(3), h]
                                            mu = [0.0, 0.0, 1.0]
                                            if 0 <= best_i < len(mot_all):
                                                mrow = mot_all[best_i]
                                                if mrow and len(mrow) >= 6:
                                                    mu = mrow[3:6]

                                            dx, dy, dz = float(mu[0]), float(mu[1]), float(mu[2])
                                            mag = (dx * dx + dy * dy + dz * dz) ** 0.5
                                            if mag < 1e-12:
                                                # Fallback: use the constraint's orientation.
                                                ori = c.get("orientation") or [0.0, 0.0, 1.0]
                                                dx, dy, dz = float(ori[0]), float(ori[1]), float(ori[2])
                                                mag = (dx * dx + dy * dy + dz * dz) ** 0.5
                                                if mag < 1e-12:
                                                    dx, dy, dz = 0.0, 0.0, 1.0
                                                    mag = 1.0

                                            direction = [dx / mag, dy / mag, dz / mag]
                                            weakest_arrows.append(
                                                {"location": loc, "direction": direction, "strength": best_val_f}
                                            )

                                        try:
                                            import visualizer
                                            # Draw/refresh in the viewport.
                                            visualizer.draw_constraint_weakest_arrows(app, weakest_arrows)
                                        except Exception:
                                            pass
                        except Exception:
                            pass

                        _step("run_analysis_in_dialog", "SUCCESS", out_path=out_path)

                    elif changed.id == "kst_remove_last" and getattr(remove_last_action, "value", False):
                        remove_last_action.value = False
                        if state["constraints"]:
                            _step("ui_remove_last_constraint", "START", constraints_total=len(state["constraints"]))
                            state["constraints"].pop()
                            _update_constraints_box()
                            try:
                                import visualizer
                                visualizer.draw_constraint_markers(app, state["constraints"])
                                visualizer.clear_kst_weakest_constraint_arrows(app)
                            except Exception:
                                pass
                            cur_type = type_in.selectedItem.name if type_in.selectedItem else "Point"
                            name_in.value = _next_cp_name(cur_type)
                            _step("ui_remove_last_constraint", "SUCCESS", constraints_total=len(state["constraints"]))
                            _update_pick_feedback()

                    elif changed.id == "kst_clear_all" and getattr(clear_all_action, "value", False):
                        clear_all_action.value = False
                        _step("ui_clear_all_constraints", "START", constraints_total=len(state["constraints"]))
                        state["constraints"].clear()
                        _update_constraints_box()
                        try:
                            import visualizer
                            visualizer.clear_kst_graphics(app)
                        except Exception:
                            pass
                        cur_type = type_in.selectedItem.name if type_in.selectedItem else "Point"
                        name_in.value = _next_cp_name(cur_type)
                        _step("ui_clear_all_constraints", "SUCCESS")
                        _update_pick_feedback()
                except Exception as e:
                    try:
                        _step("ui_input_changed", "FAIL", error=str(e))
                        ui.messageBox(f"KST input change error: {e}")
                    except Exception:
                        pass

        class _ExecuteHandler(adsk.core.CommandEventHandler):
            def __init__(self):
                super().__init__()

            def notify(self, event_args):
                try:
                    # OK closes the dialog. If results exist, show them as a final popup;
                    # otherwise just exit (users can run in-dialog via "Run Analysis").
                    try:
                        out_path = os.path.join(state["output_dir"], "results_wizard.txt")
                        if os.path.isfile(out_path) and os.path.getsize(out_path) > 0:
                            with open(out_path, "r", encoding="utf-8") as f:
                                lines = f.read().strip().splitlines()
                            if len(lines) >= 2:
                                parts = lines[1].split("\t")
                                if len(parts) >= 4:
                                    ui.messageBox(
                                        f"WTR={parts[0]}\nMRR={parts[1]}\nMTR={parts[2]}\nTOR={parts[3]}\n\n{out_path}",
                                        "KST Analysis Results",
                                    )
                    except Exception:
                        pass
                except Exception as e:
                    _step("execute_close", "FAIL", error=str(e))
                    ui.messageBox(f"KST analysis failed: {e}")

        class _DestroyHandler(adsk.core.CommandEventHandler):
            def __init__(self):
                super().__init__()

            def notify(self, event_args):
                # Keep references around
                pass

        input_changed_handler = _InputChangedHandler()
        exec_handler = _ExecuteHandler()
        destroy_handler = _DestroyHandler()

        cmd.inputChanged.add(input_changed_handler)
        cmd.execute.add(exec_handler)
        cmd.destroy.add(destroy_handler)

        cls._handlers.extend([input_changed_handler, exec_handler, destroy_handler])

    @classmethod
    def _on_execute(cls, args):
        # Execute is handled by the native-command UI's execute handler.
        return
