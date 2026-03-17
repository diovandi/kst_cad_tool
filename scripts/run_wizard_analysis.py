#!/usr/bin/env python3
"""
Run KST analysis for the Fusion 360 wizard input JSON.

Usage:
  python scripts/run_wizard_analysis.py <input_json> <output_txt>

This is used by the Fusion 360 add-in when Fusion's embedded Python does not
have numpy installed. It runs in your normal Python environment where the
`kst_rating_tool` package and its dependencies are available.
"""

from __future__ import annotations

import json
import logging
import sys
from pathlib import Path


def _setup_logger(output_path: Path) -> logging.Logger:
    """Configure a logger that writes to a sibling .log file next to the output txt."""
    log_path = output_path.with_suffix(".log")
    logger = logging.getLogger("kst_wizard")
    # Avoid duplicating handlers if main() is called multiple times in a process.
    if not logger.handlers:
        logger.setLevel(logging.DEBUG)
        handler = logging.FileHandler(log_path, encoding="utf-8")
        formatter = logging.Formatter(
            "%(asctime)s [%(levelname)s] %(message)s", datefmt="%Y-%m-%d %H:%M:%S"
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
    return logger


def main(argv: list[str]) -> int:
    if len(argv) != 3:
        print("Usage: python scripts/run_wizard_analysis.py <input_json> <output_txt>", file=sys.stderr)
        return 1

    input_path = Path(argv[1]).resolve()
    output_path = Path(argv[2]).resolve()

    logger = _setup_logger(output_path)
    logger.info("Starting wizard analysis")
    logger.info("Input JSON: %s", input_path)
    logger.info("Output txt: %s", output_path)

    if not input_path.is_file():
        msg = f"Input JSON not found: {input_path}"
        logger.error(msg)
        print(msg, file=sys.stderr)
        return 1

    repo_root = Path(__file__).resolve().parent.parent
    src_dir = repo_root / "src"
    if str(src_dir) not in sys.path:
        sys.path.insert(0, str(src_dir))

    import numpy as np  # type: ignore
    from kst_rating_tool import (
        analyze_constraints_detailed,
        ConstraintSet,
        PointConstraint,
        PinConstraint,
        LineConstraint,
        PlaneConstraint,
    )

    with input_path.open() as f:
        data = json.load(f)

    logger.debug("Raw JSON keys: %s", list(data.keys()))

    cs = ConstraintSet()
    pc = data.get("point_contacts", []) or []
    logger.info("point_contacts: %d", len(pc))
    for idx, row in enumerate(pc, start=1):
        if len(row) >= 6:
            pos = np.array(row[0:3], dtype=float)
            nrm = np.array(row[3:6], dtype=float)
            cs.points.append(PointConstraint(pos, nrm))
            logger.debug("CP%d pos=%s nrm=%s", idx, pos, nrm)

    pins = data.get("pins", []) or []
    logger.info("pins: %d", len(pins))
    for idx, row in enumerate(pins, start=1):
        if len(row) >= 6:
            center = np.array(row[0:3], dtype=float)
            axis = np.array(row[3:6], dtype=float)
            cs.pins.append(PinConstraint(center, axis))
            logger.debug("PIN%d center=%s axis=%s", idx, center, axis)

    lines = data.get("lines", []) or []
    logger.info("lines: %d", len(lines))
    for idx, row in enumerate(lines, start=1):
        if len(row) >= 10:
            midpoint = np.array(row[0:3], dtype=float)
            line_dir = np.array(row[3:6], dtype=float)
            constraint_dir = np.array(row[6:9], dtype=float)
            length = float(row[9])
            cs.lines.append(LineConstraint(midpoint, line_dir, constraint_dir, length))
            logger.debug(
                "LINE%d midpoint=%s line_dir=%s constraint_dir=%s length=%s",
                idx,
                midpoint,
                line_dir,
                constraint_dir,
                length,
            )

    planes = data.get("planes", []) or []
    logger.info("planes: %d", len(planes))
    for idx, row in enumerate(planes, start=1):
        if len(row) >= 7:
            midpoint = np.array(row[0:3], dtype=float)
            normal = np.array(row[3:6], dtype=float)
            ptype = int(row[6])
            prop = np.array(row[7:], dtype=float) if len(row) > 7 else np.array([], dtype=float)

            # Pre-validate plane properties to avoid cryptic IndexErrors later.
            if ptype == 1 and prop.size < 8:
                msg = (
                    f"Rectangular plane PLANE{idx} has prop size {prop.size}, "
                    "expected at least 8 values: "
                    "[xdir_x, xdir_y, xdir_z, xlen, ydir_x, ydir_y, ydir_z, ylen]"
                )
                logger.error(msg)
                print(msg, file=sys.stderr)
                return 1
            if ptype == 2 and prop.size < 1:
                msg = (
                    f"Circular plane PLANE{idx} has prop size {prop.size}, "
                    "expected at least 1 value: [radius]"
                )
                logger.error(msg)
                print(msg, file=sys.stderr)
                return 1

            cs.planes.append(PlaneConstraint(midpoint, normal, ptype, prop))
            logger.debug(
                "PLANE%d midpoint=%s normal=%s type=%d prop_size=%d prop=%s",
                idx,
                midpoint,
                normal,
                ptype,
                int(prop.size),
                prop,
            )

    if cs.total_cp == 0:
        msg = "Input JSON has no constraints (points, pins, lines, or planes)."
        logger.error(msg)
        print(msg, file=sys.stderr)
        return 1

    try:
        detailed = analyze_constraints_detailed(cs)
    except Exception as exc:
        logger.exception("analyze_constraints_detailed failed: %s", exc)
        print(f"KST analysis failed (see log for details): {exc}", file=sys.stderr)
        return 1
    rating = detailed.rating

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w") as f:
        f.write("WTR\tMRR\tMTR\tTOR\n")
        f.write("{}\t{}\t{}\t{}\n".format(rating.WTR, rating.MRR, rating.MTR, rating.TOR))

    logger.info(
        "Analysis complete: WTR=%.4f, MRR=%.4f, MTR=%.4f, TOR=%.4f",
        rating.WTR,
        rating.MRR,
        rating.MTR,
        rating.TOR,
    )
    print(f"Wrote {output_path} (WTR={rating.WTR:.4f}, MRR={rating.MRR:.4f}, MTR={rating.MTR:.4f}, TOR={rating.TOR:.4f})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))

