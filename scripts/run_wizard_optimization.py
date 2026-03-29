#!/usr/bin/env python3
"""
Run KST optimization from a generic JSON candidate matrix.

Usage:
  python scripts/run_wizard_optimization.py <input_json> [output_txt]
"""

from __future__ import annotations

import json
import sys
from itertools import product
from pathlib import Path
from typing import Any


def _load_constraints_from_analysis_input(data: dict):
    import numpy as np
    from kst_rating_tool import ConstraintSet, PointConstraint, PinConstraint, LineConstraint, PlaneConstraint

    cs = ConstraintSet()
    for row in data.get("point_contacts", []) or []:
        if len(row) >= 6:
            cs.points.append(PointConstraint(np.array(row[0:3], dtype=float), np.array(row[3:6], dtype=float)))
    for row in data.get("pins", []) or []:
        if len(row) >= 6:
            cs.pins.append(PinConstraint(np.array(row[0:3], dtype=float), np.array(row[3:6], dtype=float)))
    for row in data.get("lines", []) or []:
        if len(row) >= 10:
            cs.lines.append(
                LineConstraint(
                    np.array(row[0:3], dtype=float),
                    np.array(row[3:6], dtype=float),
                    np.array(row[6:9], dtype=float),
                    float(row[9]),
                )
            )
    for row in data.get("planes", []) or []:
        if len(row) >= 7:
            cs.planes.append(
                PlaneConstraint(
                    np.array(row[0:3], dtype=float),
                    np.array(row[3:6], dtype=float),
                    int(row[6]),
                    np.array(row[7:], dtype=float),
                )
            )
    return cs


def _constraint_counts(cs) -> dict[str, int]:
    return {
        "point": len(cs.points),
        "pin": len(cs.pins),
        "line": len(cs.lines),
        "plane": len(cs.planes),
    }


def _global_to_typed_index(global_idx: int, counts: dict[str, int]) -> tuple[str, int]:
    if global_idx <= 0:
        raise ValueError(f"constraint_index must be >= 1, got {global_idx}")
    rem = global_idx
    for kind in ("point", "pin", "line", "plane"):
        n = counts[kind]
        if rem <= n:
            return kind, rem
        rem -= n
    total = sum(counts.values())
    raise ValueError(f"constraint_index {global_idx} is out of range (total constraints: {total})")


def _normalize_type_name(value: Any) -> str:
    t = str(value or "").strip().lower()
    if t in ("point", "points", "cp"):
        return "point"
    if t in ("pin", "pins", "cpin"):
        return "pin"
    if t in ("line", "lines", "clin"):
        return "line"
    if t in ("plane", "planes", "cpln"):
        return "plane"
    return ""


def _build_modified_index_map(modified: list[dict], counts: dict[str, int]) -> dict[int, tuple[str, int]]:
    mapping: dict[int, tuple[str, int]] = {}
    for row in modified:
        ctype = _normalize_type_name(row.get("type"))
        idx = row.get("index")
        if ctype and isinstance(idx, int) and idx >= 1:
            if idx <= counts.get(ctype, 0):
                offset = 0
                if ctype == "pin":
                    offset = counts["point"]
                elif ctype == "line":
                    offset = counts["point"] + counts["pin"]
                elif ctype == "plane":
                    offset = counts["point"] + counts["pin"] + counts["line"]
                mapping[offset + idx] = (ctype, idx)
    return mapping


def _resolve_candidate_target(
    entry: dict,
    counts: dict[str, int],
    modified_map: dict[int, tuple[str, int]],
    modified: list[dict],
) -> tuple[str, int]:
    ctype = _normalize_type_name(entry.get("type"))
    idx = entry.get("index")
    if ctype and isinstance(idx, int) and idx >= 1:
        if idx > counts.get(ctype, 0):
            raise ValueError(f"{ctype} index {idx} is out of range ({counts.get(ctype, 0)} available)")
        return ctype, idx

    global_idx = int(entry.get("constraint_index", 0) or 0)
    if global_idx > 0:
        if global_idx in modified_map:
            return modified_map[global_idx]
        return _global_to_typed_index(global_idx, counts)

    if len(modified) == 1:
        row = modified[0]
        t = _normalize_type_name(row.get("type"))
        i = int(row.get("index", 0) or 0)
        if t and i >= 1:
            return t, i
    raise ValueError("Unable to resolve candidate target; provide type+index or constraint_index")


