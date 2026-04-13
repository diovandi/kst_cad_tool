# Fusion 360 Add-in Tree

- `KstAnalysis/` — source add-in used for development.
- `KstAnalysis.bundle/` — packaged bundle synced for Fusion deployment.
- `build_bundle.py` — rebuild/sync helper between source and bundle.

The split is intentional: edit `KstAnalysis/`, then rebuild the bundle.
