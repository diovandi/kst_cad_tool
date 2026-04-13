# Colloquium Presentation Packet

Thesis: Implementation of Mechanical Assembly Rating Tool Based on Kinematic Screw Theory

Meeting format: 30 minutes total, with 10 minutes presentation and 5 minutes demo.

Use this as the working slide script and defense prep. The key message is:

> I first built a one-to-one verified Python implementation of Rusli's KST/HOC method, because the CAD and optimization layers only make sense if the mathematical engine is trusted. The current optimization work treats KST as the deterministic physics objective, then explores faster search and acceleration strategies to reduce expensive evaluations.

## 10-Minute Slide Deck

### Slide 1 - Title and Thesis Claim, 0:30

On-slide:

- Mechanical Assembly Rating Tool Based on Kinematic Screw Theory
- Python KST engine + Fusion 360 preprocessing + optimization exploration
- Continuing Dr. Leonard Rusli's KST/HOC assembly rating work

Speaker notes:

I am implementing Rusli's KST-based mechanical assembly rating method as a modern toolchain. The contribution is not changing the KST theory. The contribution is making the theory executable from CAD geometry, validating the port against the original MATLAB/Octave behavior, and then using that validated engine as the objective for optimization.

### Slide 2 - Problem and Contribution, 1:00

On-slide:

- Fastener placement is still often heuristic: symmetry, spacing rules, trial and error
- KST gives a deterministic way to ask: "which motion is weakest resisted?"
- Gap: original method exists as research scripts, not as a CAD-integrated tool
- My contribution: CAD -> JSON v2 -> Python KST engine -> rating report -> optimization sweep

Speaker notes:

The problem is not only "where should I place a bolt?" It is "how do I explain why this placement constrains the assembly better than another placement?" KST gives a physically interpretable metric. My work turns that into a repeatable software pipeline.

### Slide 3 - The Data Structure, 1:20

On-slide:

Each CAD constraint is reduced to a KST row:

| Type | JSON v2 array | Parameters |
| --- | --- | --- |
| Point contact | `point_contacts` | `[x, y, z, nx, ny, nz]` |
| Pin | `pins` | `[x, y, z, ax, ay, az]` |
| Line | `lines` | `[mx, my, mz, lx, ly, lz, nx, ny, nz, length]` |
| Plane | `planes` | `[px, py, pz, nx, ny, nz, type, ...props]` |

Constraint order in code:

`points -> pins -> lines -> planes`

Speaker notes:

This is the answer to "what is the data itself?" The optimizer is not acting on arbitrary images or meshes. It acts on a compact geometric contract. Fusion extracts points, normals, axes, line directions, and plane size properties. The Python side converts those rows into `ConstraintSet` dataclasses and eventually into wrench systems.

For optimization, a candidate matrix replaces selected constraint rows. For example CP7.1 to CP7.5 means five possible rows for the same point constraint. Multi-constraint optimization takes the Cartesian product of the candidate rows.

### Slide 4 - KST Math in One Pipeline, 1:40

On-slide:

Core objects:

```text
Twist  t = [omega, v] in R^6
Wrench w = [f, m] in R^6
Reciprocity: w^T t = 0
```

Pipeline:

1. Build global wrench system from constraints
2. Find rank-5 wrench combinations
3. Compute reciprocal motion with nullspace
4. Build input wrench for that screw motion
5. Solve reaction equilibrium
6. Convert reactions to resistance values
7. Aggregate WTR/MRR/MTR/TOR

Speaker notes:

A twist is an instantaneous rigid-body motion. A wrench is a force/moment system. If a motion is reciprocal to the active wrenches, the constraint set does not resist that motion. In implementation terms, the code searches rank-5 wrench combinations, because a rank-5 constraint system in 6D leaves one reciprocal screw motion. That motion is then rated by asking how much reaction the constraints can generate against it.

Important implementation detail: the mathematical notation may show wrenches as columns, but the MATLAB/Python implementation stores wrenches as rows. The nullspace test is the same physical condition: each wrench row dotted with the twist must be zero.

### Slide 5 - Higher Order Constraints and Metrics, 1:30

On-slide:

HOC meaning:

- Point contact: 1 wrench generator
- Pin contact: 2 wrench generators
- Line contact: 2 wrench generators
- Plane contact: 3 wrench generators

Rusli rating metrics implemented:

