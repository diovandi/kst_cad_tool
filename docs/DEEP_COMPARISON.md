# Deep comparison: Thesis vs MATLAB vs Octave vs Python

**Note:** This document is a **historical** comparison snapshot. In the **current** workspace, **Python matches Octave for all 21 cases** (atol=1e-3, rtol=5%). See [PROJECT_STATUS_SUMMARY.md](PROJECT_STATUS_SUMMARY.md) and [PARKED.md](PARKED.md) for current parity status.

Reference: Rusli dissertation Ch 10 (Baseline Analysis) and Ch 11 (Design Optimization).
Tolerances: atol=1e-3, rtol=5%. Deviations: within_tol ≤5%, significant >5%, major >20%.

## Executive summary (historical)

- **MATLAB/Octave vs thesis:** 7/7 cases match (WTR within 5%): case1a_chair_height, case2a_cube_scalability, case2b_cube_tradeoff, case3a_cover_leverage, case4a_endcap_tradeoff, case5a_printer_4screws_orient, case5e_printer_partingline
- **Python vs thesis (current):** With the current codebase and result files, Python matches Octave (and thesis where applicable) for all 21 cases. Earlier builds had divergence (e.g. case5a/5e WTR); parity work has resolved this.

## Case 1: case1a_chair_height

**Thesis:** Ch 10 Table 10.2 — Thompson's chair. Thesis WTR motion: omega=(0, 0.708, 0.706), rho=(2, 1.724, 1.731), h=0.001, TR=0.191. Sign of omega/rho may differ.

### Metrics

| Metric | Thesis | MATLAB | Octave | Python | Status |
|--------|--------|--------|--------|--------|--------|
| WTR | 0.191 | 0.191 | 0.191 | 0.191 | OK |
| MRR | 1 | 1 | 1 | 1 | OK |
| MTR | 1.001 | 1.00076 | 1.00076 | 1.00076 | OK |
| TOR | 1.001 | 1.00076 | 1.00076 | 1.00076 | OK |
| LAR_WTR | 5.236 | 5.2356 | 5.2356 | 5.2356 | OK |
| LAR_MTR | 0.999 | 0.999236 | 0.999236 | 0.999236 | OK |

### Counts

| Count | Thesis | MATLAB | Octave | Python | Status |
|-------|--------|--------|--------|--------|--------|
| total_combo | — | 21 | 21 | 21 | — |
| combo_proc_count | — | 21 | 21 | 21 | — |
| no_mot_half | — | 21 | 21 | 21 | — |
| no_mot_unique | 21 | 21 | 21 | 21 | OK |

### WTR Motion (11 parameters)

| Param | Thesis | MATLAB | Octave | Python | Status |
|-------|--------|--------|--------|--------|--------|
| Om_x | 0 | -0 | 0 | 0 | OK |
| Om_y | 0.708 | -0.7084 | -0.7084 | -0.7084 | DIFF |
| Om_z | 0.706 | 0.7058 | 0.7058 | 0.7058 | OK |
| Mu_x | 2 | 0.7377 | 0.7377 | 0.7377 | DIFF |
| Mu_y | 1.724 | 0.4261 | 0.4261 | 0.4261 | DIFF |
| Mu_z | 1.731 | 0.4279 | 0.4279 | 0.4279 | DIFF |
| Rho_x | 0.001 | -2 | -2 | -2 | DIFF |
| Rho_y | 0.191 | 1.7244 | 1.7244 | 1.7244 | DIFF |
| Rho_z | — | 1.7309 | 1.7309 | 1.7309 | — |
| Pitch | — | 0.0005 | 0.0005 | 0.0005 | — |
| Total_Resistance | — | 0.191 | 0.191 | 0.191 | — |

*Note: Screw axis sign (e.g. ω vs -ω) can differ; same physical motion.*

### CP Table

| CP | Col | Thesis | MATLAB | Octave | Python | Status |
|----|-----|--------|--------|--------|--------|--------|
| 1 | Individual_Rating | — | 1.07968 | 1.07968 | 1.07968 | — |
| 1 | Active_Pct | — | 14.2857 | 14.2857 | 14.2857 | — |
| 1 | Best_Resistance_Pct | — | 14.2857 | 14.2857 | 14.2857 | — |
| 2 | Individual_Rating | — | 1.44482 | 1.44482 | 1.44482 | — |
| 2 | Active_Pct | — | 14.2857 | 14.2857 | 14.2857 | — |
| 2 | Best_Resistance_Pct | — | 14.2857 | 14.2857 | 14.2857 | — |
| 3 | Individual_Rating | — | 1.47838 | 1.47838 | 1.47838 | — |
| 3 | Active_Pct | — | 14.2857 | 14.2857 | 14.2857 | — |
| 3 | Best_Resistance_Pct | — | 14.2857 | 14.2857 | 14.2857 | — |
| 4 | Individual_Rating | — | 0.72765 | 0.72765 | 0.72765 | — |
| 4 | Active_Pct | — | 14.2857 | 14.2857 | 14.2857 | — |
| 4 | Best_Resistance_Pct | — | 14.2857 | 14.2857 | 14.2857 | — |
| 5 | Individual_Rating | — | 1.04603 | 1.04603 | 1.04603 | — |
| 5 | Active_Pct | — | 14.2857 | 14.2857 | 14.2857 | — |
| 5 | Best_Resistance_Pct | — | 14.2857 | 14.2857 | 14.2857 | — |
| 6 | Individual_Rating | — | 0.839033 | 0.839033 | 0.839033 | — |
| 6 | Active_Pct | — | 14.2857 | 14.2857 | 14.2857 | — |
| 6 | Best_Resistance_Pct | — | 14.2857 | 14.2857 | 14.2857 | — |
| 7 | Individual_Rating | — | 0.38975 | 0.38975 | 0.38975 | — |
| 7 | Active_Pct | — | 14.2857 | 14.2857 | 14.2857 | — |
| 7 | Best_Resistance_Pct | — | 14.2857 | 14.2857 | 14.2857 | — |

