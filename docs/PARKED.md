# Python Engine — Validation Status

**Status:** **Python is the primary analysis engine.** It is used natively by the Fusion 360 add-in and all wizard scripts. MATLAB/Octave are historical references only — no longer in the active pipeline.

**Parity:** Python matches Octave (and thus MATLAB) for **all 21 benchmark cases** (atol=1e-3, rtol=5% on WTR, MRR, MTR, TOR). This was verified during the porting phase and remains the baseline for regression testing.

---

## Current architecture

The Fusion 360 add-in (`fusion360_addin/KstAnalysis/`) writes a v2 JSON file with all four constraint types (Point, Pin, Line, Plane) and calls `scripts/run_wizard_analysis.py`, which uses the Python `kst_rating_tool` package directly. No MATLAB or Octave installation is needed.

```
Fusion 360 → wizard_input.json (v2) → run_wizard_analysis.py → kst_rating_tool → WTR/MRR/MTR/TOR
```

---

## How to re-verify parity (regression testing)

The MATLAB/Octave comparison scripts are still useful for regression testing if you change the Python engine internals:

```bash
python scripts/compare_octave_python.py all
```

This re-runs Python and Octave for each of the 21 benchmark cases and compares WTR/MRR/MTR/TOR. All 21 should pass.

---

## Historical note

Earlier documentation (e.g. DEEP_COMPARISON.md and an older version of this file) described a state where Python diverged from MATLAB/Octave for some cases (e.g. case4a endcap, case5a/5e printer). Parity work (combo order alignment, duplicate-motion resolution, and related fixes) brought **all 21 cases** into agreement. That validation is complete and Python is now the production engine.

---

## References

- **Parity comparison scripts:** [COMPARISON.md](COMPARISON.md)
- **Thesis reference comparison (Ch 10/11):** [THESIS_COMPARISON.md](THESIS_COMPARISON.md)
- **Project status:** [PROJECT_STATUS_SUMMARY.md](PROJECT_STATUS_SUMMARY.md)
- **Fusion 360 add-in:** [fusion360_addin/README.md](../fusion360_addin/README.md)
- **Scripts:** `scripts/compare_octave_python.py`, `scripts/compare_to_thesis.py`, `scripts/run_python_case.py`, `scripts/run_wizard_analysis.py`
