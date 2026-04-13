# Colloquium Concepts From Zero

This document explains the concepts behind the colloquium presentation from first principles. It is not a slide script. It is the "study this until the story feels obvious" version.

Core thesis in one sentence:

> This project takes Dr. Leonard Rusli's Kinematic Screw Theory method for rating mechanical assembly constraint quality, ports it carefully from MATLAB to Python, connects it to CAD geometry through a Fusion 360 add-in, and then explores faster ways to optimize fastener layouts while keeping the KST rating as the physics-based objective.

## 1. The Basic Engineering Problem

In an assembly, fasteners and contacts do three things:

- They constrain unwanted relative motion between parts.
- They transfer forces and moments between parts.
- They make the assembly physically manufacturable and maintainable.

In practice, fastener placement is often chosen with rules of thumb:

- Put bolts symmetrically.
- Space bolts evenly.
- Put bolts near corners or high-load areas.
- Copy an existing design.

These rules can be good, but they do not directly answer:

- Which possible rigid-body motion is still weakly resisted?
- Which constraint contributes most to resisting that motion?
- If I add, move, or remove a fastener, did the constraint quality improve?
- Can I explain the decision mathematically?

Kinematic Screw Theory, abbreviated KST, gives a way to answer those questions using rigid-body motion and constraint wrenches instead of only stress or deformation simulation.

## 2. What This Thesis Is Actually Building

The thesis is not inventing a new KST theory. It is turning an existing research method into a usable toolchain.

The current toolchain is:

```text
CAD geometry
  -> Fusion 360 add-in
  -> JSON v2 input file
  -> Python kst_rating_tool engine
  -> WTR/MRR/MTR/TOR rating outputs
  -> optimization sweep or search
```

The most important claim is:

> The optimization layer should only be trusted after the KST analysis engine is trusted.

That is why the work started with a one-to-one MATLAB-to-Python port. If the math engine was not validated first, then any optimization result could be wrong for boring reasons like numerical differences, row-order differences, or a wrong plane-contact formula.

## 3. What Data Goes Into the Tool

The tool does not optimize over raw meshes. It does not directly use the full B-Rep surface model as the mathematical object.

Instead, the CAD add-in extracts a compact constraint description. Each constraint becomes a numeric row. The JSON v2 file has four main arrays:

| Constraint type | JSON array | Meaning |
| --- | --- | --- |
| Point contact | `point_contacts` | A point and its contact normal |
| Pin | `pins` | A pin or hole center and its axis |
| Line | `lines` | A line midpoint, line direction, constraint normal, and length |
| Plane | `planes` | A plane center, normal, type, and size properties |

The row formats are:

```text
point_contacts: [x, y, z, nx, ny, nz]
pins:           [x, y, z, ax, ay, az]
lines:          [mx, my, mz, lx, ly, lz, nx, ny, nz, length]
planes:         [px, py, pz, nx, ny, nz, type, ...props]
```

For a plane:

- `type = 1` means rectangular plane.
- `type = 2` means circular plane.
- Rectangular properties include two in-plane directions and two lengths.
- Circular properties include the radius.

The code keeps a fixed global constraint order:

```text
points -> pins -> lines -> planes
```

That matters because optimization and reports refer to constraints by index. For example, if there are 6 point contacts and 1 pin, then the first plane is global constraint 8.

## 4. Rigid-Body Motion From Zero

A free rigid body in 3D has 6 degrees of freedom:

- 3 translations: along x, y, z.
- 3 rotations: about x, y, z.

KST represents an instantaneous rigid-body motion as a 6D vector called a twist.

In simplified notation:

```text
t = [omega, v]
```

where:

- `omega` is the angular velocity direction.
- `v` is the linear velocity part.

This is useful because a general rigid-body motion can be described as a screw motion. A screw motion is a rotation about an axis plus a translation along that same axis. Pure translation and pure rotation are special cases.

In the Python code, a screw motion is stored as:

```text
[omu(3), mu(3), rho(3), h]
```

where:

- `omu` is the unit screw-axis direction.
- `mu` is the moment/linear part used by the screw representation.
- `rho` is a point on the screw axis.
- `h` is pitch.

