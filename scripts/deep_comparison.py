#!/usr/bin/env python3
"""
Deep four-way comparison: Thesis (Ch 10/11) vs MATLAB vs Octave vs Python.

Parses all _full.txt result files, loads thesis reference data, and produces
4-column comparison tables for metrics, counts, WTR motion, and CP table.
Classifies deviations: exact, within tolerance (atol=1e-3, rtol=5%),
significant (>5%), major (>20%). Writes docs/DEEP_COMPARISON.md.

Usage:
  python scripts/deep_comparison.py [case_name_or_number]... [--matlab] [--out docs/DEEP_COMPARISON.md]

To include MATLAB in the report, generate MATLAB result files first. From the
repository root you can run: python scripts/compare_octave_python.py <case> --full --matlab
for each case, or from matlab_script/: matlab -batch "cp_set=N; run('run_case_batch')"
for case numbers N (e.g. 1,3,4,5,8,10,14 for thesis cases).
"""

from __future__ import annotations

import math
import sys
from pathlib import Path
from typing import Any

# Import shared parser and thesis refs
if __name__ == "__main__":
    repo_root = Path(__file__).resolve().parent.parent
    if str(repo_root) not in sys.path:
        sys.path.insert(0, str(repo_root))
    if str(repo_root / "src") not in sys.path:
        sys.path.insert(0, str(repo_root / "src"))

from scripts.compare_octave_python import parse_full_result_file
from kst_rating_tool.reference_data import CASE_NUM_TO_NAME, THESIS_REF

ATOL = 1e-3
RTOL = 0.05

# Cases that have thesis reference (subset of CASE_NUM_TO_NAME)
THESIS_CASES = list(THESIS_REF.keys())

# Metric and count keys to compare
METRIC_KEYS = ["WTR", "MRR", "MTR", "TOR", "LAR_WTR", "LAR_MTR"]
COUNT_KEYS = ["total_combo", "combo_proc_count", "no_mot_half", "no_mot_unique"]
WTR_MOTION_LABELS = [
    "Om_x", "Om_y", "Om_z", "Mu_x", "Mu_y", "Mu_z",
    "Rho_x", "Rho_y", "Rho_z", "Pitch", "Total_Resistance",
]
CP_TABLE_COLS = ["Individual_Rating", "Active_Pct", "Best_Resistance_Pct"]


def _close(a: float, b: float, atol: float = ATOL, rtol: float = RTOL) -> bool:
    if b == 0:
        return abs(a) <= atol
    return abs(a - b) <= atol or abs(a - b) / abs(b) <= rtol


def _deviation_class(actual: float, ref: float) -> str:
    """Classify deviation: exact, within_tol, significant (>5%), major (>20%)."""
    if ref == 0:
        if abs(actual) <= ATOL:
            return "exact"
        return "major" if abs(actual) > 0.2 else "significant"
    rel = abs(actual - ref) / abs(ref)
    if rel <= 1e-9:
        return "exact"
    if rel <= RTOL:
        return "within_tol"
    if rel <= 0.20:
        return "significant"
    return "major"


def _fmt_val(v: float | int | None) -> str:
    if v is None:
        return "—"
    if isinstance(v, int):
        return str(v)
    return f"{v:.6g}"


def load_result_files(repo_root: Path, case_name: str, use_matlab: bool) -> dict[str, dict[str, Any] | None]:
    """Load thesis ref, MATLAB, Octave, Python data for one case. Missing file -> None."""
    out: dict[str, dict[str, Any] | None] = {}
    # Thesis: from THESIS_REF (convert to same shape as parse_full_result_file for comparison)
    ref = THESIS_REF.get(case_name)
    if ref:
        out["thesis"] = {
            "metrics": {k: ref[k] for k in METRIC_KEYS if k in ref},
            "counts": {k: ref[k] for k in COUNT_KEYS if k in ref},
            "wtr_motion": ref.get("wtr_motion") or [],
            "cp_table": ref.get("cp_table") or [],
        }
    else:
        out["thesis"] = None

    for label, prefix, rel_dir in [
        ("matlab", "results_matlab_", "matlab_script"),
        ("octave", "results_octave_", "matlab_script"),
        ("python", "results_python_", "results/python"),
    ]:
        if label == "matlab" and not use_matlab:
            out["matlab"] = None
            continue
        path = repo_root / rel_dir / f"{prefix}{case_name}_full.txt"
        if path.is_file():
            out[label] = parse_full_result_file(path)
        else:
            out[label] = None
    return out


