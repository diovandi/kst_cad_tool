#!/usr/bin/env python3
"""
Collect Python vs Octave results for all cases, write raw numbers to CSV,
and generate deviation visualizations.

Usage:
  python scripts/visualize_octave_python.py [--run]

  --run   Run Python and Octave for all 21 cases first (like compare all).
          If omitted, uses existing results_python_*.txt and results_octave_*.txt.

Output:
  - docs/octave_python_comparison_raw.csv   Raw numbers (case, WTR/MRR/MTR/TOR Python & Octave, abs/rel diff)
  - docs/figures/octave_python_comparison_*.png   Graphs (bars, scatter, deviation)
"""

from __future__ import annotations

import argparse
import csv
import subprocess
import sys
from pathlib import Path

import numpy as np

# Reuse case list and parsing from compare script
CASE_NAME_TO_NUM = {
    "case1a_chair_height": 1,
    "case1b_chair_height_angle": 2,
    "case2a_cube_scalability": 3,
    "case2b_cube_tradeoff": 4,
    "case3a_cover_leverage": 5,
    "case3b_cover_symmetry": 6,
    "case3c_cover_orient": 7,
    "case4a_endcap_tradeoff": 8,
    "case4b_endcap_circlinsrch": 9,
    "case5a_printer_4screws_orient": 10,
    "case5b_printer_4screws_line": 11,
    "case5c_printer_snap_orient": 12,
    "case5d_printer_snap_line": 13,
    "case5e_printer_partingline": 14,
    "case5f1_printer_line_size": 15,
    "case5f2_printer_sideline_size": 16,
    "case5g_printer_5d": 17,
    "case5rev_a_printer_2screws": 18,
    "case5_printer_allscrews": 19,
    "case5rev_d_printer_remove2_bot_screw": 20,
    "case5rev_b_printer_flat_partingline": 21,
}

METRICS = ["WTR", "MRR", "MTR", "TOR"]


def parse_result_file(path: Path) -> dict[str, float]:
    """Parse a results_*.txt file (tab-separated: WTR\tvalue)."""
    out: dict[str, float] = {}
    if not path.is_file():
        return out
    for line in path.read_text().strip().splitlines():
        line = line.strip()
        if not line:
            continue
        parts = line.split("\t")
        if len(parts) >= 2:
            try:
                out[parts[0].strip()] = float(parts[1].strip())
            except ValueError:
                pass
    return out


def run_all_cases(repo_root: Path) -> None:
    """Run Python and Octave for all 21 cases (quiet)."""
    for case_num in range(1, 22):
        case_name = next(k for k, v in CASE_NAME_TO_NUM.items() if v == case_num)
        # Python
        subprocess.run(
            [sys.executable, str(repo_root / "scripts" / "run_python_case.py"), str(case_num)],
            cwd=repo_root,
            capture_output=True,
            text=True,
            timeout=120,
            check=False,
        )
        # Octave
        stdin_input = None
        if case_num == 3:
            stdin_input = "1\n"
        elif case_num == 4:
            stdin_input = "7\n"
        elif case_num == 8:
            stdin_input = "0\n"
        subprocess.run(
            ["octave", "--no-gui", "run_case_batch.m", str(case_num)],
            cwd=repo_root / "matlab_script",
            capture_output=True,
            text=True,
            timeout=120,
            input=stdin_input,
            check=False,
        )


def collect_results(repo_root: Path) -> list[dict]:
    """Collect Python and Octave results for all cases; compute diffs."""
    rows = []
    for case_num in range(1, 22):
        case_name = next(k for k, v in CASE_NAME_TO_NUM.items() if v == case_num)
        py_path = repo_root / f"results_python_{case_name}.txt"
        oct_path = repo_root / "matlab_script" / f"results_octave_{case_name}.txt"
        py_vals = parse_result_file(py_path)
        oct_vals = parse_result_file(oct_path)
        row = {
            "case_num": case_num,
            "case_name": case_name,
            **{f"{m}_py": py_vals.get(m) for m in METRICS},
            **{f"{m}_oct": oct_vals.get(m) for m in METRICS},
        }
        for m in METRICS:
            p, o = py_vals.get(m), oct_vals.get(m)
            if p is not None and o is not None:
                row[f"{m}_abs_diff"] = abs(p - o)
                row[f"{m}_rel_diff"] = (abs(p - o) / abs(o)) * 100.0 if o != 0 else (float("nan") if p != 0 else 0.0)
            else:
                row[f"{m}_abs_diff"] = None
                row[f"{m}_rel_diff"] = None
        rows.append(row)
    return rows


def write_raw_csv(rows: list[dict], out_path: Path) -> None:
    """Write raw numbers to CSV."""
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "case_num", "case_name",
        *[f"{m}_py" for m in METRICS],
        *[f"{m}_oct" for m in METRICS],
        *[f"{m}_abs_diff" for m in METRICS],
        *[f"{m}_rel_diff" for m in METRICS],
    ]
    with open(out_path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)
    print(f"Wrote raw numbers: {out_path}")


