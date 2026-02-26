"""
Reporting: HTML result file, table_mot, histogr, full-report text.
Ported from result_open.m, result_close.m, report.m, table_mot.m, histogr.m.
"""
from __future__ import annotations

import time
from pathlib import Path
from typing import TextIO

import numpy as np

from .pipeline import DetailedAnalysisResult
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
    min_rs = rowsum.min()
    WTR_idx_flat = np.where((rowsum >= min_rs - 1e-9) & (rowsum <= min_rs + 1e-9))[0]
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


def _report_quantities_from_detailed(detailed: DetailedAnalysisResult):
    """From DetailedAnalysisResult compute mot_all_uniq, Ri_uniq, rowsum, best_cp, WTR_idx, cp table. Same logic as write_report."""
    _, uniq_idx = np.unique(detailed.mot_all, axis=0, return_index=True)
    mot_all_uniq = detailed.mot_all[uniq_idx, :] if detailed.mot_all.size > 0 else np.empty((0, 10), dtype=float)
    Ri_uniq = detailed.rating.Ri
    total_cp = Ri_uniq.shape[1]
    no_mot = Ri_uniq.shape[0]
    rowsum = Ri_uniq.sum(axis=1)
    max_of_row = np.maximum(Ri_uniq.max(axis=1), 1e-12)
    best_cp = np.argmax(Ri_uniq, axis=1) + 1
    free_mot_idx = np.where(rowsum == 0)[0]
    if free_mot_idx.size > 0 and mot_all_uniq.shape[0] > 0:
        free_mot = mot_all_uniq[free_mot_idx, :]
    else:
        free_mot = np.empty((0, 10), dtype=float)
    # First index where rowsum equals (or is close to) the minimum, matching MATLAB find(rowsum>=WTR & rowsum<=WTR*1.1)
    min_rs = float(rowsum.min()) if rowsum.size else 0.0
    WTR_idx_flat = np.where((rowsum >= min_rs - 1e-9) & (rowsum <= min_rs + 1e-9))[0]
    WTR_idx_org = int(WTR_idx_flat[0]) if WTR_idx_flat.size and mot_all_uniq.shape[0] > 0 else 0
    n_col = Ri_uniq.shape[1]
    non_zero_cnt_in_col = np.count_nonzero(Ri_uniq, axis=0)
    cp_best_count = np.zeros(n_col, dtype=float)
    for i in range(n_col):
        cp_best_count[i] = np.sum(best_cp == (i + 1))
    with np.errstate(divide="ignore", invalid="ignore"):
        cp_indv_rat = np.where(non_zero_cnt_in_col > 0, Ri_uniq.sum(axis=0) / non_zero_cnt_in_col, 0.0)
    cp_active_pct = (non_zero_cnt_in_col / no_mot * 100) if no_mot > 0 else np.zeros(n_col)
    cp_best_pct = (cp_best_count / no_mot * 100) if no_mot > 0 else np.zeros(n_col)
    return (
        mot_all_uniq,
        rowsum,
        total_cp,
        best_cp,
        cp_indv_rat,
        cp_active_pct,
        cp_best_pct,
        free_mot,
        WTR_idx_org,
        no_mot,
        detailed.rating,
        detailed.combo,
        detailed.combo_proc,
    )


def write_full_report_txt(detailed: DetailedAnalysisResult, path: Path | str) -> None:
    """Write machine-readable full results (metrics, counts, WTR motion, CP table) for validation.

    Format matches the thesis report (Ch 10 tables): METRICS, COUNTS, WTR_MOTION, CP_TABLE.
    Same formulas as write_report; parseable by compare_octave_python --full.
    """
    path = Path(path)
    (
        mot_all_uniq,
        rowsum,
        total_cp,
        _best_cp,
        cp_indv_rat,
        cp_active_pct,
        cp_best_pct,
        free_mot,
        WTR_idx_org,
        no_mot,
        rating,
        combo,
        combo_proc,
    ) = _report_quantities_from_detailed(detailed)

    with open(path, "w", encoding="utf-8") as f:
        # METRICS
        f.write("METRICS\n")
        WTR, MRR, MTR, TOR = rating.WTR, rating.MRR, rating.MTR, rating.TOR
        f.write(f"WTR\t{WTR:.10g}\n")
        f.write(f"MRR\t{MRR:.10g}\n")
        f.write(f"MTR\t{MTR:.10g}\n")
        f.write(f"TOR\t{TOR:.10g}\n")
        LAR_wtr = 1.0 / WTR if WTR > 0 and np.isfinite(WTR) else float("inf")
        LAR_mtr = 1.0 / MTR if MTR > 0 and np.isfinite(MTR) else float("inf")
        f.write(f"LAR_WTR\t{LAR_wtr:.10g}\n")
        f.write(f"LAR_MTR\t{LAR_mtr:.10g}\n")
        f.write("\n")

        # COUNTS
        f.write("COUNTS\n")
        f.write(f"total_combo\t{combo.shape[0]}\n")
        f.write(f"combo_proc_count\t{combo_proc.shape[0]}\n")
        f.write(f"no_mot_half\t{detailed.no_mot_half}\n")
        no_mot_unique = int(mot_all_uniq.shape[0] / 2)
        f.write(f"no_mot_unique\t{no_mot_unique}\n")
        f.write("\n")

        # WTR_MOTION: one row (Om, Mu, Rho, Pitch, Total_Resistance)
        f.write("WTR_MOTION\n")
        f.write("Om_x\tOm_y\tOm_z\tMu_x\tMu_y\tMu_z\tRho_x\tRho_y\tRho_z\tPitch\tTotal_Resistance\n")
        if free_mot.shape[0] > 0:
            row = free_mot[0, :]
            f.write(
                f"{row[0]:.10g}\t{row[1]:.10g}\t{row[2]:.10g}\t{row[3]:.10g}\t{row[4]:.10g}\t{row[5]:.10g}\t"
                f"{row[6]:.10g}\t{row[7]:.10g}\t{row[8]:.10g}\t{row[9]:.10g}\t0\n"
            )
        elif mot_all_uniq.shape[0] > 0:
            wtr_row = mot_all_uniq[WTR_idx_org, :]
            tr = float(rowsum[WTR_idx_org])
            f.write(
                f"{wtr_row[0]:.10g}\t{wtr_row[1]:.10g}\t{wtr_row[2]:.10g}\t{wtr_row[3]:.10g}\t{wtr_row[4]:.10g}\t{wtr_row[5]:.10g}\t"
                f"{wtr_row[6]:.10g}\t{wtr_row[7]:.10g}\t{wtr_row[8]:.10g}\t{wtr_row[9]:.10g}\t{tr:.10g}\n"
            )
        else:
            f.write("0\t0\t0\t0\t0\t0\t0\t0\t0\t0\t0\n")
        f.write("\n")

        # CP_TABLE
        f.write("CP_TABLE\n")
        f.write("CP\tIndividual_Rating\tActive_Pct\tBest_Resistance_Pct\n")
        for i in range(total_cp):
            f.write(f"{i + 1}\t{cp_indv_rat[i]:.10g}\t{cp_active_pct[i]:.6f}\t{cp_best_pct[i]:.6f}\n")


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
