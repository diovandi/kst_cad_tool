"""
Reporting: HTML result file, table_mot, histogr.
Ported from result_open.m, result_close.m, report.m, table_mot.m, histogr.m.
"""
from __future__ import annotations

import time
from pathlib import Path
from typing import TextIO

import numpy as np

from .rating import RatingResults


def print_summary(results: RatingResults, file: TextIO | None = None) -> None:
    """Print a simple textual summary of rating metrics."""
    out = file or None
    print(f"WTR: {results.WTR:.4g}", file=out)
    print(f"MRR: {results.MRR:.4g}", file=out)
    print(f"MTR: {results.MTR:.4g}", file=out)
    print(f"TOR: {results.TOR:.4g}", file=out)


def result_open(inputfile: str, output_dir: Path | str | None = None) -> TextIO:
    """Open HTML result file for writing (port of result_open.m)."""
    path = Path(output_dir or ".") / f"Result - {inputfile}.html"
    f = open(path, "w", encoding="utf-8")
    f.write(f"<HEAD>\n<TITLE>\nResult file for {inputfile}\n</TITLE>\n\n")
    f.write("<STYLE TYPE=\"text/css\">\n<!--\nT1\n   {\n")
    f.write("font-family:sans-serif; \nfont-size:10pt;\n}\n-->\n</STYLE>\n")
    f.write("\n</HEAD>\n")
    f.write("<FONT SIZE=3 FACE=\"helvetica\">\n")
    return f