```text
Ri = 1 / R
rowsum = sum(Ri per motion)
WTR = min(rowsum)
MRR = mean(rowsum / max(Ri per motion))
MTR = mean(rowsum)
TOR = MTR / MRR
```

Speaker notes:

Higher Order Constraint means the contact feature is represented directly, not as a cloud of many independent point samples. A pin, line, or plane contributes a structured wrench system with more than one wrench generator. This preserves the feature's mechanical meaning.

Also be precise about TOR. In the current MATLAB `rating.m` and Python `aggregate_ratings`, the reported TOR is `MTR / MRR`. If discussing diminishing returns across fastener counts, call that a marginal WTR gain or knee-point criterion separately. Do not mix it with the reported `TOR` column unless the thesis text is corrected.

### Slide 6 - Why MATLAB-to-Python Was One-to-One First, 1:10

On-slide:

Parity choices:

- MATLAB-style `rank()` tolerance
- MATLAB-style `null()` sign/order conventions where needed
- MATLAB-style `mldivide` behavior for underdetermined systems
- MATLAB combination ordering and duplicate-motion handling
- Matching rounding and infinity/free-motion behavior

Validation:

- 21/21 dissertation benchmark cases pass against Octave/MATLAB-compatible outputs
- End-cap JSON fixture matches Rusli-aligned baseline metrics

Speaker notes:

This was intentionally conservative. Before making it faster, I needed to know whether differences came from my code or from the original method. I therefore matched MATLAB behavior in sensitive places: rank tolerance, nullspace basis convention, mldivide, combo ordering, duplicate motion resolution, and rounding. This makes the Python engine a valid foundation for the CAD interface and later optimization work.

### Slide 7 - CAD Integration, 1:00

On-slide:

Fusion 360 add-in:

- Native wizard for Point, Pin, Line, Plane
- Extracts geometry from selected vertices, edges, cylinders, planar faces
- Detects rectangular vs circular plane properties
- Writes `wizard_input.json`
- Calls external Python because Fusion's embedded Python lacks scientific dependencies
- Returns WTR/MRR/MTR/TOR and HTML report

Speaker notes:

The CAD layer is a preprocessing layer. It does not do the KST math inside Fusion. It extracts geometry, writes the same JSON v2 data contract, and calls the external Python engine. This is deliberate because it keeps the solver host-agnostic. Inventor or SolidWorks can write the same JSON later.

### Slide 8 - Optimization: Why RF/DE/GPU Are Being Explored, 1:40

On-slide:

Optimization target:

```text
maximize KST metric, usually WTR or TOR, over candidate constraint layouts
```

Why not simple gradient/Newton first?

- Rank/nullspace changes can make objective non-smooth
- WTR uses a minimum over motion directions
- Candidate sets can be discrete/combinatorial
- No closed-form gradient is available for the full pipeline

Current pivot:

- Exhaustive factorial grid is trustworthy but too slow in high-dimensional printer case
- Differential Evolution: bounded derivative-free search
- Random Forest surrogate: predicts expensive KST objective from limited samples
- GPU/torch path: optional acceleration for batched point-contact solves, with NumPy fallback

Speaker notes:

The important distinction is that KST remains the physics objective. Random Forest or Differential Evolution are not replacing the mechanics. They reduce how often we have to call the expensive deterministic objective. For the printer housing 5D case, the old incremental revision path became slower than recomputing full analysis because 16 out of 23 constraints are revised, so almost every combination changes. That is why sample-efficient search and batching are being investigated.

### Slide 9 - Current Status and Next Work, 1:10

On-slide:

Completed:

- Python KST engine for point, pin, line, plane constraints
- 21/21 MATLAB/Octave parity cases
- Fusion 360 JSON v2 analysis workflow
- End-cap workflow verified
- Optimization candidate sweeps and surrogate/DE prototypes

In progress:

- Consolidate optimization benchmark results
- Profile and reduce high-dimensional runtime
- Evaluate GPU/DirectML/CUDA only where batch size justifies overhead
- FEA structural validation and student usability validation

Speaker notes:

The current technical result is a verified analysis engine and working CAD-to-engine bridge. The optimization phase is partially complete: the tooling exists, the runtime bottleneck has been characterized, and the faster search path is being evaluated. The next step is not to claim that a surrogate is always best, but to benchmark it against the deterministic KST objective and document when it is useful.

Transition:

I will now show the data contract and the two executable paths: analysis on the end-cap JSON, and a small optimization candidate sweep.

