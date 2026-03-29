#!/usr/bin/env python3
"""
Run KST optimization from a generic JSON candidate matrix.

Usage:
  python scripts/run_wizard_optimization.py <input_json> [output_txt]

Candidate matrix entries may include:
  - constraint_index: 1-based index within the constraint type (required)
  - constraint_type: optional "point" | "pin" | "line" | "plane" (default: point contacts only)
  - candidates: list of rows matching the constraint layout (see docs/GENERIC_INPUT_FORMAT.md)
"""

from __future__ import annotations

import json
import sys
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


def _normalize_constraint_type(raw: Any) -> str:
    if raw is None:
        return "point"
    s = str(raw).strip().lower()
    if s in ("point", "cp", "point_contact"):
        return "point"
    if s in ("pin", "cpin"):
        return "pin"
    if s in ("line", "clin"):
        return "line"
    if s in ("plane", "cpln"):
        return "plane"
    raise ValueError(f"Unknown constraint_type: {raw!r}")


def _apply_candidate(
    cs,
    constraint_type: str,
    idx_1based: int,
    cand: list[float],
    np,
) -> None:
    """Replace one constraint in-place (idx is 1-based within that type)."""
    from kst_rating_tool.constraints import LineConstraint, PinConstraint, PlaneConstraint, PointConstraint

    k = idx_1based - 1
    if k < 0:
        raise ValueError("constraint_index must be >= 1")

    if constraint_type == "point":
        if len(cand) < 6:
            raise ValueError("point candidate row needs at least 6 values [Px,Py,Pz,Nx,Ny,Nz]")
        if k >= len(cs.points):
            raise IndexError(f"point constraint_index {idx_1based} out of range (have {len(cs.points)} points)")
        cs.points[k] = PointConstraint(
            position=np.array(cand[0:3], dtype=float),
            normal=np.array(cand[3:6], dtype=float),
        )
        return

    if constraint_type == "pin":
        if len(cand) < 6:
            raise ValueError("pin candidate row needs at least 6 values [x,y,z,ax,ay,az]")
        if k >= len(cs.pins):
            raise IndexError(f"pin constraint_index {idx_1based} out of range (have {len(cs.pins)} pins)")
        cs.pins[k] = PinConstraint(
            center=np.array(cand[0:3], dtype=float),
            axis=np.array(cand[3:6], dtype=float),
        )
        return

    if constraint_type == "line":
        if len(cand) < 10:
            raise ValueError("line candidate row needs at least 10 values [m,l,n,length]")
        if k >= len(cs.lines):
            raise IndexError(f"line constraint_index {idx_1based} out of range (have {len(cs.lines)} lines)")
        cs.lines[k] = LineConstraint(
            midpoint=np.array(cand[0:3], dtype=float),
            line_dir=np.array(cand[3:6], dtype=float),
            constraint_dir=np.array(cand[6:9], dtype=float),
            length=float(cand[9]),
        )
        return

    if constraint_type == "plane":
        if len(cand) < 7:
            raise ValueError("plane candidate row needs at least 7 values [px,py,pz,nx,ny,nz,type,...prop]")
        if k >= len(cs.planes):
            raise IndexError(f"plane constraint_index {idx_1based} out of range (have {len(cs.planes)} planes)")
        cs.planes[k] = PlaneConstraint(
            midpoint=np.array(cand[0:3], dtype=float),
            normal=np.array(cand[3:6], dtype=float),
            type=int(cand[6]),
            prop=np.array(cand[7:], dtype=float),
        )
        return

    raise ValueError(f"internal: bad constraint_type {constraint_type!r}")


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

    import numpy as np
    from kst_rating_tool import analyze_constraints

    payload = json.loads(in_path.read_text(encoding="utf-8"))
    analysis_input = payload.get("analysis_input", payload)
    opt = payload.get("optimization", {})
    cmat = opt.get("candidate_matrix", [])
    if not cmat:
        print("Missing optimization.candidate_matrix", file=sys.stderr)
        return 1
    first = cmat[0]
    cp_idx = int(first.get("constraint_index", 0))
    candidates = first.get("candidates", [])
    if cp_idx <= 0 or not candidates:
        print("candidate_matrix must include constraint_index and non-empty candidates", file=sys.stderr)
        return 1

    raw_type = first.get("constraint_type")
    if raw_type is None:
        # Backward compatibility: omitting constraint_type implies point contacts only
        cs_probe = _load_constraints_from_analysis_input(analysis_input)
        n_points = len(cs_probe.points)
        if cp_idx > n_points:
            print(
                "When constraint_type is omitted, constraint_index counts point contacts only. "
                f"Use constraint_type \"pin\"|\"line\"|\"plane\" for non-point constraints "
                f"(have {n_points} points, got index {cp_idx}).",
                file=sys.stderr,
            )
            return 1
        constraint_type = "point"
    else:
        try:
            constraint_type = _normalize_constraint_type(raw_type)
        except ValueError as e:
            print(str(e), file=sys.stderr)
            return 1

    rows: list[tuple[int, float, float, float, float]] = []
    for i, cand in enumerate(candidates, start=1):
        if not isinstance(cand, (list, tuple)):
            continue
        cand_list = [float(x) for x in cand]
        try:
            cs = _load_constraints_from_analysis_input(analysis_input)
            _apply_candidate(cs, constraint_type, cp_idx, cand_list, np)
        except (ValueError, IndexError) as e:
            print(f"Candidate {i}: {e}", file=sys.stderr)
            return 1
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
