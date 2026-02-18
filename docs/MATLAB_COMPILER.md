# MATLAB Compiler / Coder for KST Analysis

Investigating compiling the analysis pipeline to C or a standalone executable to speed up runs and allow the Inventor add-in to call an exe without a MATLAB license.

---

## Tools

- **MATLAB Compiler (mcc)** – Compiles M-files to a standalone application or shared library. Requires **MATLAB Compiler** license. Output runs on **MATLAB Runtime** (redistributable, no full MATLAB license).
- **MATLAB Coder** – Generates C/C++ from M-code. For deployment as a library or integration into other C/C++ apps. Different from Compiler: Coder produces source code; Compiler produces an executable that uses the Runtime.

For the add-in, **MATLAB Compiler** is the natural choice: produce a `.exe` that reads the generic JSON input and writes results; the add-in calls this exe via `Process.Start`.

---

## Workflow (MATLAB Compiler)

1. **Entry point:** A single M-function that:
   - Takes one argument: path to the generic JSON input file (and optionally output path).
   - Calls `load_generic_input`, `inputfile_check`, `input_preproc`, `cp_to_wrench`, `combo_preproc`, `main_loop`, then rating logic.
   - Writes WTR, MTR, TOR (and optionally full report) to an output file.
   - Example: use or adapt [run_wizard_analysis.m](../matlab_script/Analysis%20and%20design%20tool/run_wizard_analysis.m).

2. **Compile (from MATLAB):**
   ```matlab
   mcc -m run_wizard_analysis.m -a 'Analysis and design tool' -o kst_analysis_exe
   ```
   This bundles the script and the “Analysis and design tool” folder (so all called .m files are included). Output: `kst_analysis_exe.exe` (and possibly a folder of CTF files).

3. **Run:** On a machine with **MATLAB Runtime** installed:
   ```bat
   kst_analysis_exe.exe path\to\wizard_input.json path\to\results.txt
   ```

4. **Benchmark:** Run the same case (e.g. case1a chair) with:
   - Interpreted: `run_wizard_analysis('generic_example_analysis.json', 'out.txt');` from MATLAB.
   - Compiled: run the exe with the same JSON and output path.
   Compare execution time (e.g. with `tic`/`toc` in MATLAB and a timer around the exe in a script).

---

## Limitations

- **Global variables:** The current script relies heavily on globals. Compiler supports globals, but the entry-point function and all called functions must be compatible (no dynamic `eval` of variable names that refer to globals in unsupported ways).
- **File I/O:** `jsondecode` is supported in Compiler for supported MATLAB versions.
- **Path:** All dependencies (other .m files) must be on the path or added via `-a`. The `-a 'Analysis and design tool'` adds that directory.

---

## Reference

- MathWorks: “MATLAB Compiler” and “Deploy Applications with MATLAB Compiler”.
- MATLAB 2018b: `mcc -m` and `doc mcc`.
