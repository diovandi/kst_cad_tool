% Benchmark: time run_wizard_analysis on a generic input (e.g. Thompson's chair).
% Run from matlab_script/ directory. Compare this time to compiled exe run time.
%
% Usage: benchmark_wizard_analysis

script_dir = fileparts(mfilename('fullpath'));
input_path = fullfile(script_dir, 'Input_files', 'generic_example_analysis.json');
output_path = fullfile(script_dir, 'results_benchmark_wizard.txt');

addpath(fullfile(script_dir, 'Analysis and design tool'));
tic;
run_wizard_analysis(input_path, output_path);
elapsed = toc;
fprintf('run_wizard_analysis elapsed: %.3f s\n', elapsed);