## Case 3: case2a_cube_scalability

**Thesis:** Ch 10 Table 10.7 (scale=1) — Cube scale factor 1.

### Metrics

| Metric | Thesis | MATLAB | Octave | Python | Status |
|--------|--------|--------|--------|--------|--------|
| WTR | 0.2 | 0.1999 | 0.1999 | 0.1999 | OK |
| MRR | 1 | 1 | 1 | 1 | OK |
| MTR | 0.486 | 0.486169 | 0.486169 | 0.486169 | OK |
| TOR | 0.486 | 0.486169 | 0.486169 | 0.486169 | OK |
| LAR_WTR | 5.003 | 5.0025 | 5.0025 | 5.0025 | OK |
| LAR_MTR | 2.057 | 2.0569 | 2.0569 | 2.0569 | OK |

### Counts

| Count | Thesis | MATLAB | Octave | Python | Status |
|-------|--------|--------|--------|--------|--------|
| total_combo | — | 21 | 21 | 21 | — |
| combo_proc_count | — | 21 | 21 | 21 | — |
| no_mot_half | — | 21 | 21 | 21 | — |
| no_mot_unique | — | 21 | 21 | 21 | — |

### WTR Motion (11 parameters)

| Param | Thesis | MATLAB | Octave | Python | Status |
|-------|--------|--------|--------|--------|--------|
| Om_x | — | 0.5774 | 0.5774 | 0.5774 | — |
| Om_y | — | -0.5774 | -0.5774 | -0.5774 | — |
| Om_z | — | 0.5774 | 0.5774 | 0.5774 | — |
| Mu_x | — | 0.53 | 0.53 | 0.53 | — |
| Mu_y | — | -0 | 0 | -0 | — |
| Mu_z | — | -0.424 | -0.424 | -0.424 | — |
| Rho_x | — | 0.3333 | 0.3333 | 0.3333 | — |
| Rho_y | — | 0.75 | 0.75 | 0.75 | — |
| Rho_z | — | 0.4167 | 0.4167 | 0.4167 | — |
| Pitch | — | 0.0833 | 0.0833 | 0.0833 | — |
| Total_Resistance | — | 0.1999 | 0.1999 | 0.1999 | — |

*Note: Screw axis sign (e.g. ω vs -ω) can differ; same physical motion.*

### CP Table

| CP | Col | Thesis | MATLAB | Octave | Python | Status |
|----|-----|--------|--------|--------|--------|--------|
| 1 | Individual_Rating | — | 0.266883 | 0.266883 | 0.266883 | — |
| 1 | Active_Pct | — | 14.2857 | 14.2857 | 14.2857 | — |
| 1 | Best_Resistance_Pct | — | 14.2857 | 14.2857 | 14.2857 | — |
| 2 | Individual_Rating | — | 0.566 | 0.566 | 0.566 | — |
| 2 | Active_Pct | — | 14.2857 | 14.2857 | 14.2857 | — |
| 2 | Best_Resistance_Pct | — | 14.2857 | 14.2857 | 14.2857 | — |
| 3 | Individual_Rating | — | 0.319217 | 0.319217 | 0.319217 | — |
| 3 | Active_Pct | — | 14.2857 | 14.2857 | 14.2857 | — |
| 3 | Best_Resistance_Pct | — | 14.2857 | 14.2857 | 14.2857 | — |
| 4 | Individual_Rating | — | 0.676133 | 0.676133 | 0.676133 | — |
| 4 | Active_Pct | — | 14.2857 | 14.2857 | 14.2857 | — |
| 4 | Best_Resistance_Pct | — | 14.2857 | 14.2857 | 14.2857 | — |
| 5 | Individual_Rating | — | 0.678233 | 0.678233 | 0.678233 | — |
| 5 | Active_Pct | — | 14.2857 | 14.2857 | 14.2857 | — |
| 5 | Best_Resistance_Pct | — | 14.2857 | 14.2857 | 14.2857 | — |
| 6 | Individual_Rating | — | 0.428633 | 0.428633 | 0.428633 | — |
| 6 | Active_Pct | — | 14.2857 | 14.2857 | 14.2857 | — |
| 6 | Best_Resistance_Pct | — | 14.2857 | 14.2857 | 14.2857 | — |
| 7 | Individual_Rating | — | 0.468083 | 0.468083 | 0.468083 | — |
| 7 | Active_Pct | — | 14.2857 | 14.2857 | 14.2857 | — |
| 7 | Best_Resistance_Pct | — | 14.2857 | 14.2857 | 14.2857 | — |

