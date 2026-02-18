# Python Port — Parity Status

**Status:** **Parity achieved.** Python matches Octave (and thus MATLAB) for **all 21 cases** (atol=1e-3, rtol=5% on WTR, MRR, MTR, TOR).

**Verified:** The result files currently in the workspace (`results_python_<case>.txt` vs `matlab_script/results_octave_<case>.txt`) show **21/21 pass** for Python vs Octave.

---

## How to verify

From the repo root:

```bash
python scripts/compare_octave_python.py all
```

This re-runs Python and Octave for each case and compares. Alternatively, compare existing result files (same tolerances) — the workspace has been verified with all 21 passing.

---

## Historical note

Earlier documentation (e.g. DEEP_COMPARISON.md and an older PARKED.md) described a state where Python diverged from MATLAB/Octave for some cases (e.g. case4a endcap, case5a/5e printer). Parity work (combo order alignment, duplicate-motion resolution, and related fixes) has since brought **all 21 cases** into agreement. The current state is full parity.

---

## References

- **Full comparison:** [COMPARISON.md](COMPARISON.md)
- **Thesis reference comparison (Ch 10/11):** [THESIS_COMPARISON.md](THESIS_COMPARISON.md)
- **Project status (including parity):** [PROJECT_STATUS_SUMMARY.md](PROJECT_STATUS_SUMMARY.md)
- **Scripts:** `scripts/compare_octave_python.py`, `scripts/compare_to_thesis.py`, `scripts/run_python_case.py`
