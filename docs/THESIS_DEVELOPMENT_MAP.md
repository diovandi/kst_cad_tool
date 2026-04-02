# KST CAD Tool - Thesis & Development Map

**Created:** March 31, 2026
**Purpose:** Comprehensive synthesis of the project's academic context, architecture, risks, and development priorities.

## 1. The Core Academic Contribution
This is a bachelor's thesis for the Swiss German University & FH Südwestfalen Soest double degree program.
**The Goal:** Operationalize Dr. Leonard Rusli's 2008 PhD research (Kinematic Screw Theory for assembly rating) into a practical, CAD-integrated engineering workflow.
**The Real Novelty:** Not just porting MATLAB code to Python, but solving the **CAD-to-KST mapping problem**—automatically translating real 3D geometry (Fusion 360) into mathematically rigorous constraint abstractions (points, pins, lines, planes).

## 2. Architecture & The Canonical Contract
The system is built in three distinct layers to preserve mathematical fidelity while enabling UI flexibility:
1. **CAD Frontend (Fusion 360):** Extracts geometry (vertices, normals, dimensions) and handles user interaction.
2. **The JSON Contract (v2):** The `wizard_input.json` file is the critical architectural seam. It completely isolates the CAD host from the math engine.
3. **Python Math Engine (`kst_rating_tool`):** A strict, parity-preserving implementation of the original MATLAB logic that calculates WTR, MRR, MTR, and TOR.

## 3. Current Status & Ground Truth
- **Validation:** Python matches Octave/MATLAB for all 21 thesis benchmark cases (within 1e-3 atol / 5% rtol). **Parity is achieved.**
- **Fusion Add-in:** Supports all 4 constraint types (Point, Pin, Line, Circular/Rectangular Plane).
- **Optimization:** The factorial grid search (`optim_rev`) is prohibitively slow for high-dimensional cases (e.g., 5D printer benchmark takes hours/days). The future of optimization relies on Surrogate models (Random Forest), Bayesian Optimization, and Differential Evolution with reduced evaluation budgets.

## 4. Supervisor (Dr. Leonard Rusli) Expectations
Based on recent meetings (Mar 26 & 30):
- **Parity is non-negotiable:** Any changes to the core math must not break the 21 benchmark cases.
- **Modeling integrity:** Clear distinction between finite physical planes and infinite mathematical barriers. Proper handling of circular planes is a known tricky area.
- **Side-by-side proof:** Progress must be demonstrated with identical JSON inputs yielding identical outputs between Python and MATLAB/Octave.
- **Beyond a UI Wrapper:** The thesis must emphasize the automated CAD geometry extraction and how it enables optimization.

## 5. Developer Risk Map
- **Sacred Math Core (High Risk):** `pipeline.py`, `rating.py`, `react_wr.py`, `input_wr.py`, `motion.py`, `combination.py`, `constraints.py`. Do not touch without running regression tests.
- **Maintenance Hotspot (High Risk):** `fusion360_addin/KstAnalysis/commands/analysis_command.py` is doing too much (UI, geometry extraction, serialization, subprocess orchestration, rendering). It is brittle.
- **Value-Add Zones (Low/Medium Risk):** JSON schema validation, reporting improvements, surrogate optimization tuning, and adding clear UX tooltips in Fusion.

## 6. Immediate Build Priorities (Timeline: Pre-April 2 Draft)
1. **Thesis Defensibility:** Ensure the CAD-to-engine extraction logic is rock solid so Chapter 1-4 draft can confidently describe the methodology.
2. **Fusion UX & Reliability:** Refine plane size extraction (auto-detecting rectangular vs. circular) and ensure "save/load config" prevents malformed JSON exports.
3. **Surrogate Optimization Tests:** Get the 5D printer benchmark tests passing efficiently using DE/Surrogate paths instead of factorial brute-force.
