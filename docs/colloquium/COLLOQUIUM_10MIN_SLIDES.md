---
marp: true
paginate: true
title: Implementation of Mechanical Assembly Rating Tool Based on Kinematic Screw Theory
---

# Implementation of Mechanical Assembly Rating Tool Based on Kinematic Screw Theory

Diovandi Basheera Putra - 12301058

Colloquium presentation

Supervisor: Dr. Leonard P. Rusli

Co-advisor: Dr. Eka Budiarto

**Visual placeholder:** title slide with SGU logo plus a small CAD/constraint screenshot.

Asset candidate: `COLLOQUIUM_IMPLEMENTATION_OF_MECHANICAL_ASSEMBLY_RATING_TOOL_BASED_ON_KINEMATIC_SCREW_THEORY/figures/sgu_logo.png`

<!--
0:30. Opening claim: I am not changing Rusli's theory. I am implementing it as a verified CAD-to-KST workflow, then using that verified engine as the optimization objective.
-->

---

# Problem and Contribution

- Fastener placement is often heuristic: symmetry, spacing rules, trial and error
- KST gives a deterministic way to ask which motion is weakest resisted
- Rusli's HOC/KST method exists as research scripts, not as a CAD-integrated tool
- Contribution: `CAD geometry -> JSON v2 -> Python KST engine -> rating report -> optimization sweep`

**Illustration placeholder:** left side: heuristic bolt pattern / "rule of thumb"; right side: KST-rated layout / "weakest motion identified".

Asset candidate: use a simple custom diagram, or crop `.../figures/before_vs_after_opt.png` if it clearly communicates before/after.

<!--
1:00. Say the key problem is explainability: why one placement is better than another. KST gives a physics-readable metric. The software work makes that repeatable from CAD.
-->

---

# The Data Structure

| Type | JSON v2 array | Parameters |
| --- | --- | --- |
| Point | `point_contacts` | `[x, y, z, nx, ny, nz]` |
| Pin | `pins` | `[x, y, z, ax, ay, az]` |
| Line | `lines` | `[mx, my, mz, lx, ly, lz, nx, ny, nz, length]` |
| Plane | `planes` | `[px, py, pz, nx, ny, nz, type, ...props]` |

Constraint order: `points -> pins -> lines -> planes`

**Illustration placeholder:** CAD selection becomes structured JSON rows.

Suggested schematic:

```text
Fusion pick -> Point/Pin/Line/Plane row -> ConstraintSet -> wrench system
```

<!--
1:20. This answers "what is the data itself?" Fusion extracts compact geometric primitives, not meshes. Optimization replaces selected rows in this same structure.
-->

---

# KST Math Pipeline

```text
Twist:  t = [omega, v] in R^6
Wrench: w = [f, m] in R^6
Reciprocity: w^T t = 0
```

1. Build wrench system from selected HOC features
2. Find rank-5 wrench combinations
3. Compute reciprocal screw motion with nullspace
4. Solve reaction equilibrium for that motion
5. Convert reactions to resistance values
6. Aggregate WTR/MRR/MTR/TOR

**Illustration placeholder:** twist/wrench reciprocity diagram.

Suggested schematic:

```text
twist t = motion screw
wrench w = constraint force/moment
w^T t = 0 -> unresisted reciprocal motion
```

<!--
1:40. Important: code stores wrenches as rows, while some equations show columns. The physical condition is the same: every active wrench must dot with the twist to zero for an unresisted motion.
-->

---

# Higher Order Constraints and Metrics

HOC feature-level wrench generators:

- Point: 1 wrench
- Pin: 2 wrenches
- Line: 2 wrenches
- Plane: 3 wrenches

Rusli rating implementation:

```text
Ri = 1 / R
rowsum = sum(Ri per motion)
WTR = min(rowsum)
MRR = mean(rowsum / max(Ri per motion))
MTR = mean(rowsum)
TOR = MTR / MRR
```

**Illustration placeholder:** four HOC icons in one row:

```text
point contact -> 1 wrench | pin -> 2 | line -> 2 | plane -> 3
```

Optional add-on: small warning badge reading `Reported TOR = MTR / MRR`.

<!--
1:30. Say this carefully: reported TOR in rating.m and the Python port is MTR/MRR. If discussing a knee point, use a separate phrase like marginal WTR gain unless the thesis text is revised.
-->

---

# Why One-to-One MATLAB Parity Came First

Parity-sensitive choices:

- MATLAB-style `rank()` tolerance
- MATLAB-style `null()` sign/order conventions where needed
- MATLAB-style `mldivide` behavior
- MATLAB combination ordering and duplicate-motion handling
- Matching rounding and infinity/free-motion behavior

