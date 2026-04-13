# Colloquium Program Flowchart

Yes, this is useful to include, but preferably as a backup or compressed slide. It helps answer:

- How does CAD geometry become KST math data?
- Where does the MATLAB-to-Python parity layer sit?
- Where does optimization enter the program?
- Which part is deterministic physics and which part is search/acceleration?

## High-Level System Flow

```mermaid
flowchart TD
    A[User selects CAD geometry in Fusion 360] --> B[Fusion KstAnalysis add-in]
    B --> C[Extract point, pin, line, plane parameters]
    C --> D[Write JSON v2: wizard_input.json]
    D --> E[External Python runner: scripts/run_wizard_analysis.py]
    E --> F[Build ConstraintSet dataclasses]
    F --> G[Convert constraints to HOC wrench systems]
    G --> H[Run KST analysis pipeline]
    H --> I[Write TSV + detailed JSON + HTML report]
    I --> J[Display WTR/MRR/MTR/TOR in Fusion or CLI]
```

Slide note:

> The Fusion add-in is a geometry preprocessor. The mathematical analysis happens in external Python so the solver can use NumPy/SciPy and remain reusable by other CAD hosts.

## Core KST Engine Flow

```mermaid
flowchart TD
    A[ConstraintSet: points, pins, lines, planes] --> B[cp_to_wrench]
    B --> C[Wrench systems per HOC feature]
    C --> D[combo_preproc]
    D --> E[Candidate wrench combinations]
    E --> F{MATLAB-style rank == 5?}
    F -- no --> E
    F -- yes --> G[rec_mot: nullspace -> reciprocal screw motion]
    G --> H[input_wr_compose: build input wrench]
    H --> I[react_wr_5_compose: build reaction wrench basis]
    I --> J[rate_cp / rate_cpin / rate_clin / rate_cpln]
    J --> K[Resistance matrix R]
    K --> L[aggregate_ratings]
    L --> M[WTR, MRR, MTR, TOR]
```

Slide note:

> The rank-5 step matters because in a 6D screw space, a rank-5 wrench set leaves one reciprocal screw motion. That remaining motion is the one being rated.

## Optimization Flow

```mermaid
flowchart TD
    A[Baseline analysis_input JSON] --> B[optimization.candidate_matrix]
    B --> C[Select target constraint by type+index or global constraint_index]
    C --> D[Replace selected constraint row with candidate row]
    D --> E[Run deterministic KST analysis]
    E --> F[Record WTR/MRR/MTR/TOR]
    F --> G{More candidates?}
    G -- yes --> D
    G -- no --> H[Rank candidates / choose best metric]

    S[Optional DE or RF surrogate] --> C
    T[Optional torch/GPU acceleration] --> E
```

Slide note:

> The optimizer changes the candidate constraint rows, but the score is still produced by the same deterministic KST engine. Random Forest and Differential Evolution are search helpers, not replacements for the physical model.

## MATLAB-to-Python Parity Layer

```mermaid
flowchart LR
    A[Original MATLAB / Octave scripts] --> B[Behavior to preserve]
    B --> C[matlab_rank tolerance]
    B --> D[matlab_null conventions]
    B --> E[MATLAB mldivide behavior]
    B --> F[Combination ordering]
    B --> G[Duplicate-motion first occurrence]
    C --> H[Python kst_rating_tool]
    D --> H
    E --> H
    F --> H
    G --> H
    H --> I[21/21 benchmark parity]
```

Slide note:

> This explains why the first implementation phase prioritized one-to-one behavior. It protects the CAD and optimization phases from being built on a drifting math engine.

## Suggested Placement In The 10-Minute Presentation

Best option:

- Keep the main deck as-is, but use the high-level system flow as a backup slide after "Current Status".

If Dr. Eka pushes on math:

- Show the "Core KST Engine Flow".

If the question is about optimization:

- Show the "Optimization Flow".

If the question is about why Python matches MATLAB:

- Show the "MATLAB-to-Python Parity Layer".

## One-Screen ASCII Fallback

Use this if Mermaid is not supported by the slide renderer:

```text
Fusion CAD pick
   -> JSON v2 rows
   -> ConstraintSet
   -> HOC wrench systems
   -> rank-5 combinations
   -> nullspace reciprocal screw motion
   -> reaction solve
   -> resistance matrix R
   -> WTR/MRR/MTR/TOR
   -> report / optimization ranking
```