def compare_one_value(
    thesis_v: float | int | None,
    matlab_v: float | int | None,
    octave_v: float | int | None,
    python_v: float | int | None,
    ref_name: str = "thesis",
) -> tuple[str, str]:
    """Return (status_str, deviation_class). ref_name is which column to use as reference for classification."""
    ref = thesis_v if ref_name == "thesis" else (matlab_v if ref_name == "matlab" else octave_v)
    vals = [thesis_v, matlab_v, octave_v, python_v]
    if ref is None:
        return "—", "—"
    ref_f = float(ref)
    classes = []
    for v in vals:
        if v is None:
            classes.append("—")
        else:
            classes.append(_deviation_class(float(v), ref_f))
    worst = "exact"
    for c in classes:
        if c == "major":
            worst = "major"
            break
        if c == "significant" and worst == "exact":
            worst = "significant"
        if c == "within_tol" and worst == "exact":
            worst = "within_tol"
    status = "OK" if worst in ("exact", "within_tol") else "DIFF"
    return status, worst


def build_case_report(
    case_name: str,
    case_num: int,
    data: dict[str, dict[str, Any] | None],
    use_matlab: bool,
) -> list[str]:
    """Build markdown lines for one case."""
    lines: list[str] = []
    ref = THESIS_REF.get(case_name)
    th = data.get("thesis")
    mat = data.get("matlab")
    oct = data.get("octave")
    py = data.get("python")

    lines.append(f"## Case {case_num}: {case_name}")
    lines.append("")
    if ref:
        lines.append(f"**Thesis:** {ref.get('source', '')} — {ref.get('notes', '')}")
    lines.append("")

    # Metrics table
    lines.append("### Metrics")
    lines.append("")
    lines.append("| Metric | Thesis | MATLAB | Octave | Python | Status |")
    lines.append("|--------|--------|--------|--------|--------|--------|")
    for key in METRIC_KEYS:
        th_v = th["metrics"].get(key) if th else None
        mat_v = mat["metrics"].get(key) if mat else None
        oct_v = oct["metrics"].get(key) if oct else None
        py_v = py["metrics"].get(key) if py else None
        if not use_matlab:
            mat_v = None
        status, _ = compare_one_value(th_v, mat_v, oct_v, py_v, ref_name="thesis")
        cells = [_fmt_val(th_v), _fmt_val(mat_v), _fmt_val(oct_v), _fmt_val(py_v)]
        if not use_matlab:
            cells[1] = "—"
        lines.append(f"| {key} | {cells[0]} | {cells[1]} | {cells[2]} | {cells[3]} | {status} |")
    lines.append("")

    # Counts table
    lines.append("### Counts")
    lines.append("")
    lines.append("| Count | Thesis | MATLAB | Octave | Python | Status |")
    lines.append("|-------|--------|--------|--------|--------|--------|")
    for key in COUNT_KEYS:
        th_v = th["counts"].get(key) if th else None
        mat_v = mat["counts"].get(key) if mat else None
        oct_v = oct["counts"].get(key) if oct else None
        py_v = py["counts"].get(key) if py else None
        if not use_matlab:
            mat_v = None
        status, _ = compare_one_value(th_v, mat_v, oct_v, py_v, ref_name="thesis")
        cells = [_fmt_val(th_v), _fmt_val(mat_v), _fmt_val(oct_v), _fmt_val(py_v)]
        if not use_matlab:
            cells[1] = "—"
        lines.append(f"| {key} | {cells[0]} | {cells[1]} | {cells[2]} | {cells[3]} | {status} |")
    lines.append("")

    # WTR Motion
    lines.append("### WTR Motion (11 parameters)")
    lines.append("")
    th_w = (th.get("wtr_motion") or []) if th else []
    mat_w = (mat.get("wtr_motion") or []) if mat else []
    oct_w = (oct.get("wtr_motion") or []) if oct else []
    py_w = (py.get("wtr_motion") or []) if py else []
    if not use_matlab:
        mat_w = []
    n = max(len(th_w), len(mat_w), len(oct_w), len(py_w), 11)
    lines.append("| Param | Thesis | MATLAB | Octave | Python | Status |")
    lines.append("|-------|--------|--------|--------|--------|--------|")
    for i in range(min(n, 11)):
        lab = WTR_MOTION_LABELS[i] if i < len(WTR_MOTION_LABELS) else f"[{i}]"
        th_v = th_w[i] if i < len(th_w) else None
        mat_v = mat_w[i] if mat_w and i < len(mat_w) else None
        oct_v = oct_w[i] if oct_w and i < len(oct_w) else None
        py_v = py_w[i] if py_w and i < len(py_w) else None
        if not use_matlab:
            mat_v = None
        status, _ = compare_one_value(th_v, mat_v, oct_v, py_v, ref_name="thesis")
        cells = [_fmt_val(th_v), _fmt_val(mat_v), _fmt_val(oct_v), _fmt_val(py_v)]
        if not use_matlab:
            cells[1] = "—"
        lines.append(f"| {lab} | {cells[0]} | {cells[1]} | {cells[2]} | {cells[3]} | {status} |")
    lines.append("")
    lines.append("*Note: Screw axis sign (e.g. ω vs -ω) can differ; same physical motion.*")
    lines.append("")

    # CP Table (sample or full depending on length)
    th_cp = (th.get("cp_table") or []) if th else []
    mat_cp = (mat.get("cp_table") or []) if mat else []
    oct_cp = (oct.get("cp_table") or []) if oct else []
    py_cp = (py.get("cp_table") or []) if py else []
    if not use_matlab:
        mat_cp = []
    ncp = max(len(th_cp), len(mat_cp), len(oct_cp), len(py_cp))
    if ncp > 0:
        lines.append("### CP Table")
        lines.append("")
        # Show first 10 rows and last 3 if many
        show_indices = list(range(min(10, ncp)))
        if ncp > 13:
            show_indices += list(range(ncp - 3, ncp))
        elif ncp > 10:
            show_indices += list(range(10, ncp))
        lines.append("| CP | Col | Thesis | MATLAB | Octave | Python | Status |")
        lines.append("|----|-----|--------|--------|--------|--------|--------|")
        for idx in show_indices:
            for col in CP_TABLE_COLS:
                th_v = th_cp[idx].get(col) if idx < len(th_cp) and th_cp[idx] else None
                mat_v = mat_cp[idx].get(col) if mat_cp and idx < len(mat_cp) else None
                oct_v = oct_cp[idx].get(col) if oct_cp and idx < len(oct_cp) else None
                py_v = py_cp[idx].get(col) if py_cp and idx < len(py_cp) else None
                if not use_matlab:
                    mat_v = None
                cp_id = th_cp[idx].get("CP", idx + 1) if idx < len(th_cp) else (mat_cp[idx].get("CP", idx + 1) if mat_cp and idx < len(mat_cp) else idx + 1)
                status, _ = compare_one_value(th_v, mat_v, oct_v, py_v, ref_name="thesis")
                cells = [_fmt_val(th_v), _fmt_val(mat_v), _fmt_val(oct_v), _fmt_val(py_v)]
                if not use_matlab:
                    cells[1] = "—"
                lines.append(f"| {cp_id} | {col} | {cells[0]} | {cells[1]} | {cells[2]} | {cells[3]} | {status} |")
        if ncp > 13:
            lines.append(f"| ... | ... | (*{ncp} rows total*) |")
        lines.append("")

    return lines


