"""
Fusion 360 viewport visualization for KST Analysis Wizard.
Draws constraint markers (point=arrow, pin=cylinder axis, line=segment) and
weakest screw motions as color- and length-coded arrows.
"""

import math
import adsk.core
import adsk.fusion

_KST_MARKERS_GROUP_ID = "KstAnalysis"
_KST_WEAKEST_CONSTRAINTS_GROUP_ID = "KstAnalysisWeakestConstraints"
_KST_WEAKEST_MOTIONS_GROUP_ID = "KstAnalysisWeakestMotions"
# Marker/arrow lengths in mm (Fusion internal units are cm, converted to mm
# when we serialize constraints).
_ARROW_LEN = 10.0  # mm, for constraint direction
_PIN_HALF_LEN = 5.0  # mm
_LINE_DISPLAY_LEN = 20.0  # mm
_WEAKEST_ARROW_BASE_LEN = 50.0  # mm max length for weakest-motion arrows


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


def _parse_floats(s):
    if not s or not isinstance(s, str):
        return []
    vals = []
    for p in s.replace(",", " ").split():
        try:
            vals.append(float(p.strip()))
        except Exception:
            continue
    return vals


def _norm(u):
    n = math.sqrt(u[0] * u[0] + u[1] * u[1] + u[2] * u[2])
    if n < 1e-12:
        return (0.0, 0.0, 1.0)
    return (u[0] / n, u[1] / n, u[2] / n)


def _orthonormal_basis(n):
    nx, ny, nz = _norm(n)
    if abs(nx) < 0.9:
        ax, ay, az = 1.0, 0.0, 0.0
    else:
        ax, ay, az = 0.0, 1.0, 0.0
    ux = ny * az - nz * ay
    uy = nz * ax - nx * az
    uz = nx * ay - ny * ax
    ux, uy, uz = _norm((ux, uy, uz))
    vx = ny * uz - nz * uy
    vy = nz * ux - nx * uz
    vz = nx * uy - ny * ux
    vx, vy, vz = _norm((vx, vy, vz))
    return (ux, uy, uz), (vx, vy, vz)


def clear_kst_graphics(app):
    """Remove KST custom graphics groups from the active design."""
    try:
        design = adsk.fusion.Design.cast(app.activeProduct)
        if not design:
            return
        root = design.rootComponent
        to_delete = []
        for i in range(root.customGraphicsGroups.count):
            grp = root.customGraphicsGroups.item(i)
            if grp.id in {
                _KST_MARKERS_GROUP_ID,
                _KST_WEAKEST_CONSTRAINTS_GROUP_ID,
                _KST_WEAKEST_MOTIONS_GROUP_ID,
            }:
                to_delete.append(i)
        for i in reversed(to_delete):
            root.customGraphicsGroups.item(i).deleteMe()
    except Exception:
        pass


def _clear_graphics_group(app, group_id: str) -> None:
    """Delete one custom graphics group id (best-effort)."""
    try:
        design = adsk.fusion.Design.cast(app.activeProduct)
        if not design:
            return
        root = design.rootComponent
        to_delete = []
        for i in range(root.customGraphicsGroups.count):
            grp = root.customGraphicsGroups.item(i)
            if grp.id == group_id:
                to_delete.append(i)
        for i in reversed(to_delete):
            root.customGraphicsGroups.item(i).deleteMe()
    except Exception:
        pass


def _get_or_create_graphics_group(app, group_id: str):
    """Clear existing group_id and add a new one. Returns the new group."""
    _clear_graphics_group(app, group_id)
    design = adsk.fusion.Design.cast(app.activeProduct)
    if not design:
        return None
    root = design.rootComponent
    group = root.customGraphicsGroups.add()
    group.id = group_id
    return group