If `h = inf`, the motion is treated as a pure translation case.

## 5. Wrenches From Zero

A wrench is the force-side equivalent of a twist.

In simplified notation:

```text
w = [f, m]
```

where:

- `f` is a force vector.
- `m` is the moment vector about the same reference point.

For a point contact at point `p` with contact normal `n`, the wrench is built from:

```text
force part  = n
moment part = p x n
```

The cross product `p x n` is the moment caused by applying a force in direction `n` at position `p`.

In the code, each constraint contributes one or more wrench rows. The notation in papers may write wrench matrices with columns, but the implementation commonly stores each wrench as a row. The physical meaning is unchanged as long as the multiplication is consistent.

## 6. Reciprocity: The Key KST Idea

The core KST test is reciprocity:

```text
w^T t = 0
```

This expression is the instantaneous power pairing between a wrench and a twist:

```text
power = force dot linear_velocity + moment dot angular_velocity
```

If a wrench does no virtual work on a twist, it is reciprocal to that twist.

For this thesis, the practical interpretation is:

> If a candidate motion is reciprocal to all active constraint wrenches, then that motion is not resisted by those constraints.

So the analysis is looking for residual or weakly resisted motion directions. If the assembly still has a screw motion that the constraints do not resist well, that motion drives the weakest rating.

## 7. Rank and Nullspace Without Panic

The tool builds a global wrench matrix from all selected constraint wrenches. Call it:

```text
W_sys
```

Since rigid-body motion lives in 6D, rank is about how much of that 6D motion space is constrained.

Basic interpretation:

```text
rank < 6  -> underconstrained
rank = 6  -> enough independent directions to fully constrain rigid-body motion
dependent extra constraints -> redundant or overconstrained behavior
```

The reciprocal motion space is found with a nullspace calculation:

```text
W_sys * t = 0
```

or equivalently with a transpose depending on whether wrenches are stored as rows or columns.

The dimension of the reciprocal motion space is:

```text
6 - rank(W_sys)
```

That is why the Rusli pipeline often focuses on rank-5 wrench combinations. A rank-5 set in a 6D space leaves one remaining reciprocal screw motion. That motion is then rated.

In plain words:

> Pick a near-complete constraint set, find the one motion it still permits, then ask how well the rest of the assembly resists that motion.

## 8. Higher Order Constraints, or HOC

Higher Order Constraint means the tool represents an engineered contact feature directly instead of replacing everything with many sampled point contacts.

In this implementation:

| Feature | Number of wrench generators | Why |
| --- | ---: | --- |
| Point contact | 1 | One contact normal direction |
| Pin | 2 | A pin constrains motion in two directions normal to its axis |
| Line | 2 | A line contact has structured resistance along/normal to the line |
| Plane | 3 | A plane contact has a normal direction plus two in-plane moment/force modes |

This is one of the central ideas Dr. Eka may ask about.

The short answer is:

> HOC is feature-level constraint modeling. A pin, line, or plane is not treated as a pile of unrelated point contacts. It contributes a structured set of equivalent wrench generators that preserves the mechanical meaning of the feature.

That is also why the data format has different arrays for point, pin, line, and plane constraints.

## 9. The Rusli-KST Rating Pipeline

The analysis pipeline can be understood in seven steps:

1. Read the constraint data.
2. Convert every constraint into wrench generators.
3. Generate possible combinations of constraints.
4. Keep combinations whose wrench matrix has rank 5.
5. For each rank-5 combination, compute the reciprocal screw motion.
6. For that motion, solve a reaction equilibrium problem to see how strongly each constraint can resist it.
7. Aggregate all resistance values into rating metrics.

In code terms:

- `constraints.py` defines the input objects.
- `wrench.py` converts constraints to wrenches.
- `combination.py` creates combinations.
- `motion.py` computes reciprocal screw motions.
- `react_wr.py` builds reaction wrench systems.
- `rating.py` rates individual constraints and aggregates metrics.
- `pipeline.py` orchestrates the full analysis.

## 10. What Is Being Solved During Rating

