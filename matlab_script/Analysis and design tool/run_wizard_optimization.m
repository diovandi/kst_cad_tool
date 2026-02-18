% Run optimization from generic JSON that contains analysis_input + optimization.candidate_matrix.
% Uses base motion set isolation: only motion sets involving the modified constraint are recomputed.
%
% Usage: run_wizard_optimization('path/to/generic_example_optimization.json'[, output_path])
% Output: writes WTR, MTR, TOR per candidate to output_path (default: results_wizard_optim.txt).

function run_wizard_optimization(json_path, output_path)
if nargin < 2
    output_path = fullfile(fileparts(json_path), 'results_wizard_optim.txt');
end

script_dir = fileparts(mfilename('fullpath'));
cd(script_dir);

global cp cpin clin cpln cpln_prop no_cp no_cpin no_clin no_cpln total_cp
global combo combo_proc_org combo_dup_idx combo_dup_idx_org mot_half_org mot_all_org no_mot_half
global Ri wr_all
global wrench_proc

% Load analysis part only (constraint set)
load_generic_input(json_path);
inputfile_check;
if exist('inputfile_ok', 'var') && ~inputfile_ok
    error('Input file check failed: %s', inputfile_error);
end
input_preproc;
[wr_all, ~, ~] = cp_to_wrench(cp, cpin, clin, cpln, cpln_prop);
[combo] = combo_preproc(total_cp, 'original');
[mot_half_org, Ri, combo_proc_org, ~, ~] = main_loop(combo, wr_all, 0, 'original');
mot_half_rev = [-mot_half_org(:,1:6), mot_half_org(:,7:10)];
mot_all_org = [mot_half_org; mot_half_rev];
Ri = 1 ./ Ri;
Ri = round(Ri .* 1e4) .* 1e-4;
[mot_all_org, uniq_idx] = unique(mot_all_org, 'rows', 'first');
Ri = Ri(uniq_idx, :);
no_mot_half = size(combo_proc_org, 1);
combo_dup_idx_org = combo_dup_idx;  % required by get_base_motion_set / optim_rev_from_candidates

% Load optimization plan from JSON
raw = fileread(json_path);
data = jsondecode(raw);
if ~isfield(data, 'optimization') || ~isfield(data.optimization, 'candidate_matrix')
    error('JSON must contain optimization.candidate_matrix');
end
cm = data.optimization.candidate_matrix;
if iscell(cm), e1 = cm{1}; else, e1 = cm(1); end
constraint_index = e1.constraint_index;
cand = e1.candidates;
if iscell(cand)
    candidate_matrix = cell2mat(cellfun(@(r) reshape(r,1,[]), cand, 'UniformOutput', false));
else
    candidate_matrix = cand;
end
cp_rev_all = constraint_index;

[WTR_all, MTR_all, TOR_all] = optim_rev_from_candidates(cp_rev_all, candidate_matrix);

fid = fopen(output_path, 'w');
fprintf(fid, 'candidate\tWTR\tMTR\tTOR\n');
for k = 1:length(WTR_all)
    fprintf(fid, '%d\t%.6g\t%.6g\t%.6g\n', k, WTR_all(k), MTR_all(k), TOR_all(k));
end
fclose(fid);
fprintf('Optimization results written to %s\n', output_path);
end