def draw_constraint_markers(app, constraint_list):
    """
    Draw a marker in the viewport for each constraint in constraint_list.
    constraint_list: list of dicts with keys type, location, orientation (strings "x, y, z").
    Point: short arrow in orientation direction.
    Pin: line segment along orientation axis.
    Line: line segment from location in orientation direction.
    Plane: short normal arrow at the plane midpoint.
    """
    if not app or not constraint_list:
        return
    try:
        group = _get_or_create_graphics_group(app, _KST_MARKERS_GROUP_ID)
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
                cdir = _norm(_parse_xyz(c.get("constraint_dir") or "0,0,1"))
                p3 = _point3d(x, y, z)
                p4 = _point3d(
                    x + cdir[0] * _ARROW_LEN,
                    y + cdir[1] * _ARROW_LEN,
                    z + cdir[2] * _ARROW_LEN,
                )
                points.add(p3)
                points.add(p4)
            elif ctype == "Plane":
                # Draw normal arrow.
                p1 = _point3d(x, y, z)
                p2 = _point3d(
                    x + dx * _ARROW_LEN,
                    y + dy * _ARROW_LEN,
                    z + dz * _ARROW_LEN,
                )
                points.add(p1)
                points.add(p2)
                ptype = int(c.get("plane_type", 1))
                prop = _parse_floats(c.get("plane_prop", ""))
                if ptype == 1 and len(prop) >= 8:
                    u = _norm((prop[0], prop[1], prop[2]))
                    v = _norm((prop[4], prop[5], prop[6]))
                    hw = float(prop[3]) * 0.5
                    hh = float(prop[7]) * 0.5
                    c1 = _point3d(x + hw * u[0] + hh * v[0], y + hw * u[1] + hh * v[1], z + hw * u[2] + hh * v[2])
                    c2 = _point3d(x + hw * u[0] - hh * v[0], y + hw * u[1] - hh * v[1], z + hw * u[2] - hh * v[2])
                    c3 = _point3d(x - hw * u[0] - hh * v[0], y - hw * u[1] - hh * v[1], z - hw * u[2] - hh * v[2])
                    c4 = _point3d(x - hw * u[0] + hh * v[0], y - hw * u[1] + hh * v[1], z - hw * u[2] + hh * v[2])
                    points.add(c1); points.add(c2)
                    points.add(c2); points.add(c3)
                    points.add(c3); points.add(c4)
                    points.add(c4); points.add(c1)
                elif ptype == 2 and len(prop) >= 1:
                    radius = max(float(prop[0]), 1e-6)
                    u, v = _orthonormal_basis((dx, dy, dz))
                    seg = 24
                    prev = None
                    for i in range(seg + 1):
                        t = (2.0 * math.pi * i) / seg
                        px = x + radius * (math.cos(t) * u[0] + math.sin(t) * v[0])
                        py = y + radius * (math.cos(t) * u[1] + math.sin(t) * v[1])
                        pz = z + radius * (math.cos(t) * u[2] + math.sin(t) * v[2])
                        cur = _point3d(px, py, pz)
                        if prev is not None:
                            points.add(prev)
                            points.add(cur)
                        prev = cur
        if points.count >= 2:
            group.addLines(points)
    except Exception:
        pass


def clear_kst_weakest_constraint_arrows(app):
    """Remove only the per-constraint weakest-motion arrow overlay."""
    try:
        _clear_graphics_group(app, _KST_WEAKEST_CONSTRAINTS_GROUP_ID)
    except Exception:
        pass


def draw_constraint_weakest_arrows(app, weakest_arrows):
    """
    Draw one weakest-resistance motion arrow per constraint.

    weakest_arrows: list of dicts:
      - location: [x,y,z] (mm)
      - direction: [dx,dy,dz] (will be normalized)
      - strength: float (used for color + length scaling)
    """
    if not app or not weakest_arrows:
        return
    try:
        # Fusion's embedded Python often does not ship with numpy.
        # Keep this function pure-Python so arrows can always render.
        strengths: list[float] = []
        for a in weakest_arrows:
            try:
                v = float(a.get("strength", 0.0))
            except Exception:
                v = 0.0
            strengths.append(v)

        valid = [v for v in strengths if math.isfinite(v)]
        if not valid:
            strength_min, strength_max = 0.0, 1.0
        else:
            strength_min = float(min(valid))
            strength_max = float(max(valid))
        span = (strength_max - strength_min) or 1.0

        group = _get_or_create_graphics_group(app, _KST_WEAKEST_CONSTRAINTS_GROUP_ID)
        if not group:
            return

        for a in weakest_arrows:
            loc = a.get("location") or [0.0, 0.0, 0.0]
            dir_vec = a.get("direction") or [0.0, 0.0, 1.0]
            strength = a.get("strength", 0.0)
            try:
                strength_f = float(strength)
            except Exception:
                strength_f = 0.0

            x0, y0, z0 = float(loc[0]), float(loc[1]), float(loc[2])
            dx, dy, dz = float(dir_vec[0]), float(dir_vec[1]), float(dir_vec[2])
            n = math.sqrt(dx * dx + dy * dy + dz * dz)
            if n < 1e-12:
                continue
            dx, dy, dz = dx / n, dy / n, dz / n

            t = (strength_f - strength_min) / span
            # Map t in [0,1] if possible; clamp anyway to keep colors stable.
            t = max(0.0, min(1.0, float(t)))
            length = _WEAKEST_ARROW_BASE_LEN * (0.5 + 0.5 * t)

            p1 = _point3d(x0, y0, z0)
            p2 = _point3d(x0 + dx * length, y0 + dy * length, z0 + dz * length)
            points = adsk.core.ObjectCollection.create()
            points.add(p1)
            points.add(p2)
            lines_obj = group.addLines(points)
            try:
                # Weak -> red, Strong -> blue (matches existing weakest-motion styling).
                r, g, b = 1.0 - t, 0.0, 0.5 + 0.5 * t
                lines_obj.color = adsk.core.Color.create(
                    int(r * 255), int(g * 255), int(b * 255), 255
                )
            except Exception:
                pass
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
        group = _get_or_create_graphics_group(app, _KST_WEAKEST_MOTIONS_GROUP_ID)
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
                lines_obj.color = adsk.core.Color.create(
                    int(r * 255), int(g * 255), int(b * 255), 255
                )
            except Exception:
                pass
    except Exception:
        pass