After a reciprocal motion is found, the tool constructs an input wrench representing the external loading associated with that motion direction. Then it solves for reaction coefficients.

Conceptually:

```text
reaction_wrench_matrix * reaction_coefficients = input_wrench
```

The result says how much reaction is needed from each candidate constraint to resist that motion.

The raw resistance matrix is called `R`.

Then the code computes:

```text
Ri = 1 / R
```

This inverse representation makes it easier to aggregate contributions. Infinite resistance becomes zero contribution after inversion, because:

```text
1 / inf = 0
```

The code also handles free motions:

```text
if a motion has row sum 0, then WTR = MRR = MTR = TOR = 0
```

That means the assembly has a motion that is not resisted.

## 11. Rating Metrics From Zero

The implemented rating formulas match the Rusli MATLAB `rating.m` behavior.

Start with:

```text
Ri = 1 / R
rowsum = sum(Ri for each motion)
max_of_row = max(Ri for each motion)
```

Then:

```text
WTR = min(rowsum)
MRR = mean(rowsum / max_of_row)
MTR = mean(rowsum)
TOR = MTR / MRR
```

Meaning:

- `WTR`, Weakest Total Resistance, focuses on the worst resisted motion direction. It is the most important "weakest link" metric.
- `MRR`, Mean Redundancy Ratio, describes how resistance is distributed relative to the strongest constraint contribution in each motion.
- `MTR`, Mean Total Resistance, averages total resistance across motions.
- `TOR`, as implemented in this code and in Rusli's `rating.m`, is `MTR / MRR`.

Important warning:

Some text in the colloquium document talks about a knee-point or marginal improvement rule like:

```text
marginal_gain(n) = (WTR(n+1) - WTR(n)) / WTR(n)
```

That is a useful separate idea, but it is not the same as the reported `TOR` value in the current code. If asked, say:

> In the current implementation, reported TOR follows Rusli's rating code as `MTR / MRR`. A marginal WTR gain for knee-point detection should be defined separately.

## 12. Why MATLAB-to-Python Parity Matters

The original analysis tool was in MATLAB. The thesis ports that behavior to Python so it can connect to modern CAD workflows.

However, porting numerical code is not just rewriting syntax. Python and MATLAB can differ in:

- Matrix rank tolerance.
- Nullspace basis sign and ordering.
- Linear solve behavior for square, singular, or underdetermined systems.
- Combination ordering.
- Which duplicate motion is kept first.
- Rounding behavior.
- Handling of `inf` and free motions.

The Python implementation intentionally matched MATLAB behavior in those sensitive places.

Examples:

- `matlab_rank()` uses MATLAB-style rank tolerance.
- `matlab_null()` tries to match MATLAB-style nullspace conventions where needed.
- `_matlab_mldivide()` imitates MATLAB `A \ b`, including QR-with-column-pivoting behavior for non-square systems.
- Combination ordering avoids global resorting because the first duplicate motion kept can affect parity.

The defense explanation:

> One-to-one parity was the correct first phase because it isolates the math. Once the Python engine matches the reference behavior, CAD integration and optimization can be tested on a trusted foundation.

## 13. CAD Integration From Zero

The Fusion 360 add-in is a preprocessing interface.

It does not solve all KST math inside Fusion. Instead, it:

1. Lets the user pick geometry in Fusion.
2. Extracts the needed numeric parameters.
3. Writes a JSON v2 file.
4. Calls the external Python script.
5. Displays the returned rating metrics.

Examples:

- A vertex or sketch point becomes a point contact location.
- A planar face gives a normal direction.
- A cylindrical face or circular edge gives a pin axis.
- A linear edge gives a line direction.
- A planar face gives a plane center, normal, and rectangular or circular size properties.

Why external Python?

Fusion's embedded Python environment does not reliably include the scientific dependencies needed by the solver, such as NumPy and SciPy. Calling external Python keeps the math engine in the normal project environment.

Why JSON?

Because JSON separates the CAD host from the math engine. In the future, Inventor or SolidWorks can produce the same JSON structure and reuse the same Python solver.

## 14. What The End-Cap Demo Proves

