#!/usr/bin/env python3
"""
Run KST parametric constraint revision optimization (optim_main_rev).

Reads a JSON file describing which constraints to vary and how (using the
``modified_constraints``-style spec from GENERIC_INPUT_FORMAT.md), performs
a factorial grid search, and writes a TSV with one row per grid point.

Usage
-----
  python scripts/run_wizard_revision.py <revision.json> [output.tsv]
                                        [--metric TOR] [--plot]

Input JSON format
-----------------
{
  "analysis_input": {
    "point_contacts": [[x,y,z,nx,ny,nz], ...],
    "pins":           [[x,y,z,ax,ay,az], ...],
    "lines":          [[mx,my,mz,lx,ly,lz,nx,ny,nz,len], ...],
    "planes":         [[px,py,pz,nx,ny,nz,type,...prop], ...]
  },
  "optimization": {
    "no_step": 10,
    "groups": [
      {
        "type":     "point",        // constraint type: point|pin|line|plane
        "index":    6,              // 1-based index within that type
        "rev_type": "line",         // search type (see table below)
        "srch_spc": [ox,oy,oz, dx,dy,dz]   // search space parameters
      }
    ]
  }
}

rev_type strings and their MATLAB integer codes
------------------------------------------------
  none              -> 1  (skip)
  line              -> 2  (move along a line)
  curve_line        -> 3  (move along a curved path)
  plane             -> 4  (move in a plane)      [2D: uses 2 x-dimensions]
  orient_1d         -> 5  (rotate normal 1D)
  orient_2d         -> 6  (rotate normal 2D)     [2D: uses 2 x-dimensions]
  line_orient       -> 7  (line constraint orientation)
  resize_line       -> 8  (vary line length)
  resize_rect_plane -> 9  (vary rect plane dims) [2D: uses 2 x-dimensions]
  resize_circ_plane -> 10 (vary circ plane radius)

Output TSV columns
------------------
  x1 [x2 ...] | WTR | MRR | MTR | TOR | WTR_chg | MRR_chg | MTR_chg | TOR_chg
  (x_chg columns are % change vs baseline)
"""

from __future__ import annotations

import argparse
import itertools
import json
import sys
from pathlib import Path
from typing import Any

_REV_TYPE_MAP: dict[str, int] = {
    "none": 1,
    "line": 2,
    "curve_line": 3,
    "plane": 4,
    "orient_1d": 5,
    "orient_2d": 6,
    "line_orient": 7,
    "resize_line": 8,
    "resize_rect_plane": 9,
    "resize_circ_plane": 10,
}


def _setup_src() -> None:
    repo_root = Path(__file__).resolve().parent.parent
    src_dir = repo_root / "src"
    if str(src_dir) not in sys.path:
        sys.path.insert(0, str(src_dir))


def _load_constraints(analysis_input: dict):
    import numpy as np
    from kst_rating_tool import (
        ConstraintSet,
        LineConstraint,
        PinConstraint,
        PlaneConstraint,
        PointConstraint,
    )

    cs = ConstraintSet()
    for row in analysis_input.get("point_contacts", []) or []:
        if len(row) >= 6:
            cs.points.append(
                PointConstraint(np.array(row[0:3], dtype=float), np.array(row[3:6], dtype=float))
            )
    for row in analysis_input.get("pins", []) or []:
        if len(row) >= 6:
            cs.pins.append(
                PinConstraint(np.array(row[0:3], dtype=float), np.array(row[3:6], dtype=float))
            )
    for row in analysis_input.get("lines", []) or []:
        if len(row) >= 10:
            cs.lines.append(
                LineConstraint(
                    np.array(row[0:3], dtype=float),
                    np.array(row[3:6], dtype=float),
                    np.array(row[6:9], dtype=float),
                    float(row[9]),
                )
            )
    for row in analysis_input.get("planes", []) or []:
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


def _type_to_offset(cs, ctype: str) -> int:
    """Return the global 1-based offset for the first constraint of the given type."""
    n_pt = len(cs.points)
    n_pin = len(cs.pins)
    n_lin = len(cs.lines)
    if ctype == "point":
        return 0
    if ctype == "pin":
        return n_pt
    if ctype == "line":
        return n_pt + n_pin
    if ctype == "plane":
        return n_pt + n_pin + n_lin
    raise ValueError(f"Unknown constraint type: {ctype!r}. Expected point|pin|line|plane.")


def _parse_rev_type(value: Any) -> int:
    if isinstance(value, int):
        if value not in range(1, 11):
            raise ValueError(f"rev_type integer must be 1-10, got {value}")
        return value
    key = str(value).strip().lower().replace(" ", "_")
    if key not in _REV_TYPE_MAP:
        raise ValueError(
            f"Unknown rev_type {value!r}. Valid values: {', '.join(_REV_TYPE_MAP)}"
        )
    return _REV_TYPE_MAP[key]


