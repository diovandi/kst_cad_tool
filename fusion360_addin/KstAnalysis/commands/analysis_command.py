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
    if hasattr(entity, "boundingBox"):
        box = entity.boundingBox
        p = box.minPoint
        return ((p.x + box.maxPoint.x) / 2, (p.y + box.maxPoint.y) / 2, (p.z + box.maxPoint.z) / 2)
    if hasattr(entity, "geometry"):
        geom = entity.geometry
        if hasattr(geom, "origin"):
            o = geom.origin
            return (o.x, o.y, o.z)
        if hasattr(geom, "startPoint"):
            s, e = geom.startPoint, geom.endPoint
            return ((s.x + e.x) / 2, (s.y + e.y) / 2, (s.z + e.z) / 2)
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

        # ---- UI: Pickers ----
        cmd_inputs.addTextBoxCommandInput(
            "kst_help",
            "How to use",
            "For each CP: pick a <b>location</b> (e.g. hole edge/vertex) then pick an <b>orientation</b> (usually the mounting face normal). Click <b>Add Constraint</b>. Repeat. Then click <b>Run Analysis</b>.",
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
        loc_sel.setSelectionLimits(1, 1)
        orient_sel.setSelectionLimits(1, 1)

        btn_row = cmd_inputs.addButtonRowCommandInput("kst_actions", "Actions", False)
        btn_row.listItems.add("Add Constraint", False, "")
        btn_row.listItems.add("Remove Last", False, "")
        btn_row.listItems.add("Clear All", False, "")

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
                except Exception:
                    continue
            data = {
                "version": 2,
                "point_contacts": point_contacts,
                "pins": pins,
                "lines": lines,
                "planes": planes,
            }
            in_path = os.path.join(state["output_dir"], "wizard_input.json")
            with open(in_path, "w") as f:
                json.dump(data, f, indent=2)
            return in_path

        def _run_external_analysis(in_path):
            if not os.path.isfile(state["wizard_script"]):
                raise RuntimeError(f"Missing external script: {state['wizard_script']}")
            out_path = os.path.join(state["output_dir"], "results_wizard.txt")
            # Use system python (where numpy is installed)
            cmdline = ["python", state["wizard_script"], in_path, out_path]
            proc = subprocess.run(cmdline, capture_output=True, text=True)
            if proc.returncode != 0:
                msg = proc.stderr.strip() or proc.stdout.strip() or f"exit code {proc.returncode}"
                raise RuntimeError(msg)
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

                    # React to type/method changes for dynamic UI behavior.
                    if changed.id in ("kst_cp_type", "kst_orient_method"):
                        _configure_selection_filters_for_type()
                        return

                    if changed.id == "kst_actions":
                        # Determine which button was clicked
                        clicked = None
                        for li in btn_row.listItems:
                            if li.isSelected:
                                clicked = li.name
                                li.isSelected = False
                                break
                        if not clicked:
                            return

                        if clicked == "Add Constraint":
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
                                row = {
                                    "cp_name": cp_name,
                                    "type": ctype,
                                    "location": loc_str,
                                    "orientation": orient_str,
                                    "line_length": L,
                                    # For now, reuse line direction as constraint direction; backend can refine later.
                                    "constraint_dir": orient_str,
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
                                row = {
                                    "cp_name": cp_name,
                                    "type": ctype,
                                    "location": loc_str,
                                    "orientation": orient_str,
                                    # Default: rectangular plane, placeholder properties.
                                    "plane_type": 1,
                                    "plane_prop": "0",
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

                        elif clicked == "Remove Last":
                            if state["constraints"]:
                                state["constraints"].pop()
                                _update_constraints_box()
                                try:
                                    import visualizer
                                    visualizer.draw_constraint_markers(app, state["constraints"])
                                except Exception:
                                    pass
                                name_in.value = _next_cp_name()

                        elif clicked == "Clear All":
                            state["constraints"].clear()
                            _update_constraints_box()
                            try:
                                import visualizer
                                visualizer.clear_kst_graphics(app)
                            except Exception:
                                pass
                            name_in.value = _next_cp_name()
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