def build_summary_table(data_by_case: dict[str, dict[str, dict[str, Any] | None]], use_matlab: bool) -> list[str]:
    """Summary table: one row per case, columns Thesis/MATLAB/Octave/Python for WTR and status."""
    lines: list[str] = []
    lines.append("## Summary (WTR and overall status)")
    lines.append("")
    header = "| Case | Thesis WTR | MATLAB | Octave | Python | Notes |"
    if not use_matlab:
        header = "| Case | Thesis WTR | Octave | Python | Notes |"
    lines.append(header)
    sep = "|------|------------|--------|--------|--------|-------|"
    if not use_matlab:
        sep = "|------|------------|--------|--------|-------|"
    lines.append(sep)
    cases_in_report = [c for c in THESIS_CASES if c in data_by_case]
    for case_name in cases_in_report:
        data = data_by_case.get(case_name) or {}
        th = data.get("thesis")
        mat = data.get("matlab")
        oct = data.get("octave")
        py = data.get("python")
        th_wtr = th["metrics"].get("WTR") if th else None
        mat_wtr = mat["metrics"].get("WTR") if mat else None
        oct_wtr = oct["metrics"].get("WTR") if oct else None
        py_wtr = py["metrics"].get("WTR") if py else None
        if not use_matlab:
            mat_wtr = None
        th_s = _fmt_val(th_wtr)
        mat_s = _fmt_val(mat_wtr)
        oct_s = _fmt_val(oct_wtr)
        py_s = _fmt_val(py_wtr)
        notes = []
        if py_wtr is not None and th_wtr is not None and th_wtr != 0:
            rel = abs(py_wtr - th_wtr) / abs(th_wtr)
            if rel > 0.20:
                notes.append("Python major WTR diff")
            elif rel > RTOL:
                notes.append("Python WTR diff")
        if not notes:
            notes.append("—")
        if use_matlab:
            lines.append(f"| {case_name} | {th_s} | {mat_s} | {oct_s} | {py_s} | {notes[0]} |")
        else:
            lines.append(f"| {case_name} | {th_s} | {oct_s} | {py_s} | {notes[0]} |")
    lines.append("")
    return lines


