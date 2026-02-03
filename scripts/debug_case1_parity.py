#!/usr/bin/env python3
"""
Debug script: run case 1, dump R/Ri/mot_all/rowsum and first-motion rate_cp details
to compare with Octave for one-to-one parity.
"""
from __future__ import annotations

import sys
from pathlib import Path

repo_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(repo_root / "src"))

import numpy as np
from kst_rating_tool.io_legacy import load_case_m_file
from kst_rating_tool.pipeline import analyze_constraints_detailed
from kst_rating_tool.rating import rate_cp, aggregate_ratings

def main():
    case_path = repo_root / "matlab_script" / "Input_files" / "case1a_chair_height.m"
    constraints = load_case_m_file(case_path)
    det = analyze_constraints_detailed(constraints)

    R = det.R
    mot_all = det.mot_all
    _, uniq_idx = np.unique(mot_all, axis=0, return_index=True)
    R_uniq = R[uniq_idx, :]
    res = aggregate_ratings(R_uniq)
    Ri = res.Ri
    rowsum = Ri.sum(axis=1)

    print("=== Python case1a_chair_height ===")
    print("no_mot_half:", det.no_mot_half)
    print("mot_all.shape:", mot_all.shape)
    print("R.shape:", R.shape)
    print("R_uniq.shape:", R_uniq.shape)
    print("Ri.shape:", Ri.shape)
    print("Number of inf in R:", np.isinf(R).sum())
    print("Number of inf in R_uniq:", np.isinf(R_uniq).sum())
    print("Rows with rowsum==0:", np.sum(rowsum == 0))
    print("min(rowsum):", rowsum.min())
    print("WTR, MRR, MTR, TOR:", res.WTR, res.MRR, res.MTR, res.TOR)
    free_idx = np.where(rowsum == 0)[0]
    for idx in free_idx[:5]:
        print(f"  free motion idx {idx}: h={mot_all[uniq_idx[idx], 9]}, R_uniq row all inf? {np.all(np.isinf(R_uniq[idx]))}")
    print()

    # First motion: run rate_cp for first combo's motion
    cp, cpin, clin, cpln, cpln_prop = constraints.to_matlab_style_arrays()
    no_cp = cp.shape[0]
    from kst_rating_tool.react_wr import react_wr_5_compose
    from kst_rating_tool.input_wr import input_wr_compose
    from kst_rating_tool.combination import combo_preproc
    from kst_rating_tool.wrench import cp_to_wrench
    from kst_rating_tool.react_wr import form_combo_wrench

    wr_all_sys, pts, max_d = cp_to_wrench(constraints)
    wr_all = [w.as_array() for w in wr_all_sys]
    combo = combo_preproc(constraints)
    combo_row = combo[0]
    react_wr_5 = react_wr_5_compose(constraints, combo_row, det.mot_half[0, 6:9])
    mot_arr = det.mot_half[0, :]
    from kst_rating_tool.motion import ScrewMotion
    screw = ScrewMotion(mot_arr[0:3], mot_arr[3:6], mot_arr[6:9], float(mot_arr[9]))
    input_wr, _ = input_wr_compose(screw, pts, max_d)

    print("First motion (mot_half[0]):", mot_arr)
    print("First combo_row:", combo_row)
    print("react_wr_5 shape:", react_wr_5.shape)
    print("input_wr:", input_wr)
    for j in range(no_cp):
        rp, rn = rate_cp(mot_arr, react_wr_5, input_wr, cp[j, :])
        print(f"  rate_cp cp[{j}]: Rcp_pos={rp}, Rcp_neg={rn}")

    # Save R_uniq, Ri, mot_all, rowsum for Octave comparison
    out = repo_root / "debug_python_case1"
    np.savez(out, R_uniq=R_uniq, Ri=Ri, mot_all=mot_all, uniq_idx=uniq_idx, rowsum=rowsum)
    print(f"\nSaved {out}.npz (R_uniq, Ri, mot_all, uniq_idx, rowsum)")

if __name__ == "__main__":
    main()