## Case 4: case2b_cube_tradeoff

**Thesis:** Ch 10 Table 10.6 — Cube 7 constraints (CP2,CP3,CP4,CP5,CP7,CP10,CP12). WTR Motion 1 in thesis.

### Metrics

| Metric | Thesis | MATLAB | Octave | Python | Status |
|--------|--------|--------|--------|--------|--------|
| WTR | 0.2 | 0.1999 | 0.1999 | 0.1999 | OK |
| MRR | 1 | 1 | 1 | 1 | OK |
| MTR | 0.486 | 0.486169 | 0.486169 | 0.486169 | OK |
| TOR | 0.486 | 0.486169 | 0.486169 | 0.486169 | OK |
| LAR_WTR | 5.003 | 5.0025 | 5.0025 | 5.0025 | OK |
| LAR_MTR | 2.057 | 2.0569 | 2.0569 | 2.0569 | OK |

### Counts

| Count | Thesis | MATLAB | Octave | Python | Status |
|-------|--------|--------|--------|--------|--------|
| total_combo | — | 21 | 21 | 21 | — |
| combo_proc_count | — | 21 | 21 | 21 | — |
| no_mot_half | — | 21 | 21 | 21 | — |
| no_mot_unique | — | 21 | 21 | 21 | — |

### WTR Motion (11 parameters)

| Param | Thesis | MATLAB | Octave | Python | Status |
|-------|--------|--------|--------|--------|--------|
| Om_x | — | 0.5774 | 0.5774 | 0.5774 | — |
| Om_y | — | -0.5774 | -0.5774 | -0.5774 | — |
| Om_z | — | 0.5774 | 0.5774 | 0.5774 | — |
| Mu_x | — | 0.53 | 0.53 | 0.53 | — |
| Mu_y | — | -0 | 0 | -0 | — |
| Mu_z | — | -0.424 | -0.424 | -0.424 | — |
| Rho_x | — | 0.3333 | 0.3333 | 0.3333 | — |
| Rho_y | — | 0.75 | 0.75 | 0.75 | — |
| Rho_z | — | 0.4167 | 0.4167 | 0.4167 | — |
| Pitch | — | 0.0833 | 0.0833 | 0.0833 | — |
| Total_Resistance | — | 0.1999 | 0.1999 | 0.1999 | — |

*Note: Screw axis sign (e.g. ω vs -ω) can differ; same physical motion.*

### CP Table

| CP | Col | Thesis | MATLAB | Octave | Python | Status |
|----|-----|--------|--------|--------|--------|--------|
| 1 | Individual_Rating | — | 0.266883 | 0.266883 | 0.266883 | — |
| 1 | Active_Pct | — | 14.2857 | 14.2857 | 14.2857 | — |
| 1 | Best_Resistance_Pct | — | 14.2857 | 14.2857 | 14.2857 | — |
| 2 | Individual_Rating | — | 0.566 | 0.566 | 0.566 | — |
| 2 | Active_Pct | — | 14.2857 | 14.2857 | 14.2857 | — |
| 2 | Best_Resistance_Pct | — | 14.2857 | 14.2857 | 14.2857 | — |
| 3 | Individual_Rating | — | 0.319217 | 0.319217 | 0.319217 | — |
| 3 | Active_Pct | — | 14.2857 | 14.2857 | 14.2857 | — |
| 3 | Best_Resistance_Pct | — | 14.2857 | 14.2857 | 14.2857 | — |
| 4 | Individual_Rating | — | 0.676133 | 0.676133 | 0.676133 | — |
| 4 | Active_Pct | — | 14.2857 | 14.2857 | 14.2857 | — |
| 4 | Best_Resistance_Pct | — | 14.2857 | 14.2857 | 14.2857 | — |
| 5 | Individual_Rating | — | 0.678233 | 0.678233 | 0.678233 | — |
| 5 | Active_Pct | — | 14.2857 | 14.2857 | 14.2857 | — |
| 5 | Best_Resistance_Pct | — | 14.2857 | 14.2857 | 14.2857 | — |
| 6 | Individual_Rating | — | 0.428633 | 0.428633 | 0.428633 | — |
| 6 | Active_Pct | — | 14.2857 | 14.2857 | 14.2857 | — |
| 6 | Best_Resistance_Pct | — | 14.2857 | 14.2857 | 14.2857 | — |
| 7 | Individual_Rating | — | 0.468083 | 0.468083 | 0.468083 | — |
| 7 | Active_Pct | — | 14.2857 | 14.2857 | 14.2857 | — |
| 7 | Best_Resistance_Pct | — | 14.2857 | 14.2857 | 14.2857 | — |

## Case 5: case3a_cover_leverage

**Thesis:** Ch 10 Table 10.10 (battery cover baseline) — Battery cover assembly (HOC).

### Metrics

