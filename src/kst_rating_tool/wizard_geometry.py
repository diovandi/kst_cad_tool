"""Geometry sanity checks for wizard JSON / ConstraintSet (Fusion and scripts)."""

from __future__ import annotations

from typing import List

from .constraints import ConstraintSet

# Meeting spec: very small contact features can destabilize optimization / rating.
MIN_RECOMMENDED_FEATURE_MM = 7.0


def geometry_size_warnings(cs: ConstraintSet, *, min_mm: float = MIN_RECOMMENDED_FEATURE_MM) -> List[str]:
    """Return human-readable warnings for line/plane sizes below *min_mm* (millimetres)."""
    msgs: List[str] = []
    for i, ln in enumerate(cs.lines, start=1):
        if ln.length < min_mm:
            msgs.append(
                f"Line constraint {i}: length {ln.length:.4g} mm is below recommended minimum {min_mm} mm."
            )
    for i, pl in enumerate(cs.planes, start=1):
        ptype = int(pl.type)
        prop = pl.prop
        if ptype == 1 and prop.size >= 8:
            try:
                xlen = float(prop[3])
                ylen = float(prop[7])
            except (TypeError, ValueError, IndexError):
                continue
            if min(xlen, ylen) < min_mm:
                msgs.append(
                    f"Plane constraint {i} (rectangular): in-plane sizes "
                    f"{xlen:.4g} x {ylen:.4g} mm — smallest side is below {min_mm} mm."
                )
        elif ptype == 2 and prop.size >= 1:
            try:
                r = float(prop[0])
            except (TypeError, ValueError):
                continue
            if 2.0 * r < min_mm:
                msgs.append(
                    f"Plane constraint {i} (circular): diameter {2.0 * r:.4g} mm is below recommended {min_mm} mm."
                )
    return msgs
