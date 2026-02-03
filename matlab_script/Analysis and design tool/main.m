% Kinematic Constraint Analysis and Synthesis for Mechanical Part Assembly
% filename: main.m
% Purpose: Analyze and optimize mechanical assembly constraint configuration
%
% Called functions: inputfile_check, input_preproc, cp_to_wrench, combo_preproc,
%                   main_loop, rating, result_open, histogr, result_close,
%                   report, optim_main_rev, optim_main_red, optim_postproc,
%                   sens_analysis_pos, sens_analysis_orient, main_specmot_orig
% 
% Copyright 2008 Leonard Rusli
% The Ohio State University

clc
clear variables
clear global

% Initialize variables

global cp cpin clin cpln cpln_prop no_cp no_cpin no_clin no_cpln total_cp
global grp_members grp_rev_type grp_srch_spc
global combo combo_proc_org wrench_proc input_wr_proc d_proc
global timestart 
global wr_all combo_dup_idx
global pts max_d

% Request input file from user
[cp, cpin, clin, cpln, cpln_prop, inputfile,...
    grp_members, grp_rev_type, grp_srch_spc,...
    add_cp_type, add_cp]=input_menu();

% Time stamp for stop watch
tic % Start stopwatch to measure elapsed time
timestart=clock; 

clc
disp('Initializing input file...')

% Check for input file for consistency & format
inputfile_check
if inputfile_ok==false
    disp(inputfile_error)
    return
end

% Input file preprocessor to normalize constraint normal vector and count number of constraints for each type
input_preproc

% Transform constraints into wrenches
[wr_all pts max_d]=cp_to_wrench(cp,cpin,clin,cpln,cpln_prop);

% Create combination scheme for composing pivot constraint sets
[combo]=combo_preproc(total_cp,'original');

% Main for-loop subroutine to process pivot constraint sets
clc
[mot_half R combo_proc_org input_wr_proc_org ...
    d_proc_org]=main_loop(combo,wr_all,1,'original');

% Stop further analysis if there is no evaluated motion
if size(mot_half,1)==0
    clc;fprintf('There is no motion to be evaluated. \n');
    return
end

fprintf('Calculating final ratings... \n')

% Motion post-processing
mot_half_rev=[-mot_half(:,1:6) mot_half(:,7:10)]; % Inverse om and mu to get reverse motion
mot_half_org=mot_half; % Store evaluated motions from original/baseline analysis
combo_dup_idx_org=combo_dup_idx; % Keep track duplicate motion references
mot_all_org=[mot_half;mot_half_rev]; % Merge forward and reverse motion
no_mot_half=size(combo_proc_org,1); % Count the number of half-duplex/forward motion only
no_mot=size(mot_all_org,1); % Count the number of total motion in original/baseline set

% Rating post-processing
Ri=1./R;
Ri=(round(Ri.*1e4)).*1e-4; % Round rating matrix values to 4 decimal places

%  Remove duplicate motions
[mot_all_org_uniq uniq_idx]=unique(mot_all_org,'rows'); % Identify and remove extra duplicate motion
Ri_uniq=Ri(uniq_idx,:); % Remove rating matrix rows affiliated with duplicate motion

% Calculate overall assembly ratings
[Rating_all_org WTR_idx_org free_mot free_mot_idx best_cp rowsum]=rating(Ri_uniq, mot_all_org_uniq);

% Generate analysis report 
[result]=result_open(inputfile); % Open result file for writing
report % Write report in result file

% Plot total resistance histogram
histogr(Rating_all_org, rowsum)

result_close % Close results file

toc % Stop stopwatch and display elapsed time

% Show design optimization menu
fprintf('\n0. Skip optimization')
fprintf('\n1. Constraint revision')
fprintf('\n2. Constraint reduction')
fprintf('\n3. Constraint addition')
fprintf('\n4. Sensitivity analysis position')
fprintf('\n5. Sensitivity analysis orientation')
fprintf('\n6. Known loading condition study\n\n')
optim_type = input('Run which type of optimization? ');

tic; % Start stopwatch to measure optimization elapsed time

if optim_type == 1
    no_step=input('How many steps for each variable? '); % Prompt user input for optimization search resolution
    optim_main_rev % Start constraint modification optimization routine
    optim_postproc(no_step,no_dim, WTR_optim_chg, MRR_optim_chg,...
        MTR_optim_chg, TOR_optim_chg,inputfile)
elseif optim_type == 2
    no_red=input('How many constraints to remove at a time? ');
    optim_main_red % Start constraint reduction optimization routine
elseif optim_type == 3
    disp('THE optim_main_add.m PRELIMINARY CODE CONTAINS ERRORS. IN THE DISSERTATION CONSTRAINT ADDITION IS STILL DONE MANUALLY.')
%     optim_main_add % Start constraint addition optimization routine
elseif optim_type == 4
    sens_analysis_pos % Start position sensitivity analysis routine
elseif optim_type == 5
    sens_analysis_orient % Start orientation sensitivity analysis routine
elseif optim_type == 6
    % Prompt user input for specified loading condition screw axis
    mot_input=input('Specify loading screw axis (0 for mot_set): '); 
    if mot_input==0
        specmot=mot_set; % Use variable mot_set if multiple loading screw axis is defined
    else
        specmot=mot_all_org_uniq(mot_input,:); % Use selected motion from evaluated set
    end
    [Ri_spec_mot mot_proc]=main_specmot_orig(specmot) % Start specified loading condition routine
else
    disp('Optimization skipped');
end

fprintf('Calculation done.\n'); toc; % Display optimization elapsed time

save(inputfile) % Store workspace as 'inputfile'.mat

