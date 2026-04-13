# MATLAB Integration with the Inventor Add-in

The Analysis Wizard generates a **generic JSON input file**. To run analysis from the add-in, you can either call MATLAB or a compiled standalone executable.

---

## Option A: Invoke MATLAB process

From the add-in (C#), start MATLAB in batch mode and run a script that:

1. Calls `load_generic_input('<path_to_json>')`
2. Runs `inputfile_check`, `input_preproc`, `cp_to_wrench`, `combo_preproc`, `main_loop`, rating
3. Writes results to a file (e.g. `results_wizard.txt` or `.mat`)

Example batch script (e.g. `run_wizard_analysis.m`):

```matlab
function run_wizard_analysis(input_path, output_path)
if nargin < 2, output_path = 'results_wizard.txt'; end
cd(fileparts(which('main.m')));  % or your Analysis and design tool folder
load_generic_input(input_path);
inputfile_check;
if ~inputfile_ok, error(inputfile_error); end
input_preproc;
% ... rest of main.m flow (cp_to_wrench, main_loop, rating, write output)
% Write WTR, MTR, TOR to output_path
end
```

From C#:

```csharp
var startInfo = new ProcessStartInfo
{
    FileName = "matlab.exe",
    Arguments = $"-batch \"run_wizard_analysis('{inputPath}', '{outputPath}')\"",
    WorkingDirectory = matlabScriptDir
};
Process.Start(startInfo);
```

You need to set `matlabScriptDir` to the folder containing `main.m`, `load_generic_input.m`, etc., and ensure `matlab.exe` is on the PATH or use its full path.

---

## Option B: MATLAB Engine API for .NET

Use the **MATLAB Engine API for .NET** so the add-in calls MATLAB in-process (no separate process). This requires:

- MATLAB or MATLAB Runtime installed
- Reference to `MatLab.Engine.dll` (from MATLAB installation)
- Start engine, evaluate `load_generic_input(...)` and the analysis sequence, then read results back.

See MathWorks documentation: “Call MATLAB from .NET”.

---

## Option C: Compiled standalone executable

After using **MATLAB Compiler** (see [MATLAB_COMPILER.md](MATLAB_COMPILER.md)) to build a standalone executable that reads the generic JSON and writes results:

- The add-in calls that executable via `Process.Start(exePath, inputPath)`.
- No MATLAB license needed on the machine running the add-in; only the MATLAB Runtime (redistributable) is required.

---

## Result display in the wizard

Once analysis has run (by any option), read the output file (e.g. WTR, MTR, TOR, RI) and display them in the wizard’s results area (e.g. `_lblResults` or a dedicated results grid).