def _build_revision_config(groups: list[dict], cs, np_mod):
    """Translate JSON groups into a RevisionConfig."""
    import numpy as np
    from kst_rating_tool.optimization import RevisionConfig

    grp_members = []
    grp_rev_type_list = []
    grp_srch_spc = []

    for i, grp in enumerate(groups):
        ctype = str(grp.get("type", "point")).strip().lower()
        idx_1based = int(grp.get("index", 1))
        rev_type_int = _parse_rev_type(grp.get("rev_type", "none"))
        srch_spc_raw = grp.get("srch_spc", [])

        # Convert (type, 1-based-within-type) -> global 1-based
        offset = _type_to_offset(cs, ctype)
        global_idx = offset + idx_1based
        total = cs.total_cp
        if global_idx < 1 or global_idx > total:
            raise ValueError(
                f"Group {i}: computed global index {global_idx} out of range "
                f"(total_cp={total}, type={ctype!r}, index={idx_1based})"
            )

        grp_members.append(np.array([global_idx], dtype=np.int_))
        grp_rev_type_list.append(rev_type_int)
        grp_srch_spc.append(np.array(srch_spc_raw, dtype=float))

    grp_rev_type = np.array(grp_rev_type_list, dtype=np.int_)
    return RevisionConfig(
        grp_members=grp_members,
        grp_rev_type=grp_rev_type,
        grp_srch_spc=grp_srch_spc,
    )


def _compute_no_dim(x_map) -> int:
    return int(x_map.ravel().max()) if x_map.size else 0


def _iter_grid(no_dim: int, no_step: int):
    """Yield (indices_tuple, x_vec) for every grid point."""
    import numpy as np
    a_vals = np.linspace(-1.0, 1.0, no_step + 1)
    for indices in itertools.product(range(no_step + 1), repeat=no_dim):
        x_vec = np.array([a_vals[i] for i in indices], dtype=float)
        yield indices, x_vec


def _rating_at(WTR_arr, MRR_arr, MTR_arr, TOR_arr, idx_tuple):
    """Index into any-dimensional rating arrays."""
    import numpy as np
    if WTR_arr.ndim == 1:
        i = idx_tuple[0]
        return float(WTR_arr[i]), float(MRR_arr[i]), float(MTR_arr[i]), float(TOR_arr[i])
    return (
        float(WTR_arr[idx_tuple]),
        float(MRR_arr[idx_tuple]),
        float(MTR_arr[idx_tuple]),
        float(TOR_arr[idx_tuple]),
    )


