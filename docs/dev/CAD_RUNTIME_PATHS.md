# CAD Runtime Paths

This document is the single source of truth for how each CAD integration talks to the KST engine.

## Runtime matrix

| Integration | UI host | Input contract | Compute backend | Current status |
|---|---|---|---|---|
| Fusion 360 (repo mode) | `fusion360_addin/KstAnalysis` | v2 JSON (`point_contacts`, `pins`, `lines`, `planes`) | `scripts/run_wizard_analysis.py` and `scripts/run_wizard_optimization.py` (Python) | Active |
| Fusion 360 (bundle mode) | `fusion360_addin/KstAnalysis.bundle` | Same v2 JSON | Same Python backend, bundled `kst_rating_tool` copy | Active |
| Inventor add-in | `inventor_addin` | Generic wizard JSON | External runner (Python preferred, MATLAB optional) | Skeleton/prototype |
| SolidWorks add-in | `solidworks_addin` + `shared_cad_ui` | Shared CAD UI JSON model (`KstInputFile`) | External runner (Python preferred, MATLAB optional) | Prototype |
| Wizard demo (desktop) | `scripts/wizard_demo.py` | Same conceptual schema | Python scripts | Active for demos |

## Canonical JSON contract

- Use the format in `docs/dev/GENERIC_INPUT_FORMAT.md`.
- Analysis path expects all four constraint arrays:
  - `point_contacts`
  - `pins`
  - `lines`
  - `planes`
- Optimization path expects:
  - baseline constraints + selected groups
  - candidate matrix / search-space metadata

## Fusion bundle sync policy

The Fusion bundle includes a copied package at:

- `fusion360_addin/KstAnalysis.bundle/kst_rating_tool`

The source of truth remains:

- `src/kst_rating_tool`

To prevent drift:

```bash
python fusion360_addin/build_bundle.py
python fusion360_addin/build_bundle.py --verify
```

- `build_bundle.py` now builds and automatically verifies sync.
- `--verify` performs a hash-based check and exits non-zero on mismatch.

## Recommended execution policy

- Prefer Python backend scripts (`scripts/run_wizard_analysis.py`, `scripts/run_wizard_optimization.py`) for day-to-day use and CI-aligned behavior.
- Treat MATLAB/Octave paths as parity/reference workflows and legacy interoperability support.
- Keep CAD host UI concerns (selection, UX, serialization) separated from rating math (`src/kst_rating_tool`).