Result: Python matches all 21 MATLAB/Octave-compatible benchmark cases.

**Image placeholder:** parity validation plot or table excerpt.

Asset candidates:

- `../../assets/figures/octave_python_scatter.png`
- `../../assets/figures/octave_python_comparison_bars.png`

<!--
1:10. This was the correct first stage because CAD and optimization errors would otherwise be impossible to separate from math-port errors.
-->

---

# CAD Integration

Fusion 360 add-in:

- Native wizard for Point, Pin, Line, Plane
- Extracts vertices, edges, cylinders, planar faces
- Distinguishes rectangular and circular plane properties
- Writes `wizard_input.json`
- Calls external Python solver
- Displays WTR/MRR/MTR/TOR and writes HTML report

**Image placeholder:** Fusion 360 wizard screenshot.

Asset candidates:

- `COLLOQUIUM_IMPLEMENTATION_OF_MECHANICAL_ASSEMBLY_RATING_TOOL_BASED_ON_KINEMATIC_SCREW_THEORY/figures/kstAnalysisFusion.png`
- `COLLOQUIUM_IMPLEMENTATION_OF_MECHANICAL_ASSEMBLY_RATING_TOOL_BASED_ON_KINEMATIC_SCREW_THEORY/figures/kstAnalysisMenu.png`
- `COLLOQUIUM_IMPLEMENTATION_OF_MECHANICAL_ASSEMBLY_RATING_TOOL_BASED_ON_KINEMATIC_SCREW_THEORY/figures/CPlane.png`

<!--
1:00. The solver is host-agnostic. Fusion is currently the preprocessor; Inventor or SolidWorks can produce the same JSON later.
-->

---

# Optimization Progress

Optimization target:

```text
maximize a KST rating metric over candidate constraint layouts
```

Why sample-efficient methods:

- Rank/nullspace and WTR-minimum behavior can be non-smooth
- Candidate sets can be discrete or combinatorial
- Full factorial search becomes too slow for high-dimensional printer case

Current exploration:

- Differential Evolution for bounded derivative-free search
- Random Forest surrogate to reduce expensive KST evaluations
- Optional torch/GPU path for batched point-contact solves

**Illustration placeholder:** optimization strategy map.

Suggested schematic:

```text
candidate x -> KST objective -> score
       ^          |
       |          v
   DE / RF surrogate suggests next candidate
```

Asset candidate: `COLLOQUIUM_IMPLEMENTATION_OF_MECHANICAL_ASSEMBLY_RATING_TOOL_BASED_ON_KINEMATIC_SCREW_THEORY/figures/before_vs_after_opt.png`

<!--
1:40. Say RF/DE are not the physics model. KST remains the objective. RF/DE reduce calls to that deterministic objective. GPU is being profiled, not assumed to help every case.
-->

---

# Current Status

Completed:

- Python KST engine for point, pin, line, plane constraints
- 21/21 MATLAB/Octave parity cases
- Fusion 360 JSON v2 analysis workflow
- End-cap workflow verified against Rusli-aligned fixture
- Optimization candidate sweeps and surrogate/DE prototypes

Next:

- Consolidate optimization benchmarks
- Profile runtime and accelerator value
- Complete Ansys FEA structural validation
- Run student usability validation

**Image placeholder:** status/roadmap visual with four lanes:

```text
Engine parity -> CAD integration -> optimization benchmark -> FEA/usability validation
```

Asset candidates:

- `COLLOQUIUM_IMPLEMENTATION_OF_MECHANICAL_ASSEMBLY_RATING_TOOL_BASED_ON_KINEMATIC_SCREW_THEORY/figures/endcap.png`
- `COLLOQUIUM_IMPLEMENTATION_OF_MECHANICAL_ASSEMBLY_RATING_TOOL_BASED_ON_KINEMATIC_SCREW_THEORY/figures/printerHousing.png`

<!--
1:10. Transition to demo: I will show the explicit input data, run the end-cap analysis, then run a small candidate sweep.
-->

---

# Backup: Program Flow

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

**Illustration placeholder:** convert this into a horizontal/vertical flowchart.

Full flowcharts: `COLLOQUIUM_PROGRAM_FLOWCHART.md`