The end-cap fixture contains:

- 6 point contacts.
- 1 pin.
- 1 circular plane.

The input file is:

```text
test_inputs/endcap_circular_plane.json
```

The demo command is:

```powershell
python3 scripts/run_wizard_analysis.py test_inputs\endcap_circular_plane.json results\presentation\presentation_endcap.tsv --skip-geometry-check
```

The expected rating is approximately:

```text
WTR = 1.0000
MRR = 1.2774
MTR = 1.8113
TOR = 1.4179
```

This demo proves:

- The JSON v2 input path works.
- The engine handles mixed constraint types.
- Circular plane support is active.
- The output is consistent with the Rusli-aligned end-cap fixture.

## 15. Optimization From Zero

Optimization means changing constraint parameters and comparing ratings.

The design variables can be:

- A point contact location.
- A contact normal direction.
- A pin axis.
- A line position, line direction, or length.
- A plane position, normal, or size.
- A choice of which constraints are included or removed.

The objective is usually a KST metric, such as:

```text
maximize WTR
```

The most basic optimization is a candidate sweep:

```text
candidate 1 -> run KST -> WTR/MRR/MTR/TOR
candidate 2 -> run KST -> WTR/MRR/MTR/TOR
candidate 3 -> run KST -> WTR/MRR/MTR/TOR
...
choose best candidate
```

In the JSON optimization format, this appears as:

```text
analysis_input
optimization.candidate_matrix
```

The `analysis_input` is the baseline constraint set.

The `candidate_matrix` says which constraint row to replace and what candidate rows to try.

## 16. Why Optimization Is Hard Here

The KST objective is deterministic, but it is not a simple smooth formula.

Reasons:

- Rank can change when a candidate moves.
- Nullspace basis can change.
- Duplicate-motion handling can change which motion is kept.
- WTR uses a minimum over motion directions.
- Candidate choices can be discrete.
- Some cases are combinatorial, especially when several constraints vary at once.

This means a simple gradient or Newton method is not the obvious first choice for the full pipeline.

If asked:

> For a tightly restricted one-dimensional problem, such as moving one fastener along a line, a line search or Newton-style method can be future work. For the full current pipeline, derivative-free and surrogate-assisted methods are more appropriate because the objective is expensive and not reliably differentiable.

## 17. Why Differential Evolution

Differential Evolution, or DE, is a derivative-free optimization method.

Plain-English version:

- Keep a population of candidate parameter vectors.
- Try variations by combining existing candidates.
- Keep candidates that improve the objective.
- Repeat within bounds.

Why it fits this work:

- It does not need gradients.
- It works with bounded variables like `[-1, 1]^d`.
- It can search continuous parameterizations like orientation or position changes.
- It is easier to use as a reference than a full factorial grid when the grid explodes.

Caveat:

DE still calls the real KST objective many times. In SciPy, `popsize` is a multiplier by dimension, not an absolute population count. Also, polishing with L-BFGS-B can add many hidden evaluations. For expensive KST cases, disabling polish and tuning population size is reasonable.

## 18. Why Random Forest Surrogates

A surrogate model is an approximate model used to reduce expensive real evaluations.

In this thesis:

```text
real objective = KST rating
surrogate = model trained to predict KST rating from design variables
```

Random Forest is useful here because:

- It can model nonlinear behavior.
- It does not need gradients.
- It can work with limited samples.
- It gives a practical first surrogate for expensive black-box objective calls.

Important:

> Random Forest is not the physical model. KST remains the physical objective. The surrogate only suggests promising candidates, and the best candidates still need to be evaluated by the real KST engine.

That distinction is very important for the defense.

## 19. Why GPU or Torch Acceleration

The core rating process includes many small linear algebra operations. Some of these can be batched.

The current accelerator work explores:

- NumPy CPU as the default path.
- Optional PyTorch CPU/GPU path.
- CUDA for NVIDIA GPUs when available.
- DirectML for Windows AMD/Intel GPU paths when available.

But GPU is not automatically faster.

Why?

- Many solves are tiny, often 6x6.
- Moving data to the GPU has overhead.
- Kernel launch overhead can dominate small batches.
- Not every constraint type is currently accelerated in the torch path.