def build_executive_summary(data_by_case: dict[str, dict[str, dict[str, Any] | None]], use_matlab: bool) -> list[str]:
    """Executive summary: agreement vs thesis and Python divergence."""
    lines: list[str] = []
    lines.append("## Executive summary")
    lines.append("")
    match_thesis: list[str] = []
    python_divergence: list[str] = []
    cases_in_report = [c for c in THESIS_CASES if c in data_by_case]
    for case_name in cases_in_report:
        data = data_by_case.get(case_name) or {}
        th = data.get("thesis")
        oct = data.get("octave")
        py = data.get("python")
        if not th:
            continue
        th_wtr = th["metrics"].get("WTR")
        oct_wtr = oct["metrics"].get("WTR") if oct else None
        py_wtr = py["metrics"].get("WTR") if py else None
        oct_ok = _close(oct_wtr, th_wtr) if (oct_wtr is not None and th_wtr is not None) else False
        py_ok = _close(py_wtr, th_wtr) if (py_wtr is not None and th_wtr is not None) else False
        if oct_ok:
            match_thesis.append(case_name)
        if py_wtr is not None and th_wtr is not None and th_wtr != 0:
            rel = abs(py_wtr - th_wtr) / abs(th_wtr)
            if rel > RTOL:
                python_divergence.append(f"{case_name} (WTR {py_wtr:.4g} vs thesis {th_wtr:.4g})")

    total_cases = len(cases_in_report)
    lines.append("- **MATLAB/Octave vs thesis:** " + (f"{len(match_thesis)}/{total_cases} cases match (WTR within 5%): " + ", ".join(match_thesis) if match_thesis else "No result files."))
    lines.append("- **Python vs thesis:** " + (f"Divergence (WTR >5%) in: " + "; ".join(python_divergence) if python_divergence else "All cases within tolerance."))
    lines.append("")
    return lines


