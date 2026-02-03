% Batch driver for KST analysis: run one case without interactive prompts.
% Usage: from matlab_script directory: octave --no-gui run_case_batch.m <case_number>
% Example: octave --no-gui run_case_batch.m 1
% Writes WTR, MRR, MTR, TOR to results_octave_<casename>.txt for comparison.

1;  % Prevent Octave from treating this as a function file

% Paths relative to this script (works from any cwd)
script_dir = fileparts(mfilename('fullpath'));
addpath(fullfile(script_dir, 'Analysis and design tool'));
addpath(fullfile(script_dir, 'Input_files'));

% Get case number from first command-line argument
args = argv();
if isempty(args)
  error('Usage: octave run_case_batch.m <case_number> (e.g. 1 for case1a_chair_height)');
end
cp_set = str2double(args{1});
if isnan(cp_set) || cp_set < 1 || cp_set > 21
  error('Case number must be 1..21');
end

% Initialize globals (same as main.m)
global cp cpin clin cpln cpln_prop no_cp no_cpin no_clin no_cpln total_cp
global grp_members grp_rev_type grp_srch_spc
global combo combo_proc_org wrench_proc input_wr_proc d_proc
global wr_all combo_dup_idx
global pts max_d

% Defaults so case script only needs to set cp (and optionally grp_*)
cp = []; cpin = []; clin = []; cpln = []; cpln_prop = [];
grp_members = []; grp_rev_type = []; grp_srch_spc = [];

% Case labels (match input_menu.m)
f1  = 'case1a_chair_height';
f2  = 'case1b_chair_height_angle';
f3  = 'case2a_cube_scalability';
f4  = 'case2b_cube_tradeoff';
f5  = 'case3a_cover_leverage';
f6  = 'case3b_cover_symmetry';
f7  = 'case3c_cover_orient';
f8  = 'case4a_endcap_tradeoff';
f9  = 'case4b_endcap_circlinsrch';
f10 = 'case5a_printer_4screws_orient';
f11 = 'case5b_printer_4screws_line';
f12 = 'case5c_printer_snap_orient';
f13 = 'case5d_printer_snap_line';
f14 = 'case5e_printer_partingline';
f15 = 'case5f1_printer_line_size';
f16 = 'case5f2_printer_sideline_size';
f17 = 'case5g_printer_5d';
f18 = 'case5rev_a_printer_2screws';
f19 = 'case5_printer_allscrews';
f20 = 'case5rev_d_printer_remove2_bot_screw';
f21 = 'case5rev_b_printer_flat_partingline';

% Run the selected case script (sets cp and optionally grp_*)
% For cases that use input(), set defaults first so they are not prompted
if cp_set == 3
  scale = 1;  % case2a_cube_scalability uses input('Scaling factor = ')
end
if cp_set == 8
  no_snap = 1;  % case4a_endcap_tradeoff uses input('How many snaps? ')
end