[![](https://mermaid.ink/img/pako:eNpNUWFv2jAQ_Ssnf22gUCBN8mESJFDo2jJBtkoLqLKSK3hL7Mh2SlPEf9-RhmqWLN-d3nv39HxkqcqQBew1V4d0z7WFONpIoDNOfhrUYDDH1BoIxxHsUBVodQ1CwqwyQkkYuL0tdDrfYJK0k-_GjiXPayMM8CzrCLn9FJw0uDCZvlvNUwulEtI6UArpQC4kUplziVByzWkNatMSw4YYJc9aWIT79fIJ3m4COIgPrrMXIcvKdv8YddkTNfDpeQ9qcgI_arsnY7qSEnUAJtWitOaa-pdWg7eGu2XdikwbkVkyqUSeQaikIdPkd40WMm55mnNj8OJw1qDvEsK9IWWYfuENWAXzZQgHjTLdg6mNxeLCu2t482RVUW7rGC4-KJQSz5m0uHmDW7QJxOtfcAUZWi5yzD4DuYJ5_PgAGkulbctaNKz7JBKGkq3hOV5dP67o0hsvV__9otIQPiy2zGE7LTIWWF2hwwrUBT-37HgW3DC7xwI3LKAy4_rvhm3kiTgll7-VKi40rardngWvPDfUVSXFhZHgO_rVrymFkaEOVSUtC26GjQYLjuydOn_U7bl9b-R5vu_2-4Nbh9UsGHndoU8D33MHQ9d1-yeHfTRbe13vdnT6Bw065Gk?type=png)](https://mermaid.ai/live/edit#pako:eNpNUWFv2jAQ_Ssnf22gUCBN8mESJFDo2jJBtkoLqLKSK3hL7Mh2SlPEf9-RhmqWLN-d3nv39HxkqcqQBew1V4d0z7WFONpIoDNOfhrUYDDH1BoIxxHsUBVodQ1CwqwyQkkYuL0tdDrfYJK0k-_GjiXPayMM8CzrCLn9FJw0uDCZvlvNUwulEtI6UArpQC4kUplziVByzWkNatMSw4YYJc9aWIT79fIJ3m4COIgPrrMXIcvKdv8YddkTNfDpeQ9qcgI_arsnY7qSEnUAJtWitOaa-pdWg7eGu2XdikwbkVkyqUSeQaikIdPkd40WMm55mnNj8OJw1qDvEsK9IWWYfuENWAXzZQgHjTLdg6mNxeLCu2t482RVUW7rGC4-KJQSz5m0uHmDW7QJxOtfcAUZWi5yzD4DuYJ5_PgAGkulbctaNKz7JBKGkq3hOV5dP67o0hsvV__9otIQPiy2zGE7LTIWWF2hwwrUBT-37HgW3DC7xwI3LKAy4_rvhm3kiTgll7-VKi40rardngWvPDfUVSXFhZHgO_rVrymFkaEOVSUtC26GjQYLjuydOn_U7bl9b-R5vu_2-4Nbh9UsGHndoU8D33MHQ9d1-yeHfTRbe13vdnT6Bw065Gk)

[![](https://mermaid.ink/img/pako:eNpdUWFv2jAQ_Ssnfw6srE2aROomCG1pC6qUIVVaQJFJjmA1sS3bEWWI_z7HhK1bPjh37967d2cfSSFKJDHZ1mJf7KgysJyuONhvnCWCa6Mo4-YHmhiksJH2QDJuz5px7JKa2v8aBoNvMMkKmRuR7xXyYrc-t5m4UpK9ORD0QRtsNEhUMHtNYIvUtAp7cuLI06wQzUbkUqFUouhrU1e7zxLKS1ZSg3D2gY7MODXMjttz7x334bgYL-fjyUCbQ42gKH-Huzvwv5_OrAfLAi7OfT9BB9QOe8wUFnkj7O68rWstaYFgcYuybjBagy4U7sFSrHnv_ei0s4xx2Rp7F7mdTwqNMWxaVpfgcPjnjmZO8mTtaOEk_v8iV7Eel503VLPLsk9O_Zwpeyd5IeEL9BHjf-L6Uyzry6jPTvmSpWi7Gcrteg01in1A2jNeHGOe0apSWHVy24Px6uI9d_VF9rZMPVik3dFFy9d0TTxSKVaS2KgWPdKgamiXkmMnXRGzwwZXJLZhSdX7iqz4yWok5T-FaC4yJdpqR-ItrbXNWtk9_JTRStG_FOQlqkS03JA4ch1IfCQfJP4a-cOrYBT6YRhFwWh0feuRA4n9cHgTWSAKg-ubIAhGJ4_8cp5Xw_DWP_0GuLv50Q?type=png)](https://mermaid.ai/live/edit#pako:eNpdUWFv2jAQ_Ssnfw6srE2aROomCG1pC6qUIVVaQJFJjmA1sS3bEWWI_z7HhK1bPjh37967d2cfSSFKJDHZ1mJf7KgysJyuONhvnCWCa6Mo4-YHmhiksJH2QDJuz5px7JKa2v8aBoNvMMkKmRuR7xXyYrc-t5m4UpK9ORD0QRtsNEhUMHtNYIvUtAp7cuLI06wQzUbkUqFUouhrU1e7zxLKS1ZSg3D2gY7MODXMjttz7x334bgYL-fjyUCbQ42gKH-Huzvwv5_OrAfLAi7OfT9BB9QOe8wUFnkj7O68rWstaYFgcYuybjBagy4U7sFSrHnv_ei0s4xx2Rp7F7mdTwqNMWxaVpfgcPjnjmZO8mTtaOEk_v8iV7Eel503VLPLsk9O_Zwpeyd5IeEL9BHjf-L6Uyzry6jPTvmSpWi7Gcrteg01in1A2jNeHGOe0apSWHVy24Px6uI9d_VF9rZMPVik3dFFy9d0TTxSKVaS2KgWPdKgamiXkmMnXRGzwwZXJLZhSdX7iqz4yWok5T-FaC4yJdpqR-ItrbXNWtk9_JTRStG_FOQlqkS03JA4ch1IfCQfJP4a-cOrYBT6YRhFwWh0feuRA4n9cHgTWSAKg-ubIAhGJ4_8cp5Xw_DWP_0GuLv50Q)

[![](https://mermaid.ink/img/pako:eNpNUV1vmzAU_StXfl2aNGtDgYdOy-e0qc1EmCoNqsgxt2AVbGQbJTTKf58xWRpLyPjcc861zz0SJjMkIXkr5Z4VVBmI56kAu74nU6qx5AKBClq2mustF3Vj4Odm_fwKNzePME1kbXjFP6jhUgwZFRnPqMFtRY3ih9feaeq4s2SDJTIDhqocDTAptFGUCwO7Fkxb4xcuMjyAVJCXckfLK8rWlc5-M-c3TyKsS8oQtPPF7NpSyT3suSngcqcOOhvMncEiiRoBGRpUFRdcG87g1ya-vPZMXjjy0nZjUmXwEkejp8h-do_X0Zm0dKTV8Ukq_Gypv5368sqWoUXdX_wKE9JBP5KIivcrIYyAFVJqhB1qAxXaOJnt1Us3ybruArcRzRddXtESdKOUzK22n8ysZ8afTCMVK0ar33-AMmYTU25mPXtBBiRXPCOhUQ0OSGUjod2RHDuflJgCK0xJaH8zqt5TkoqT1dRU_JWy-i9TsskLEr7RUttTU3dPmXOaK1pdUIV2kmomG2FIGDgLEh7JgYRfg8nw1hv7E98PAm88vnsYkJaEE394H1gg8L27e8_zxqcB-XBNb4f-w-T0D9Vq41c?type=png)](https://mermaid.ai/live/edit#pako:eNpNUV1vmzAU_StXfl2aNGtDgYdOy-e0qc1EmCoNqsgxt2AVbGQbJTTKf58xWRpLyPjcc861zz0SJjMkIXkr5Z4VVBmI56kAu74nU6qx5AKBClq2mustF3Vj4Odm_fwKNzePME1kbXjFP6jhUgwZFRnPqMFtRY3ih9feaeq4s2SDJTIDhqocDTAptFGUCwO7Fkxb4xcuMjyAVJCXckfLK8rWlc5-M-c3TyKsS8oQtPPF7NpSyT3suSngcqcOOhvMncEiiRoBGRpUFRdcG87g1ya-vPZMXjjy0nZjUmXwEkejp8h-do_X0Zm0dKTV8Ukq_Gypv5368sqWoUXdX_wKE9JBP5KIivcrIYyAFVJqhB1qAxXaOJnt1Us3ybruArcRzRddXtESdKOUzK22n8ysZ8afTCMVK0ar33-AMmYTU25mPXtBBiRXPCOhUQ0OSGUjod2RHDuflJgCK0xJaH8zqt5TkoqT1dRU_JWy-i9TsskLEr7RUttTU3dPmXOaK1pdUIV2kmomG2FIGDgLEh7JgYRfg8nw1hv7E98PAm88vnsYkJaEE394H1gg8L27e8_zxqcB-XBNb4f-w-T0D9Vq41c)

<!--
Use only if asked how the code/program flows. This slide is a backup; including it in the main 10-minute talk may make the presentation too dense.
-->
