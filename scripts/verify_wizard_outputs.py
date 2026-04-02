#!/usr/bin/env python3
"""
Verify run_wizard_analysis outputs are self-consistent.

Reads the summary TSV (WTR/MRR/MTR/TOR) and the sibling *_detailed.json
(written next to the TSV) and checks that rating fields match exactly.

Usage:
  python scripts/verify_wizard_outputs.py <path/to/output.tsv>
Exit code 0 if OK, 1 otherwise.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print("Usage: python scripts/verify_wizard_outputs.py <output.tsv>", file=sys.stderr)
        return 1
    tsv_path = Path(argv[1]).resolve()
    if not tsv_path.is_file():
        print(f"Not found: {tsv_path}", file=sys.stderr)
        return 1
    json_path = tsv_path.with_name(tsv_path.stem + "_detailed.json")
    if not json_path.is_file():
        print(f"Not found: {json_path}", file=sys.stderr)
        return 1

    lines = [ln.strip() for ln in tsv_path.read_text(encoding="utf-8").splitlines() if ln.strip()]
    if len(lines) < 2 or lines[0].split("\t")[0] != "WTR":
        print("TSV missing header or data row", file=sys.stderr)
        return 1
    parts = lines[1].split("\t")
    if len(parts) < 4:
        print("TSV data row malformed", file=sys.stderr)
        return 1
    wtr, mrr, mtr, tor = (float(parts[i]) for i in range(4))

    data = json.loads(json_path.read_text(encoding="utf-8"))
    if not data.get("success"):
        print("JSON reports success=false", file=sys.stderr)
        return 1
    r = data["rating"]
    keys = ("WTR", "MRR", "MTR", "TOR")
    tsv_vals = (wtr, mrr, mtr, tor)
    for k, tv in zip(keys, tsv_vals):
        jv = float(r[k])
        if jv != tv and abs(jv - tv) > 1e-12 * max(1.0, abs(tv)):
            print(f"Mismatch {k}: tsv={tv!r} json={jv!r}", file=sys.stderr)
            return 1

    html_path = tsv_path.parent / f"Result - {tsv_path.stem}.html"
    if html_path.is_file():
        import re

        text = html_path.read_text(encoding="utf-8", errors="replace")
        pat = {
            "WTR": r"Weakest Total Resistance rating \(WTR\):\s*([0-9.eE+-]+)",
            "MRR": r"Mean Redundancy Ratio \(MRR\):\s*([0-9.eE+-]+)",
            "MTR": r"Mean Total Resistance Rating \(MTR\):\s*([0-9.eE+-]+)",
            "TOR": r"Trade Off Ratio \(TOR\):\s*([0-9.eE+-]+)",
        }
        for k, tv in zip(keys, tsv_vals):
            m = re.search(pat[k], text)
            if not m:
                print(f"HTML missing {k} summary line", file=sys.stderr)
                return 1
            hv = float(m.group(1))
            # HTML report rounds metrics (e.g. :.4f); allow small display error.
            if abs(hv - tv) > 5e-5 * max(1.0, abs(tv)):
                print(f"Mismatch {k}: tsv={tv!r} html={hv!r}", file=sys.stderr)
                return 1
        print(
            f"OK: TSV, {json_path.name}, and {html_path.name} report identical WTR/MRR/MTR/TOR."
        )
    else:
        print(f"OK: TSV and {json_path.name} ratings match (WTR/MRR/MTR/TOR).")

    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
