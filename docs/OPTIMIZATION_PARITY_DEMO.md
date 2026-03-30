# Matlab vs Python optimization — parity checklist (meeting demo)

Use this for the **side-by-side** validation your supervisor asked for (same JSON, same candidate ordering, compare ratings).

## 1. Pick one frozen input

- Example bundled with the repo: `matlab_script/Input_files/generic_example_optimization.json`
- Or export your own from the Fusion wizard (save config) and merge into the same schema (`analysis_input` + `optimization.candidate_matrix`).

## 2. Run Python (reproducible)

From the repo root:

```bash
python3 scripts/run_optimization_parity_demo.py
```

Or explicitly:

```bash
python3 scripts/run_wizard_optimization.py matlab_script/Input_files/generic_example_optimization.json results/python/optimization_parity_demo.tsv
```

Output is TSV: `candidate`, `WTR`, `MRR`, `MTR`, `TOR`.

## 3. Run MATLAB/Octave on the same file

Use your existing wizard optimization driver with the **same** JSON path. Capture the table (screenshot or CSV export).

## 4. Compare

- Candidate **index** order must match (same `candidate_matrix` row order and `itertools.product` ordering; see `docs/COMPARISON.md` for known printer-case ordering differences).
- For the generic point-only example above, numeric values should match within floating-point tolerance.

## 5. What to bring to the meeting

- Screenshot or file of **Python TSV** + **MATLAB output** for the same case.
- If a case differs, note whether it is one of the documented combo-order issues (printer cases in `docs/DEEP_COMPARISON.md`).