## 5-Minute Demo Script

Use CLI demo as the safest live path. If Fusion 360 is stable, open it first as a visual preface, but keep the CLI as the reliable fallback.

### Demo Step 1 - Show the input data, 0:45

Command:

```powershell
Get-Content test_inputs\endcap_circular_plane.json
```

Say:

This is the CAD-to-math contract. The end-cap case has six point contacts, one pin, and one circular plane. The plane row ends with `2, 0.625`, where `2` means circular plane and `0.625` is the radius in the fixture's length unit.

### Demo Step 2 - Run KST analysis, 1:15

Command:

```powershell
python3 scripts/run_wizard_analysis.py test_inputs\endcap_circular_plane.json results\presentation\presentation_endcap.tsv --skip-geometry-check
Get-Content results\presentation\presentation_endcap.tsv
```

Expected output:

```text
WTR    MRR                 MTR                 TOR
1.0    1.277412872841444   1.8112647058823529  1.4179164578111947
```

Say:

The script converts JSON rows into `ConstraintSet`, builds the HOC wrench systems, computes reciprocal motions and resistance, then writes a TSV, detailed JSON, and MATLAB-style HTML report. The values match the Rusli-aligned end-cap baseline to the displayed precision.

### Demo Step 3 - Show the optimization data, 1:00

Command:

```powershell
Get-Content matlab_script\Input_files\generic_example_optimization.json
```

Say:

This file wraps an `analysis_input` plus an `optimization.candidate_matrix`. Here the selected constraint is point 7, and five candidate rows move it along a line. The optimizer is not guessing from a mesh; it is replacing one structured KST constraint row at a time.

### Demo Step 4 - Run candidate sweep, 1:15

Command:

```powershell
python3 scripts/run_wizard_optimization.py matlab_script\Input_files\generic_example_optimization.json results\presentation\presentation_optimization.tsv
Get-Content results\presentation\presentation_optimization.tsv
```

Expected output:

```text
candidate    WTR      MRR    MTR          TOR
1            0.191    1      1.008292857  1.008292857
2            0.191    1      1.00557381   1.00557381
3            0.191    1      1.000669048  1.000669048
4            0.191    1      0.9969095238 0.9969095238
5            0.191    1      0.9945428571 0.9945428571
```

Say:

This is the simplest discrete sweep. For larger cases, the same objective can be evaluated by Differential Evolution or surrogate-guided sampling rather than a full factorial grid.

### Demo Step 5 - Close the loop, 0:45

Say:

The live demo demonstrates three things: the input data is explicit, the KST computation is reproducible, and the optimization layer changes candidate constraints while keeping the same verified rating engine underneath.

## Examiner Q&A Prep

### Dr. Eka: "Explain the math from KST to the Rusli method."

Answer:

KST represents motion as a twist and constraint/loading as a wrench in 6D Plucker coordinates. The core relation is reciprocity: `w^T t = 0`. Rusli's method builds a wrench system from HOC features, finds rank-5 combinations that leave one reciprocal screw motion, computes that motion with a nullspace calculation, then solves a reaction equilibrium problem to rate how well the remaining constraints resist that motion. The final rating is aggregated over all reciprocal motion directions. WTR is the minimum row sum of inverse resistance, so it is explicitly a weakest-direction criterion.

### Dr. Eka: "What exactly is a higher order constraint?"

Answer:

It is a feature-level equivalent wrench model. Instead of discretizing a plane or a pin into many independent point contacts, the engineered feature contributes a structured wrench system. In this implementation, point has 1 wrench generator, pin has 2, line has 2, and plane has 3. That is why the JSON has separate `point_contacts`, `pins`, `lines`, and `planes` arrays instead of one generic point list.

### Dr. Eka: "Why Random Forest?"

Answer:

Random Forest is used as a surrogate for an expensive deterministic objective, not as a replacement for the mechanics. The KST objective can be non-smooth because rank/nullspace membership and the WTR minimum can change abruptly between candidates. RF handles nonlinear mixed behavior with relatively few samples and does not require gradients. The best predicted candidates still need to be re-evaluated by the real KST engine.

### Dr. Eka: "Why Differential Evolution?"

Answer:

