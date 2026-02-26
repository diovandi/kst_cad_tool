"""
Fusion 360 viewport visualization for KST Analysis Wizard.
Draws constraint markers (point=arrow, pin=cylinder axis, line=segment) and
weakest screw motions as color- and length-coded arrows.
"""

import math
import adsk.core
import adsk.fusion

_KST_GROUP_ID = "KstAnalysis"
_ARROW_LEN = 1.0  # cm, for constraint direction
_PIN_HALF_LEN = 0.5
_LINE_DISPLAY_LEN = 2.0
_WEAKEST_ARROW_BASE_LEN = 5.0  # cm max length for weakest-motion arrows


def _point3d(x, y, z):
    return adsk.core.Point3D.create(float(x), float(y), float(z))


def _parse_xyz(s):
    if not s or not isinstance(s, str):
        return (0.0, 0.0, 0.0)
    parts = [p.strip() for p in s.replace(",", " ").split()[:3]]
    out = []
    for i in range(3):
        try:
            out.append(float(parts[i]) if i < len(parts) and parts[i] else 0.0)
        except (ValueError, IndexError):
            out.append(0.0)
    return (out[0], out[1], out[2])


def _norm(u):
    n = math.sqrt(u[0] * u[0] + u[1] * u[1] + u[2] * u[2])
    if n < 1e-12:
        return (0.0, 0.0, 1.0)
    return (u[0] / n, u[1] / n, u[2] / n)


def clear_kst_graphics(app):
    """Remove the KST custom graphics group from the active design."""
    try:
        design = adsk.fusion.Design.cast(app.activeProduct)
        if not design:
            return
        root = design.rootComponent
        to_delete = []
        for i in range(root.customGraphicsGroups.count):
            grp = root.customGraphicsGroups.item(i)
            if grp.id == _KST_GROUP_ID:
                to_delete.append(i)
        for i in reversed(to_delete):
            root.customGraphicsGroups.item(i).deleteMe()
    except Exception:
        pass


def _get_or_create_graphics_group(app):
    """Clear existing KST group and add a new one. Returns the new group."""
    clear_kst_graphics(app)
    design = adsk.fusion.Design.cast(app.activeProduct)
    if not design:
        return None
    root = design.rootComponent
    group = root.customGraphicsGroups.add()
    group.id = _KST_GROUP_ID
    return group


def draw_constraint_markers(app, constraint_list):
    """
    Draw a marker in the viewport for each constraint in constraint_list.
    constraint_list: list of dicts with keys type, location, orientation (strings "x, y, z").
    Point: short arrow in orientation direction.
    Pin: line segment along orientation axis.
    Line: line segment from location in orientation direction.
    """
    if not app or not constraint_list:
        return
    try:
        group = _get_or_create_graphics_group(app)
        if not group:
            return
        points = adsk.core.ObjectCollection.create()
        for c in constraint_list:
            ctype = (c.get("type") or "Point").strip()
            loc = _parse_xyz(c.get("location") or "0,0,0")
            orient = _parse_xyz(c.get("orientation") or "0,0,1")
            orient = _norm(orient)
            x, y, z = loc[0], loc[1], loc[2]
            dx, dy, dz = orient[0], orient[1], orient[2]
            if ctype == "Point":
                p1 = _point3d(x, y, z)
                p2 = _point3d(
                    x + dx * _ARROW_LEN,
                    y + dy * _ARROW_LEN,
                    z + dz * _ARROW_LEN,
                )
                points.add(p1)
                points.add(p2)
            elif ctype == "Pin":
                p1 = _point3d(
                    x - dx * _PIN_HALF_LEN,
                    y - dy * _PIN_HALF_LEN,
                    z - dz * _PIN_HALF_LEN,
                )
                p2 = _point3d(
                    x + dx * _PIN_HALF_LEN,
                    y + dy * _PIN_HALF_LEN,
                    z + dz * _PIN_HALF_LEN,
                )
                points.add(p1)
                points.add(p2)
            elif ctype == "Line":
                p1 = _point3d(x, y, z)
                p2 = _point3d(
                    x + dx * _LINE_DISPLAY_LEN,
                    y + dy * _LINE_DISPLAY_LEN,
                    z + dz * _LINE_DISPLAY_LEN,
                )
                points.add(p1)
                points.add(p2)
        if points.count >= 2:
            group.addLines(points)
    except Exception:
        pass


def draw_weakest_motions(app, result, top_n=3):
    """
    Draw the top_n weakest screw motions as arrows in the viewport.
    result: DetailedAnalysisResult from kst_rating_tool.analyze_constraints_detailed.
    Arrow at rho in direction mu; length and color by rating (red=weak, blue=strong).
    """
    if not app or not result:
        return
    try:
        import numpy as np
        from kst_rating_tool.motion import specmot_row_to_screw
    except ImportError:
        return
    try:
        Ri = result.Ri
        mot_all = result.mot_all
        if mot_all is None or mot_all.size == 0 or Ri is None or Ri.size == 0:
            return
        if mot_all.shape[0] != Ri.shape[0]:
            return
        rowsum = np.sum(Ri, axis=1)
        valid = np.isfinite(rowsum) & (rowsum > 0)
        if not np.any(valid):
            return
        idx = np.argsort(rowsum)
        n = min(top_n, int(np.sum(valid)))
        chosen = []
        for i in range(idx.size):
            if valid[idx[i]] and len(chosen) < n:
                chosen.append(idx[i])
        if not chosen:
            return
        rowsum_chosen = rowsum[chosen]
        r_min, r_max = float(np.min(rowsum_chosen)), float(np.max(rowsum_chosen))
        span = (r_max - r_min) or 1.0
        group = _get_or_create_graphics_group(app)
        if not group:
            return
        for row_i in chosen:
            row = mot_all[row_i, :]
            if row.size < 7:
                continue
            screw = specmot_row_to_screw(row)
            rho = screw.rho
            mu = screw.mu
            mnorm = np.linalg.norm(mu)
            if mnorm < 1e-12:
                continue
            mu = mu / mnorm
            rs = float(rowsum[row_i])
            t = (rs - r_min) / span
            length = _WEAKEST_ARROW_BASE_LEN * (0.5 + 0.5 * t)
            end = rho + length * mu
            p1 = _point3d(rho[0], rho[1], rho[2])
            p2 = _point3d(end[0], end[1], end[2])
            points = adsk.core.ObjectCollection.create()
            points.add(p1)
            points.add(p2)
            lines_obj = group.addLines(points)
            try:
                r, g, b = 1.0 - t, 0.0, 0.5 + 0.5 * t
                lines_obj.color = adsk.core.Color.create(r, g, b, 255)
            except Exception:
                pass
    except Exception:
        pass