| Metric | Thesis | MATLAB | Octave | Python | Status |
|--------|--------|--------|--------|--------|--------|
| WTR | 2 | 1.9998 | 1.9998 | 1.9998 | OK |
| MRR | 1.5 | 1.5 | 1.5 | 1.5 | OK |
| MTR | 2 | 1.99998 | 1.99998 | 1.99998 | OK |
| TOR | 1.333 | 1.33332 | 1.33332 | 1.33332 | OK |
| LAR_WTR | 0.5 | 0.50005 | 0.50005 | 0.50005 | OK |
| LAR_MTR | 0.5 | 0.500006 | 0.500006 | 0.500006 | OK |

### Counts

| Count | Thesis | MATLAB | Octave | Python | Status |
|-------|--------|--------|--------|--------|--------|
| total_combo | — | 372 | 372 | 372 | — |
| combo_proc_count | — | 15 | 16 | 16 | — |
| no_mot_half | — | 15 | 16 | 16 | — |
| no_mot_unique | — | 8 | 8 | 8 | — |

### WTR Motion (11 parameters)

| Param | Thesis | MATLAB | Octave | Python | Status |
|-------|--------|--------|--------|--------|--------|
| Om_x | — | -1 | -1 | -0.8944 | — |
| Om_y | — | 0 | -0 | 0.4472 | — |
| Om_z | — | 0 | -0 | 0 | — |
| Mu_x | — | 0 | -0 | 0 | — |
| Mu_y | — | 0 | -0 | 0 | — |
| Mu_z | — | 0 | -0 | 0.8729 | — |
| Rho_x | — | 0 | 0 | 0.8001 | — |
| Rho_y | — | 0 | 0 | 1.6002 | — |
| Rho_z | — | -0 | 0 | -0 | — |
| Pitch | — | 0 | 0 | 0 | — |
| Total_Resistance | — | 2 | 2 | 1.9998 | — |

*Note: Screw axis sign (e.g. ω vs -ω) can differ; same physical motion.*

### CP Table

| CP | Col | Thesis | MATLAB | Octave | Python | Status |
|----|-----|--------|--------|--------|--------|--------|
| 1 | Individual_Rating | — | 1 | 1 | 1 | — |
| 1 | Active_Pct | — | 18.75 | 18.75 | 18.75 | — |
| 1 | Best_Resistance_Pct | — | 18.75 | 18.75 | 18.75 | — |
| 2 | Individual_Rating | — | 0.999967 | 0.999967 | 0.999967 | — |
| 2 | Active_Pct | — | 18.75 | 18.75 | 18.75 | — |
| 2 | Best_Resistance_Pct | — | 12.5 | 12.5 | 12.5 | — |
| 3 | Individual_Rating | — | 0.999933 | 0.999933 | 0.999933 | — |
| 3 | Active_Pct | — | 18.75 | 18.75 | 18.75 | — |
| 3 | Best_Resistance_Pct | — | 12.5 | 12.5 | 12.5 | — |
| 4 | Individual_Rating | — | 1.00003 | 1.00003 | 1.00003 | — |
| 4 | Active_Pct | — | 18.75 | 18.75 | 18.75 | — |
| 4 | Best_Resistance_Pct | — | 6.25 | 6.25 | 6.25 | — |
| 5 | Individual_Rating | — | 2 | 2 | 2 | — |
| 5 | Active_Pct | — | 6.25 | 6.25 | 6.25 | — |
| 5 | Best_Resistance_Pct | — | 6.25 | 6.25 | 6.25 | — |
| 6 | Individual_Rating | — | 2 | 2 | 2 | — |
| 6 | Active_Pct | — | 6.25 | 6.25 | 6.25 | — |
| 6 | Best_Resistance_Pct | — | 6.25 | 6.25 | 6.25 | — |
| 7 | Individual_Rating | — | 2 | 2 | 2 | — |
| 7 | Active_Pct | — | 6.25 | 6.25 | 6.25 | — |
| 7 | Best_Resistance_Pct | — | 6.25 | 6.25 | 6.25 | — |
| 8 | Individual_Rating | — | 2 | 2 | 2 | — |
| 8 | Active_Pct | — | 6.25 | 6.25 | 6.25 | — |
| 8 | Best_Resistance_Pct | — | 6.25 | 6.25 | 6.25 | — |
| 9 | Individual_Rating | — | 1.49998 | 1.49998 | 1.49998 | — |
| 9 | Active_Pct | — | 50 | 50 | 50 | — |
| 9 | Best_Resistance_Pct | — | 25 | 25 | 25 | — |

## Case 8: case4a_endcap_tradeoff

**Thesis:** Ch 10 Table 10.14 (end cap Non-HOC baseline) — End cap assembly, non-HOC (cp-only, 24 points). Processed 282 motions, 148 unique.

### Metrics

| Metric | Thesis | MATLAB | Octave | Python | Status |
|--------|--------|--------|--------|--------|--------|
| WTR | 1.829 | 1.8289 | 1.8289 | 1.8562 | OK |
| MRR | 3.028 | 3.02796 | 3.02796 | 2.71382 | OK |
| MTR | 2.855 | 2.85464 | 2.85464 | 4.0415 | DIFF |
| TOR | 0.943 | 0.942761 | 0.942761 | 1.48923 | DIFF |
| LAR_WTR | 0.547 | 0.546777 | 0.546777 | 0.538735 | OK |
| LAR_MTR | 0.35 | 0.350307 | 0.350307 | 0.247433 | DIFF |

