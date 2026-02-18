# KST Wizard Demo — Meeting Guide (This Week)

Use this to show your supervisor what the future Inventor add-in will look like. The demo is a **Python GUI** that mimics the two wizards; it runs on your machine without Inventor or MATLAB.

---

## How to run it

From the **project root** (where you see `README.md`, `scripts/`, `matlab_script/`):

```bash
python scripts/wizard_demo.py
```

A window opens with **two tabs**: **Analysis Wizard** and **Optimization Wizard**. No extra installs needed (uses Python’s built-in `tkinter`).

---

## Tab 1: Analysis Wizard

**Purpose:** Define assembly constraints (type, location, orientation), then “run” analysis. In the real add-in, the user would pick these from the CAD model; here you type numbers or use the Select buttons.

### What you see

- **Table** with columns:
  - **Type** — constraint type (e.g. Point).
  - **Location (x, y, z)** — position of the contact point.
  - **Orientation (nx, ny, nz)** — unit normal (or axis for a pin).
  - **Select Loc** / **Select Orient** — demo “Select” buttons.

- **Buttons:**
  - **Add constraint** — adds a new row to the table.
  - **Remove selected** — deletes the selected row.
  - **Analyze** — writes the constraint set to a JSON file and shows the path.

### How to use it (for the meeting)

1. **Add constraints:** Click **Add constraint** once or twice so you have 1–2 rows.
2. **Fill location/orientation** (either way):
   - **Option A:** Double‑click a row’s **Select Loc** cell → a message explains “in Inventor you’d pick from the model” → OK → the demo fills placeholder numbers (e.g. `1.0, 2.0, 3.0` and `0.0, 0.0, 1.0`).
   - **Option B:** Click in the **Location** or **Orientation** cell and type numbers, e.g. `0, 0, 4` and `0, 0, -1` (one point on the z‑axis, normal down).
3. **Analyze:** Click **Analyze**. The status text will say something like:  
   `Input file written to: /home/.../KstAnalysis/wizard_input.json`  
   and note that in the add-in, MATLAB (or a compiled exe) would run and show WTR, MTR, TOR.

**Takeaway for supervisor:** “This is the Constraint Definition Wizard. The user defines constraints; in Inventor they’d pick location and orientation from the model. Clicking Analyze produces the input file that the analysis script uses.”

---

## Tab 2: Optimization Wizard

**Purpose:** Choose **which constraint** to vary (e.g. CP7), define a **search** (e.g. line with 5 steps), generate an **optimization plan** (JSON), and optionally **load results** after running MATLAB.

### What you see

- **Constraint** — dropdown CP1–CP24 (which constraint to optimize).
- **Search space** — Line, Discrete, Orient 1D, Orient 2D (Line is the main demo).
- **Steps** — number of points along the line (e.g. 5).
- **Line origin (x,y,z)** and **Line direction (x,y,z)** — for a line search (e.g. `0, 0, 4` and `0, 0, 1` = move along z from 4).

- **Buttons:**
  - **Generate optimization plan** — builds a JSON that describes “optimize this constraint along this line with this many steps” and writes `wizard_optimization.json` to `~/KstAnalysis/`. Uses the analysis input from Tab 1 if it exists.
  - **Run optimization** — shows a message: “Run in MATLAB: run_wizard_optimization('.../wizard_optimization.json'); results in results_wizard_optim.txt. Then click Load results.”
  - **Load results** — reads `results_wizard_optim.txt` (candidate number, WTR, MTR, TOR per row) and fills the **results table** below.

### How to use it (for the meeting)

1. **Constraint:** Leave as CP7 (or pick another).
2. **Search space:** Line. **Steps:** 5. **Line origin:** `0, 0, 4`. **Line direction:** `0, 0, 1`.
3. Click **Generate optimization plan**. Status shows the path to `wizard_optimization.json`.
4. Click **Run optimization** → message explains: run MATLAB with that file, then come back and click **Load results**.
5. **If you’ve already run MATLAB** (from the repo: `run_wizard_optimization('.../wizard_optimization.json')`) and `results_wizard_optim.txt` is in `~/KstAnalysis/`, click **Load results** to show the table (candidate, WTR, MTR, TOR).

**Takeaway for supervisor:** “This is the Optimization Wizard. We select which constraint to optimize and how (e.g. line search, 5 steps). The wizard writes an optimization plan. MATLAB runs it and writes results; we load them here. In the add-in, we’d trigger MATLAB or a compiled exe from this same UI.”

---

## Where files go

All demo output goes under your home directory:

- **`~/KstAnalysis/wizard_input.json`** — from Analysis Wizard → Analyze (constraint set for one-shot analysis).
- **`~/KstAnalysis/wizard_optimization.json`** — from Optimization Wizard → Generate optimization plan (constraint set + which constraint to vary + candidate matrix).
- **`~/KstAnalysis/results_wizard_optim.txt`** — written by MATLAB when you run `run_wizard_optimization.m`; Optimization Wizard → Load results reads this.

---

## One-page summary for the meeting

| What | Where | Purpose |
|------|--------|--------|
| **Wizard demo** | `python scripts/wizard_demo.py` | Show the two wizards (Analysis + Optimization) without Inventor. |
| **Analysis Wizard** | Tab 1 | Define constraints (table + Select); Analyze → writes `wizard_input.json`. In Inventor: pick from model. |
| **Optimization Wizard** | Tab 2 | Pick constraint (e.g. CP7), line search, steps → Generate plan → `wizard_optimization.json`. Run optimization (MATLAB) → Load results → table of WTR/MTR/TOR per candidate. |
| **Output folder** | `~/KstAnalysis/` | `wizard_input.json`, `wizard_optimization.json`, `results_wizard_optim.txt`. |
| **Real add-in** | `inventor_addin/` (C#) | Same flow inside Inventor; geometry from CAD; can call MATLAB or compiled exe. |

**Message for supervisor:** “This demo shows the UI flow we’re building for the Inventor add-in: define constraints for analysis, then optionally set up and run constraint optimization and view results. The real add-in will run inside Inventor and read geometry from the model; the analysis/optimization backend is the same MATLAB (or compiled) code we already have.”