def build_root_cause_section() -> list[str]:
    """Short root cause analysis for known Python divergences."""
    lines: list[str] = []
    lines.append("## Root cause notes (Python vs MATLAB/Octave)")
    lines.append("")
    lines.append("- **Cases 1–7, 21:** Point-only or simple geometry; Python matches MATLAB/Octave within tolerance.")
    lines.append("- **Case 8 (endcap):** Combo order and duplicate-motion resolution differ; Python can get different WTR motion and counts (e.g. total_combo 68380 vs 42504) depending on constraint set parsing.")
    lines.append("- **Cases 10–20 (printer):** Combo row order (`nchoosek` vs `itertools.combinations`) and which resistance row is kept for duplicate screw motions differ; Python often finds a different minimum (WTR) motion, so WTR and WTR motion diverge. Thesis/Ch 10 baseline matches MATLAB/Octave.")
    lines.append("")
    return lines


def main() -> int:
    repo_root = Path(__file__).resolve().parent.parent

    # Argument parsing
    use_matlab = "--matlab" in sys.argv
    out_path_arg = None
    case_args = []

    i = 1
    while i < len(sys.argv):
        arg = sys.argv[i]
        if arg == "--matlab":
            pass
        elif arg == "--out":
            i += 1
            if i < len(sys.argv):
                out_path_arg = Path(sys.argv[i]).resolve()
        elif arg.lower() == "all":
            pass
        else:
            case_args.append(arg)
        i += 1

    if out_path_arg:
        out_path = out_path_arg
    else:
        out_path = repo_root / "docs" / "DEEP_COMPARISON.md"

    # Determine which cases to run
    cases_to_run = []
    if not case_args:
        cases_to_run = THESIS_CASES
    else:
        for arg in case_args:
            name = None
            if arg.isdigit():
                n = int(arg)
                if 1 <= n <= 21:
                    name = CASE_NUM_TO_NAME.get(n)
            else:
                arg_clean = arg.replace(".m", "").strip()
                # Find matching name
                if arg_clean in THESIS_REF:
                    name = arg_clean
                else:
                    # try by value in CASE_NUM_TO_NAME
                    for k, v in CASE_NUM_TO_NAME.items():
                        if v == arg_clean:
                            name = v
                            break

            if name and name in THESIS_REF:
                if name not in cases_to_run:
                    cases_to_run.append(name)
            else:
                print(f"Warning: Unknown or non-thesis case argument '{arg}', skipping.", file=sys.stderr)

    if not cases_to_run:
        print("No valid cases selected to run.", file=sys.stderr)
        return 1

    print(f"Running comparison for {len(cases_to_run)} cases...", file=sys.stderr)

    data_by_case: dict[str, dict[str, dict[str, Any] | None]] = {}
    case_reports: list[str] = []
    for case_name in cases_to_run:
        case_num = next((n for n, name in CASE_NUM_TO_NAME.items() if name == case_name), 0)
        data = load_result_files(repo_root, case_name, use_matlab)
        data_by_case[case_name] = data
        case_reports.extend(build_case_report(case_name, case_num, data, use_matlab))

    report: list[str] = []
    report.append("# Deep comparison: Thesis vs MATLAB vs Octave vs Python")
    report.append("")
    report.append("Reference: Rusli dissertation Ch 10 (Baseline Analysis) and Ch 11 (Design Optimization).")
    report.append("Tolerances: atol=1e-3, rtol=5%. Deviations: within_tol ≤5%, significant >5%, major >20%.")
    report.append("")
    report.extend(build_executive_summary(data_by_case, use_matlab))
    report.extend(case_reports)
    report.append("---")
    report.append("")
    report.extend(build_summary_table(data_by_case, use_matlab))
    report.extend(build_root_cause_section())

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text("\n".join(report), encoding="utf-8")
    print(f"Wrote {out_path}", file=sys.stderr)
    print("\n".join(report))
    return 0


if __name__ == "__main__":
    sys.exit(main())
