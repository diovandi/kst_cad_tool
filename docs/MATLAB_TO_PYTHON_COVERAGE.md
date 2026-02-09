# MATLAB → Python Coverage

This document maps each aspect of the MATLAB “Analysis and design tool” to the Python port and notes what is **replicated**, **partially replicated**, or **not replicated**.

---

## Summary

| Category | Replicated | Partial | Not in Python |
|-----------|------------|---------|----------------|
| Core analysis (main loop, rating) | ✓ (all constraint types) | — | — |
| Constraints & wrenches | ✓ | — | — |
| Optimization (revision, reduction, postproc) | ✓ | — | — |
| Known loading (specmot) | ✓ (analysis + optimization) | — | — |
| I/O & reporting | ✓ | — | HTML report, table_mot, histogr, optim_postproc_plot |
| Sensitivity analysis | ✓ | — | sens_analysis_pos, sens_analysis_orient |
| Constraint addition | Stub | — | MATLAB has errors too |
| Point search / cp_rev_to_wrench | — | — | move_pt_srch; cp_rev via ConstraintSet |

---

## 1. Core pipeline (main.m flow)

| MATLAB | Python | Notes |
|--------|--------|--------|
| **main.m** | `pipeline.analyze_constraints`, `analyze_constraints_detailed` | No interactive menu; CLI/API only. |
| **input_menu** | `io_legacy.load_case_m_file` + `scripts/run_python_case.py` | File path / case name instead of menu. |
| **inputfile_check** | `io_legacy` (parse + ConstraintSet) | Validation via parsing; no separate check script. |
| **input_preproc** | `io_legacy` (normalize) + `ConstraintSet` | Normalization in loader; counts from `ConstraintSet`. |
| **cp_to_wrench** | `wrench.cp_to_wrench` | ✓ Full: points, pins, lines, planes. |
| **combo_preproc** | `combination.combo_preproc` | ✓ |
| **main_loop** | `pipeline.analyze_constraints` / `analyze_constraints_detailed` | ✓ Logic; **only point constraints (rate_cp) used** in loop. |
| **rating** | `rating.aggregate_ratings` | ✓ WTR, MRR, MTR, TOR. |
| **result_open** | `reporting.result_open` | ✓ Opens HTML file and writes header. |
| **report** | `reporting.write_report` | ✓ Full HTML report (ratings, table_mot, CP table). |
| **histogr** | `reporting.histogr` | ✓ Plots histogram (matplotlib). |
| **result_close** | `reporting.result_close` | ✓ Writes time and closes file. |

---

## 2. Per-constraint rating (main_loop / specmot)

| MATLAB | Python | Notes |
|--------|--------|--------|
| **rate_cp** | `rating.rate_cp` | ✓ |
| **rate_cpin** | `rating.rate_cpin` | ✓ |
| **rate_clin** | `rating.rate_clin` | ✓ |
| **rate_cpln1** | `rating.rate_cpln1` | ✓ (rectangular plane). |
| **rate_cpln2** | `rating.rate_cpln2` | ✓ (circular plane). |
| **rate_motset** | `rating.rate_motset` | ✓ (used by revision optimizer). |

All constraint types (cp, cpin, clin, cpln) are rated in the Python main loop and in `analyze_specified_motions`.

---

## 3. Motion, wrenches, reaction

| MATLAB | Python | Notes |
|--------|--------|--------|
| **rec_mot** | `motion.rec_mot` | ✓ |
| **calc_d** | `motion.calc_d` | ✓ |
| **input_wr_compose** | `input_wr.input_wr_compose` | ✓ |
| **form_combo_wrench** | `react_wr.form_combo_wrench` | ✓ |
| **react_wr_5_compose** | `react_wr.react_wr_5_compose` | ✓ (points, pins, lines, planes). |

---

## 4. Optimization

| MATLAB | Python | Notes |
|--------|--------|--------|
| **optim_main_rev** | `optimization.revision.optim_main_rev` | ✓ |
| **optim_rev** | `optimization.revision.optim_rev` | ✓ |
| **optim_main_red** | `optimization.reduction.optim_main_red` | ✓ |
| **optim_postproc** | `optimization.postproc.optim_postproc` | ✓ Index/optimum logic; **no figure saving** (no .fig/.eps). |
| **optim_main_add** | `optimization.addition.optim_main_add` | Stub (raises NotImplementedError). MATLAB version is preliminary and has errors. |

---

## 5. Search space (revision)

