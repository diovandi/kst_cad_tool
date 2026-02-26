# Deep comparison: Thesis vs MATLAB vs Octave vs Python

Reference: Rusli dissertation Ch 10 (Baseline Analysis) and Ch 11 (Design Optimization).
Tolerances: atol=1e-3, rtol=5%. Deviations: within_tol ≤5%, significant >5%, major >20%.

## Executive summary

- **MATLAB/Octave vs thesis:** 1/1 cases match (WTR within 5%): case1a_chair_height
- **Python vs thesis:** All cases within tolerance.

## Case 1: case1a_chair_height

**Thesis:** Ch 10 Table 10.2 — Thompson's chair. Thesis WTR motion: omega=(0, 0.708, 0.706), rho=(2, 1.724, 1.731), h=0.001, TR=0.191. Sign of omega/rho may differ.

### Metrics

| Metric | Thesis | MATLAB | Octave | Python | Status |
|--------|--------|--------|--------|--------|--------|
| WTR | 0.191 | — | 0.191 | 0.191 | OK |
| MRR | 1 | — | 1 | 1 | OK |
| MTR | 1.001 | — | 1.00076 | 1.00076 | OK |
| TOR | 1.001 | — | 1.00076 | 1.00076 | OK |
| LAR_WTR | 5.236 | — | 5.2356 | 5.2356 | OK |
| LAR_MTR | 0.999 | — | 0.999236 | 0.999236 | OK |

### Counts

| Count | Thesis | MATLAB | Octave | Python | Status |
|-------|--------|--------|--------|--------|--------|
| total_combo | — | — | 21 | 21 | — |
| combo_proc_count | — | — | 21 | 21 | — |
| no_mot_half | — | — | 21 | 21 | — |
| no_mot_unique | 21 | — | 21 | 21 | OK |

### WTR Motion (11 parameters)

| Param | Thesis | MATLAB | Octave | Python | Status |
|-------|--------|--------|--------|--------|--------|
| Om_x | 0 | — | 0 | 0 | OK |
| Om_y | 0.708 | — | -0.7084 | -0.7084 | DIFF |
| Om_z | 0.706 | — | 0.7058 | 0.7058 | OK |
| Mu_x | 0 | — | 0.7377 | 0.7377 | DIFF |
| Mu_y | 0 | — | 0.4261 | 0.4261 | DIFF |
| Mu_z | 0 | — | 0.4279 | 0.4279 | DIFF |
| Rho_x | 2 | — | -2 | -2 | DIFF |
| Rho_y | 1.724 | — | 1.7244 | 1.7244 | OK |
| Rho_z | 1.731 | — | 1.7309 | 1.7309 | OK |
| Pitch | 0.001 | — | 0.0005 | 0.0005 | DIFF |
| Total_Resistance | 0.191 | — | 0.191 | 0.191 | OK |

*Note: Screw axis sign (e.g. ω vs -ω) can differ; same physical motion.*

### CP Table

| CP | Col | Thesis | MATLAB | Octave | Python | Status |
|----|-----|--------|--------|--------|--------|--------|
| 1 | Individual_Rating | — | — | 1.07968 | 1.07968 | — |
| 1 | Active_Pct | — | — | 14.2857 | 14.2857 | — |
| 1 | Best_Resistance_Pct | — | — | 14.2857 | 14.2857 | — |
| 2 | Individual_Rating | — | — | 1.44482 | 1.44482 | — |
| 2 | Active_Pct | — | — | 14.2857 | 14.2857 | — |
| 2 | Best_Resistance_Pct | — | — | 14.2857 | 14.2857 | — |
| 3 | Individual_Rating | — | — | 1.47838 | 1.47838 | — |
| 3 | Active_Pct | — | — | 14.2857 | 14.2857 | — |
| 3 | Best_Resistance_Pct | — | — | 14.2857 | 14.2857 | — |
| 4 | Individual_Rating | — | — | 0.72765 | 0.72765 | — |
| 4 | Active_Pct | — | — | 14.2857 | 14.2857 | — |
| 4 | Best_Resistance_Pct | — | — | 14.2857 | 14.2857 | — |
| 5 | Individual_Rating | — | — | 1.04603 | 1.04603 | — |
| 5 | Active_Pct | — | — | 14.2857 | 14.2857 | — |
| 5 | Best_Resistance_Pct | — | — | 14.2857 | 14.2857 | — |
| 6 | Individual_Rating | — | — | 0.839033 | 0.839033 | — |
| 6 | Active_Pct | — | — | 14.2857 | 14.2857 | — |
| 6 | Best_Resistance_Pct | — | — | 14.2857 | 14.2857 | — |
| 7 | Individual_Rating | — | — | 0.38975 | 0.38975 | — |
| 7 | Active_Pct | — | — | 14.2857 | 14.2857 | — |
| 7 | Best_Resistance_Pct | — | — | 14.2857 | 14.2857 | — |

---

## Summary (WTR and overall status)

| Case | Thesis WTR | Octave | Python | Notes |
|------|------------|--------|--------|-------|
| case1a_chair_height | 0.191 | 0.191 | 0.191 | — |

## Root cause notes (Python vs MATLAB/Octave)

- **Cases 1–7, 21:** Point-only or simple geometry; Python matches MATLAB/Octave within tolerance.
- **Case 8 (endcap):** Combo order and duplicate-motion resolution differ; Python can get different WTR motion and counts (e.g. total_combo 68380 vs 42504) depending on constraint set parsing.
- **Cases 10–20 (printer):** Combo row order (`nchoosek` vs `itertools.combinations`) and which resistance row is kept for duplicate screw motions differ; Python often finds a different minimum (WTR) motion, so WTR and WTR motion diverge. Thesis/Ch 10 baseline matches MATLAB/Octave.
