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
    """Return (x,y,z) from a face, edge, or vertex. Units in cm (Fusion internal)."""
    if hasattr(entity, "pointOnFace"):
        p = entity.pointOnFace
        return (p.x, p.y, p.z)
    if hasattr(entity, "geometry"):
        geom = entity.geometry
        # BRepVertex.geometry → Point3D (has x/y/z but no origin or startPoint)
        if hasattr(geom, "x") and hasattr(geom, "y") and hasattr(geom, "z") and not hasattr(geom, "origin"):
            return (geom.x, geom.y, geom.z)
        if hasattr(geom, "origin"):
            o = geom.origin
            return (o.x, o.y, o.z)
        if hasattr(geom, "startPoint"):
            s, e = geom.startPoint, geom.endPoint
            return ((s.x + e.x) / 2, (s.y + e.y) / 2, (s.z + e.z) / 2)
    if hasattr(entity, "boundingBox"):
        box = entity.boundingBox
        p = box.minPoint
        return ((p.x + box.maxPoint.x) / 2, (p.y + box.maxPoint.y) / 2, (p.z + box.maxPoint.z) / 2)
    return (0, 0, 0)


def _get_normal_or_axis_from_entity(entity):
    """Return (nx,ny,nz) unit vector from a face (normal) or edge (direction)."""
    if hasattr(entity, "geometry"):
        geom = entity.geometry
        if hasattr(geom, "normal"):
            n = geom.normal
            L = (n.x**2 + n.y**2 + n.z**2) ** 0.5
            if L > 1e-10:
                return (n.x / L, n.y / L, n.z / L)
        if hasattr(geom, "startPoint") and hasattr(geom, "endPoint"):
            s, e = geom.startPoint, geom.endPoint
            dx, dy, dz = e.x - s.x, e.y - s.y, e.z - s.z
            L = (dx*dx + dy*dy + dz*dz) ** 0.5
            if L > 1e-10:
                return (dx / L, dy / L, dz / L)
    if hasattr(entity, "pointOnFace") and hasattr(entity, "normal"):
        n = entity.normal
        if n:
            L = (n.x**2 + n.y**2 + n.z**2) ** 0.5
            if L > 1e-10:
                return (n.x / L, n.y / L, n.z / L)
    return (0, 0, 1)


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


def _get_plane_properties_from_face(face_ent):
    """Compute (plane_type, plane_prop_str) for a Fusion face.

    - Rectangular (type 1): plane_prop_str has 8 values
      ux, uy, uz, width, vx, vy, vz, height
    - Circular (type 2): plane_prop_str has 1 value: radius

    Falls back to a small default rectangle if geometry details are unavailable.
    """
    try:
        geom = getattr(face_ent, "geometry", None)
        # Normal as unit vector
        nx, ny, nz = _get_normal_or_axis_from_entity(face_ent)

        # Detect circular faces (cylinders / cones, etc.) via geometry type name if available
        geom_type = type(geom).__name__ if geom is not None else ""
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
            prop_str = f"{ux}, {uy}, {uz}, {width}, {vx}, {vy}, {vz}, {height}"
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
            return 2, f"{radius}"

        # Rectangular plane
        prop_str = f"{ux}, {uy}, {uz}, {width}, {vx}, {vy}, {vz}, {height}"
        return 1, prop_str
    except Exception:
        # Fallback: small default rectangle aligned with computed normal
        nx, ny, nz = _get_normal_or_axis_from_entity(face_ent)
        (ux, uy, uz), (vx, vy, vz) = _compute_orthonormal_basis_from_normal(nx, ny, nz)
        width = height = 1.0
        prop_str = f"{ux}, {uy}, {uz}, {width}, {vx}, {vy}, {vz}, {height}"
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