def _normalize_candidate_row(raw: Any, cs_base, ctype: str, idx: int) -> list[float]:
    import numpy as np

    vals = [float(v) for v in (raw or [])]
    if ctype == "point":
        if len(vals) == 6:
            return vals
        if len(vals) == 3:
            base = cs_base.points[idx - 1]
            return vals + [float(base.normal[0]), float(base.normal[1]), float(base.normal[2])]
        raise ValueError(f"Point candidates must have 3 or 6 values, got {len(vals)}")
    if ctype == "pin":
        if len(vals) == 6:
            return vals
        if len(vals) == 3:
            base = cs_base.pins[idx - 1]
            return vals + [float(base.axis[0]), float(base.axis[1]), float(base.axis[2])]
        raise ValueError(f"Pin candidates must have 3 or 6 values, got {len(vals)}")
    if ctype == "line":
        if len(vals) == 10:
            return vals
        if len(vals) == 7:
            base = cs_base.lines[idx - 1]
            return vals + [float(base.constraint_dir[0]), float(base.constraint_dir[1]), float(base.constraint_dir[2])]
        raise ValueError(f"Line candidates must have 7 or 10 values, got {len(vals)}")
    if ctype == "plane":
        if len(vals) >= 7:
            return vals
        base = cs_base.planes[idx - 1]
        if len(vals) == 6:
            return vals + [float(base.type)] + [float(x) for x in np.asarray(base.prop, dtype=float).reshape(-1)]
        raise ValueError(f"Plane candidates must have at least 7 values, got {len(vals)}")
    raise ValueError(f"Unsupported constraint type: {ctype}")


def _apply_candidate_to_constraints(cs, ctype: str, idx: int, cand: list[float]) -> None:
    import numpy as np
    from kst_rating_tool.constraints import PointConstraint, PinConstraint, LineConstraint, PlaneConstraint

    if ctype == "point":
        cs.points[idx - 1] = PointConstraint(position=np.array(cand[0:3], dtype=float), normal=np.array(cand[3:6], dtype=float))
        return
    if ctype == "pin":
        cs.pins[idx - 1] = PinConstraint(center=np.array(cand[0:3], dtype=float), axis=np.array(cand[3:6], dtype=float))
        return
    if ctype == "line":
        cs.lines[idx - 1] = LineConstraint(
            midpoint=np.array(cand[0:3], dtype=float),
            line_dir=np.array(cand[3:6], dtype=float),
            constraint_dir=np.array(cand[6:9], dtype=float),
            length=float(cand[9]),
        )
        return
    if ctype == "plane":
        cs.planes[idx - 1] = PlaneConstraint(
            midpoint=np.array(cand[0:3], dtype=float),
            normal=np.array(cand[3:6], dtype=float),
            type=int(cand[6]),
            prop=np.array(cand[7:], dtype=float),
        )
        return
    raise ValueError(f"Unsupported constraint type: {ctype}")


def main(argv: list[str]) -> int:
    if len(argv) < 2 or len(argv) > 3:
        print("Usage: python scripts/run_wizard_optimization.py <input_json> [output_txt]", file=sys.stderr)
        return 1

    in_path = Path(argv[1]).resolve()
    out_path = Path(argv[2]).resolve() if len(argv) == 3 else in_path.with_name("results_wizard_optim.txt")
    if not in_path.is_file():
        print(f"Input JSON not found: {in_path}", file=sys.stderr)
        return 1

    repo_root = Path(__file__).resolve().parent.parent
    src_dir = repo_root / "src"
    if str(src_dir) not in sys.path:
        sys.path.insert(0, str(src_dir))

    from kst_rating_tool import analyze_constraints

    payload = json.loads(in_path.read_text(encoding="utf-8"))
    analysis_input = payload.get("analysis_input", payload)
    opt = payload.get("optimization", {})
    modified = opt.get("modified_constraints", []) or []
    cmat = opt.get("candidate_matrix", [])
    if not cmat:
        print("Missing optimization.candidate_matrix", file=sys.stderr)
        return 1

    cs_base = _load_constraints_from_analysis_input(analysis_input)
    counts = _constraint_counts(cs_base)
    modified_map = _build_modified_index_map(modified, counts)

    candidate_sets: list[tuple[tuple[str, int], list[list[float]]]] = []
    for entry in cmat:
        if not isinstance(entry, dict):
            continue
        target = _resolve_candidate_target(entry, counts, modified_map, modified)
        raw_candidates = entry.get("candidates", [])
        if not raw_candidates:
            raise ValueError(f"No candidates provided for {target[0]} index {target[1]}")
        normalized = [_normalize_candidate_row(c, cs_base, target[0], target[1]) for c in raw_candidates]
        candidate_sets.append((target, normalized))
    if not candidate_sets:
        print("candidate_matrix must include at least one non-empty candidates list", file=sys.stderr)
        return 1

    rows: list[tuple[int, float, float, float, float]] = []
    all_candidates = [cand_list for _, cand_list in candidate_sets]
    for i, combo in enumerate(product(*all_candidates), start=1):
        cs = _load_constraints_from_analysis_input(analysis_input)
        for (target, _), cand in zip(candidate_sets, combo):
            _apply_candidate_to_constraints(cs, target[0], target[1], cand)
        rating = analyze_constraints(cs)
        rows.append((i, float(rating.WTR), float(rating.MRR), float(rating.MTR), float(rating.TOR)))

    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8") as f:
        f.write("candidate\tWTR\tMRR\tMTR\tTOR\n")
        for idx, wtr, mrr, mtr, tor in rows:
            f.write(f"{idx}\t{wtr:.10g}\t{mrr:.10g}\t{mtr:.10g}\t{tor:.10g}\n")
    print(f"Wrote {out_path} ({len(rows)} candidates)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