def main(argv: list[str]) -> int:
    _setup_src()

    parser = argparse.ArgumentParser(
        description="Parametric constraint revision optimization (optim_main_rev)."
    )
    parser.add_argument("input_json", help="Path to revision JSON (analysis_input + optimization.groups)")
    parser.add_argument("output_tsv", nargs="?", default=None, help="Output TSV path (default: next to input)")
    parser.add_argument("--metric", default="TOR", choices=["TOR", "WTR", "MRR", "MTR"],
                        help="Metric to report as primary (default: TOR)")
    parser.add_argument("--plot", action="store_true", help="Save response-surface plots alongside TSV")
    args = parser.parse_args(argv[1:])

    import numpy as np
    from kst_rating_tool import analyze_constraints_detailed
    from kst_rating_tool.optimization import optim_main_rev, optim_postproc, optim_postproc_plot

    input_path = Path(args.input_json).resolve()
    if not input_path.is_file():
        print(f"ERROR: Input JSON not found: {input_path}", file=sys.stderr)
        return 1

    try:
        with input_path.open() as f:
            data = json.load(f)
    except Exception as exc:
        print(f"ERROR: Failed to load JSON: {exc}", file=sys.stderr)
        return 1

    analysis_input = data.get("analysis_input") or data  # allow bare analysis JSON too
    optimization = data.get("optimization", {})
    groups = optimization.get("groups", [])
    no_step = int(optimization.get("no_step", 10))

    if not groups:
        print("ERROR: JSON must have optimization.groups with at least one entry.", file=sys.stderr)
        return 1

    try:
        cs = _load_constraints(analysis_input)
    except Exception as exc:
        print(f"ERROR: Failed to build ConstraintSet: {exc}", file=sys.stderr)
        return 1

    if cs.total_cp == 0:
        print("ERROR: No constraints found in analysis_input.", file=sys.stderr)
        return 1

    try:
        config = _build_revision_config(groups, cs, np)
    except Exception as exc:
        print(f"ERROR: Failed to build RevisionConfig: {exc}", file=sys.stderr)
        return 1

    print(f"Running baseline analysis ({cs.total_cp} constraints)...")
    try:
        baseline = analyze_constraints_detailed(cs)
    except Exception as exc:
        print(f"ERROR: Baseline analysis failed: {exc}", file=sys.stderr)
        return 1

    Rating_org = np.array([
        baseline.rating.WTR, baseline.rating.MRR,
        baseline.rating.MTR, baseline.rating.TOR,
    ])
    print(
        f"Baseline: WTR={Rating_org[0]:.4f}  MRR={Rating_org[1]:.4f}  "
        f"MTR={Rating_org[2]:.4f}  TOR={Rating_org[3]:.4f}"
    )

    n_inc = no_step + 1
    tot_it = n_inc ** max(1, len(groups))  # approximate; actual depends on no_dim
    printed = [0]

    def _progress(current: int, total: int) -> None:
        pct = 100.0 * current / max(total, 1)
        if current - printed[0] >= max(1, total // 10):
            print(f"  Revision grid: {current}/{total} ({pct:.0f}%)", flush=True)
            printed[0] = current

    print(f"Running revision search (no_step={no_step}, {len(groups)} group(s))...")
    try:
        WTR_all, MRR_all, MTR_all, TOR_all, x_map = optim_main_rev(
            baseline, config, no_step, progress_callback=_progress
        )
    except Exception as exc:
        print(f"ERROR: optim_main_rev failed: {exc}", file=sys.stderr)
        return 1

    no_dim = _compute_no_dim(x_map)
    if no_dim == 0:
        print("WARNING: no_dim=0, no revision parameters detected. Check rev_type != 'none'.")
        no_dim = 1

    # % change vs baseline
    def _pct(arr, base):
        with np.errstate(divide="ignore", invalid="ignore"):
            return np.where(base != 0, (arr - base) / base * 100, 0.0)

    WTR_chg = _pct(WTR_all, Rating_org[0])
    MRR_chg = _pct(MRR_all, Rating_org[1])
    MTR_chg = _pct(MTR_all, Rating_org[2])
    TOR_chg = _pct(TOR_all, Rating_org[3])

    # Post-process: find best point
    postproc = optim_postproc(
        no_step, no_dim,
        WTR_chg, MRR_chg, MTR_chg, TOR_chg,
        WTR_all, MRR_all, MTR_all, TOR_all,
    )

    # Determine output path
    if args.output_tsv:
        output_path = Path(args.output_tsv).resolve()
    else:
        output_path = input_path.with_name(input_path.stem + "_revision.tsv")
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Write TSV
    a_vals = np.linspace(-1.0, 1.0, n_inc)
    x_headers = "\t".join(f"x{k+1}" for k in range(no_dim))
    header = f"{x_headers}\tWTR\tMRR\tMTR\tTOR\tWTR_chg\tMRR_chg\tMTR_chg\tTOR_chg"

    with output_path.open("w", encoding="utf-8", newline="") as f:
        f.write(header + "\n")
        for idx_tuple, x_vec in _iter_grid(no_dim, no_step):
            wtr, mrr, mtr, tor = _rating_at(WTR_all, MRR_all, MTR_all, TOR_all, idx_tuple)
            wtr_c, mrr_c, mtr_c, tor_c = _rating_at(WTR_chg, MRR_chg, MTR_chg, TOR_chg, idx_tuple)
            x_cols = "\t".join(f"{v:.6f}" for v in x_vec)
            f.write(
                f"{x_cols}\t{wtr:.6f}\t{mrr:.6f}\t{mtr:.6f}\t{tor:.6f}"
                f"\t{wtr_c:.3f}\t{mrr_c:.3f}\t{mtr_c:.3f}\t{tor_c:.3f}\n"
            )

    print(f"\nWrote {(no_step + 1) ** no_dim} grid points to: {output_path}")

    # Report best point
    metric_key = args.metric
    best_idx_key = f"{metric_key}_max_idx"
    best_idx = postproc.get(best_idx_key)
    x_inc = postproc["x_inc"]
    if best_idx is not None:
        if no_dim == 1:
            best_x = [x_inc[int(best_idx)]]
            wtr_b, mrr_b, mtr_b, tor_b = _rating_at(WTR_all, MRR_all, MTR_all, TOR_all, (int(best_idx),))
        else:
            best_x = [x_inc[int(i)] for i in best_idx]
            wtr_b, mrr_b, mtr_b, tor_b = _rating_at(WTR_all, MRR_all, MTR_all, TOR_all, tuple(int(i) for i in best_idx))
        x_str = "  ".join(f"x{k+1}={v:.4f}" for k, v in enumerate(best_x))
        print(f"\nBest {metric_key}: {x_str}")
        print(f"  WTR={wtr_b:.4f}  MRR={mrr_b:.4f}  MTR={mtr_b:.4f}  TOR={tor_b:.4f}")
        # % changes at best
        if no_dim == 1:
            wtr_bc, mrr_bc, mtr_bc, tor_bc = _rating_at(WTR_chg, MRR_chg, MTR_chg, TOR_chg, (int(best_idx),))
        else:
            wtr_bc, mrr_bc, mtr_bc, tor_bc = _rating_at(WTR_chg, MRR_chg, MTR_chg, TOR_chg, tuple(int(i) for i in best_idx))
        print(
            f"  vs baseline: DWTR={wtr_bc:+.1f}%  DMRR={mrr_bc:+.1f}%  "
            f"DMTR={mtr_bc:+.1f}%  DTOR={tor_bc:+.1f}%"
        )

    # Optional plots
    if args.plot:
        try:
            optim_postproc_plot(
                no_step, no_dim,
                WTR_chg, MRR_chg, MTR_chg, TOR_chg,
                inputfile=input_path.stem,
                output_dir=output_path.parent,
            )
            print(f"Plots saved to: {output_path.parent}")
        except Exception as exc:
            print(f"WARNING: Plotting failed: {exc}", file=sys.stderr)

    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