def plot_figures(rows: list[dict], figures_dir: Path) -> None:
    """Generate deviation graphs and save to figures_dir."""
    import matplotlib.pyplot as plt

    figures_dir.mkdir(parents=True, exist_ok=True)
    case_nums = [r["case_num"] for r in rows]
    x = np.arange(len(case_nums))
    width = 0.35

    # --- 1. Grouped bar: Python vs Octave per metric (4 subplots) ---
    fig, axes = plt.subplots(2, 2, figsize=(14, 10))
    axes = axes.flatten()
    for mi, metric in enumerate(METRICS):
        ax = axes[mi]
        py_vals = [r.get(f"{metric}_py") for r in rows]
        oct_vals = [r.get(f"{metric}_oct") for r in rows]
        py_vals = [v if v is not None else np.nan for v in py_vals]
        oct_vals = [v if v is not None else np.nan for v in oct_vals]
        bars1 = ax.bar(x - width / 2, py_vals, width, label="Python", color="steelblue", alpha=0.9)
        bars2 = ax.bar(x + width / 2, oct_vals, width, label="Octave", color="coral", alpha=0.9)
        ax.set_ylabel(metric)
        ax.set_xlabel("Case number")
        ax.set_title(f"{metric}: Python vs Octave")
        ax.set_xticks(x)
        ax.set_xticklabels(case_nums)
        ax.legend(loc="upper right", fontsize=8)
        ax.grid(axis="y", alpha=0.3)
    plt.tight_layout()
    out = figures_dir / "octave_python_comparison_bars.png"
    fig.savefig(out, dpi=150)
    plt.close(fig)
    print(f"Saved: {out}")

    # --- 2. Relative deviation (%) per case per metric (bar) ---
    fig, ax = plt.subplots(figsize=(14, 6))
    rel = {m: [] for m in METRICS}
    for r in rows:
        for m in METRICS:
            v = r.get(f"{m}_rel_diff")
            rel[m].append(v if v is not None and np.isfinite(v) else 0.0)
    x = np.arange(len(case_nums))
    w = 0.2
    for i, m in enumerate(METRICS):
        offset = (i - 1.5) * w
        ax.bar(x + offset, rel[m], w, label=m)
    ax.set_xticks(x)
    ax.set_xticklabels(case_nums)
    ax.set_xlabel("Case number")
    ax.set_ylabel("Relative deviation (%)")
    ax.set_title("Relative deviation: (|Python − Octave| / |Octave|) × 100")
    ax.legend()
    ax.grid(axis="y", alpha=0.3)
    plt.tight_layout()
    out = figures_dir / "octave_python_deviation_rel.png"
    fig.savefig(out, dpi=150)
    plt.close(fig)
    print(f"Saved: {out}")

    # --- 3. Scatter: Python vs Octave (one subplot per metric) ---
    fig, axes = plt.subplots(2, 2, figsize=(10, 10))
    axes = axes.flatten()
    for mi, metric in enumerate(METRICS):
        ax = axes[mi]
        py_vals = [r.get(f"{metric}_py") for r in rows]
        oct_vals = [r.get(f"{metric}_oct") for r in rows]
        py_vals = np.array([v if v is not None else np.nan for v in py_vals])
        oct_vals = np.array([v if v is not None else np.nan for v in oct_vals])
        valid = np.isfinite(py_vals) & np.isfinite(oct_vals)
        ax.scatter(np.array(oct_vals)[valid], np.array(py_vals)[valid], alpha=0.7, s=40)
        lims = [
            min(np.nanmin(py_vals), np.nanmin(oct_vals)),
            max(np.nanmax(py_vals), np.nanmax(oct_vals)),
        ]
        if np.isfinite(lims).all():
            ax.plot(lims, lims, "k--", alpha=0.5, label="y=x")
        ax.set_xlabel(f"{metric} (Octave)")
        ax.set_ylabel(f"{metric} (Python)")
        ax.set_title(f"{metric}: Python vs Octave")
        ax.legend(loc="upper left", fontsize=8)
        ax.grid(True, alpha=0.3)
    plt.tight_layout()
    out = figures_dir / "octave_python_scatter.png"
    fig.savefig(out, dpi=150)
    plt.close(fig)
    print(f"Saved: {out}")

    # --- 4. Single summary: max relative deviation per case ---
    fig, ax = plt.subplots(figsize=(12, 5))
    max_rel = []
    for r in rows:
        vals = [r.get(f"{m}_rel_diff") for m in METRICS]
        vals = [v for v in vals if v is not None and np.isfinite(v)]
        max_rel.append(max(vals) if vals else 0.0)
    colors = ["green" if x <= 5 else "orange" if x <= 20 else "red" for x in max_rel]
    ax.bar(case_nums, max_rel, color=colors, alpha=0.8)
    ax.axhline(y=5, color="gray", linestyle="--", alpha=0.7, label="5%")
    ax.axhline(y=20, color="gray", linestyle=":", alpha=0.7, label="20%")
    ax.set_xlabel("Case number")
    ax.set_ylabel("Max relative deviation (%)")
    ax.set_title("Worst relative deviation across WTR, MRR, MTR, TOR per case")
    ax.legend(loc="upper right")
    ax.grid(axis="y", alpha=0.3)
    plt.tight_layout()
    out = figures_dir / "octave_python_max_deviation.png"
    fig.savefig(out, dpi=150)
    plt.close(fig)
    print(f"Saved: {out}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Visualize Python vs Octave comparison (raw CSV + graphs).")
    parser.add_argument("--run", action="store_true", help="Run Python and Octave for all 21 cases first.")
    args = parser.parse_args()
    repo_root = Path(__file__).resolve().parent.parent

    if args.run:
        print("Running all 21 cases (Python + Octave)...")
        run_all_cases(repo_root)
        print("Done running.\n")

    rows = collect_results(repo_root)
    docs = repo_root / "docs"
    raw_path = docs / "octave_python_comparison_raw.csv"
    write_raw_csv(rows, raw_path)

    figures_dir = docs / "figures"
    try:
        plot_figures(rows, figures_dir)
    except ImportError as e:
        print(f"Matplotlib not available: {e}", file=sys.stderr)
        return 1

    print("\nRaw numbers and figures are in docs/ and docs/figures/.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