### Counts

| Count | Thesis | MATLAB | Octave | Python | Status |
|-------|--------|--------|--------|--------|--------|
| total_combo | — | 42504 | 42504 | 68380 | — |
| combo_proc_count | — | 141 | 141 | 147 | — |
| no_mot_half | — | 141 | 141 | 147 | — |
| no_mot_unique | 148 | 74 | 74 | 74 | DIFF |

### WTR Motion (11 parameters)

| Param | Thesis | MATLAB | Octave | Python | Status |
|-------|--------|--------|--------|--------|--------|
| Om_x | — | -1 | -1 | -0 | — |
| Om_y | — | 0 | 0 | -0 | — |
| Om_z | — | 0 | -0 | -1 | — |
| Mu_x | — | 0 | -0 | -0 | — |
| Mu_y | — | 0 | -0 | -0 | — |
| Mu_z | — | -0.4088 | -0.4088 | -0 | — |
| Rho_x | — | -0 | -0 | 0 | — |
| Rho_y | — | -0.448 | -0.448 | 0 | — |
| Rho_z | — | -0 | 0 | 0 | — |
| Pitch | — | 0 | 0 | 0 | — |
| Total_Resistance | — | 1.8289 | 1.8289 | 1.8562 | — |

*Note: Screw axis sign (e.g. ω vs -ω) can differ; same physical motion.*

### CP Table

| CP | Col | Thesis | MATLAB | Octave | Python | Status |
|----|-----|--------|--------|--------|--------|--------|
| 1 | Individual_Rating | — | 0.93685 | 0.93685 | 0.93685 | — |
| 1 | Active_Pct | — | 2.7027 | 2.7027 | 2.7027 | — |
| 1 | Best_Resistance_Pct | — | 2.7027 | 2.7027 | 2.7027 | — |
| 2 | Individual_Rating | — | 0.93685 | 0.93685 | 0.93685 | — |
| 2 | Active_Pct | — | 2.7027 | 2.7027 | 2.7027 | — |
| 2 | Best_Resistance_Pct | — | 2.7027 | 2.7027 | 2.7027 | — |
| 3 | Individual_Rating | — | 0.93685 | 0.93685 | 0.93685 | — |
| 3 | Active_Pct | — | 2.7027 | 2.7027 | 2.7027 | — |
| 3 | Best_Resistance_Pct | — | 2.02703 | 2.02703 | 2.02703 | — |
| 4 | Individual_Rating | — | 0.93685 | 0.93685 | 0.93685 | — |
| 4 | Active_Pct | — | 2.7027 | 2.7027 | 2.7027 | — |
| 4 | Best_Resistance_Pct | — | 2.02703 | 2.02703 | 2.02703 | — |
| 5 | Individual_Rating | — | 0.53772 | 0.53772 | 0.53772 | — |
| 5 | Active_Pct | — | 37.1622 | 37.1622 | 37.1622 | — |
| 5 | Best_Resistance_Pct | — | 10.1351 | 10.1351 | 8.10811 | — |
| 6 | Individual_Rating | — | 0.53772 | 0.53772 | 0.53772 | — |
| 6 | Active_Pct | — | 37.1622 | 37.1622 | 37.1622 | — |
| 6 | Best_Resistance_Pct | — | 9.45946 | 9.45946 | 7.43243 | — |
| 7 | Individual_Rating | — | 0.53772 | 0.53772 | 0.53772 | — |
| 7 | Active_Pct | — | 37.1622 | 37.1622 | 37.1622 | — |
| 7 | Best_Resistance_Pct | — | 8.78378 | 8.78378 | 6.75676 | — |
| 8 | Individual_Rating | — | 0.53772 | 0.53772 | 0.53772 | — |
| 8 | Active_Pct | — | 37.1622 | 37.1622 | 37.1622 | — |
| 8 | Best_Resistance_Pct | — | 8.10811 | 8.10811 | 6.08108 | — |
| 9 | Individual_Rating | — | 0.533864 | 0.533864 | 0.533864 | — |
| 9 | Active_Pct | — | 37.1622 | 37.1622 | 37.1622 | — |
| 9 | Best_Resistance_Pct | — | 6.08108 | 6.08108 | 0 | — |
| 10 | Individual_Rating | — | 0.667084 | 0.667084 | 0.667084 | — |
| 10 | Active_Pct | — | 37.1622 | 37.1622 | 37.1622 | — |
| 10 | Best_Resistance_Pct | — | 9.45946 | 9.45946 | 0 | — |
| 23 | Individual_Rating | — | 0.5401 | 0.5401 | 0.5401 | — |
| 23 | Active_Pct | — | 3.37838 | 3.37838 | 3.37838 | — |
| 23 | Best_Resistance_Pct | — | 0 | 0 | 0 | — |
| 24 | Individual_Rating | — | 0.5401 | 0.5401 | 0.5401 | — |
| 24 | Active_Pct | — | 3.37838 | 3.37838 | 3.37838 | — |
| 24 | Best_Resistance_Pct | — | 0 | 0 | 0 | — |
| 25 | Individual_Rating | — | — | — | 1.33072 | — |
| 25 | Active_Pct | — | — | — | 89.1892 | — |
| 25 | Best_Resistance_Pct | — | — | — | 60.8108 | — |
| ... | ... | (*25 rows total*) |