def result_close(
    result: TextIO,
    timestart: tuple[float, ...] | float | None = None,
) -> None:
    """Close HTML result file and write total time (port of result_close.m)."""
    if timestart is not None:
        elapsed = time.perf_counter() - (timestart[0] if isinstance(timestart, tuple) else timestart)
        total_min = int(elapsed // 60)
        total_sec = (elapsed % 60)
        result.write(f"<p>\nTotal analysis time: {total_min:5.0f} minutes {total_sec:2.0f} seconds \n<p>")
    result.write("\n</font>\n")
    result.close()


def table_mot(
    result: TextIO,
    mot_list: np.ndarray,
    TR: np.ndarray,
) -> None:
    """Write screw axis motion table to HTML (port of table_mot.m). mot_list (n,10), TR (n,)."""
    result.write("<TABLE BORDER=2>\n")
    result.write(
        "<b> <tr><th>Om(x)</th>  <th>Om(y)</th> <th>Om(z)</th> <th>Mu(x)</th> <th>Mu(y)</th> "
        "<th>Mu(z)</th> <th>Rho(x)</th><th>Rho(y)</th><th>Rho(z)</th> <th>Pitch</th>   "
        "<th>Total Resistance</th> <tr></b>\n"
    )
    TR = np.atleast_1d(TR)
    for i in range(mot_list.shape[0]):
        row = mot_list[i, :]
        result.write(
            f"<tr><td>{row[0]:7.4f}</td>  <td>{row[1]:7.4f}</td>  <td>{row[2]:7.4f}</td>  "
            f"<td>{row[3]:7.4f}</td>  <td>{row[4]:7.4f}</td>  <td>{row[5]:7.4f}</td>  "
            f"<td>{row[6]:7.4f}</td>  <td>{row[7]:7.4f}</td>  <td>{row[8]:7.4f}</td>  "
            f"<td>{row[9]:5.4f}</td>    "
        )
        tr_val = TR[i] if i < TR.size else 0.0
        result.write(f"<td>{tr_val:7.4f}</td></tr>\n")
    result.write("</TABLE>\n")


def write_report(
    result: TextIO,
    inputfile: str,
    rating: RatingResults,
    mot_all_uniq: np.ndarray,
    R_uniq: np.ndarray,
    total_cp: int,
    no_mot: int,
    combo: np.ndarray,
    combo_proc: np.ndarray,
) -> None:
    """Write full HTML report (port of report.m)."""
    result.write(f"<b>Input File: {inputfile} <p>\n\n</b>")
    WTR, MRR, MTR, TOR = rating.WTR, rating.MRR, rating.MTR, rating.TOR
    LAR_wtr = 1.0 / WTR if WTR > 0 and np.isfinite(WTR) else float("inf")
    LAR_mtr = 1.0 / MTR if MTR > 0 and np.isfinite(MTR) else float("inf")
    result.write(f"Weakest Total Resistance rating (WTR): {WTR:5.4f} (LAR: {LAR_wtr:6.3f})<br>\n")
    result.write(f"Mean Redundancy Ratio (MRR): {MRR:5.4f} <br>\n")
    result.write(f"Mean Total Resistance Rating (MTR): {MTR:5.4f} (LAR: {LAR_mtr:6.3f})<br>\n")
    result.write(f"Trade Off Ratio (TOR): {TOR:5.4f} <p>\n\n")

    Ri_uniq = rating.Ri
    rowsum = Ri_uniq.sum(axis=1)
    max_of_row = np.maximum(Ri_uniq.max(axis=1), 1e-12)
    best_cp = np.argmax(Ri_uniq, axis=1) + 1
    free_mot_idx = np.where(rowsum == 0)[0]
    free_mot = mot_all_uniq[free_mot_idx, :] if free_mot_idx.size else np.empty((0, 10), dtype=float)

    if free_mot.shape[0] > 0:
        result.write("<b>Unconstrained Motion: </b><br>\n")
        table_mot(result, free_mot, np.zeros(free_mot.shape[0], dtype=float))
        return

    result.write("<b>There is no unconstrained motion. </b><p>\n\n")
    WTR_idx_flat = np.where(rowsum >= rowsum.min() - 1e-9)[0]
    WTR_idx_org = WTR_idx_flat[0] if WTR_idx_flat.size else 0
    result.write("<p>\n<b>Weakest Constrained Motion (according to WTR): <br></b>\n")
    WTR_mot = mot_all_uniq[WTR_idx_org : WTR_idx_org + 1, :]
    TR_row = rowsum[WTR_idx_org : WTR_idx_org + 1]
    table_mot(result, WTR_mot, TR_row)

    n_col = Ri_uniq.shape[1]
    non_zero_cnt_in_col = np.count_nonzero(Ri_uniq, axis=0)
    cp_best_count = np.zeros(n_col, dtype=float)
    for i in range(n_col):
        cp_best_count[i] = np.sum(best_cp == (i + 1))
    with np.errstate(divide="ignore", invalid="ignore"):
        cp_indv_rat = np.where(non_zero_cnt_in_col > 0, Ri_uniq.sum(axis=0) / non_zero_cnt_in_col, 0.0)
    cp_active_pct = (non_zero_cnt_in_col / no_mot * 100) if no_mot > 0 else np.zeros(n_col)
    cp_best_pct = (cp_best_count / no_mot * 100) if no_mot > 0 else np.zeros(n_col)

    result.write("<p><TABLE BORDER=2>\n")
    result.write(
        "<b> <FONT SIZE=3 FACE=\"helvetica\"><tr><th>CP#</th>  <th>Individual Rating</th> "
        "<th>Active %</th> <th>Best Resistance %</th> <tr></b>\n"
    )
    for i in range(total_cp):
        result.write(
            f"<tr><td>{i + 1}</td>  <td>{cp_indv_rat[i]:5.4f}</td>  "
            f"<td>{cp_active_pct[i]:4.1f}%</td>  <td>{cp_best_pct[i]:4.1f}%</td>  </tr>\n"
        )
    result.write("</font></TABLE><p>\n")
    result.write(f"Total Possible Combination: {combo.shape[0]:8.0f} <br>\n")
    result.write(f"Total Linearly Independent Combination Processed: {combo_proc.shape[0]:8.0f} <br>\n\n")
    result.write(f"Total Unique screw motion found: {mot_all_uniq.shape[0] / 2:8.0f}<p>\n\n")


def histogr(rating: RatingResults, rowsum: np.ndarray) -> None:
    """Plot total resistance histogram (port of histogr.m). Uses matplotlib."""
    if rating.WTR == 0:
        return
    try:
        import matplotlib.pyplot as plt
    except ImportError:
        return
    rowsum = np.atleast_1d(rowsum)
    n_bins = max(1, int(len(rowsum) * (2 ** 0.5)))
    fig = plt.figure(figsize=(6, 3))
    plt.hist(rowsum, bins=n_bins)
    plt.xlabel("Total Resistance Value")
    plt.ylabel("Number of motions")
    plt.show()