def _selections_to_constraints(selection_input):
    """Convert Fusion selection list to list of (location_str, orientation_str)."""
    constraints = []
    if not selection_input or selection_input.selectionCount == 0:
        return constraints
    count = selection_input.selectionCount
    # Pairs: (location_entity, orientation_entity)
    for i in range(0, count - 1, 2):
        loc_ent = selection_input.selection(i).entity
        orient_ent = selection_input.selection(i + 1).entity
        pt = _get_point_from_entity(loc_ent)
        normal = _get_normal_or_axis_from_entity(orient_ent)
        loc_str = "{}, {}, {}".format(pt[0], pt[1], pt[2])
        orient_str = "{}, {}, {}".format(normal[0], normal[1], normal[2])
        constraints.append((loc_str, orient_str))
    if count % 2 == 1:
        # Odd: use last entity as location only, orientation 0,0,1
        loc_ent = selection_input.selection(count - 1).entity
        pt = _get_point_from_entity(loc_ent)
        constraints.append(("{}, {}, {}".format(pt[0], pt[1], pt[2]), "0, 0, 1"))
    return constraints


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

        # Best-effort repo root guess for external script execution
        repo_root_guess = os.path.abspath(os.path.join(_ADDIN_DIR, os.pardir, os.pardir))
        wizard_script = os.path.join(repo_root_guess, "scripts", "run_wizard_analysis.py")

        # ---- In-command state ----
        state = {
            "constraints": [],  # list[dict]: {cp_name,type,location,orientation}
            "output_dir": output_dir,
            "wizard_script": wizard_script,
        }

        # ---- Logging ----
        log_path = os.path.join(output_dir, "fusion_wizard.log")
        logger = logging.getLogger("kst_fusion_wizard")
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

        # ---- UI: Pickers ----
        cmd_inputs.addTextBoxCommandInput(
            "kst_help",
            "How to use",
            "For each CP: (1) set CP Name + Type, (2) pick a <b>location</b>, (3) pick an <b>orientation</b>, (4) click <b>Add Constraint</b> to save. Repeat for more CPs, then click <b>OK</b> to run analysis.",
            4,
            True,
        )

        name_in = cmd_inputs.addStringValueInput("kst_cp_name", "CP Name", "CP1")

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
        remove_last_action = cmd_inputs.addBoolValueInput("kst_remove_last", "Remove Last", False, "", False)
        clear_all_action = cmd_inputs.addBoolValueInput("kst_clear_all", "Clear All", False, "", False)

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

        cmd_inputs.addTextBoxCommandInput(
            "kst_results",
            "Results",
            "(run analysis to see WTR/MRR/MTR/TOR)",
            4,
            True,
        )

        # ---- Helpers ----
        def _format_constraints_text(rows):
            if not rows:
                return "(none yet)"
            lines = []
            for i, r in enumerate(rows, start=1):
                lines.append(
                    f"{i}. {r.get('cp_name','CP')}  {r.get('type','Point')}  "
                    f"loc=({r.get('location','')})  orient=({r.get('orientation','')})"
                )
            return "\n".join(lines)

        def _update_constraints_box():
            constraints_box.text = _format_constraints_text(state["constraints"])

        def _next_cp_name():
            return f"CP{len(state['constraints']) + 1}"

        def _fmt_vec3(vec):
            try:
                return "{}, {}, {}".format(vec[0], vec[1], vec[2])
            except Exception:
                return "0, 0, 0"

        def _update_pick_feedback():
            try:
                loc_txt = "(none)"
                ori_txt = "(none)"
                if loc_sel and loc_sel.selectionCount > 0:
                    loc_ent = loc_sel.selection(0).entity
                    loc_txt = _fmt_vec3(_get_point_from_entity(loc_ent))
                if orient_sel and orient_sel.selectionCount > 0:
                    orient_ent = orient_sel.selection(0).entity
                    ori_txt = _fmt_vec3(_get_normal_or_axis_from_entity(orient_ent))
                pick_feedback.text = f"loc=({loc_txt})\norient=({ori_txt})"
            except Exception:
                try:
                    pick_feedback.text = "(selection info unavailable)"
                except Exception:
                    pass

        def _configure_selection_filters_for_type():
            """Adjust selection filters and visibility based on current constraint type."""
            ctype = type_in.selectedItem.name if type_in.selectedItem else "Point"
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
                if ctype == "Point":
                    # Location: vertices only for precise CPs
                    loc_sel.addSelectionFilter("Vertices")
                    # Orientation: faces or edges depending on method (we keep both; method decides how to interpret)
                    orient_sel.addSelectionFilter("Faces")
                    orient_sel.addSelectionFilter("Edges")
                elif ctype == "Pin":
                    orient_method.isVisible = False
                    # Location: vertex for pin center
                    loc_sel.addSelectionFilter("Vertices")
                    # Orientation: edge as pin axis
                    orient_sel.addSelectionFilter("Edges")
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
            except Exception:
                # If filter configuration fails, keep whatever defaults Fusion provides.
                pass

        def _ensure_output_dir():
            try:
                os.makedirs(state["output_dir"], exist_ok=True)
            except Exception:
                pass

        def _write_input_json():
            _ensure_output_dir()
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
            except Exception as exc:
                logger.exception("Failed to write wizard_input.json: %s", exc)
                raise
            return in_path

        def _run_external_analysis(in_path):
            if not os.path.isfile(state["wizard_script"]):
                msg = f"Missing external script: {state['wizard_script']}"
                logger.error(msg)
                raise RuntimeError(msg)
            out_path = os.path.join(state["output_dir"], "results_wizard.txt")
            # Use system python (where numpy is installed)
            cmdline = ["python", state["wizard_script"], in_path, out_path]
            logger.info("Running external analysis: %s", " ".join(cmdline))
            proc = subprocess.run(cmdline, capture_output=True, text=True)
            if proc.returncode != 0:
                msg = proc.stderr.strip() or proc.stdout.strip() or f"exit code {proc.returncode}"
                logger.error("External analysis failed (code %s): %s", proc.returncode, msg)
                raise RuntimeError(msg)
            logger.info("External analysis completed successfully, results at %s", out_path)
            return out_path

        def _update_results_box_from_file(path):
            try:
                with open(path) as f:
                    lines = f.read().strip().splitlines()
                if len(lines) >= 2:
                    parts = lines[1].split("\t")
                    if len(parts) >= 4:
                        cmd_inputs.itemById("kst_results").text = (
                            f"WTR={parts[0]}\nMRR={parts[1]}\nMTR={parts[2]}\nTOR={parts[3]}\n\n{path}"
                        )
                        return
                cmd_inputs.itemById("kst_results").text = f"(wrote {path}, but could not parse results)"
            except Exception as e:
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
                        _configure_selection_filters_for_type()
                        _update_pick_feedback()
                        return

                    if changed.id == "kst_add" and getattr(add_action, "value", False):
                        add_action.value = False
                        ctype = type_in.selectedItem.name if type_in.selectedItem else "Point"
                        cp_name = (name_in.value or "").strip() or _next_cp_name()

                        # Per-type handling
                        if ctype == "Point":
                            method = orient_method.selectedItem.name if orient_method.selectedItem else "Normal to Plane"
                            if method == "Two Points":
                                origin_str, direction_str = _pick_two_vertices_for_line(app)
                                if not origin_str or not direction_str:
                                    ui.messageBox("Two-point orientation cancelled or invalid.")
                                    return
                                loc_str = origin_str
                                orient_str = direction_str
                            else:
                                try:
                                    loc_ent = loc_sel.selection(0).entity
                                    orient_ent = orient_sel.selection(0).entity
                                except Exception:
                                    ui.messageBox("Pick both Location and Orientation before adding.")
                                    return
                                pt = _get_point_from_entity(loc_ent)
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
                                ui.messageBox("For a Pin, pick a vertex (location) and an edge (axis).")
                                return
                            pt = _get_point_from_entity(loc_ent)
                            axis = _get_normal_or_axis_from_entity(orient_ent)
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
                                ui.messageBox("For a Line, pick an edge to define the contact.")
                                return
                            geom = getattr(loc_ent, "geometry", None)
                            if not geom or not hasattr(geom, "startPoint") or not hasattr(geom, "endPoint"):
                                ui.messageBox("Selected entity is not a valid edge for Line constraint.")
                                return
                            s, e = geom.startPoint, geom.endPoint
                            mx = (s.x + e.x) / 2.0
                            my = (s.y + e.y) / 2.0
                            mz = (s.z + e.z) / 2.0
                            dx = e.x - s.x
                            dy = e.y - s.y
                            dz = e.z - s.z
                            L = (dx * dx + dy * dy + dz * dz) ** 0.5
                            if L < 1e-10:
                                ui.messageBox("Selected edge is too short for Line constraint.")
                                return
                            nx, ny, nz = dx / L, dy / L, dz / L
                            loc_str = "{}, {}, {}".format(mx, my, mz)
                            orient_str = "{}, {}, {}".format(nx, ny, nz)
                            cn = _get_constraint_normal_for_edge(loc_ent, (nx, ny, nz))
                            cdir_str = "{}, {}, {}".format(cn[0], cn[1], cn[2])
                            row = {
                                "cp_name": cp_name,
                                "type": ctype,
                                "location": loc_str,
                                "orientation": orient_str,
                                "line_length": L,
                                "constraint_dir": cdir_str,
                            }

                        elif ctype == "Plane":
                            try:
                                loc_ent = loc_sel.selection(0).entity
                            except Exception:
                                ui.messageBox("For a Plane, pick a face to define the contact.")
                                return
                            pt = _get_point_from_entity(loc_ent)
                            normal = _get_normal_or_axis_from_entity(loc_ent)
                            loc_str = "{}, {}, {}".format(pt[0], pt[1], pt[2])
                            orient_str = "{}, {}, {}".format(normal[0], normal[1], normal[2])
                            plane_type, plane_prop = _get_plane_properties_from_face(loc_ent)
                            row = {
                                "cp_name": cp_name,
                                "type": ctype,
                                "location": loc_str,
                                "orientation": orient_str,
                                "plane_type": plane_type,
                                "plane_prop": plane_prop,
                            }
                        else:
                            ui.messageBox(f"Unknown constraint type: {ctype}")
                            return

                        state["constraints"].append(row)
                        _update_constraints_box()

                        # Visual feedback
                        try:
                            import visualizer
                            visualizer.draw_constraint_markers(app, state["constraints"])
                        except Exception:
                            pass

                        # Prepare next name and clear picks
                        name_in.value = _next_cp_name()
                        try:
                            loc_sel.clearSelection()
                            orient_sel.clearSelection()
                        except Exception:
                            pass
                        _update_pick_feedback()

                    elif changed.id == "kst_remove_last" and getattr(remove_last_action, "value", False):
                        remove_last_action.value = False
                        if state["constraints"]:
                            state["constraints"].pop()
                            _update_constraints_box()
                            try:
                                import visualizer
                                visualizer.draw_constraint_markers(app, state["constraints"])
                            except Exception:
                                pass
                            name_in.value = _next_cp_name()
                            _update_pick_feedback()

                    elif changed.id == "kst_clear_all" and getattr(clear_all_action, "value", False):
                        clear_all_action.value = False
                        state["constraints"].clear()
                        _update_constraints_box()
                        try:
                            import visualizer
                            visualizer.clear_kst_graphics(app)
                        except Exception:
                            pass
                        name_in.value = _next_cp_name()
                        _update_pick_feedback()
                except Exception as e:
                    try:
                        ui.messageBox(f"KST input change error: {e}")
                    except Exception:
                        pass

        class _ExecuteHandler(adsk.core.CommandEventHandler):
            def __init__(self):
                super().__init__()

            def notify(self, event_args):
                try:
                    if not state["constraints"]:
                        ui.messageBox("Add at least one constraint before running analysis.")
                        return
                    in_path = _write_input_json()
                    out_path = _run_external_analysis(in_path)
                    _update_results_box_from_file(out_path)
                except Exception as e:
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
