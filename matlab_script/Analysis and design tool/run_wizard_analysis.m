% Run analysis from a generic JSON input file (e.g. from the Inventor wizard).
% Usage (from MATLAB command line or -batch):
%   run_wizard_analysis('path/to/wizard_input.json')
%   run_wizard_analysis('path/to/wizard_input.json', 'path/to/results.txt')
%
% Called by the add-in when invoking MATLAB process (Option A in MATLAB_INTEGRATION.md).

function run_wizard_analysis(input_path, output_path)
if nargin < 1
    error('Usage: run_wizard_analysis(input_path [, output_path])');
end
if nargin < 2
    output_path = fullfile(fileparts(input_path), 'results_wizard.txt');
end

% Ensure we are in the Analysis and design tool directory so globals and helpers are available
script_dir = fileparts(mfilename('fullpath'));
cd(script_dir);

% Declare globals used by main flow
global cp cpin clin cpln cpln_prop no_cp no_cpin no_clin no_cpln total_cp
global grp_members grp_rev_type grp_srch_spc
global combo combo_proc_org wrench_proc input_wr_proc d_proc
global wr_all combo_dup_idx pts max_d

grp_members = [];
grp_rev_type = [];
grp_srch_spc = [];

% Load generic input
load_generic_input(input_path);

% Check and preprocess
inputfile_check;
if exist('inputfile_ok', 'var') && inputfile_ok == false
    error('Input file check failed: %s', inputfile_error);
end
input_preproc;

% Build wrenches and run main loop (same as main.m)
[wr_all, pts, max_d] = cp_to_wrench(cp, cpin, clin, cpln, cpln_prop);
[combo] = combo_preproc(total_cp, 'original');
[mot_half, R, combo_proc_org, input_wr_proc_org, d_proc_org] = main_loop(combo, wr_all, 1, 'original');

if size(mot_half, 1) == 0
    fid = fopen(output_path, 'w');
    fprintf(fid, 'No motion to evaluate.\n');
    fclose(fid);
    return;
end

% Rating (simplified: WTR, MTR, TOR)
mot_half_rev = [-mot_half(:,1:6), mot_half(:,7:10)];
mot_all = [mot_half; mot_half_rev];
[mot_uniq, ~] = unique(mot_all, 'rows');
Ri = 1 ./ R;
Ri = round(Ri .* 1e4) .* 1e-4;
[~, wtr_idx] = min(R);
WTR = R(wtr_idx);
MTR = max(R);
TOR = sum(R) / numel(R);

% Write summary to output file
fid = fopen(output_path, 'w');
fprintf(fid, 'WTR\t%.6g\n', WTR);
fprintf(fid, 'MTR\t%.6g\n', MTR);
fprintf(fid, 'TOR\t%.6g\n', TOR);
fprintf(fid, 'no_mot_unique\t%d\n', size(mot_uniq, 1));
fclose(fid);
end