| MATLAB | Python | Notes |
|--------|--------|--------|
| **move_lin_srch** | `optimization.search_space.move_lin_srch` | ✓ |
| **move_pln_srch** | `optimization.search_space.move_pln_srch` | ✓ |
| **move_curvlin_srch** | `optimization.search_space.move_curvlin_srch` | ✓ |
| **orient1d_srch** | `optimization.search_space.orient1d_srch` | ✓ |
| **orient2d_srch** | `optimization.search_space.orient2d_srch` | ✓ |
| **line_orient1d_srch** | `optimization.search_space.line_orient1d_srch` | ✓ |
| **resize_lin_srch** | `optimization.search_space.resize_lin_srch` | ✓ |
| **resize_rectpln_srch** | `optimization.search_space.resize_rectpln_srch` | ✓ |
| **resize_circpln_srch** | `optimization.search_space.resize_circpln_srch` | ✓ |
| **move_pt_srch** | — | Not replicated. MATLAB: “PRELIMINARY CODE AND CONTAINS ERRORS”. |

---

## 6. Known loading (specmot)

| MATLAB | Python | Notes |
|--------|--------|--------|
| **main_specmot_orig** | `pipeline.analyze_specified_motions` | ✓ Analysis for given screw motions; all constraint types. |
| **main_specmot_optim** | `optimization.specmot_optim.main_specmot_optim` | ✓ Parameter-space optimization for specmot. |
| **rate_specmot** | `optimization.specmot_optim.rate_specmot` | ✓ Applies revision config then rates specified motions. |

---

## 7. Sensitivity analysis (MATLAB options 4 & 5)

| MATLAB | Python | Notes |
|--------|--------|--------|
| **sens_analysis_pos** | `optimization.sensitivity.sens_analysis_pos` | ✓ Position perturbation; returns SAP_WTR, SAP_MRR, SAP_MTR, SAP_TOR. |
| **sens_analysis_orient** | `optimization.sensitivity.sens_analysis_orient` | ✓ Orientation perturbation; returns SAO_* arrays. |
| **sens_analysis_postproc** | — | Optional plots; use optim_postproc_plot on SAP_* or SAO_* per constraint. |

---

## 8. I/O and reporting

| MATLAB | Python | Notes |
|--------|--------|--------|
| **result_open** | `reporting.result_open` | ✓ Opens HTML file and writes header. |
| **result_close** | `reporting.result_close` | ✓ Writes time and closes file. |
| **report** | `reporting.write_report` | ✓ Full HTML report (ratings, table_mot, CP table). |
| **table_mot** | `reporting.table_mot` | ✓ Writes screw-axis table to HTML. |
| **histogr** | `reporting.histogr` | ✓ Plots total resistance histogram (matplotlib). |
| **optim_postproc** figure/saveas | `optimization.postproc.optim_postproc_plot` | ✓ Plots and optionally saves .png/.pdf. |

---

## 9. Other MATLAB-only

| MATLAB | Python | Notes |
|--------|--------|--------|
| **cp_rev_to_wrench** | — | Revision in Python rebuilds constraints and uses `cp_to_wrench`; no direct port of this helper. |
| **variables.txt** | — | Documentation only; no code equivalent needed. |

---

## 10. Input loading

| MATLAB | Python | Notes |
|--------|--------|--------|
| Case .m files (cp only) | `io_legacy.load_case_m_file` | ✓ Parses cp matrix; **cp-only**. Pins/lines/planes not loaded from .m. |
| input_menu (21 cases) | `run_python_case.py` case name/number | Same case set (1–21) supported by script. |

---

## 11. Performance (parallel analysis)

| Feature | Python | Notes |
|--------|--------|--------|
| **Parallel combo loop** | `analyze_constraints(..., n_workers=N)`, `analyze_constraints_detailed(..., n_workers=N)` | Optional process-based parallelism over combo rows. Default `n_workers=1` (sequential). Results are merged in combo order so output matches sequential run. Use `n_workers=2` or more to speed up large cases (e.g. printer cases with many combos). |

---

## Conclusion

- **Replicated:** Core analysis for **all constraint types** (rate_cp, rate_cpin, rate_clin, rate_cpln1, rate_cpln2), wrenches, combo, motion, rating aggregation, revision/reduction/postproc optimization, search-space functions, specmot analysis and **specmot optimization** (rate_specmot, main_specmot_optim), sensitivity analysis (sens_analysis_pos, sens_analysis_orient), HTML-style reporting (result_open/close, write_report, table_mot), histogr, and optim_postproc_plot.
- **Partially replicated / not replicated:** move_pt_srch (MATLAB has errors; not ported). io_legacy loads **cp-only** from .m files; for pins/lines/planes use ConstraintSet.from_matlab_style_arrays with arrays from elsewhere. optim_main_add is a deliberate stub on both sides.

The Python port now replicates the vast majority of the MATLAB "Analysis and design tool" functionality.