## Case 10: case5a_printer_4screws_orient

**Thesis:** Ch 10 Table 10.18 (printer housing baseline) — Printer housing 4 screws. WTR motion: axis (0,0,1), point (0.322, 3.25, 0), Pitch 0, TR 2.437.

### Metrics

| Metric | Thesis | MATLAB | Octave | Python | Status |
|--------|--------|--------|--------|--------|--------|
| WTR | 2.437 | 2.4367 | 2.4367 | 1.7499 | DIFF |
| MRR | 4.555 | 4.55502 | 4.55502 | 4.55501 | OK |
| MTR | 17.628 | 17.6278 | 17.6278 | 16.7053 | OK |
| TOR | 3.87 | 3.86997 | 3.86997 | 3.66745 | OK |
| LAR_WTR | 0.41 | 0.410391 | 0.410391 | 0.571461 | DIFF |
| LAR_MTR | 0.057 | 0.0567286 | 0.0567286 | 0.0598613 | OK |

### Counts

| Count | Thesis | MATLAB | Octave | Python | Status |
|-------|--------|--------|--------|--------|--------|
| total_combo | — | 44275 | 44275 | 44275 | — |
| combo_proc_count | — | 334 | 330 | 327 | — |
| no_mot_half | — | 334 | 330 | 327 | — |
| no_mot_unique | 213 | 213 | 213 | 213 | OK |

### WTR Motion (11 parameters)

| Param | Thesis | MATLAB | Octave | Python | Status |
|-------|--------|--------|--------|--------|--------|
| Om_x | 0 | 0 | -0 | -0 | OK |
| Om_y | 0 | 0 | -0 | 0 | OK |
| Om_z | 1 | -1 | -1 | 1 | DIFF |
| Mu_x | 0 | -0.9515 | -0.9515 | 0.9975 | DIFF |
| Mu_y | 0 | 0.0943 | 0.0943 | -0.0218 | DIFF |
| Mu_z | 0 | 0 | -0 | 0 | OK |
| Rho_x | 0.322 | 0.3221 | 0.3221 | 0.3225 | OK |
| Rho_y | 3.25 | 3.2497 | 3.2497 | 14.7559 | DIFF |
| Rho_z | 0 | 0 | -0 | 0 | OK |
| Pitch | 0 | 0 | 0 | 0 | OK |
| Total_Resistance | 2.437 | 2.4373 | 2.4373 | 1.7499 | DIFF |

*Note: Screw axis sign (e.g. ω vs -ω) can differ; same physical motion.*

### CP Table

| CP | Col | Thesis | MATLAB | Octave | Python | Status |
|----|-----|--------|--------|--------|--------|--------|
| 1 | Individual_Rating | — | 1.58244 | 1.58244 | 1.5058 | — |
| 1 | Active_Pct | 27.2 | 39.9061 | 39.9061 | 39.9061 | DIFF |
| 1 | Best_Resistance_Pct | 2.3 | 5.6338 | 5.6338 | 5.6338 | DIFF |
| 2 | Individual_Rating | — | 1.09963 | 1.09963 | 1.0333 | — |
| 2 | Active_Pct | 26 | 37.7934 | 37.7934 | 37.7934 | DIFF |
| 2 | Best_Resistance_Pct | 1.5 | 3.52113 | 3.52113 | 3.52113 | DIFF |
| 3 | Individual_Rating | — | 1.4935 | 1.4935 | 1.40279 | — |
| 3 | Active_Pct | 27.2 | 39.9061 | 39.9061 | 39.9061 | DIFF |
| 3 | Best_Resistance_Pct | 2.9 | 3.05164 | 3.05164 | 3.05164 | DIFF |
| 4 | Individual_Rating | — | 1.14064 | 1.14064 | 1.05669 | — |
| 4 | Active_Pct | 27.2 | 39.9061 | 39.9061 | 39.9061 | DIFF |
| 4 | Best_Resistance_Pct | 2.3 | 2.58216 | 2.58216 | 2.58216 | DIFF |
| 5 | Individual_Rating | — | 1.07583 | 1.07583 | 1.01467 | — |
| 5 | Active_Pct | 27.2 | 39.9061 | 39.9061 | 39.9061 | DIFF |
| 5 | Best_Resistance_Pct | 0.3 | 0.938967 | 0.938967 | 0.938967 | DIFF |
| 6 | Individual_Rating | — | 1.28344 | 1.28344 | 1.22588 | — |
| 6 | Active_Pct | 23.7 | 38.2629 | 38.2629 | 38.2629 | DIFF |
| 6 | Best_Resistance_Pct | 0 | 0 | 0 | 0 | OK |
| 7 | Individual_Rating | — | 1.28344 | 1.28344 | 1.22588 | — |
| 7 | Active_Pct | 23.7 | 38.2629 | 38.2629 | 38.2629 | DIFF |
| 7 | Best_Resistance_Pct | 0 | 0 | 0 | 0 | OK |
| 8 | Individual_Rating | — | 0.956003 | 0.956003 | 0.90851 | — |
| 8 | Active_Pct | 23.7 | 38.2629 | 38.2629 | 38.2629 | DIFF |
| 8 | Best_Resistance_Pct | 0 | 0 | 0 | 0 | OK |
| 9 | Individual_Rating | — | 0.956003 | 0.956003 | 0.90851 | — |
| 9 | Active_Pct | 23.7 | 38.2629 | 38.2629 | 38.2629 | DIFF |
| 9 | Best_Resistance_Pct | 0 | 0 | 0 | 0 | OK |
| 10 | Individual_Rating | — | 1.27999 | 1.27999 | 1.23698 | — |
| 10 | Active_Pct | 17.9 | 32.6291 | 32.6291 | 32.6291 | DIFF |
| 10 | Best_Resistance_Pct | 0 | 0 | 0 | 0 | OK |
| 21 | Individual_Rating | — | 1.82513 | 1.82513 | 1.69174 | — |
| 21 | Active_Pct | 39.9 | 52.5822 | 52.5822 | 52.5822 | DIFF |
| 21 | Best_Resistance_Pct | 7.2 | 9.15493 | 9.15493 | 9.15493 | DIFF |
| 22 | Individual_Rating | — | 1.79561 | 1.79561 | 1.65847 | — |
| 22 | Active_Pct | 39 | 56.1033 | 56.1033 | 56.1033 | DIFF |
| 22 | Best_Resistance_Pct | 5.8 | 5.86855 | 5.86855 | 5.86855 | OK |
| 23 | Individual_Rating | — | 1.72887 | 1.72887 | 1.6309 | — |
| 23 | Active_Pct | 49.7 | 69.2488 | 69.2488 | 69.2488 | DIFF |
| 23 | Best_Resistance_Pct | 5.5 | 10.0939 | 10.0939 | 10.0939 | DIFF |
| ... | ... | (*23 rows total*) |

