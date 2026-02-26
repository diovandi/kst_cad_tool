"""
Thesis reference data and case name mappings.

Shared constants for analysis and comparison scripts.
"""
from __future__ import annotations

# Thesis reference values from Chapter 10 and 11 (Rusli dissertation).
# Keys: case name (no .m). Values: dict with WTR, MRR, MTR, TOR, optional LAR_WTR, LAR_MTR,
# optional wtr_motion (list of 11: Om_x..Pitch, TR), optional no_mot_unique, notes.
THESIS_REF: dict[str, dict] = {
    "case1a_chair_height": {
        "source": "Ch 10 Table 10.2",
        "WTR": 0.191,
        "MRR": 1.000,
        "MTR": 1.001,
        "TOR": 1.001,
        "LAR_WTR": 5.236,
        "LAR_MTR": 0.999,
        "wtr_motion": [0.000, 0.708, 0.706, 0.000, 0.000, 0.000, 2.000, 1.724, 1.731, 0.001, 0.191],  # Om(3), Mu(3)=0, Rho(3), Pitch=h, TR (thesis table: 8 values; expanded to 11 for motion + TR)
        "no_mot_unique": 21,
        "notes": "Thompson's chair. Thesis WTR motion: omega=(0, 0.708, 0.706), rho=(2, 1.724, 1.731), h=0.001, TR=0.191. Sign of omega/rho may differ.",
    },
    "case2a_cube_scalability": {
        "source": "Ch 10 Table 10.7 (scale=1)",
        "WTR": 0.200,
        "MRR": 1.000,
        "MTR": 0.486,
        "TOR": 0.486,
        "LAR_WTR": 5.003,
        "LAR_MTR": 2.057,
        "notes": "Cube scale factor 1.",
    },
    "case2b_cube_tradeoff": {
        "source": "Ch 10 Table 10.6",
        "WTR": 0.200,
        "MRR": 1.000,
        "MTR": 0.486,
        "TOR": 0.486,
        "LAR_WTR": 5.003,
        "LAR_MTR": 2.057,
        "wtr_motion_1": [0.577, 0.577, 0.577, 0.333, 0.750, 0.417, 0.083, 0.200],
        "notes": "Cube 7 constraints (CP2,CP3,CP4,CP5,CP7,CP10,CP12). WTR Motion 1 in thesis.",
    },
    "case3a_cover_leverage": {
        "source": "Ch 10 Table 10.10 (battery cover baseline)",
        "WTR": 2.000,
        "MRR": 1.500,
        "MTR": 2.000,
        "TOR": 1.333,
        "LAR_WTR": 0.500,
        "LAR_MTR": 0.500,
        "notes": "Battery cover assembly (HOC).",
    },
    "case4a_endcap_tradeoff": {
        "source": "Ch 10 Table 10.14 (end cap Non-HOC baseline)",
        "WTR": 1.829,
        "MRR": 3.028,
        "MTR": 2.855,
        "TOR": 0.943,
        "LAR_WTR": 0.547,
        "LAR_MTR": 0.350,
        "no_mot_unique": 148,
        "notes": "End cap assembly, non-HOC (cp-only, 24 points). Processed 282 motions, 148 unique.",
    },
    "case5a_printer_4screws_orient": {
        "source": "Ch 10 Table 10.18 (printer housing baseline)",
        "WTR": 2.437,
        "MRR": 4.555,
        "MTR": 17.628,
        "TOR": 3.870,
        "LAR_WTR": 0.410,
        "LAR_MTR": 0.057,
        "no_mot_unique": 213,
        "wtr_motion": [0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 0.322, 3.25, 0.0, 0.0, 2.437],
        "notes": "Printer housing 4 screws. WTR motion: axis (0,0,1), point (0.322, 3.25, 0), Pitch 0, TR 2.437.",
        "cp_table": [
            {"CP": i, "Active_Pct": a, "Best_Resistance_Pct": b}
            for i, (a, b) in enumerate(
                [
                    (27.2, 2.3), (26.0, 1.5), (27.2, 2.9), (27.2, 2.3), (27.2, 0.3),
                    (23.7, 0.0), (23.7, 0.0), (23.7, 0.0), (23.7, 0.0),
                    (17.9, 0.0), (17.9, 5.5), (17.9, 0.0), (17.9, 5.2),
                    (38.7, 1.5), (38.7, 0.9), (63.6, 6.4), (63.6, 2.9),
                    (45.4, 7.8), (47.4, 6.9), (40.5, 8.1), (39.9, 7.2), (39.0, 5.8), (49.7, 5.5),
                ],
                start=1,
            )
        ],
    },
    "case5e_printer_partingline": {
        "source": "Ch 10 Table 10.18 (printer baseline, same as case5a)",
        "WTR": 2.437,
        "MRR": 4.555,
        "MTR": 17.628,
        "TOR": 3.870,
        "LAR_WTR": 0.410,
        "LAR_MTR": 0.057,
        "no_mot_unique": 213,
        "wtr_motion": [0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 0.322, 3.25, 0.0, 0.0, 2.437],
        "notes": "Printer parting line study; baseline metrics same as case5a.",
        "cp_table": [
            {"CP": i, "Active_Pct": a, "Best_Resistance_Pct": b}
            for i, (a, b) in enumerate(
                [
                    (27.2, 2.3), (26.0, 1.5), (27.2, 2.9), (27.2, 2.3), (27.2, 0.3),
                    (23.7, 0.0), (23.7, 0.0), (23.7, 0.0), (23.7, 0.0),
                    (17.9, 0.0), (17.9, 5.5), (17.9, 0.0), (17.9, 5.2),
                    (38.7, 1.5), (38.7, 0.9), (63.6, 6.4), (63.6, 2.9),
                    (45.4, 7.8), (47.4, 6.9), (40.5, 8.1), (39.9, 7.2), (39.0, 5.8), (49.7, 5.5),
                ],
                start=1,
            )
        ],
    },
}

# Case number to name (match run_python_case.py)
CASE_NUM_TO_NAME: dict[int, str] = {
    1: "case1a_chair_height",
    2: "case1b_chair_height_angle",
    3: "case2a_cube_scalability",
    4: "case2b_cube_tradeoff",
    5: "case3a_cover_leverage",
    6: "case3b_cover_symmetry",
    7: "case3c_cover_orient",
    8: "case4a_endcap_tradeoff",
    9: "case4b_endcap_circlinsrch",
    10: "case5a_printer_4screws_orient",
    11: "case5b_printer_4screws_line",
    12: "case5c_printer_snap_orient",
    13: "case5d_printer_snap_line",
    14: "case5e_printer_partingline",
    15: "case5f1_printer_line_size",
    16: "case5f2_printer_sideline_size",
    17: "case5g_printer_5d",
    18: "case5rev_a_printer_2screws",
    19: "case5_printer_allscrews",
    20: "case5rev_d_printer_remove2_bot_screw",
    21: "case5rev_b_printer_flat_partingline",
}
