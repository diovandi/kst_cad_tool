"""
Fusion 360 command: KST Analysis Wizard.
Shows a selection input to pick geometry (location/orientation) from the model,
then opens the tkinter wizard with the constraint table (pre-filled from selection if any).
"""

import adsk.core
import adsk.fusion
import os
import sys

# Ensure add-in and repo are on path (Fusion runs from add-in folder)
_ADDIN_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_REPO_ROOT = os.path.dirname(os.path.dirname(_ADDIN_DIR))
for _p in (_REPO_ROOT, _ADDIN_DIR):
    if _p not in sys.path:
        sys.path.insert(0, _p)


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
        cls._handlers.append(cmd_def.commandCreated.add(cls._on_command_created))
        if panel:
            panel.controls.addCommand(cmd_def)

    @classmethod
    def _on_command_created(cls, args):
        cmd = args.command
        cmd_inputs = cmd.commandInputs
        cmd_inputs.addSelectionInput(
            "kst_selections",
            "Select location then orientation (pairs)",
            "Select faces or edges: 1st=location, 2nd=orientation, repeat for more constraints."
        )
        sel_input = cmd_inputs.itemById("kst_selections")
        if sel_input:
            try:
            sel_input.addSelectionFilter("Faces")
            sel_input.addSelectionFilter("Edges")
            sel_input.addSelectionFilter("Vertices")
        except Exception:
            pass
        sel_input.setSelectionLimits(0, 0)  # 0 = unlimited
        cls._handlers.append(cmd.execute.add(cls._on_execute))

    @classmethod
    def _on_execute(cls, args):
        cmd = args.command
        cmd_inputs = cmd.commandInputs
        sel_input = cmd_inputs.itemById("kst_selections")
        initial_constraints = _selections_to_constraints(sel_input) if sel_input else []
        try:
            from ui import analysis_wizard
            analysis_wizard.run_analysis_wizard(initial_constraints=initial_constraints)
        except Exception as e:
            app = adsk.core.Application.get()
            app.userInterface.messageBox("KST Wizard error: {}".format(str(e)))