inp_dir = fullfile(script_dir, 'Input_files');
switch cp_set
  case 1,  run(fullfile(inp_dir, 'case1a_chair_height.m'));   inputfile = f1;
  case 2,  run(fullfile(inp_dir, 'case1b_chair_height_angle.m')); inputfile = f2;
  case 3,  run(fullfile(inp_dir, 'case2a_cube_scalability.m'));   inputfile = f3;
  case 4,  run(fullfile(inp_dir, 'case2b_cube_tradeoff.m'));      inputfile = f4;
  case 5,  run(fullfile(inp_dir, 'case3a_cover_leverage.m'));     inputfile = f5;
  case 6,  run(fullfile(inp_dir, 'case3b_cover_symmetry.m'));     inputfile = f6;
  case 7,  run(fullfile(inp_dir, 'case3c_cover_orient.m'));       inputfile = f7;
  case 8,  run(fullfile(inp_dir, 'case4a_endcap_tradeoff.m'));   inputfile = f8;
  case 9,  run(fullfile(inp_dir, 'case4b_endcap_circlinsrch.m')); inputfile = f9;
  case 10, run(fullfile(inp_dir, 'case5a_printer_4screws_orient.m')); inputfile = f10;
  case 11, run(fullfile(inp_dir, 'case5b_printer_4screws_line.m')); inputfile = f11;
  case 12, run(fullfile(inp_dir, 'case5c_printer_snap_orient.m')); inputfile = f12;
  case 13, run(fullfile(inp_dir, 'case5d_printer_snap_line.m')); inputfile = f13;
  case 14, run(fullfile(inp_dir, 'case5e_printer_partingline.m')); inputfile = f14;
  case 15, run(fullfile(inp_dir, 'case5f1_printer_line_size.m')); inputfile = f15;
  case 16, run(fullfile(inp_dir, 'case5f2_printer_sideline_size.m')); inputfile = f16;
  case 17, run(fullfile(inp_dir, 'case5g_printer_5d.m')); inputfile = f17;
  case 18, run(fullfile(inp_dir, 'case5rev_a_printer_2screws.m')); inputfile = f18;
  case 19, run(fullfile(inp_dir, 'case5_printer_allscrews.m')); inputfile = f19;
  case 20, run(fullfile(inp_dir, 'case5rev_d_printer_remove2_bot_screw.m')); inputfile = f20;
  case 21, run(fullfile(inp_dir, 'case5rev_b_printer_flat_partingline.m')); inputfile = f21;
end

% Ensure cpin, clin, cpln, cpln_prop exist for inputfile_check (cp-only cases leave them unset)
if isempty(cpin), cpin = []; end
if isempty(clin), clin = []; end
if isempty(cpln), cpln = []; end
if isempty(cpln_prop), cpln_prop = []; end

% Check input file
inputfile_check;
if exist('inputfile_ok','var') && inputfile_ok == false
  disp(inputfile_error);
  exit(1);
end

% Preprocess and run analysis (same sequence as main.m, no waitbar)
input_preproc;
[wr_all, pts, max_d] = cp_to_wrench(cp, cpin, clin, cpln, cpln_prop);
combo = combo_preproc(total_cp, 'original');

[mot_half, R, combo_proc_org, input_wr_proc_org, d_proc_org] = main_loop(combo, wr_all, 0, 'original');

if size(mot_half, 1) == 0
  fprintf('There is no motion to be evaluated.\n');
  exit(1);
end

% Motion post-processing (match main.m)
mot_half_rev = [-mot_half(:,1:6), mot_half(:,7:10)];
mot_all_org = [mot_half; mot_half_rev];
Ri = 1 ./ R;
Ri = round(Ri .* 1e4) .* 1e-4;
[mot_all_org_uniq, uniq_idx] = unique(mot_all_org, 'rows');
Ri_uniq = Ri(uniq_idx, :);

% Overall ratings
[Rating_all_org, WTR_idx_org, free_mot, free_mot_idx, best_cp, rowsum] = rating(Ri_uniq, mot_all_org_uniq);

% Write results for comparison (WTR, MRR, MTR, TOR)
outname = ['results_octave_', inputfile, '.txt'];
fid = fopen(outname, 'w');
if fid == -1
  error('Could not open %s for writing', outname);
end
fprintf(fid, 'WTR\t%.10g\n', Rating_all_org(1));
fprintf(fid, 'MRR\t%.10g\n', Rating_all_org(2));
fprintf(fid, 'MTR\t%.10g\n', Rating_all_org(3));
fprintf(fid, 'TOR\t%.10g\n', Rating_all_org(4));
fclose(fid);
fprintf('Wrote %s (WTR=%.4f, MRR=%.4f, MTR=%.4f, TOR=%.4f)\n', ...
  outname, Rating_all_org(1), Rating_all_org(2), Rating_all_org(3), Rating_all_org(4));