## Case 14: case5e_printer_partingline

**Thesis:** Ch 10 Table 10.18 (printer baseline, same as case5a) — Printer parting line study; baseline metrics same as case5a.

### Metrics

| Metric | Thesis | MATLAB | Octave | Python | Status |
|--------|--------|--------|--------|--------|--------|
| WTR | 2.437 | 2.4367 | 2.4367 | 1.7499 | DIFF |
| MRR | 4.555 | 4.55502 | 4.55502 | 4.55501 | OK |
| MTR | 17.628 | 17.6278 | 17.6278 | 16.7053 | OK |
| TOR | 3.87 | 3.86997 | 3.86997 | 3.66745 | OK |
| LAR_WTR | 0.41 | 0.410391 | 0.410391 | 0.571461 | DIFF |
| LAR_MTR | 0.057 | 0.0567286 | 0.0567286 | 0.0598613 | OK |

### Counts

| Count | Thesis | MATLAB | Octave | Python | Status |
|-------|--------|--------|--------|--------|--------|
| total_combo | — | 44275 | 44275 | 44275 | — |
| combo_proc_count | — | 334 | 330 | 327 | — |
| no_mot_half | — | 334 | 330 | 327 | — |
| no_mot_unique | 213 | 213 | 213 | 213 | OK |

### WTR Motion (11 parameters)

| Param | Thesis | MATLAB | Octave | Python | Status |
|-------|--------|--------|--------|--------|--------|
| Om_x | 0 | 0 | -0 | -0 | OK |
| Om_y | 0 | 0 | -0 | 0 | OK |
| Om_z | 1 | -1 | -1 | 1 | DIFF |
| Mu_x | 0 | -0.9515 | -0.9515 | 0.9975 | DIFF |
| Mu_y | 0 | 0.0943 | 0.0943 | -0.0218 | DIFF |
| Mu_z | 0 | 0 | -0 | 0 | OK |
| Rho_x | 0.322 | 0.3221 | 0.3221 | 0.3225 | OK |
| Rho_y | 3.25 | 3.2497 | 3.2497 | 14.7559 | DIFF |
| Rho_z | 0 | 0 | -0 | 0 | OK |
| Pitch | 0 | 0 | 0 | 0 | OK |
| Total_Resistance | 2.437 | 2.4373 | 2.4373 | 1.7499 | DIFF |

*Note: Screw axis sign (e.g. ω vs -ω) can differ; same physical motion.*

### CP Table