Best defense wording:

> GPU acceleration is being profiled as an optional path. It is useful only when the batch size and supported operation path justify the overhead. The default remains NumPy CPU with safe fallback.

## 20. The Printer-Housing Runtime Problem

The printer housing case is the main scalability warning.

In the 5D printer benchmark:

- There are 23 constraints.
- 16 out of 23 constraints are revised by the optimization setup.
- Almost every combination is affected.

The original incremental optimization idea recomputes only combinations involving changed constraints. That sounds faster, but in this case almost all combinations involve changed constraints.

So the incremental method becomes slower than a fresh full analysis.

Defense phrasing:

> The optimization bottleneck is not only Python being slower than MATLAB. It is also that the incremental algorithm loses its advantage when most constraints are modified. That motivated the pivot to recomputation-based surrogate and DE evaluation for the high-dimensional case.

## 21. What Is Validated Now

Validated:

- Core Python KST engine for point, pin, line, and plane constraints.
- 21/21 MATLAB/Octave-compatible benchmark cases.
- End-cap JSON v2 analysis workflow.
- Circular plane fixture behavior.
- Basic optimization candidate sweep path.

In progress:

- High-dimensional optimization benchmark consolidation.
- Runtime profiling and acceleration.
- Surrogate and DE comparison.

Pending:

- Ansys FEA structural validation.
- Formal usability testing with students.

Do not overclaim the pending parts.

## 22. The Clean Defense Story

If you need to explain the whole thesis in one minute:

> The original Rusli method rates a mechanical assembly by converting its constraints into KST wrench systems, finding reciprocal screw motions, and calculating resistance metrics such as WTR. My first step was to port that MATLAB method to Python while preserving numerical parity, because the math engine must be trusted before optimization or CAD integration can be trusted. Then I built a Fusion 360 preprocessing workflow that extracts point, pin, line, and plane constraints into a JSON v2 data contract. The Python engine reads that data, runs the KST pipeline, and reports WTR/MRR/MTR/TOR. The current optimization work changes constraint rows or candidate sets and uses the same deterministic KST rating as the objective, while exploring Differential Evolution, Random Forest surrogates, and optional GPU batching to reduce the cost of expensive evaluations.

## 23. Quick Vocabulary Sheet

| Term | Meaning |
| --- | --- |
| KST | Kinematic Screw Theory, a 6D framework for rigid-body motion and constraint |
| Twist | 6D representation of instantaneous motion |
| Wrench | 6D representation of force and moment |
| Reciprocity | Condition `w^T t = 0`, meaning the wrench does no work on the twist |
| Nullspace | Set of motions left possible by a wrench matrix |
| Rank | Number of independent constraint directions in a matrix |
| HOC | Higher Order Constraint, feature-level constraint model |
| WTR | Weakest Total Resistance, worst resisted motion score |
| MRR | Mean Redundancy Ratio |
| MTR | Mean Total Resistance |
| TOR | In current code, `MTR / MRR` |
| Candidate matrix | List of alternate constraint rows to evaluate |
| Differential Evolution | Derivative-free bounded optimizer |
| Random Forest surrogate | Approximate model used to reduce real KST evaluations |
| MATLAB parity | Matching MATLAB numerical behavior in Python |
| JSON v2 | CAD-to-math data contract with point, pin, line, plane arrays |

## 24. Things To Say Carefully

Say:

- "KST remains the deterministic physics objective."
- "Random Forest is a surrogate, not the physical model."
- "Differential Evolution is used because the objective is expensive and not reliably differentiable."
- "GPU is optional and being profiled."
- "Reported TOR in the current code is `MTR / MRR`."
- "FEA and usability validation are planned next."

Do not say:

- "The Random Forest decides the best mechanical layout" without saying it is validated by KST.
- "GPU makes it faster" without saying it depends on batch size and backend support.
- "TOR is marginal WTR gain" unless you explicitly define a separate marginal metric.
- "The theory is new" because the theory comes from Rusli's KST/HOC work.
- "FEA validation is finished" if it is still pending.