DE is a bounded derivative-free search method. It fits this phase because the parameter space is normalized, usually `[-1, 1]^d`, and the objective is expensive and not reliably differentiable. It gives a practical reference search when a full factorial grid is too slow. I also found an implementation issue that matters computationally: SciPy's `popsize` is a multiplier by dimension, and L-BFGS-B polishing adds hidden evaluations, so for expensive cases I disable polish and tune population size.

### Dr. Eka: "Why not Newton or gradient-based optimization?"

Answer:

For a restricted one-dimensional line search, a deterministic line-search or Newton-style method could be future work. But the full pipeline is not a smooth closed-form scalar function of the design variables. It includes discrete candidate replacement, rank tests, nullspace basis changes, duplicate-motion handling, and a minimum over motion resistances. That is why the current optimization path is derivative-free or surrogate-assisted.

### "Is MATLAB-to-Python one-to-one the correct approach?"

Answer:

Yes for the first phase. The goal was to establish a trusted engine. If the Python port changed numerical behavior while I was also integrating CAD and optimization, any discrepancy would be impossible to diagnose. Once parity was established, faster alternatives could be explored safely. This is why the implementation mirrors MATLAB rank tolerance, nullspace conventions, mldivide behavior, rounding, combo ordering, and duplicate-motion behavior.

### "Is there a faster way?"

Answer:

Yes, and that is the current optimization/performance phase. The faster path is not to rewrite the theory first. It is to identify the bottleneck and accelerate only where justified: batched point-contact rating, optional torch GPU/DirectML/CUDA for sufficiently large batches, process/thread parallelism for candidate sweeps, and surrogate/DE search to reduce the number of expensive KST evaluations. For the printer 5D case, recomputing full analysis can be faster than the original incremental revision method because almost all combinations are affected.

### "What exactly are you optimizing?"

Answer:

The layout variables are constraint parameters: location, orientation, and sometimes size, encoded as rows in the JSON/candidate matrix. The objective is a Rusli KST rating metric, usually WTR when the question is weakest resisted motion, or the reported TOR/MTR/MRR when comparing configuration quality. I should be explicit in the thesis about which metric is optimized in each experiment.

### "What is the difference between reported TOR and marginal improvement?"

Answer:

In the Rusli MATLAB code and the Python port, reported `TOR` is `MTR / MRR`. If I want a knee-point rule across increasing fastener counts, I should define a separate marginal improvement measure such as:

```text
marginal_gain(n) = (WTR(n+1) - WTR(n)) / WTR(n)
```

I should not call both of these `TOR` without clarification.

### "What is validated and what is not yet validated?"

Answer:

Validated now: core Python engine against 21 MATLAB/Octave-compatible benchmark cases, and the end-cap JSON workflow against a Rusli-aligned fixture. Working but still being consolidated: high-dimensional optimization benchmarking and GPU/accelerator value. Pending: structural validation with Ansys FEA and formal usability testing.

## One-Slide Backup: Code Map

Use this only if asked.

| Topic | File |
| --- | --- |
| Constraint dataclasses | `src/kst_rating_tool/constraints.py` |
| Wrench construction | `src/kst_rating_tool/wrench.py` |
| Reciprocal motion | `src/kst_rating_tool/motion.py` |
| Main analysis pipeline | `src/kst_rating_tool/pipeline.py` |
| Rating metrics | `src/kst_rating_tool/rating.py` |
| MATLAB parity helpers | `src/kst_rating_tool/utils.py` |
| JSON analysis runner | `scripts/run_wizard_analysis.py` |
| JSON optimization runner | `scripts/run_wizard_optimization.py` |
| Fusion command | `fusion360_addin/KstAnalysis/commands/analysis_command.py` |
| GPU/runtime notes | `docs/dev/GPU_RUNTIME.md` |
| Generic JSON schema | `docs/dev/GENERIC_INPUT_FORMAT.md` |

## Last-Minute Warnings

- Do not overclaim FEA/usability validation as completed. Say it is the next validation phase.
- Do not say Random Forest is the physical model. It is only a surrogate used to reduce calls to the KST model.
- Do not say GPU will definitely speed up every case. Small 6x6 solves can be dominated by transfer/kernel overhead. Say it is being profiled and used only when batch size justifies it.
- Do not mix the code's reported `TOR = MTR / MRR` with a separate marginal WTR knee-point formula.
- If asked about "MATLAB vs Python differences", name concrete parity measures: MATLAB rank tolerance, nullspace convention, QR-with-column-pivoting `mldivide`, rounding, combo ordering, and duplicate-motion first occurrence.