| CP | Col | Thesis | MATLAB | Octave | Python | Status |
|----|-----|--------|--------|--------|--------|--------|
| 1 | Individual_Rating | — | 1.58244 | 1.58244 | 1.5058 | — |
| 1 | Active_Pct | 27.2 | 39.9061 | 39.9061 | 39.9061 | DIFF |
| 1 | Best_Resistance_Pct | 2.3 | 5.6338 | 5.6338 | 5.6338 | DIFF |
| 2 | Individual_Rating | — | 1.09963 | 1.09963 | 1.0333 | — |
| 2 | Active_Pct | 26 | 37.7934 | 37.7934 | 37.7934 | DIFF |
| 2 | Best_Resistance_Pct | 1.5 | 3.52113 | 3.52113 | 3.52113 | DIFF |
| 3 | Individual_Rating | — | 1.4935 | 1.4935 | 1.40279 | — |
| 3 | Active_Pct | 27.2 | 39.9061 | 39.9061 | 39.9061 | DIFF |
| 3 | Best_Resistance_Pct | 2.9 | 3.05164 | 3.05164 | 3.05164 | DIFF |
| 4 | Individual_Rating | — | 1.14064 | 1.14064 | 1.05669 | — |
| 4 | Active_Pct | 27.2 | 39.9061 | 39.9061 | 39.9061 | DIFF |
| 4 | Best_Resistance_Pct | 2.3 | 2.58216 | 2.58216 | 2.58216 | DIFF |
| 5 | Individual_Rating | — | 1.07583 | 1.07583 | 1.01467 | — |
| 5 | Active_Pct | 27.2 | 39.9061 | 39.9061 | 39.9061 | DIFF |
| 5 | Best_Resistance_Pct | 0.3 | 0.938967 | 0.938967 | 0.938967 | DIFF |
| 6 | Individual_Rating | — | 1.28344 | 1.28344 | 1.22588 | — |
| 6 | Active_Pct | 23.7 | 38.2629 | 38.2629 | 38.2629 | DIFF |
| 6 | Best_Resistance_Pct | 0 | 0 | 0 | 0 | OK |
| 7 | Individual_Rating | — | 1.28344 | 1.28344 | 1.22588 | — |
| 7 | Active_Pct | 23.7 | 38.2629 | 38.2629 | 38.2629 | DIFF |
| 7 | Best_Resistance_Pct | 0 | 0 | 0 | 0 | OK |
| 8 | Individual_Rating | — | 0.956003 | 0.956003 | 0.90851 | — |
| 8 | Active_Pct | 23.7 | 38.2629 | 38.2629 | 38.2629 | DIFF |
| 8 | Best_Resistance_Pct | 0 | 0 | 0 | 0 | OK |
| 9 | Individual_Rating | — | 0.956003 | 0.956003 | 0.90851 | — |
| 9 | Active_Pct | 23.7 | 38.2629 | 38.2629 | 38.2629 | DIFF |
| 9 | Best_Resistance_Pct | 0 | 0 | 0 | 0 | OK |
| 10 | Individual_Rating | — | 1.27999 | 1.27999 | 1.23698 | — |
| 10 | Active_Pct | 17.9 | 32.6291 | 32.6291 | 32.6291 | DIFF |
| 10 | Best_Resistance_Pct | 0 | 0 | 0 | 0 | OK |
| 21 | Individual_Rating | — | 1.82513 | 1.82513 | 1.69174 | — |
| 21 | Active_Pct | 39.9 | 52.5822 | 52.5822 | 52.5822 | DIFF |
| 21 | Best_Resistance_Pct | 7.2 | 9.15493 | 9.15493 | 9.15493 | DIFF |
| 22 | Individual_Rating | — | 1.79561 | 1.79561 | 1.65847 | — |
| 22 | Active_Pct | 39 | 56.1033 | 56.1033 | 56.1033 | DIFF |
| 22 | Best_Resistance_Pct | 5.8 | 5.86855 | 5.86855 | 5.86855 | OK |
| 23 | Individual_Rating | — | 1.72887 | 1.72887 | 1.6309 | — |
| 23 | Active_Pct | 49.7 | 69.2488 | 69.2488 | 69.2488 | DIFF |
| 23 | Best_Resistance_Pct | 5.5 | 10.0939 | 10.0939 | 10.0939 | DIFF |
| ... | ... | (*23 rows total*) |

---

## Summary (WTR and overall status)

| Case | Thesis WTR | MATLAB | Octave | Python | Notes |
|------|------------|--------|--------|--------|-------|
| case1a_chair_height | 0.191 | 0.191 | 0.191 | 0.191 | — |
| case2a_cube_scalability | 0.2 | 0.1999 | 0.1999 | 0.1999 | — |
| case2b_cube_tradeoff | 0.2 | 0.1999 | 0.1999 | 0.1999 | — |
| case3a_cover_leverage | 2 | 1.9998 | 1.9998 | 1.9998 | — |
| case4a_endcap_tradeoff | 1.829 | 1.8289 | 1.8289 | 1.8562 | — |
| case5a_printer_4screws_orient | 2.437 | 2.4367 | 2.4367 | 1.7499 | Python major WTR diff |
| case5e_printer_partingline | 2.437 | 2.4367 | 2.4367 | 1.7499 | Python major WTR diff |

## Root cause notes (historical; parity now achieved)

- **Cases 1–7, 21:** Point-only or simple geometry; Python matches MATLAB/Octave within tolerance.
- **Case 8 (endcap) and cases 10–20 (printer):** Earlier, combo order and duplicate-motion resolution could differ between Python and MATLAB/Octave, leading to different WTR in some cases. The current Python implementation and result files show **full parity** with Octave for all 21 cases (see PROJECT_STATUS_SUMMARY.md and PARKED.md).
